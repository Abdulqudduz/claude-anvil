"""MCP tool contracts, exercised in-process against a temp store.

OpenAlex and PDF hosts are httpx.MockTransport fakes; the PDF is generated
with PyMuPDF. Each tool returns a JSON string, decoded here and checked
against the shapes documented in skills/vista/references/output-shape.md.
"""

import json

import httpx
import pytest
from conftest import PAPER_TOC, make_pdf, paper_pages

from vista import mcp_server as m
from vista.pipeline import fetch
from vista.sources import openalex
from vista.sources.openalex import OpenAlexClient

PDF = make_pdf(paper_pages(), toc=PAPER_TOC)


def work(wid: str, title: str, arxiv: str | None = "2106.01234", cites: int = 500) -> dict:
    loc = {"is_oa": True, "landing_page_url": f"https://arxiv.org/abs/{arxiv}",
           "pdf_url": f"https://arxiv.org/pdf/{arxiv}"} if arxiv else {}
    return {"id": f"https://openalex.org/{wid}", "display_name": title,
            "publication_year": 2022, "cited_by_count": cites,
            "primary_location": loc, "locations": [loc] if loc else [],
            "authorships": [{"author": {"display_name": "Ada"}}]}


class OpenAlexFake:
    """Serves /works searches and single-work lookups; records requests."""

    def __init__(self, results=(), single=None):
        self.results = list(results)
        self.single = single
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/works":
            return httpx.Response(200, json={"results": self.results, "meta": {}})
        return httpx.Response(200, json=self.single) if self.single else httpx.Response(404)


@pytest.fixture
def server(monkeypatch):
    """Fresh server state with fake OpenAlex and PDF hosts."""
    monkeypatch.setattr(m, "_STORE", None)
    monkeypatch.setattr(openalex, "_sleep", lambda s: None)
    monkeypatch.setattr(fetch, "_resolve", lambda host: ["93.184.216.34"])
    oa = OpenAlexFake()
    monkeypatch.setattr(m, "_openalex",
                        lambda: OpenAlexClient(transport=httpx.MockTransport(oa)))
    pdf_requests: list[httpx.Request] = []

    def pdf_host(request):
        pdf_requests.append(request)
        if "arxiv.org" in request.url.host:
            return httpx.Response(200, content=PDF, headers={"content-type": "application/pdf"})
        return httpx.Response(403)

    real_pdf_client = fetch.pdf_client
    monkeypatch.setattr(m, "pdf_client",
                        lambda: real_pdf_client(transport=httpx.MockTransport(pdf_host)))
    yield oa, pdf_requests
    if m._STORE is not None:
        m._STORE.close()


def call(tool, **kw):
    return json.loads(tool(**kw))


def test_topic_followups_end_to_end(server):
    oa, pdf_requests = server
    oa.results = [work("W1", "Paper One")]
    out = call(m.topic_followups, topic="graph nets", max_papers=1)
    assert out["paper_count"] == 1
    p = out["papers"][0]
    assert p["paper_id"] == "W1" and p["track"] == "topic" and p["field"] == "ad-hoc"
    types = {s["type"]: s for s in p["sections"]}
    assert types["future_work"]["method"] == "outline"
    assert "video is open" in types["future_work"]["content"]
    # A second call re-uses the cached PDF and sections: no new PDF request.
    call(m.topic_followups, topic="graph nets", max_papers=1)
    assert len(pdf_requests) == 1


def test_unavailable_pdf_is_flagged(server):
    oa, _ = server
    oa.results = [work("W2", "Paywalled", arxiv=None)]
    oa.results[0]["primary_location"] = {"pdf_url": "https://publisher.example/p.pdf"}
    p = call(m.broad_followups, query="x")["papers"][0]
    assert p["note"] == "pdf_unavailable" and p["sections"] == []


def test_find_seminal_uses_legacy_track_and_no_arxiv_filter(server):
    oa, _ = server
    oa.results = [work("W3", "Old Classic")]
    out = call(m.find_seminal, topic="boosting")
    assert out["papers"][0]["track"] == "legacy"
    filt = oa.requests[0].url.params["filter"]
    assert "locations.source.id" not in filt and "publication_year:2000-2019" in filt


def test_broad_followups_rejects_unknown_field_name(server):
    # The tool schema enum rejects unknown names at the MCP layer; the shared
    # body also refuses them rather than silently dropping the filter.
    out = json.loads(m._live({"query": "x"}, track="broad", query="x", fields=["statistics"]))
    assert "valid" in out["error"]


def test_paper_followups_not_found_returns_candidates(server):
    oa, _ = server
    oa.results = [work("W9", "RoBERTa: A Robustly Optimized BERT Pretraining Approach")]
    out = call(m.paper_followups, identifier="BERT")
    assert out["error"] == "not found"
    assert out["candidates"][0]["paper_id"] == "W9"


def test_paper_followups_by_arxiv_url(server):
    oa, _ = server
    oa.single = work("W4", "Exact Paper")
    out = call(m.paper_followups, identifier="https://arxiv.org/abs/2106.01234v2")
    assert out["paper_id"] == "W4" and out["track"] == "paper"
    assert oa.requests[0].url.path == "/works/doi:10.48550/arxiv.2106.01234"


def _seed_paper(server, wid="W1"):
    oa, _ = server
    oa.results = [work(wid, f"Paper {wid}")]
    call(m.topic_followups, topic="t", max_papers=1)


