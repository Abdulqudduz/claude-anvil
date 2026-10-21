"""Section extraction from real (generated) PDFs: outline, font, regex strategies.

PDFs are built in memory with PyMuPDF, so no binary fixtures are checked in.
"""

from pathlib import Path

from conftest import BODY, PAPER_TOC, make_pdf, paper_pages

from vista.pipeline.extract import (
    EXTRACTOR_VERSION,
    classify_heading,
    extract_and_store,
    extract_paper,
    run_extract,
)
from vista.storage.db import Paper, Store


def _write(tmp_path: Path, data: bytes, name="p.pdf") -> Path:
    p = tmp_path / name
    p.write_bytes(data)
    return p


def _by_type(secs):
    return {s.section_type: s for s in secs}


def test_outline_strategy_uses_bookmarks_for_boundaries(tmp_path):
    pdf = _write(tmp_path, make_pdf(paper_pages(), toc=PAPER_TOC))
    secs = _by_type(extract_paper(pdf))
    assert secs["future_work"].method == "outline"
    assert "video is open" in secs["future_work"].content
    assert "non-convex" in secs["future_work"].content
    assert "Someone" not in secs["future_work"].content, "References entry ends the section"
    lim = secs["limitations"]
    assert lim.method == "outline" and lim.heading == "5 Conclusions and Limitations"
    assert "scales poorly" in lim.content
    assert "video" not in lim.content, "next outline entry ends the section"


def test_outline_heading_not_in_text_falls_back_to_page_start(tmp_path):
    toc = [[1, "Intro", 1], [1, "Future Work", 2]]  # titles absent from the body text
    pages = [[("Intro text here.", BODY, False)],
             [("Body of page two about open directions.", BODY, False)]]
    secs = _by_type(extract_paper(_write(tmp_path, make_pdf(pages, toc=toc))))
    assert "open directions" in secs["future_work"].content


def test_font_strategy_when_no_outline(tmp_path):
    pdf = _write(tmp_path, make_pdf(paper_pages(heading_size=14.0)))
    secs = _by_type(extract_paper(pdf))
    assert secs["future_work"].method == "font"
    assert "video is open" in secs["future_work"].content
    assert "Someone" not in secs["future_work"].content
    assert secs["limitations"].method == "font"


def test_bold_same_size_headings_are_detected(tmp_path):
    pdf = _write(tmp_path, make_pdf(paper_pages(heading_size=BODY, heading_bold=True)))
    assert _by_type(extract_paper(pdf))["future_work"].method == "font"


def test_regex_strategy_when_no_outline_or_typography(tmp_path):
    pdf = _write(tmp_path, make_pdf(paper_pages(heading_size=BODY, heading_bold=False)))
    secs = _by_type(extract_paper(pdf))
    assert secs["future_work"].method == "regex"
    assert "video is open" in secs["future_work"].content


def test_later_strategy_fills_missing_types_only(tmp_path):
    # Outline lists only the future-work section; the plain "Discussion"
    # heading on page 1 is found by a later strategy.
    toc = [[1, "6 Future Work", 2]]
    pages = paper_pages(heading_size=BODY, heading_bold=False)
    pages[0] += [("Discussion", BODY, False), ("We discuss the tradeoffs at length.", BODY, False)]
    secs = _by_type(extract_paper(_write(tmp_path, make_pdf(pages, toc=toc))))
    assert secs["future_work"].method == "outline"
    assert secs["discussion"].method == "regex"


def test_classify_new_heading_forms():
    assert classify_heading("6 Conclusions and Limitations") == "limitations"
    assert classify_heading("Limitations and Broader Impact") == "limitations"
    assert classify_heading("Discussion and Future Work") == "future_work"
    assert classify_heading("Discussion and Conclusions") == "discussion"
    assert classify_heading("Related Work") is None


def _store_with(tmp_path, pdf: Path) -> Store:
    s = Store.open(":memory:")
    s.upsert_paper(Paper(id="W1", title="T", field="ml", track="recent", oa_url="http://x"))
    s.mark_fetched("W1", str(pdf))
    return s


def test_extract_and_store_writes_empty_placeholder(tmp_path):
    pdf = _write(tmp_path, make_pdf([[("Nothing relevant here.", BODY, False)]]))
    s = _store_with(tmp_path, pdf)
    assert extract_and_store(s, "W1", pdf) == []
    rows = s.get_sections("W1")
    assert [(r["content"], r["method"]) for r in rows] == [("", "empty")]
    assert s.papers(needs_extraction=True) == []


