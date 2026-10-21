"""Tests for the SQLite store: idempotent writes and needs_* resume flags.

Runs fully offline against an in-memory database. These characterize the
"idempotent and resumable" contract the pipeline relies on: each stage's
"unfinished" set is defined by the absence (or empty-placeholder presence) of
rows in the next table.
"""

import json
import sqlite3

import pytest

from vista.storage.db import Direction, Paper, Section, Store


def _store() -> Store:
    return Store.open(":memory:")


def _paper(pid: str, **kw) -> Paper:
    base = dict(title=f"Paper {pid}", field="ml", track="recent")
    base.update(kw)
    return Paper(id=pid, **base)


def test_open_initializes_schema():
    s = _store()
    names = {
        r["name"]
        for r in s.conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        )
    }
    assert {"papers", "sections", "directions", "runs", "v_directions_full"} <= names


def test_upsert_paper_is_idempotent():
    s = _store()
    s.upsert_paper(_paper("W1", cited_by_count=10))
    s.upsert_paper(_paper("W1", cited_by_count=99))  # same id, new value
    rows = s.papers()
    assert len(rows) == 1, "re-upsert must update, not duplicate"
    assert rows[0]["cited_by_count"] == 99


def test_needs_pdf_requires_a_url_and_no_path():
    s = _store()
    s.upsert_paper(_paper("has_url", oa_url="http://x/a.pdf"))
    s.upsert_paper(_paper("no_url"))  # nothing to fetch from
    s.upsert_paper(_paper("done", oa_url="http://x/b.pdf", pdf_path="/tmp/b.pdf"))
    assert {r["id"] for r in s.papers(needs_pdf=True)} == {"has_url"}


def test_flags_progress_through_stages():
    s = _store()
    s.upsert_paper(_paper("W1", oa_url="http://x/a.pdf"))
    # Stage 1: needs a PDF, nothing downstream yet.
    assert [r["id"] for r in s.papers(needs_pdf=True)] == ["W1"]
    assert s.papers(needs_extraction=True) == []
    assert s.papers(needs_analysis=True) == []

    # After fetch.
    s.mark_fetched("W1", "/tmp/a.pdf")
    assert s.papers(needs_pdf=True) == []
    assert [r["id"] for r in s.papers(needs_extraction=True)] == ["W1"]

    # After extract.
    s.upsert_sections([Section("W1", "conclusion", "Conclusion", "We conclude.")])
    assert s.papers(needs_extraction=True) == []
    assert [r["id"] for r in s.papers(needs_analysis=True)] == ["W1"]

    # After analyze.
    s.replace_directions("W1", [Direction("W1", "Investigate X")])
    assert s.papers(needs_analysis=True) == []


def test_empty_placeholder_section_clears_needs_extraction():
    # The empty-placeholder negative cache: a paper that yielded no real sections
    # still gets a placeholder row so it is not re-extracted forever.
    s = _store()
    s.upsert_paper(_paper("W1", oa_url="http://x/a.pdf"))
    s.mark_fetched("W1", "/tmp/a.pdf")
    assert [r["id"] for r in s.papers(needs_extraction=True)] == ["W1"]
    s.upsert_sections([Section("W1", "conclusion", None, "", method="empty")])
    assert s.papers(needs_extraction=True) == [], "placeholder row stops re-extraction"


def test_upsert_sections_conflict_updates_in_place():
    s = _store()
    s.upsert_paper(_paper("W1"))
    s.upsert_sections([Section("W1", "conclusion", "C", "first")])
    s.upsert_sections([Section("W1", "conclusion", "C", "second")])  # same key
    secs = s.get_sections("W1")
    assert len(secs) == 1
    assert secs[0]["content"] == "second"


def test_replace_directions_replaces_not_appends():
    s = _store()
    s.upsert_paper(_paper("W1"))
    s.replace_directions("W1", [Direction("W1", "A"), Direction("W1", "B")])
    assert len(s.get_directions("W1")) == 2
    s.replace_directions("W1", [Direction("W1", "C")])
    dirs = s.get_directions("W1")
    assert [d["direction"] for d in dirs] == ["C"]


def test_papers_field_and_track_filters():
    s = _store()
    s.upsert_paper(_paper("a", field="ml", track="recent"))
    s.upsert_paper(_paper("b", field="ai", track="recent"))
    s.upsert_paper(_paper("c", field="ml", track="legacy"))
    assert {r["id"] for r in s.papers(field="ml")} == {"a", "c"}
    assert {r["id"] for r in s.papers(track="recent")} == {"a", "b"}
    assert {r["id"] for r in s.papers(field="ml", track="legacy")} == {"c"}


