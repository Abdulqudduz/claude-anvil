"""PDF download policy: retries, size cap, deadline, address and scheme checks.

Offline: requests go through httpx.MockTransport, DNS is stubbed, and backoff
sleeps are recorded instead of slept.
"""

import httpx
import pytest

from vista import config
from vista.pipeline import fetch
from vista.pipeline.fetch import FetchRejected, _download, fetch_pdf, pdf_client, run_fetch
from vista.storage.db import Paper, Store

PDF = b"%PDF-1.4\n" + b"x" * 100
PUBLIC = "93.184.216.34"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    waits: list[float] = []
    monkeypatch.setattr(fetch, "_sleep", waits.append)
    hosts = {"internal.example": ["10.0.0.5"], "v6local.example": ["::1"]}
    monkeypatch.setattr(fetch, "_resolve", lambda host: hosts.get(host, [PUBLIC]))
    return waits


def scripted(*responses):
    requests: list[httpx.Request] = []
    queue = list(responses)

    def handler(request):
        requests.append(request)
        r = queue.pop(0)
        return r(request) if callable(r) else r

    return pdf_client(transport=httpx.MockTransport(handler)), requests


def pdf_response(body=PDF, **headers):
    return httpx.Response(200, content=body,
                          headers={"content-type": "application/pdf", **headers})


def test_success_writes_file(tmp_path):
    client, reqs = scripted(pdf_response())
    dest = tmp_path / "a.pdf"
    assert _download("https://arxiv.org/pdf/1.pdf", dest, client)
    assert dest.read_bytes() == PDF
    assert reqs[0].headers["User-Agent"] == config.USER_AGENT


def test_404_is_not_retried(tmp_path, offline):
    client, reqs = scripted(httpx.Response(404))
    with pytest.raises(httpx.HTTPStatusError):
        _download("https://example.org/a.pdf", tmp_path / "a.pdf", client)
    assert len(reqs) == 1 and offline == []


def test_403_paywall_is_not_retried(tmp_path):
    client, reqs = scripted(httpx.Response(403))
    with pytest.raises(httpx.HTTPStatusError):
        _download("https://example.org/a.pdf", tmp_path / "a.pdf", client)
    assert len(reqs) == 1


def test_5xx_is_retried_then_succeeds(tmp_path, offline):
    client, reqs = scripted(httpx.Response(503), pdf_response())
    assert _download("https://example.org/a.pdf", tmp_path / "a.pdf", client)
    assert len(reqs) == 2 and len(offline) == 1


def test_html_body_is_not_a_pdf(tmp_path):
    client, _ = scripted(httpx.Response(200, content=b"<html>paywall</html>",
                                        headers={"content-type": "text/html"}))
    assert _download("https://example.org/landing", tmp_path / "a.pdf", client) is False


def test_pdf_content_type_with_html_body_is_rejected(tmp_path):
    client, _ = scripted(pdf_response(body=b"<html>nope</html>"))
    dest = tmp_path / "a.pdf"
    assert _download("https://example.org/a.pdf", dest, client) is False
    assert not dest.exists() and not (tmp_path / "a.pdf.part").exists()


def test_declared_size_over_cap_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "MAX_PDF_BYTES", 50)
    client, _ = scripted(pdf_response(**{"content-length": "51"}))
    with pytest.raises(FetchRejected, match="exceeds"):
        _download("https://example.org/a.pdf", tmp_path / "a.pdf", client)


def test_streamed_size_over_cap_is_rejected_and_cleaned(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "MAX_PDF_BYTES", 50)

    def chunked(request):  # no content-length header: size known only while streaming
        return httpx.Response(200, headers={"content-type": "application/pdf"},
                              stream=httpx.ByteStream(PDF))

    client, _ = scripted(chunked)
    dest = tmp_path / "a.pdf"
    with pytest.raises(FetchRejected):
        _download("https://example.org/a.pdf", dest, client)
    assert not dest.exists() and not (tmp_path / "a.pdf.part").exists()


def test_overall_deadline(tmp_path, monkeypatch):
    clock = iter([0.0, fetch.DOWNLOAD_DEADLINE_SECONDS + 1])
    monkeypatch.setattr(fetch, "_monotonic", lambda: next(clock))
    client, _ = scripted(pdf_response())
    with pytest.raises(FetchRejected, match="deadline"):
        _download("https://example.org/a.pdf", tmp_path / "a.pdf", client)


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ftp://example.org/a.pdf",
    "http://127.0.0.1/a.pdf",
    "http://169.254.169.254/latest/meta-data",
    "http://[::1]/a.pdf",
    "http://internal.example/a.pdf",
    "http://v6local.example/a.pdf",
])
def test_non_public_or_non_http_urls_are_rejected(tmp_path, url):
    client, reqs = scripted()
    with pytest.raises(FetchRejected):
        _download(url, tmp_path / "a.pdf", client)
    assert reqs == [], "rejected before any request"


def test_redirect_to_private_address_is_rejected(tmp_path):
    client, reqs = scripted(httpx.Response(302, headers={"location": "http://10.1.2.3/x.pdf"}))
    with pytest.raises(FetchRejected):
        _download("https://example.org/a.pdf", tmp_path / "a.pdf", client)
    assert len(reqs) == 1