def test_unparseable_pdf_gets_error_placeholder(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 this is not really a pdf")
    s = _store_with(tmp_path, bad)
    extract_and_store(s, "W1", bad)
    assert [r["method"] for r in s.get_sections("W1")] == ["error"]


def test_run_extract_counts_and_records_method(tmp_path):
    pdf = _write(tmp_path, make_pdf(paper_pages(), toc=PAPER_TOC))
    s = _store_with(tmp_path, pdf)
    assert run_extract(s) == {"attempted": 1, "with_sections": 1, "no_sections": 0}
    assert {r["method"] for r in s.get_sections("W1")} == {"outline"}
    assert run_extract(s)["attempted"] == 0, "idempotent"


def test_run_extract_skips_missing_pdf(tmp_path):
    s = _store_with(tmp_path, tmp_path / "gone.pdf")
    assert run_extract(s) == {"attempted": 1, "with_sections": 0, "no_sections": 0}
    assert s.get_sections("W1") == []


# --- re-extraction of placeholders from older extractors --------------------

HEAD_SCHEMA = """
CREATE TABLE papers (id TEXT PRIMARY KEY, doi TEXT, arxiv_id TEXT, title TEXT NOT NULL,
  authors_json TEXT, year INTEGER, venue TEXT, venue_id TEXT, abstract TEXT,
  cited_by_count INTEGER, field TEXT NOT NULL, track TEXT NOT NULL, oa_url TEXT,
  pdf_url TEXT, pdf_path TEXT, discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
  fetched_at TEXT, raw_json TEXT);
CREATE TABLE sections (paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  section_type TEXT NOT NULL, heading TEXT, content TEXT, method TEXT,
  extracted_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (paper_id, section_type));
"""


def _head_catalog(tmp_path, pdf: Path, method="regex-empty") -> Path:
    """A catalog in the pre-change (HEAD) schema whose paper has only a placeholder."""
    import sqlite3

    db = tmp_path / "head.db"
    conn = sqlite3.connect(db)
    conn.executescript(HEAD_SCHEMA)
    conn.execute("INSERT INTO papers (id, title, field, track, pdf_path) "
                 "VALUES ('W1', 'T', 'ml', 'recent', ?)", (str(pdf),))
    conn.execute("INSERT INTO sections (paper_id, section_type, heading, content, method) "
                 "VALUES ('W1', 'conclusion', NULL, '', ?)", (method,))
    conn.commit()
    conn.close()
    return db


def test_head_catalog_regex_empty_placeholder_is_reextracted(tmp_path):
    # The regex extractor found nothing in this PDF; the outline strategy can.
    pdf = _write(tmp_path, make_pdf(paper_pages(), toc=PAPER_TOC))
    s = Store.open(_head_catalog(tmp_path, pdf))
    out = run_extract(s)
    assert out["attempted"] == 1 and out["with_sections"] == 1
    rows = s.get_sections("W1")
    assert all(r["content"] for r in rows), "stale placeholder replaced, not kept alongside"
    assert {r["method"] for r in rows} == {"outline"}
    assert {r["extractor_version"] for r in rows} == {EXTRACTOR_VERSION}
    assert run_extract(s)["attempted"] == 0, "current-version rows are final"


def test_live_path_reextracts_stale_placeholder(tmp_path):
    from vista.core import fetch_and_extract

    pdf = _write(tmp_path, make_pdf(paper_pages(), toc=PAPER_TOC))
    s = Store.open(_head_catalog(tmp_path, pdf))
    out = fetch_and_extract(s, "W1", http=None)
    assert {sec["type"] for sec in out["sections"]} >= {"future_work", "limitations"}


def test_error_placeholder_is_retried_every_run(tmp_path):
    pdf = _write(tmp_path, make_pdf(paper_pages(), toc=PAPER_TOC))
    s = _store_with(tmp_path, pdf)
    from vista.storage.db import Section
    s.upsert_sections([Section("W1", "conclusion", None, "", "error", EXTRACTOR_VERSION)])
    assert run_extract(s)["with_sections"] == 1, "a transient parse error is not cached forever"


def test_current_empty_placeholder_needs_retry_empty_flag(tmp_path):
    pdf = _write(tmp_path, make_pdf([[("Nothing relevant here.", BODY, False)]]))
    s = _store_with(tmp_path, pdf)
    extract_and_store(s, "W1", pdf)
    assert run_extract(s)["attempted"] == 0
    assert run_extract(s, retry_empty=True) == {"attempted": 1, "with_sections": 0,
                                                "no_sections": 1}


def test_cli_extract_retry_empty_flag(tmp_path):
    from typer.testing import CliRunner

    from vista.cli import app

    result = CliRunner().invoke(app, ["extract", "--retry-empty"])
    assert result.exit_code == 0, result.output