def test_delete_paper_cascades_to_sections_and_directions():
    # Foreign keys are ON; deleting a paper removes its children.
    s = _store()
    s.upsert_paper(_paper("W1"))
    s.upsert_sections([Section("W1", "conclusion", "C", "x")])
    s.replace_directions("W1", [Direction("W1", "A")])
    with s.tx():
        s.conn.execute("DELETE FROM papers WHERE id = 'W1'")
    assert s.get_sections("W1") == []
    assert s.get_directions("W1") == []


def test_begin_and_finish_run_records_provenance():
    s = _store()
    run_id = s.begin_run({"fields": ["ml"], "track": "recent"})
    s.finish_run(run_id, notes='{"discover": 3}')
    row = s.conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert row["finished_at"] is not None
    assert "discover" in row["notes"]


def test_upsert_preserves_fetch_provenance():
    # A re-discover builds Papers with pdf_path=None; it must not clobber the
    # pdf_path/fetched_at that the fetch stage recorded.
    s = _store()
    s.upsert_paper(_paper("W9"))
    s.conn.execute(
        "UPDATE papers SET pdf_path='/tmp/w9.pdf', fetched_at='2026-01-01' WHERE id='W9'"
    )
    s.conn.commit()
    s.upsert_paper(_paper("W9", cited_by_count=123))  # re-discover
    row = s.get_paper("W9")
    assert row["pdf_path"] == "/tmp/w9.pdf", "re-discover must not reset pdf_path"
    assert row["fetched_at"] == "2026-01-01"
    assert row["cited_by_count"] == 123, "other columns still update"


# --- directions: natural key, curation-preserving writes --------------------


def _curate(s: Store, text: str, status="interesting", notes=None) -> int:
    row = next(d for d in s.get_directions("W1") if d["direction"] == text)
    assert s.set_direction_status(row["id"], status, notes)
    return row["id"]


def test_upsert_directions_appends_and_dedupes_by_normalized_text():
    s = _store()
    s.upsert_paper(_paper("W1"))
    s.upsert_directions("W1", [Direction("W1", "Study X", field_tags_json='["a"]')])
    s.upsert_directions("W1", [Direction("W1", "study   x.", rationale="why",
                                         field_tags_json='["crossref:me"]'),
                               Direction("W1", "Study Y")])
    dirs = {d["direction"]: d for d in s.get_directions("W1")}
    assert set(dirs) == {"study   x.", "Study Y"}, "same key updates in place, new key appends"
    assert dirs["study   x."]["rationale"] == "why"
    assert json.loads(dirs["study   x."]["field_tags_json"]) == ["a", "crossref:me"]


def test_upsert_keeps_id_and_curation_of_matching_row():
    s = _store()
    s.upsert_paper(_paper("W1"))
    s.upsert_directions("W1", [Direction("W1", "Study X", rationale="old")])
    did = _curate(s, "Study X", "started", "my note")
    s.upsert_directions("W1", [Direction("W1", "Study X")])  # empty fields don't clobber
    row = s.get_directions("W1")[0]
    assert (row["id"], row["user_status"], row["user_notes"], row["rationale"]) == \
        (did, "started", "my note", "old")


def test_replace_never_deletes_curated_rows():
    # The bug: a second submit_directions (e.g. a cross-reference run) used to
    # wipe every direction for the paper, including the user's curation.
    s = _store()
    s.upsert_paper(_paper("W1"))
    s.replace_directions("W1", [Direction("W1", t) for t in ("A", "B", "C")])
    _curate(s, "A", "interesting")
    _curate(s, "B", "open", notes="keep me")
    s.replace_directions("W1", [Direction("W1", "D")])
    assert {d["direction"] for d in s.get_directions("W1")} == {"A", "B", "D"}


def test_set_direction_status_validates_and_reports_missing():
    s = _store()
    s.upsert_paper(_paper("W1"))
    assert s.set_direction_status(999, "open") is False
    with pytest.raises(ValueError):
        s.set_direction_status(1, "bogus")


# --- negative caches and progress flags ------------------------------------


