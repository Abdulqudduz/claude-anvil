"""Discovery filters, BibTeX seeding, markdown rendering, and the CLI. Offline."""

import pytest
from typer.testing import CliRunner

from vista import config
from vista.cli import app
from vista.config import RunConfig
from vista.pipeline.discover import field_filter, run_discover
from vista.render.markdown import paper_relpath, render_all
from vista.sources.bibtex import discover_bibs, seed_from_bib
from vista.sources.openalex import OpenAlexWork
from vista.storage.db import Direction, Paper, Section, Store


def _work(wid="W1", title="A Title", doi=None) -> OpenAlexWork:
    return OpenAlexWork(id=wid, doi=doi, title=title, abstract=None, year=2021, venue=None,
                        venue_id=None, cited_by_count=10, authors=[], oa_url=None,
                        pdf_url=None, arxiv_id=None, raw={})


class FakeClient:
    def __init__(self, works=(), by_doi=None):
        self.works_list = list(works)
        self.by_doi = by_doi or {}
        self.filters: list[str] = []

    def works(self, *, filter_str, max_results=None, **kw):
        self.filters.append(filter_str)
        return iter(self.works_list[:max_results] if max_results else self.works_list)

    def work_by_doi(self, doi):
        return self.by_doi.get(doi)


# --- discover ---------------------------------------------------------------


def test_field_filter_per_fulltext_strategy():
    cfg = RunConfig(per_field_limit=7)
    ml, limit = field_filter("ml", "recent", cfg)
    assert "locations.source.id:S4306400194" in ml and limit == 7
    assert "primary_location.source.id" not in ml and "is_oa" not in ml
    stats, _ = field_filter("stats", "recent", cfg)
    assert "primary_location.source.id:S4394736638|" in stats
    assert "locations.source.id" not in stats.replace("primary_location.source.id", "")
    rw, _ = field_filter("ransomware", "legacy", cfg)
    assert "title_and_abstract.search:ransomware" in rw
    assert "publication_year:2005-2019" in rw and "cited_by_count:>99" in rw
    with pytest.raises(ValueError, match="unknown track"):
        field_filter("ml", "sideways", cfg)


def test_run_discover_both_tracks_stores_papers():
    s = Store.open(":memory:")
    client = FakeClient([_work("W1"), _work("W2")])
    counts = run_discover(s, RunConfig(fields=["ml"], track="both"), client=client)
    assert counts == {"ml/recent": 2, "ml/legacy": 2}
    assert len(client.filters) == 2
    assert {r["track"] for r in s.papers()} == {"legacy"}, "later track re-tags the same ids"


# --- bibtex -----------------------------------------------------------------


def test_seed_from_bib_resolves_by_doi_then_exact_title(tmp_path):
    bib = tmp_path / "refs" / "a.bib"
    bib.parent.mkdir()
    bib.write_text("""
@article{one, title={First Paper}, doi={10.1/one}}
@article{two, title={{Second Paper}}}
@article{three, title={Unknown}}
""")
    assert list(discover_bibs([tmp_path])) == [bib]
    client = FakeClient(works=[_work("W2", "Second Paper")],
                        by_doi={"10.1/one": _work("W1", "First Paper")})
    s = Store.open(":memory:")
    counts = seed_from_bib(s, [bib], field="stats", client=client)
    assert counts == {"entries": 3, "resolved": 2, "stored": 2, "missing": 1}
    assert {r["id"]: r["track"] for r in s.papers()} == {"W1": "seed", "W2": "seed"}


# --- render -----------------------------------------------------------------


def test_render_all_writes_index_papers_tags_and_queries():
    s = Store.open(":memory:")
    s.upsert_paper(Paper(id="W1", title="Graph Nets!", field="ml", track="legacy",
                         arxiv_id="2101.00001", cited_by_count=5,
                         authors_json='[{"name": "A"}, {"name": "B"}]'))
    s.upsert_sections([Section("W1", "future_work", "Future Work", "Do things.", "outline")])
    s.upsert_directions("W1", [Direction("W1", "Study X", rationale="r", quote="q",
                                         field_tags_json='["gnn"]', feasibility="high")])
    assert render_all(s) == {"papers": 1}
    out = config.OUT_DIR
    rel = paper_relpath("ml", "Graph Nets!", "W1")
    assert rel == "papers/ml--graph-nets--W1.md"
    paper_md = (out / rel).read_text()
    assert "Study X" in paper_md and "Do things." in paper_md and "arxiv.org/abs/2101.00001" in paper_md
    index = (out / "index.md").read_text()
    assert f"({rel})" in index and "1 directions" in index and str(config.DB_PATH) in index
    assert f"({rel})" in (out / "by-tag.md").read_text()
    assert str(config.DB_PATH) in (out / "queries.md").read_text()
    for f in ("index.md", "by-tag.md", rel):
        assert "—" not in (out / f).read_text()


# --- CLI --------------------------------------------------------------------

runner = CliRunner()


def test_cli_status_on_empty_store():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert "papers: 0" in result.output
    assert config.DB_PATH.exists(), "store created under the patched data dir"


def test_cli_rejects_unknown_field():
    result = runner.invoke(app, ["discover", "--fields", "ml,bogus"])
    assert result.exit_code != 0
    assert "bogus" in result.output


def test_cli_render_and_extract_on_empty_store(tmp_path):
    out = tmp_path / "rendered"
    assert runner.invoke(app, ["render", "--out", str(out)]).exit_code == 0
    assert (out / "index.md").exists()
    result = runner.invoke(app, ["extract"])
    assert result.exit_code == 0 and "attempted: 0" in result.output
