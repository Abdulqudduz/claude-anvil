"""Offline tests for identifier resolution dispatch.

resolve_identifier classifies a free-form string (OpenAlex id, DOI, arXiv id,
or title) and calls the right client method. A fake client records the calls,
so no network is touched.
"""

import pytest

from vista.core import resolve_identifier, search_works
from vista.sources.openalex import OpenAlexWork


def _work(**kw) -> OpenAlexWork:
    base = dict(
        id="W1", doi=None, title="T", abstract=None, year=None, venue=None,
        venue_id=None, cited_by_count=0, authors=[], oa_url=None, pdf_url=None,
        arxiv_id=None, raw={},
    )
    base.update(kw)
    return OpenAlexWork(**base)


class FakeClient:
    def __init__(self, *, work=None, works_list=None):
        self.work = work
        self.works_list = works_list or []
        self.calls = []

    def work_by_id(self, wid):
        self.calls.append(("by_id", wid))
        return self.work

    def work_by_doi(self, doi):
        self.calls.append(("by_doi", doi))
        return self.work

    def works(self, **kw):
        self.calls.append(("works", kw))
        return iter(self.works_list)


def test_resolve_bare_openalex_id():
    c = FakeClient(work=_work(id="W42"))
    out = resolve_identifier("W42", c)
    assert out.work.id == "W42"
    assert c.calls == [("by_id", "W42")]


def test_resolve_openalex_url_is_stripped():
    c = FakeClient(work=_work(id="W42"))
    resolve_identifier("https://openalex.org/W42", c)
    assert c.calls == [("by_id", "W42")]


def test_resolve_doi():
    c = FakeClient(work=_work())
    resolve_identifier("10.1109/tnnls.2020.2978386", c)
    assert c.calls[0] == ("by_doi", "10.1109/tnnls.2020.2978386")


def test_resolve_arxiv_id_via_datacite_doi():
    # arXiv mints a DataCite DOI for every paper, and OpenAlex resolves it
    # directly, so an arXiv id is one exact lookup, not a search.
    target = _work(id="Wx", arxiv_id="2106.01234")
    c = FakeClient(work=target)
    assert resolve_identifier("2106.01234", c).work is target
    assert c.calls == [("by_doi", "10.48550/arxiv.2106.01234")]


def test_resolve_arxiv_prefix_and_version_suffix():
    c = FakeClient(work=_work())
    resolve_identifier("arXiv:2305.10601v2", c)
    assert c.calls == [("by_doi", "10.48550/arxiv.2305.10601")]


def test_resolve_old_style_arxiv_id():
    c = FakeClient(work=_work())
    resolve_identifier("hep-th/9901001", c)
    assert c.calls == [("by_doi", "10.48550/arxiv.hep-th/9901001")]


def test_resolve_title_fallback():
    target = _work(id="Wt", title="A Comprehensive Survey on Graph Neural Networks")
    c = FakeClient(works_list=[target])
    out = resolve_identifier("a comprehensive survey on graph neural networks.", c)
    assert out.work is target, "case and punctuation are ignored"


def test_resolve_returns_none_when_nothing_matches():
    c = FakeClient(works_list=[])
    out = resolve_identifier("Totally Unmatched Title Xyzzy", c)
    assert out.work is None and out.candidates == []


def test_short_title_does_not_resolve_to_a_superstring():
    # The bug: substring matching made "BERT" resolve to the most-cited title
    # containing "bert". Near misses now come back as candidates instead.
    roberta = _work(id="Wr", title="RoBERTa: A Robustly Optimized BERT Pretraining Approach")
    out = resolve_identifier("BERT", FakeClient(works_list=[roberta]))
    assert out.work is None
    assert out.candidates == [roberta]


@pytest.mark.parametrize("ident, arxiv_id", [
    ("https://arxiv.org/abs/2106.01234", "2106.01234"),
    ("https://arxiv.org/abs/2106.01234v3", "2106.01234"),
    ("arxiv.org/pdf/2106.01234v2.pdf", "2106.01234"),
    ("http://www.arxiv.org/abs/hep-th/9901001", "hep-th/9901001"),
    ("math.AG/0101001", "math.ag/0101001"),
])
def test_resolve_arxiv_urls_and_subject_classes(ident, arxiv_id):
    c = FakeClient(work=_work())
    resolve_identifier(ident, c)
    assert c.calls == [("by_doi", "10.48550/arxiv." + arxiv_id)]


def test_search_works_builds_one_filter_and_rejects_unknown_fields():
    c = FakeClient(works_list=[_work()])
    search_works(c, query="graph, nets", fields=["ml"], year_min=2020,
                 min_citations=30, max_papers=3, require_arxiv=True)
    (_, kw), = c.calls
    f = kw["filter_str"]
    assert "concepts.id:C119857082" in f
    assert "locations.source.id:S4306400194" in f
    assert "title_and_abstract.search:graph nets" in f
    assert kw["max_results"] == 3
    with pytest.raises(ValueError, match="valid"):
        search_works(c, query="x", fields=["statistics"])