def test_public_redirect_is_followed(tmp_path):
    client, reqs = scripted(httpx.Response(301, headers={"location": "/real.pdf"}), pdf_response())
    assert _download("https://example.org/a.pdf", tmp_path / "a.pdf", client)
    assert str(reqs[1].url) == "https://example.org/real.pdf"


def test_redirect_loop_is_bounded(tmp_path):
    loop = httpx.Response(302, headers={"location": "https://example.org/a.pdf"})
    client, reqs = scripted(*[loop] * (fetch.MAX_REDIRECTS + 1))
    with pytest.raises(FetchRejected, match="redirects"):
        _download("https://example.org/a.pdf", tmp_path / "a.pdf", client)


def _row(**kw):
    base = {"id": "W1", "arxiv_id": None, "pdf_url": None, "oa_url": None}
    base.update(kw)
    return base


def test_fetch_pdf_tries_candidates_in_order():
    client, reqs = scripted(httpx.Response(404), pdf_response())
    path = fetch_pdf(_row(arxiv_id="2106.01234", pdf_url="https://example.org/p.pdf"),
                     client=client)
    assert path == config.PDF_DIR / "W1.pdf" and path.exists()
    assert [str(r.url) for r in reqs] == ["https://arxiv.org/pdf/2106.01234.pdf",
                                          "https://example.org/p.pdf"]


def test_fetch_pdf_none_when_all_fail():
    client, _ = scripted(httpx.Response(403))
    assert fetch_pdf(_row(oa_url="http://127.0.0.1/x.pdf", pdf_url="https://e.org/a.pdf"),
                     client=client) is None


def test_run_fetch_records_failure_and_skips_it_next_time(monkeypatch):
    s = Store.open(":memory:")
    s.upsert_paper(Paper(id="W1", title="T", field="ml", track="recent",
                         pdf_url="https://example.org/a.pdf"))
    queue = [httpx.Response(404), pdf_response()]
    transport = httpx.MockTransport(lambda request: queue.pop(0))
    monkeypatch.setattr(fetch, "pdf_client", lambda: pdf_client(transport=transport))
    assert run_fetch(s) == {"attempted": 1, "ok": 0, "failed": 1}
    assert run_fetch(s)["attempted"] == 0, "negative cache"
    assert run_fetch(s, retry_failed=True) == {"attempted": 1, "ok": 1, "failed": 0}
    assert s.get_paper("W1")["pdf_path"].endswith("W1.pdf")


# --- DNS pinning: the connection goes to the address that was checked --------


class RecordingBackend:
    """Stands in for httpcore's socket backend; records connect targets."""

    def __init__(self, fail_first=0):
        self.hosts: list[str] = []
        self.fail_first = fail_first

    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        import httpcore

        self.hosts.append(host)
        if len(self.hosts) <= self.fail_first:
            raise httpcore.ConnectError("refused")
        return "stream"

    def sleep(self, seconds):
        pass


def test_backend_connects_to_validated_ip_not_hostname():
    inner = RecordingBackend()
    assert fetch.PublicOnlyBackend(inner).connect_tcp("files.example", 443) == "stream"
    assert inner.hosts == [PUBLIC]


def test_backend_tries_each_validated_address(monkeypatch):
    monkeypatch.setattr(fetch, "_resolve", lambda host: [PUBLIC, "93.184.216.35"])
    inner = RecordingBackend(fail_first=1)
    fetch.PublicOnlyBackend(inner).connect_tcp("files.example", 443)
    assert inner.hosts == [PUBLIC, "93.184.216.35"]


def test_backend_rejects_private_resolution_and_unix_sockets(monkeypatch):
    monkeypatch.setattr(fetch, "_resolve", lambda host: [PUBLIC, "10.0.0.1"])
    inner = RecordingBackend()
    with pytest.raises(FetchRejected):
        fetch.PublicOnlyBackend(inner).connect_tcp("mixed.example", 443)
    assert inner.hosts == [], "one non-public answer rejects the host"
    with pytest.raises(FetchRejected):
        fetch.PublicOnlyBackend(inner).connect_unix_socket("/tmp/x.sock")


def test_dns_rebinding_between_check_and_connect_is_rejected(tmp_path, monkeypatch):
    # The pre-request check sees a public address; the second lookup (at
    # connect time) returns loopback, where a real listener is waiting. With
    # pinning the connect re-validates and refuses; without it, httpx would
    # resolve the name itself.
    import socket

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.setblocking(False)
    port = listener.getsockname()[1]
    answers = iter([[PUBLIC], ["127.0.0.1"]])
    monkeypatch.setattr(fetch, "_resolve", lambda host: next(answers))
    real_getaddrinfo = socket.getaddrinfo

    def numeric_only(host, *args, **kw):
        # Any hostname lookup outside fetch._resolve means the connection was
        # not pinned to the checked address (and would hit real DNS).
        assert fetch._is_ip_literal(host), f"unpinned DNS lookup of {host}"
        return real_getaddrinfo(host, *args, **kw)

    monkeypatch.setattr(socket, "getaddrinfo", numeric_only)
    with pdf_client() as client, pytest.raises(FetchRejected, match="non-public"):
        _download(f"http://rebind.example:{port}/a.pdf", tmp_path / "a.pdf", client)
    with pytest.raises(BlockingIOError):
        listener.accept()  # nobody connected
    listener.close()
