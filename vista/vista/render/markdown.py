"""Render the SQLite store to browseable markdown.

Layout (under config.OUT_DIR unless out_dir is given):
  index.md                              master index, grouped by field
  by-tag.md                             directions grouped by field tag
  papers/<field>--<slug>--<id>.md       one file per paper with full directions
  queries.md                            example SQL queries to mine the data
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from vista import config
from vista.storage.db import Store


def _slug(s: str, maxlen: int = 80) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s[:maxlen] or "untitled"


def paper_relpath(field: str, title: str | None, paper_id: str) -> str:
    """Path of a paper's markdown file relative to the output directory."""
    return f"papers/{field}--{_slug(title or 'untitled')}--{paper_id}.md"


def _md_link_for_paper(row) -> str:
    """Best external link: arXiv > DOI > OA URL."""
    if row["arxiv_id"]:
        return f"https://arxiv.org/abs/{row['arxiv_id']}"
    if row["doi"]:
        doi = row["doi"]
        if not doi.startswith("http"):
            doi = "https://doi.org/" + doi.removeprefix("doi:")
        return doi
    return row["oa_url"] or ""


def _author_str(authors_json: str | None) -> str:
    if not authors_json:
        return ""
    try:
        authors = json.loads(authors_json)
    except json.JSONDecodeError:
        return ""
    names = [a.get("name") for a in authors if a.get("name")]
    if not names:
        return ""
    if len(names) > 4:
        return ", ".join(names[:3]) + f", et al. ({len(names)} authors)"
    return ", ".join(names)


def render_paper_md(store: Store, paper_row, out_dir: Path) -> Path:
    pid = paper_row["id"]
    sections = store.get_sections(pid)
    directions = store.get_directions(pid)

    title = paper_row["title"] or "Untitled"
    path = out_dir / paper_relpath(paper_row["field"], paper_row["title"], pid)
    path.parent.mkdir(parents=True, exist_ok=True)

    link = _md_link_for_paper(paper_row)
    authors = _author_str(paper_row["authors_json"])

    lines: list[str] = []
    lines.append("---")
    lines.append(f"id: {pid}")
    lines.append(f"title: {json.dumps(title)}")
    lines.append(f"field: {paper_row['field']}")
    lines.append(f"track: {paper_row['track']}")
    lines.append(f"year: {paper_row['year'] or ''}")
    lines.append(f"venue: {json.dumps(paper_row['venue'] or '')}")
    lines.append(f"cited_by_count: {paper_row['cited_by_count'] or 0}")
    if paper_row["doi"]:
        lines.append(f"doi: {paper_row['doi']}")
    if paper_row["arxiv_id"]:
        lines.append(f"arxiv_id: {paper_row['arxiv_id']}")
    lines.append("---\n")

    lines.append(f"# {title}\n")
    if authors:
        lines.append(f"**Authors:** {authors}")
    meta_bits = []
    if paper_row["year"]:
        meta_bits.append(str(paper_row["year"]))
    if paper_row["venue"]:
        meta_bits.append(paper_row["venue"])
    meta_bits.append(f"cited {paper_row['cited_by_count'] or 0}x")
    meta_bits.append(f"{paper_row['field']}/{paper_row['track']}")
    lines.append(f"**Meta:** {' · '.join(meta_bits)}")
    if link:
        lines.append(f"**Link:** [{link}]({link})")
    lines.append("")

    if paper_row["abstract"]:
        lines.append("## Abstract\n")
        lines.append(paper_row["abstract"])
        lines.append("")

    if directions:
        lines.append("## Research Directions (LLM-extracted)\n")
        for i, d in enumerate(directions, 1):
            lines.append(f"### {i}. {d['direction']}\n")
            tags = []
            try:
                tags = json.loads(d["field_tags_json"] or "[]")
            except json.JSONDecodeError:
                pass
            badges = []
            if d["feasibility"]:
                badges.append(f"feasibility: **{d['feasibility']}**")
            if d["novelty"]:
                badges.append(f"novelty: **{d['novelty']}**")
            if tags:
                badges.append("tags: " + ", ".join(f"`{t}`" for t in tags))
            if badges:
                lines.append(" · ".join(badges) + "\n")
            if d["rationale"]:
                lines.append(f"_Rationale:_ {d['rationale']}\n")
            if d["quote"]:
                lines.append(f"> {d['quote']}\n")
            if d["dependencies"]:
                lines.append(f"_Dependencies:_ {d['dependencies']}\n")

    if sections:
        lines.append("## Source Sections\n")
        for s in sections:
            if not s["content"]:
                continue
            lines.append(f"### {s['section_type'].replace('_', ' ').title()}")
            if s["heading"]:
                lines.append(f"_(matched heading: {s['heading']})_\n")
            content = s["content"]
            if len(content) > 4000:
                content = content[:4000] + "\n\n[...truncated]"
            lines.append("```\n" + content + "\n```\n")

    path.write_text("\n".join(lines))
    return path


