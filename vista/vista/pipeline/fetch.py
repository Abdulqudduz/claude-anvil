"""Download OA PDFs to the local cache.

URLs come from third-party metadata (OpenAlex `pdf_url` / `oa_url`), so every
download is bounded: http(s) only, no hop (including redirects) to a private,
loopback, link-local, or otherwise non-public address, a byte cap, and an
overall wall-clock deadline on top of httpx's per-read timeout.

The address check is enforced where the socket is opened: `PublicOnlyBackend`
(an httpcore network backend) resolves the host, rejects it unless every
address is public, and connects to a checked IP. TLS SNI, certificate
verification, and the Host header still use the hostname, because httpcore
takes those from the request origin, not from the connect target. So a DNS
answer that changes between a check and the connect (rebinding) cannot
redirect the connection.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
import time
from pathlib import Path

import httpcore
import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from vista import config
from vista.net import is_transient
from vista.storage.db import Store

log = logging.getLogger(__name__)

MAX_PDF_BYTES = 50 * 1024 * 1024
DOWNLOAD_DEADLINE_SECONDS = 120.0
MAX_REDIRECTS = 5
READ_TIMEOUT_SECONDS = 60.0

# Indirections so tests can stub DNS, the clock, and backoff waits.
_sleep = time.sleep
_monotonic = time.monotonic


def _resolve(host: str) -> list[str]:
    return [info[4][0] for info in socket.getaddrinfo(host, None)]


class FetchRejected(Exception):
    """A download refused by policy (scheme, address, size, deadline). Not retried."""


def public_addresses(host: str) -> list[str]:
    """The host's addresses, if every one is globally routable; else FetchRejected.

    Raises httpcore.ConnectError when the name does not resolve, which httpx
    maps to the (retryable) httpx.ConnectError.
    """
    try:
        addrs = [host] if _is_ip_literal(host) else _resolve(host)
    except OSError as e:
        raise httpcore.ConnectError(f"cannot resolve {host}: {e}") from e
    if not addrs:
        raise httpcore.ConnectError(f"no addresses for {host}")
    for a in addrs:
        if not ipaddress.ip_address(a.split("%", 1)[0]).is_global:
            raise FetchRejected(f"{host} resolves to non-public address {a}")
    return addrs


class PublicOnlyBackend(httpcore.NetworkBackend):
    """Connects only to checked, public addresses (see the module docstring)."""

    def __init__(self, inner: httpcore.NetworkBackend | None = None):
        self._inner = inner or httpcore.SyncBackend()

    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        last: Exception | None = None
        for ip in public_addresses(host):
            try:
                return self._inner.connect_tcp(ip, port, timeout=timeout,
                                               local_address=local_address,
                                               socket_options=socket_options)
            except httpcore.ConnectError as e:  # try the next checked address
                last = e
        raise last  # type: ignore[misc]

    def connect_unix_socket(self, path, timeout=None, socket_options=None):
        raise FetchRejected("unix sockets are not allowed")

    def sleep(self, seconds: float) -> None:
        self._inner.sleep(seconds)


class PublicOnlyTransport(httpx.HTTPTransport):
    """httpx's standard transport, with its connection pool on PublicOnlyBackend.

    httpx exposes no network_backend option, so the pool is rebuilt here with
    the same defaults httpx uses (TLS verification on, HTTP/1.1, no proxies).
    The `_pool` attribute is httpx-internal; tests exercise a real connect
    through this class, so an httpx upgrade that changes it fails loudly.
    """

    def __init__(self) -> None:
        super().__init__()
        self._pool = httpcore.ConnectionPool(
            ssl_context=httpx.create_ssl_context(),
            network_backend=PublicOnlyBackend(),
        )


def pdf_client(*, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    """The one HTTP client factory for PDF downloads (CLI, MCP, live path).

    Tests inject a MockTransport; real use always goes through
    PublicOnlyTransport (passing a transport also disables env proxies).
    """
    return httpx.Client(
        headers={"User-Agent": config.USER_AGENT, "Accept": "application/pdf,*/*"},
        timeout=READ_TIMEOUT_SECONDS,
        transport=transport or PublicOnlyTransport(),
    )


def _check_url(url: httpx.URL) -> None:
    """Fail fast before a request: scheme, and the host's current addresses.

    PublicOnlyBackend repeats the address check at connect time, which is
    the check that actually binds the connection.
    """
    if url.scheme not in ("http", "https"):
        raise FetchRejected(f"scheme {url.scheme!r} not allowed: {url}")
    if not url.host:
        raise FetchRejected(f"no host in {url}")
    try:
        public_addresses(url.host)
    except httpcore.ConnectError as e:
        raise httpx.ConnectError(str(e)) from e


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _pdf_path_for(paper_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", paper_id)
    return config.PDF_DIR / f"{safe}.pdf"


def _candidate_urls(row) -> list[str]:
    urls = [
        f"https://arxiv.org/pdf/{row['arxiv_id']}.pdf" if row["arxiv_id"] else None,
        row["pdf_url"],
        row["oa_url"],
    ]
    return list(dict.fromkeys(u for u in urls if u))  # dedup, keep order


@retry(
    retry=retry_if_exception(is_transient),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
    sleep=lambda seconds: _sleep(seconds),
    reraise=True,
)
def _download(url: str, dest: Path, client: httpx.Client) -> bool:
    """Fetch one URL to `dest`. False if the response is not a PDF.

    Raises FetchRejected on a policy violation, httpx errors otherwise
    (transient ones are retried by the decorator; other 4xx are not).
    """
    deadline = _monotonic() + DOWNLOAD_DEADLINE_SECONDS
    target = httpx.URL(url)
    for _ in range(MAX_REDIRECTS + 1):
        _check_url(target)
        with client.stream("GET", target, follow_redirects=False) as r:
            if r.is_redirect:
                target = target.join(r.headers["location"])
                continue
            r.raise_for_status()
            ctype = r.headers.get("content-type", "").lower()
            # Some servers return HTML for paywalled content with 200 OK.
            if "pdf" not in ctype and not target.path.endswith(".pdf"):
                log.warning("non-PDF content-type from %s: %s", target, ctype)
                return False
            declared = r.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > MAX_PDF_BYTES:
                raise FetchRejected(f"{target}: {declared} bytes exceeds {MAX_PDF_BYTES}")
            return _write_capped(r, dest, deadline, target)
    raise FetchRejected(f"more than {MAX_REDIRECTS} redirects from {url}")


def _write_capped(r: httpx.Response, dest: Path, deadline: float, url: httpx.URL) -> bool:
    tmp = dest.with_suffix(dest.suffix + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with open(tmp, "wb") as fh:
            for chunk in r.iter_bytes():
                total += len(chunk)
                if total > MAX_PDF_BYTES:
                    raise FetchRejected(f"{url}: body exceeds {MAX_PDF_BYTES} bytes")
                if _monotonic() > deadline:
                    raise FetchRejected(f"{url}: exceeded {DOWNLOAD_DEADLINE_SECONDS}s deadline")
                fh.write(chunk)
        with open(tmp, "rb") as fh:
            head = fh.read(8)
        if not head.startswith(b"%PDF"):
            log.warning("downloaded file is not a PDF: %s (head=%r)", url, head)
            tmp.unlink(missing_ok=True)
            return False
        tmp.replace(dest)
        return True
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def fetch_pdf(row, *, client: httpx.Client) -> Path | None:
    dest = _pdf_path_for(row["id"])
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    for url in _candidate_urls(row):
        log.info("fetching %s -> %s", url, dest.name)
        try:
            if _download(url, dest, client):
                return dest
        except (httpx.HTTPError, FetchRejected, OSError) as e:
            log.warning("failed %s: %s", url, e)
    return None


def fetch_and_record(store: Store, row, *, client: httpx.Client) -> Path | None:
    """Fetch a paper's PDF and record success or failure on its row."""
    path = fetch_pdf(row, client=client)
    if path:
        store.mark_fetched(row["id"], str(path))
    else:
        store.mark_fetch_failed(row["id"])
    return path


def run_fetch(store: Store, *, max_papers: int | None = None,
              retry_failed: bool = False) -> dict[str, int]:
    if retry_failed:
        store.clear_fetch_failures()
    rows = store.papers(needs_pdf=True)
    if max_papers:
        rows = rows[:max_papers]
    out = {"attempted": 0, "ok": 0, "failed": 0}
    with pdf_client() as client:
        for row in rows:
            out["attempted"] += 1
            out["ok" if fetch_and_record(store, row, client=client) else "failed"] += 1
    return out
