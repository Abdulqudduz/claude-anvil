"""Discover candidate papers via OpenAlex and write them to the store."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator

from vista.config import ARXIV_SOURCE_ID, FIELDS, RunConfig
from vista.sources.openalex import OpenAlexClient, OpenAlexWork, build_filter
from vista.storage.db import Paper, Store

log = logging.getLogger(__name__)

TRACKS = ("recent", "legacy")


def field_filter(field: str, track: str, cfg: RunConfig) -> tuple[str, int]:
    """The OpenAlex filter string and result limit for a (field, track) pair."""
    fconf = FIELDS[field]
    if track == "recent":
        year_min, year_max = cfg.year_min_recent, None
        min_cites = fconf.get("min_citations_recent", 30)
        limit = cfg.per_field_limit
    elif track == "legacy":
        year_min, year_max = cfg.year_min_legacy, cfg.year_max_legacy
        min_cites = fconf.get("min_citations_legacy", 300)
        limit = cfg.legacy_per_field_limit
    else:
        raise ValueError(f"unknown track {track!r}; valid: {list(TRACKS)} or 'both'")

    strategy = fconf.get("fulltext_filter", "any")
    arxiv = strategy == "arxiv-required"
    filt = build_filter(
        concept_ids=fconf.get("concept_ids"),
        # OpenAlex venue coverage of NeurIPS/ICML is sparse, so an arXiv
        # requirement replaces the venue filter rather than adding to it.
        venue_ids=None if arxiv else (fconf.get("venue_ids") or None),
        location_source_ids=[ARXIV_SOURCE_ID] if arxiv else None,
        year_min=year_min,
        year_max=year_max,
        min_citations=min_cites,
        is_oa=None,  # don't pre-filter; we'll handle at fetch time
        keyword_search=fconf.get("keywords") if strategy == "any" else None,
    )
    return filt, limit


def discover_field(client: OpenAlexClient, *, field: str, track: str,
                   cfg: RunConfig) -> Iterator[OpenAlexWork]:
    """Yield top-cited works for a (field, track) combination."""
    filt, limit = field_filter(field, track, cfg)
    log.info("[%s/%s] OpenAlex filter: %s", field, track, filt)
    yield from client.works(filter_str=filt, max_results=limit)


def store_works(store: Store, works: Iterable[OpenAlexWork], *, field: str, track: str) -> int:
    n = 0
    for w in works:
        store.upsert_paper(Paper.from_work(w, field=field, track=track))
        n += 1
    return n


def run_discover(store: Store, cfg: RunConfig, *,
                 client: OpenAlexClient | None = None) -> dict[str, int]:
    tracks = list(TRACKS) if cfg.track == "both" else [cfg.track]
    counts: dict[str, int] = {}
    own = client is None
    client = client or OpenAlexClient()
    try:
        for field in cfg.fields:
            for track in tracks:
                works = discover_field(client, field=field, track=track, cfg=cfg)
                n = store_works(store, works, field=field, track=track)
                counts[f"{field}/{track}"] = n
                log.info("[%s/%s] stored %d papers", field, track, n)
    finally:
        if own:
            client.close()
    return counts