def test_submit_append_then_replace_preserves_curation(server):
    _seed_paper(server)
    out = call(m.submit_directions, paper_id="W1",
               directions=[{"direction": "Do A", "field_tags": ["x"]}, {"direction": "Do B"}])
    assert out == {"paper_id": "W1", "mode": "append", "stored": 2, "total": 2}
    a = next(r for r in call(m.list_directions)["results"] if r["direction"] == "Do A")
    assert call(m.mark_direction, direction_id=a["direction_id"], status="interesting")["status"] \
        == "interesting"
    # Cross-reference run: append a tag to an existing direction, add a new one.
    out = call(m.submit_directions, paper_id="W1",
               directions=[{"direction": "do a", "field_tags": ["crossref:me"]},
                           {"direction": "Do C"}])
    assert out["total"] == 3
    out = call(m.submit_directions, paper_id="W1", directions=[{"direction": "Do D"}],
               mode="replace")
    remaining = {r["direction"]: r for r in call(m.list_directions, user_status=None)["results"]}
    assert set(remaining) == {"do a", "Do D"}, "curated A survives replace; B and C go"
    assert remaining["do a"]["field_tags"] == ["x", "crossref:me"]


def test_direction_listings_share_one_shape(server):
    _seed_paper(server)
    call(m.submit_directions, paper_id="W1",
         directions=[{"direction": "Study 100%_coverage", "rationale": "r", "field_tags": ["t"]}])
    listed = call(m.list_directions)["results"][0]
    searched = call(m.search_directions, query="100%_cov")["results"][0]
    assert listed == searched
    for key in ("direction_id", "paper_id", "paper_title", "rationale", "field_tags",
                "field", "track", "venue", "user_status"):
        assert key in listed
    assert listed["field_tags"] == ["t"]
    assert call(m.search_directions, query="100%x")["count"] == 0, "LIKE wildcards escaped"


def test_submit_and_mark_errors(server):
    assert call(m.submit_directions, paper_id="nope", directions=[])["error"]
    assert call(m.mark_direction, direction_id=12345, status="open")["error"] == \
        "no such direction"
    assert "invalid status" in call(m.mark_direction, direction_id=1, status="bogus")["error"]


def test_get_paper_and_status(server):
    _seed_paper(server)
    call(m.submit_directions, paper_id="W1", directions=[{"direction": "Do A"}])
    p = call(m.get_paper, paper_id="W1")
    assert p["directions"][0]["direction"] == "Do A" and p["sections"]
    assert call(m.get_paper, paper_id="W404")["error"] == "not found"
    st = call(m.status)
    assert st["totals"] == {"papers": 1, "directions": 1}
    assert st["by_field_track"][0]["with_sections"] == 1


def test_run_sql_reads_and_blocks_everything_else(server):
    _seed_paper(server)
    out = call(m.run_sql, query="SELECT id FROM papers -- trailing comment")
    assert out == {"row_count": 1, "truncated": False, "rows": [{"id": "W1"}]}
    out = call(m.run_sql, query="SELECT value FROM json_each('[1,2,3]')", limit=2)
    assert out["row_count"] == 2 and out["truncated"] is True
    # A literal containing a write keyword is fine: no text filtering.
    assert call(m.run_sql, query="SELECT 'update; drop' AS s")["rows"] == [{"s": "update; drop"}]
    for q in ("DELETE FROM papers", "DROP TABLE papers", "PRAGMA table_info(papers)",
              "ATTACH 'x.db' AS x", "VACUUM INTO 'copy.db'", "UPDATE papers SET title='x'"):
        assert "error" in call(m.run_sql, query=q), q
    assert call(m.run_sql, query="SELECT COUNT(*) AS n FROM papers")["rows"] == [{"n": 1}]


def test_get_schema(server):
    assert "CREATE TABLE IF NOT EXISTS papers" in call(m.get_schema)["schema"]


def test_bulk_tools(server, monkeypatch):
    oa, _ = server
    oa.results = [work("W7", "Bulk Paper")]
    out = call(m.discover, fields=["ml"], per_field=1)
    assert out == {"counts": {"ml/recent": 1}}
    assert "error" in call(m.discover, fields=["bogus"])
    monkeypatch.setattr(fetch, "pdf_client", m.pdf_client)
    out = call(m.extract_pending)
    assert out["fetch"]["ok"] == 1 and out["extract"]["with_sections"] == 1
    out = call(m.render_markdown)
    assert out["render"] == {"papers": 1}


def test_tool_schemas_advertise_config_enums():
    import asyncio

    tools = {t.name: t for t in asyncio.run(m.mcp.list_tools())}
    assert len(tools) == 15
    status = tools["mark_direction"].inputSchema["properties"]["status"]
    assert status["enum"] == ["open", "interesting", "started", "abandoned"]
    fields = tools["broad_followups"].inputSchema["properties"]["fields"]
    assert fields["anyOf"][0]["items"]["enum"] == ["ml", "ai", "stats", "ransomware"]


def test_run_sql_interrupts_runaway_query(server, monkeypatch):
    import time

    monkeypatch.setattr(m, "SQL_TIME_LIMIT_SECONDS", 0.3)
    _seed_paper(server)
    start = time.monotonic()
    out = call(m.run_sql, query="WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r) "
                                "SELECT COUNT(*) FROM r")
    assert time.monotonic() - start < 5
    assert "time limit" in out["error"]
    # The connection is per call, so the next query is unaffected.
    assert call(m.run_sql, query="SELECT 1 AS one")["rows"] == [{"one": 1}]