def render_index(store: Store, out_dir: Path) -> Path:
    rows = store.papers()
    by_field: dict[str, list] = defaultdict(list)
    for r in rows:
        by_field[r["field"]].append(r)

    lines: list[str] = ["# Vista: research-direction index\n"]
    lines.append(f"This index is auto-generated. Use `sqlite3 {config.DB_PATH}` "
                 "or browse the per-paper files for deeper context.\n")

    n_dirs_by_paper = dict(store.conn.execute(
        "SELECT paper_id, COUNT(*) FROM directions GROUP BY paper_id"
    ).fetchall())
    total_dirs = sum(n_dirs_by_paper.values())
    lines.append(f"**Papers:** {len(rows)} · **Directions:** {total_dirs}\n")

    for field in sorted(by_field):
        flines = sorted(by_field[field], key=lambda r: -(r["cited_by_count"] or 0))
        lines.append(f"\n## {field} ({len(flines)} papers)\n")
        for r in flines:
            n_dirs = n_dirs_by_paper.get(r["id"], 0)
            link_path = paper_relpath(field, r["title"], r["id"])
            year = r["year"] or "?"
            cb = r["cited_by_count"] or 0
            track_tag = f"[{r['track']}]" if r["track"] != "recent" else ""
            lines.append(
                f"- {track_tag} **{r['title']}** ({year}, cited {cb}x, "
                f"{n_dirs} directions): [open]({link_path})"
            )
    path = out_dir / "index.md"
    path.write_text("\n".join(lines))
    return path


def render_by_tag(store: Store, out_dir: Path) -> Path:
    rows = list(store.conn.execute(
        "SELECT d.*, p.title AS paper_title, p.field, p.year, p.cited_by_count "
        "FROM directions d JOIN papers p ON p.id = d.paper_id"
    ))
    by_tag: dict[str, list] = defaultdict(list)
    for d in rows:
        try:
            tags = json.loads(d["field_tags_json"] or "[]")
        except json.JSONDecodeError:
            tags = []
        for t in tags:
            by_tag[t.lower()].append(d)

    lines = ["# Directions by tag\n"]
    for tag in sorted(by_tag, key=lambda t: -len(by_tag[t])):
        items = by_tag[tag]
        lines.append(f"\n## `{tag}` ({len(items)})\n")
        for d in items[:50]:
            link = paper_relpath(d["field"], d["paper_title"], d["paper_id"])
            lines.append(f"- {d['direction']} (from [{d['paper_title']}]({link}))")
    path = out_dir / "by-tag.md"
    path.write_text("\n".join(lines))
    return path


def render_queries(out_dir: Path) -> Path:
    body = """# Example queries

The store is at `DB_PATH`. Use `sqlite3` or
[Datasette](https://datasette.io) (`uv run --with datasette datasette DB_PATH`).

## High-feasibility, recent directions

```sql
SELECT direction, paper_title, year, cited_by_count
FROM v_directions_full
WHERE feasibility = 'high' AND track = 'recent'
ORDER BY cited_by_count DESC
LIMIT 30;
```

## Neglected futures: legacy papers with high citations

```sql
SELECT direction, paper_title, year, cited_by_count
FROM v_directions_full
WHERE track = 'legacy'
ORDER BY cited_by_count DESC
LIMIT 50;
```

## Group directions by tag

```sql
SELECT
  json_each.value AS tag,
  COUNT(*) AS n
FROM directions, json_each(directions.field_tags_json)
GROUP BY tag
ORDER BY n DESC;
```

## Mark a direction as interesting

```sql
UPDATE directions
SET user_status = 'interesting',
    user_notes = 'Maps to my masked-causes work'
WHERE id = 42;
```

## All directions for a single paper

```sql
SELECT direction, feasibility, novelty
FROM directions
WHERE paper_id = 'W2741809807';
```
"""
    path = out_dir / "queries.md"
    path.write_text(body.replace("DB_PATH", str(config.DB_PATH)))
    return path


def render_all(store: Store, out_dir: Path | None = None) -> dict[str, int]:
    out_dir = out_dir or config.OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = store.papers()
    n_paper_files = 0
    for r in rows:
        render_paper_md(store, r, out_dir)
        n_paper_files += 1
    render_index(store, out_dir)
    render_by_tag(store, out_dir)
    render_queries(out_dir)
    return {"papers": n_paper_files}
