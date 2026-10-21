"""LLM analyzer.

Primary path is the MCP server in `vista.mcp_server`, which exposes tools
that an MCP client (Claude Code, etc.) can call directly. The LLM never has
to be the Anthropic SDK; it can be whoever is on the other end of the MCP
connection.

This module keeps an opt-in Anthropic-API path for fully unattended batch
runs (cron, CI, etc.) where you don't want a human in the loop. The
`anthropic` package is an optional dep (the `[api]` extra).

The request uses structured outputs (`output_config.format` with a JSON
schema, anthropic>=0.97), so the reply is schema-valid JSON;
`_extract_json_array` remains only as a tolerant decoder.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from vista.config import DEFAULT_MODEL
from vista.storage.db import Direction, Store

log = logging.getLogger(__name__)

# Room for adaptive thinking plus 3-8 directions. Thinking tokens count
# against max_tokens, so a small cap truncates the JSON.
MAX_TOKENS = 16000
MAX_SECTION_CHARS = 12000

SYSTEM_PROMPT = """You are a research analyst distilling concrete research \
directions from the "Future Work", "Limitations", "Discussion", and \
"Conclusion" sections of academic papers.

Your job: given the abstract and section text from one paper, produce a list \
of *actionable* research directions. Each direction should be one that a \
graduate student or researcher could plausibly pursue as a project.

For each direction:
- "direction": one sentence stating what to investigate. Be concrete; avoid \
generic wishes like "more experiments" or "better models". If the paper is \
vague, refine the direction into the most specific actionable form supported \
by the text.
- "rationale": one or two sentences on why this direction matters, grounded \
in the paper's findings or limitations.
- "quote": a short verbatim phrase from the input text that motivated this \
direction (max ~30 words, exact substring of the input).
- "field_tags": 1-4 lower-case tags (e.g., ["nlp", "interpretability", \
"reinforcement-learning"]).
- "feasibility": how realistic for a small team in 2-3 quarters (low, medium, \
or high).
- "novelty": relative to the apparent state of the field (low, medium, or high).
- "dependencies": short note on prerequisites (data, hardware, theory) or null.

Aim for 3-8 directions. If fewer than 3 are well-supported, return however \
many are well-supported (even zero). Do not invent directions not grounded in \
the text. If the input is mostly boilerplate or empty, return no directions.
"""

_LEVEL = {"type": "string", "enum": ["low", "medium", "high"]}
DIRECTIONS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "directions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string"},
                    "rationale": {"type": "string"},
                    "quote": {"type": "string"},
                    "field_tags": {"type": "array", "items": {"type": "string"}},
                    "feasibility": _LEVEL,
                    "novelty": _LEVEL,
                    "dependencies": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                },
                "required": ["direction", "rationale", "quote", "field_tags",
                             "feasibility", "novelty", "dependencies"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["directions"],
    "additionalProperties": False,
}


class AnalyzerRefused(Exception):
    """The model declined the request (stop_reason == "refusal")."""


class AnalyzerTruncated(Exception):
    """The reply hit max_tokens before the JSON finished."""


def _client():
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError(
            "anthropic package not installed; pip install -e '.[api]' or use the MCP server"
        ) from e
    return Anthropic()


def directions_from_dicts(paper_id: str, items: list[dict]) -> list[Direction]:
    """Coerce a list of {direction, rationale, ...} dicts into Direction rows."""
    out: list[Direction] = []
    for it in items:
        d = it.get("direction")
        if not d:
            continue
        out.append(
            Direction(
                paper_id=paper_id,
                direction=str(d),
                rationale=str(it.get("rationale") or "") or None,
                quote=str(it.get("quote") or "") or None,
                field_tags_json=json.dumps(it.get("field_tags") or [], ensure_ascii=False),
                feasibility=str(it.get("feasibility") or "") or None,
                novelty=str(it.get("novelty") or "") or None,
                dependencies=str(it.get("dependencies") or "") or None,
            )
        )
    return out


def _build_user_message(paper: dict[str, Any], sections: list[dict]) -> str:
    parts: list[str] = [f"# Paper\n\nTitle: {paper['title']}"]
    if paper.get("year"):
        parts.append(f"Year: {paper['year']}")
    if paper.get("venue"):
        parts.append(f"Venue: {paper['venue']}")
    if paper.get("abstract"):
        parts.append(f"\nAbstract:\n{paper['abstract']}")

    parts.append("\n# Sections")
    for s in sections:
        if not s.get("content"):
            continue
        parts.append(f"\n## {s['section_type'].replace('_', ' ').title()}")
        if s.get("heading"):
            parts.append(f"(heading: {s['heading']})")
        content = s["content"]
        if len(content) > MAX_SECTION_CHARS:
            content = content[:MAX_SECTION_CHARS] + "\n[...truncated]"
        parts.append(content)
    return "\n".join(parts)


def _extract_json_array(text: str) -> list[dict]:
    """Decode the directions list from a reply.

    Accepts the structured-output object {"directions": [...]} and, for
    robustness, a bare array, optionally fenced or wrapped in prose.
    """
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end < start:
            return []
        try:
            data = json.loads(text[start: end + 1])
        except json.JSONDecodeError:
            return []
    if isinstance(data, dict):
        data = data.get("directions")
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict)]


def analyze_paper(
    paper_row,
    section_rows: list,
    *,
    model: str = DEFAULT_MODEL,
    client=None,
) -> list[Direction]:
    """Distill one paper's directions. Raises AnalyzerRefused / AnalyzerTruncated."""
    sections = [dict(s) for s in section_rows if s["content"]]
    if not sections:
        return []
    if client is None:
        client = _client()
    paper = dict(paper_row)

    resp = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_message(paper, sections)}],
        output_config={"format": {"type": "json_schema", "schema": DIRECTIONS_SCHEMA}},
    )
    if resp.stop_reason == "refusal":
        raise AnalyzerRefused(paper["id"])
    if resp.stop_reason == "max_tokens":
        raise AnalyzerTruncated(paper["id"])
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    return directions_from_dicts(paper["id"], _extract_json_array(text))


def run_analyze(
    store: Store,
    *,
    model: str = DEFAULT_MODEL,
    max_papers: int | None = None,
    client=None,
) -> dict[str, int]:
    """Analyze every paper with section text that has not been analyzed yet.

    A paper is marked analyzed (`papers.analyzed_at`) when the model answered,
    even with zero directions or a refusal, so reruns do not re-bill it. A
    truncated reply or an API error leaves it unmarked for the next run.
    """
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set; cannot run analyzer")
        client = _client()
    rows = store.papers(needs_analysis=True)
    if max_papers:
        rows = rows[:max_papers]
    out = {"attempted": 0, "with_directions": 0, "no_directions": 0,
           "refused": 0, "failed": 0}
    for row in rows:
        out["attempted"] += 1
        try:
            directions = analyze_paper(row, store.get_sections(row["id"]),
                                       model=model, client=client)
        except AnalyzerRefused:
            log.warning("analyzer refused %s; marking analyzed", row["id"])
            store.mark_analyzed(row["id"])
            out["refused"] += 1
            continue
        except Exception as e:  # truncation, API errors: retry on a later run
            log.warning("analyze failed for %s: %r", row["id"], e)
            out["failed"] += 1
            continue
        store.replace_directions(row["id"], directions)
        store.mark_analyzed(row["id"])
        out["with_directions" if directions else "no_directions"] += 1
    return out
