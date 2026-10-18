"""OpenAlex client.

An API key is optional. Without one, requests share a small free daily budget
per IP address; set OPENALEX_API_KEY for a key with its own, larger budget.

Docs: https://help.openalex.org/how-to-use-the-api/rate-limits-and-authentication
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Iterator

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from vista.config import USER_AGENT, VERSION, openalex_api_key

API = "https://api.openalex.org"
MAX_RETRY_AFTER_SECONDS = 60.0

log = logging.getLogger(__name__)
_warned_no_key = False
_sleep = time.sleep  # indirection so tests can stub out backoff waits


class OpenAlexBudgetExhausted(httpx.HTTPStatusError):
    """A 429 caused by a spent daily budget. Retrying cannot succeed until reset."""


def _budget_exhausted(response: httpx.Response) -> bool:
    # OpenAlex returns 429 both for per-second throttling (transient) and for a
    # spent daily budget (not transient). Only the latter drives the remaining
    # budget to zero.
    return response.headers.get("x-ratelimit-remaining") == "0"


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, OpenAlexBudgetExhausted):
        return False
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return False


def _retry_after_seconds(exc: BaseException | None) -> float | None:
    if not isinstance(exc, httpx.HTTPStatusError):
        return None
    raw = exc.response.headers.get("Retry-After")
    try:
        return min(float(raw), MAX_RETRY_AFTER_SECONDS) if raw is not None else None
    except ValueError:  # HTTP-date form; fall back to exponential backoff
        return None


_backoff = wait_exponential_jitter(initial=1, max=15)


def _wait(retry_state) -> float:
    retry_after = _retry_after_seconds(retry_state.outcome.exception())
    return retry_after if retry_after is not None else _backoff(retry_state)


@dataclass
class OpenAlexWork:
    id: str
    doi: str | None
    title: str
    abstract: str | None
    year: int | None
    venue: str | None
    venue_id: str | None
    cited_by_count: int
    authors: list[dict]
    oa_url: str | None
    pdf_url: str | None
    arxiv_id: str | None
    raw: dict

    @classmethod
    def from_api(cls, w: dict) -> "OpenAlexWork":
        oa = w.get("open_access", {}) or {}
        primary = w.get("primary_location") or {}
        source = primary.get("source") or {}
        venue = source.get("display_name")
        venue_id = source.get("id")
        if venue_id and venue_id.startswith("https://openalex.org/"):
            venue_id = venue_id.rsplit("/", 1)[-1]

        # Find arXiv id from any location
        arxiv_id = None
        for loc in [primary] + (w.get("locations") or []):
            if not loc:
                continue
            url = (loc.get("landing_page_url") or "") + " " + (loc.get("pdf_url") or "")
            m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+/[0-9]{7})", url)
            if m:
                arxiv_id = m.group(1)
                break

        # OA pdf preference: primary -> any oa location
        pdf_url = primary.get("pdf_url")
        if not pdf_url:
            for loc in w.get("locations") or []:
                if loc.get("is_oa") and loc.get("pdf_url"):
                    pdf_url = loc.get("pdf_url")
                    break

        oid = w["id"]
        if oid.startswith("https://openalex.org/"):
            oid = oid.rsplit("/", 1)[-1]

        return cls(
            id=oid,
            doi=w.get("doi"),
            title=w.get("display_name") or w.get("title") or "",
            abstract=_invert_abstract(w.get("abstract_inverted_index")),
            year=w.get("publication_year"),
            venue=venue,
            venue_id=venue_id,
            cited_by_count=w.get("cited_by_count") or 0,
            authors=[
                {
                    "name": (a.get("author") or {}).get("display_name"),
                    "orcid": (a.get("author") or {}).get("orcid"),
                }
                for a in w.get("authorships") or []
            ],
            oa_url=oa.get("oa_url"),
            pdf_url=pdf_url,
            arxiv_id=arxiv_id,
            raw=w,
        )


def _invert_abstract(inv: dict | None) -> str | None:
    if not inv:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions) or None


class OpenAlexClient:
    def __init__(
        self,
        *,
        mailto: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ):
        ua = USER_AGENT if not mailto else f"vista/{VERSION} (mailto:{mailto})"
        headers = {"User-Agent": ua, "Accept": "application/json"}
        key = api_key or openalex_api_key()
        if key:
            # Bearer header rather than the equivalent `api_key` query param, so
            # the key never appears in URLs, logs, or HTTPStatusError messages.
            headers["Authorization"] = f"Bearer {key}"
        else:
            _warn_no_key_once()
        self.client = httpx.Client(
            base_url=API, headers=headers, timeout=timeout, transport=transport,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "OpenAlexClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(4),
        wait=_wait,
        sleep=lambda seconds: _sleep(seconds),
        reraise=True,
    )
    def _get(self, path: str, params: dict[str, Any]) -> dict:
        r = self.client.get(path, params=params)
        if r.status_code == 429 and _budget_exhausted(r):
            raise OpenAlexBudgetExhausted(
                "OpenAlex daily budget exhausted (429). Keyless requests share one small "
                "budget per IP; set OPENALEX_API_KEY to a free key from "
                "https://openalex.org/settings/api for your own, larger budget.",
                request=r.request,
                response=r,
            )
        r.raise_for_status()
        return r.json()

    def works(self, *, filter_str: str, sort: str = "cited_by_count:desc",
              per_page: int = 50, max_results: int | None = None) -> Iterator[OpenAlexWork]:
        cursor = "*"
        seen = 0
        while True:
            data = self._get(
                "/works",
                {"filter": filter_str, "sort": sort, "per-page": per_page, "cursor": cursor},
            )
            for w in data.get("results", []):
                yield OpenAlexWork.from_api(w)
                seen += 1
                if max_results and seen >= max_results:
                    return
            cursor = (data.get("meta") or {}).get("next_cursor")
            if not cursor:
                return

    def work_by_doi(self, doi: str) -> OpenAlexWork | None:
        clean = doi.lower().removeprefix("https://doi.org/").removeprefix("doi:")
        try:
            data = self._get(f"/works/doi:{clean}", {})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        return OpenAlexWork.from_api(data)

    def work_by_id(self, work_id: str) -> OpenAlexWork | None:
        wid = work_id
        if wid.startswith("https://openalex.org/"):
            wid = wid.rsplit("/", 1)[-1]
        try:
            data = self._get(f"/works/{wid}", {})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        return OpenAlexWork.from_api(data)


def _warn_no_key_once() -> None:
    global _warned_no_key
    if not _warned_no_key:
        _warned_no_key = True
        log.warning(
            "OPENALEX_API_KEY is not set: OpenAlex requests share a small free daily "
            "budget per IP address. Get a free key at https://openalex.org/settings/api."
        )


# Characters with syntactic meaning inside an OpenAlex `filter` string: a comma
# separates filters and a pipe ORs values. Full-text search ignores punctuation,
# so replacing them with spaces keeps the query's meaning.
_FILTER_SEPARATORS = str.maketrans({",": " ", "|": " "})


def search_filter(field: str, text: str) -> str:
    """Build a `<field>.search:<text>` filter safe for arbitrary free text."""
    return f"{field}.search:{' '.join(text.translate(_FILTER_SEPARATORS).split())}"


def build_filter(
    *,
    concept_ids: list[str] | None = None,
    venue_ids: list[str] | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    min_citations: int | None = None,
    is_oa: bool | None = True,
    types: list[str] | None = None,
    keyword_search: str | None = None,
) -> str:
    parts: list[str] = []
    if concept_ids:
        parts.append("concepts.id:" + "|".join(concept_ids))
    if venue_ids:
        parts.append("primary_location.source.id:" + "|".join(venue_ids))
    if year_min and year_max:
        parts.append(f"publication_year:{year_min}-{year_max}")
    elif year_min:
        parts.append(f"publication_year:>{year_min - 1}")
    elif year_max:
        parts.append(f"publication_year:<{year_max + 1}")
    if min_citations is not None:
        parts.append(f"cited_by_count:>{min_citations - 1}")
    if is_oa is not None:
        parts.append(f"is_oa:{'true' if is_oa else 'false'}")
    if types:
        parts.append("type:" + "|".join(types))
    if keyword_search:
        # OpenAlex supports `default.search` via the `search` param, but we
        # prefer filter-style: title_and_abstract.search
        parts.append(search_filter("title_and_abstract", keyword_search))
    return ",".join(parts)