def test_needs_pdf_includes_arxiv_only_papers_and_skips_failed():
    s = _store()
    s.upsert_paper(_paper("arx", arxiv_id="2106.01234"))
    s.upsert_paper(_paper("dead", oa_url="http://x/dead.pdf"))
    s.mark_fetch_failed("dead")
    assert {r["id"] for r in s.papers(needs_pdf=True)} == {"arx"}
    assert s.clear_fetch_failures() == 1
    assert {r["id"] for r in s.papers(needs_pdf=True)} == {"arx", "dead"}


def test_mark_fetched_clears_failure_and_stamps_time():
    s = _store()
    s.upsert_paper(_paper("W1", oa_url="http://x"))
    s.mark_fetch_failed("W1")
    s.mark_fetched("W1", "/tmp/w1.pdf")
    row = s.get_paper("W1")
    assert row["fetch_failed_at"] is None and row["fetched_at"].endswith("+00:00")


def test_analyzed_marker_stops_reanalysis_with_zero_directions():
    s = _store()
    s.upsert_paper(_paper("W1"))
    s.upsert_sections([Section("W1", "conclusion", "C", "text")])
    assert [r["id"] for r in s.papers(needs_analysis=True)] == ["W1"]
    s.mark_analyzed("W1")  # model returned nothing
    assert s.papers(needs_analysis=True) == []


def test_empty_placeholder_is_not_analyzable():
    s = _store()
    s.upsert_paper(_paper("W1"))
    s.upsert_sections([Section("W1", "conclusion", None, "", method="empty")])
    assert s.papers(needs_analysis=True) == []


def test_status_counts():
    s = _store()
    s.upsert_paper(_paper("a", oa_url="http://x"))
    s.upsert_paper(_paper("b"))
    s.mark_fetched("a", "/tmp/a.pdf")
    s.upsert_sections([Section("a", "conclusion", "C", "text"),
                       Section("b", "conclusion", None, "", method="empty")])
    s.upsert_directions("a", [Direction("a", "X")])
    out = s.status_counts()
    assert out["totals"] == {"papers": 2, "directions": 1}
    assert out["by_field_track"] == [{"field": "ml", "track": "recent", "papers": 2,
                                      "with_pdf": 1, "with_sections": 1, "with_directions": 1}]


def test_paper_from_work():
    from vista.sources.openalex import OpenAlexWork

    w = OpenAlexWork(id="W5", doi="10.1/x", title="T", abstract="A", year=2020, venue="V",
                     venue_id="S1", cited_by_count=3, authors=[{"name": "N"}],
                     oa_url="o", pdf_url="p", arxiv_id="2101.00001", raw={"k": 1})
    p = Paper.from_work(w, field="ml", track="seed")
    assert (p.id, p.field, p.track, p.arxiv_id) == ("W5", "ml", "seed", "2101.00001")
    assert json.loads(p.authors_json) == [{"name": "N"}] and json.loads(p.raw_json) == {"k": 1}


def test_old_catalog_is_migrated_in_place(tmp_path):
    # A catalog created before fetch_failed_at / analyzed_at existed, with an
    # old-shape view, opens cleanly and gains the new columns and view fields.
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE papers (id TEXT PRIMARY KEY, doi TEXT, arxiv_id TEXT, title TEXT NOT NULL,
          authors_json TEXT, year INTEGER, venue TEXT, venue_id TEXT, abstract TEXT,
          cited_by_count INTEGER, field TEXT NOT NULL, track TEXT NOT NULL, oa_url TEXT,
          pdf_url TEXT, pdf_path TEXT, discovered_at TEXT, fetched_at TEXT, raw_json TEXT);
        INSERT INTO papers (id, title, field, track) VALUES ('W1', 'T', 'ml', 'recent');
        CREATE TABLE directions (id INTEGER PRIMARY KEY AUTOINCREMENT, paper_id TEXT NOT NULL,
          direction TEXT NOT NULL, rationale TEXT, quote TEXT, field_tags_json TEXT,
          feasibility TEXT, novelty TEXT, dependencies TEXT, user_status TEXT DEFAULT 'open',
          user_notes TEXT, analyzed_at TEXT);
        CREATE VIEW v_directions_full AS SELECT d.id AS direction_id FROM directions d;
    """)
    conn.close()
    s = Store.open(db)
    cols = {r["name"] for r in s.conn.execute("PRAGMA table_info(papers)")}
    assert {"fetch_failed_at", "analyzed_at"} <= cols
    view_cols = {r["name"] for r in s.conn.execute("PRAGMA table_info(v_directions_full)")}
    assert {"quote", "user_notes", "paper_id"} <= view_cols
    assert s.get_paper("W1")["title"] == "T"
    s.close()
