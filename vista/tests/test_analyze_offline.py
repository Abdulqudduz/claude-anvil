"""Offline tests for the analyzer. No API key; the SDK client is a fake.

These cover prompt building, coercion of model output into Direction rows,
the request shape sent to the Messages API (structured outputs, token
budget), stop_reason handling, and the analyzed-empty marker.
"""

import json
from types import SimpleNamespace

import pytest

from vista.pipeline import analyze
from vista.pipeline.analyze import (
    AnalyzerRefused,
    AnalyzerTruncated,
    _build_user_message,
    analyze_paper,
    directions_from_dicts,
    run_analyze,
)
from vista.storage.db import Paper, Section, Store


def test_directions_from_dicts_basic():
    items = [
        {
            "direction": "Study X",
            "rationale": "because",
            "field_tags": ["ml", "nlp"],
            "feasibility": "high",
            "novelty": "medium",
            "quote": "q",
            "dependencies": "gpu",
        }
    ]
    out = directions_from_dicts("W1", items)
    assert len(out) == 1
    d = out[0]
    assert d.paper_id == "W1"
    assert d.direction == "Study X"
    assert json.loads(d.field_tags_json) == ["ml", "nlp"]
    assert d.feasibility == "high"


def test_directions_from_dicts_drops_items_without_direction():
    out = directions_from_dicts("W1", [{"rationale": "orphan"}, {"direction": "ok"}])
    assert [d.direction for d in out] == ["ok"]


def test_directions_from_dicts_empty_optionals_become_none():
    d = directions_from_dicts("W1", [{"direction": "D"}])[0]
    assert d.rationale is None
    assert d.quote is None
    assert d.feasibility is None
    assert json.loads(d.field_tags_json) == []


def test_build_user_message_includes_metadata_and_truncates():
    paper = {"id": "W1", "title": "T", "year": 2021, "venue": "ICML", "abstract": "Abs"}
    sections = [{"section_type": "discussion", "heading": "Discussion",
                 "content": "x" * 13000}]
    msg = _build_user_message(paper, sections)
    assert "Title: T" in msg
    assert "Year: 2021" in msg
    assert "Venue: ICML" in msg
    assert "Discussion" in msg
    assert "[...truncated]" in msg  # content over 12000 chars is clipped
    assert len(msg) < 13000


class FakeClient:
    """Records messages.create kwargs and replays scripted replies."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls: list[dict] = []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def reply(payload, stop_reason="end_turn"):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(stop_reason=stop_reason,
                           content=[SimpleNamespace(type="text", text=text)])


PAPER = {"id": "W1", "title": "T", "year": 2020, "venue": "V", "abstract": "A"}
SECTIONS = [{"section_type": "future_work", "heading": "Future Work", "content": "Study Y."}]


def test_request_uses_structured_output_and_room_for_thinking():
    c = FakeClient(reply({"directions": [{"direction": "Study Y", "field_tags": ["x"]}]}))
    out = analyze_paper(PAPER, SECTIONS, model="m", client=c)
    assert [d.direction for d in out] == ["Study Y"]
    kw = c.calls[0]
    assert kw["output_config"]["format"] == {"type": "json_schema",
                                             "schema": analyze.DIRECTIONS_SCHEMA}
    assert kw["max_tokens"] >= 16000
    assert kw["system"] == analyze.SYSTEM_PROMPT, "plain string: no useless cache_control"
    assert "\u2014" not in analyze.SYSTEM_PROMPT


def test_no_request_for_empty_sections():
    c = FakeClient()
    assert analyze_paper(PAPER, [{"section_type": "conclusion", "content": ""}], client=c) == []
    assert c.calls == []


def test_refusal_and_truncation_raise():
    with pytest.raises(AnalyzerRefused):
        analyze_paper(PAPER, SECTIONS, client=FakeClient(reply("", "refusal")))
    with pytest.raises(AnalyzerTruncated):
        analyze_paper(PAPER, SECTIONS, client=FakeClient(reply('{"directions": [', "max_tokens")))


def _store_with_papers(*ids):
    s = Store.open(":memory:")
    for pid in ids:
        s.upsert_paper(Paper(id=pid, title=pid, field="ml", track="recent"))
        s.upsert_sections([Section(pid, "future_work", "FW", f"text {pid}")])
    return s


def test_run_analyze_marks_empty_and_refused_but_not_failed():
    s = _store_with_papers("A", "B", "C", "D")
    c = FakeClient(
        reply({"directions": [{"direction": "Do X"}]}),
        reply({"directions": []}),
        reply("", "refusal"),
        reply("{", "max_tokens"),
    )
    out = run_analyze(s, model="m", client=c)
    assert out == {"attempted": 4, "with_directions": 1, "no_directions": 1,
                   "refused": 1, "failed": 1}
    # Only the truncated paper is retried next run; the empty one is not re-billed.
    assert [r["id"] for r in s.papers(needs_analysis=True)] == ["D"]


def test_run_analyze_skips_papers_that_already_have_directions():
    s = _store_with_papers("A")
    s.upsert_directions("A", directions_from_dicts("A", [{"direction": "Mine"}]))
    c = FakeClient()
    assert run_analyze(s, model="m", client=c)["attempted"] == 0
    assert c.calls == []


def test_run_analyze_without_key_or_client_errors():
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        run_analyze(Store.open(":memory:"))
