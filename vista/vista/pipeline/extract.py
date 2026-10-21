"""Extract Future Work / Limitations / Discussion / Conclusion sections from PDFs.

Three strategies, most structured first. Each section type is taken from the
first strategy that finds it, so a later strategy only fills gaps:

1. ``outline``: the PDF's own bookmarks (``doc.get_toc()``), which hyperref
   emits for most LaTeX papers. Section boundaries come from the outline, so
   no heading has to be guessed from body text.
2. ``font``: heading lines detected from span geometry (larger than the body
   font, or bold), via ``page.get_text("dict")``.
3. ``regex``: the plain-text walker in :func:`find_sections`, for PDFs with
   neither an outline nor typographic headings.

In every strategy, deciding *which* heading is a "Future Work" heading is a
classification of a short title string against :data:`SECTION_PATTERNS`.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from vista.storage.db import Section, Store

log = logging.getLogger(__name__)

# Optional leading section number: decimal ("6", "6.", "6.1") or upper-case
# roman ("VI", "VI."). There is no "Chapter N" form.
_NUM = r"(?:\d+(?:\.\d+)*\.?\s+|[IVX]+\.?\s+)?"

# Heading patterns we treat as the start of a section we care about, matched
# against a whole stripped heading line or outline title. Order matters: the
# first match wins, so combined headings ("Discussion and Future Work") land
# in future_work.
SECTION_PATTERNS: dict[str, re.Pattern] = {
    "future_work": re.compile(
        rf"^\s*{_NUM}"
        r"(?:(?:conclusions?|limitations?|summary|discussion)\s+and\s+)?"
        r"(future\s+work|future\s+research|future\s+directions?|open\s+(?:problems?|questions?|directions?)|outlook)"
        r"\s*[:\.]?\s*$",
        re.IGNORECASE,
    ),
    "limitations": re.compile(
        rf"^\s*{_NUM}"
        r"(?:(?:conclusions?|discussion)\s+and\s+)?"
        r"(limitations?(?:\s+and\s+broader\s+impacts?)?|threats\s+to\s+validity|caveats)"
        r"\s*[:\.]?\s*$",
        re.IGNORECASE,
    ),
    "discussion": re.compile(
        rf"^\s*{_NUM}"
        r"(discussion|discussion\s+and\s+conclusions?)"
        r"\s*[:\.]?\s*$",
        re.IGNORECASE,
    ),
    "conclusion": re.compile(
        rf"^\s*{_NUM}"
        r"(conclusions?|concluding\s+remarks|summary\s+and\s+conclusions?)"
        r"\s*[:\.]?\s*$",
        re.IGNORECASE,
    ),
}
SECTION_ORDER = list(SECTION_PATTERNS)

# Generic heading: a short numbered line of mostly title-case words, used by
# the regex walker to terminate capture. Conservative, tuned to avoid eating
# body paragraphs.
GENERIC_HEADING = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\.?\s+|[IVX]+\.\s+|[A-Z]\.\s+)"
    r"[A-Z][A-Za-z0-9\-:,&\s]{2,80}\s*$"
)
REFS_HEADING = re.compile(
    rf"^\s*{_NUM}"
    r"(references|bibliography|acknowledge?ments?|appendix(?:\s+[A-Z0-9]+)?|appendices|supplementary\s+material)"
    r"\s*[:\.]?\s*$",
    re.IGNORECASE)
MAX_SECTION_LINES = 200  # safety cap, every strategy

# Bump whenever a change could find sections an earlier version missed (new
# strategy, new heading patterns). Empty placeholders written by an older
# version are then re-extracted automatically. 1 = the regex-only extractor.
EXTRACTOR_VERSION = 2
MAX_HEADING_CHARS = 80

# Font heuristic: a line is a heading if it is short and either noticeably
# larger than the body font or entirely bold at (about) body size.
HEADING_SIZE_RATIO = 1.15
_BOLD_FLAG = 16  # PyMuPDF span flag bit for bold


@dataclass
class ExtractedSection:
    section_type: str
    heading: str
    content: str
    method: str = "regex"


def classify_heading(title: str) -> str | None:
    """The tracked section type a heading string names, or None."""
    for stype, pat in SECTION_PATTERNS.items():
        if pat.match(title.strip()):
            return stype
    return None


def _heading_key(s: str) -> str:
    """Comparable form of a heading: numbering stripped, alphanumerics only."""
    s = re.sub(rf"^\s*{_NUM}", "", s.strip())
    return "".join(ch for ch in s.casefold() if ch.isalnum())


def _clip_body(lines: list[str]) -> str:
    """Cut a captured body at a references/appendix heading and the line cap."""
    body: list[str] = []
    for line in lines:
        if REFS_HEADING.match(line.strip()) or len(body) >= MAX_SECTION_LINES:
            break
        body.append(line.rstrip())
    return "\n".join(body).strip()


def _keep_longest(sections: list[ExtractedSection]) -> list[ExtractedSection]:
    """If a type is found more than once (e.g. per-chapter conclusions), keep
    the longest: typically the one with the meaningful content."""
    by_type: dict[str, ExtractedSection] = {}
    for s in sections:
        cur = by_type.get(s.section_type)
        if cur is None or len(s.content) > len(cur.content):
            by_type[s.section_type] = s
    return [by_type[k] for k in SECTION_ORDER if k in by_type]


# ---------------------------------------------------------------------------
# Strategy 1: PDF outline
# ---------------------------------------------------------------------------

def _page_lines(doc) -> tuple[list[str], list[int]]:
    """All text lines in reading order, plus the index where each page starts."""
    lines: list[str] = []
    starts: list[int] = []
    for page in doc:
        starts.append(len(lines))
        lines.extend(page.get_text().splitlines())
    return lines, starts


def _locate(lines: list[str], key: str, lo: int, hi: int) -> tuple[int, int] | None:
    """Find a heading line (or a heading wrapped over two lines) in lines[lo:hi].

    Returns (index, number_of_heading_lines) or None.
    """
    for i in range(lo, min(hi, len(lines))):
        if _heading_key(lines[i]) == key:
            return i, 1
        if i + 1 < len(lines) and _heading_key(lines[i] + " " + lines[i + 1]) == key:
            return i, 2
    return None


def sections_from_outline(doc) -> list[ExtractedSection]:
    toc = doc.get_toc(simple=True)  # [[level, title, page (1-based, -1 if none)], ...]
    if not toc:
        return []
    lines, starts = _page_lines(doc)
    # Body start/end for each outline entry, in outline (document) order.
    located: list[tuple[int, int]] = []  # (heading_index, body_start)
    cursor = 0
    for _level, title, page in toc:
        lo = max(cursor, starts[page - 1]) if 1 <= page <= len(starts) else cursor
        hi = starts[page + 1] if 0 <= page + 1 < len(starts) else len(lines)
        hit = _locate(lines, _heading_key(title), lo, hi)
        if hit:
            idx, n = hit
            located.append((idx, idx + n))
            cursor = idx + n
        else:  # heading text not found: assume the section starts where we are
            located.append((lo, lo))
            cursor = lo
    found: list[ExtractedSection] = []
    for k, (level, title, _page) in enumerate(toc):
        stype = classify_heading(title)
        if not stype:
            continue
        end = next(
            (located[j][0] for j in range(k + 1, len(toc)) if toc[j][0] <= level),
            len(lines),
        )
        content = _clip_body(lines[located[k][1]:end])
        if content:
            found.append(ExtractedSection(stype, title.strip(), content, "outline"))
    return _keep_longest(found)


# ---------------------------------------------------------------------------
# Strategy 2: typographic headings
# ---------------------------------------------------------------------------

@dataclass
class _StyledLine:
    text: str
    size: float
    bold: bool


def _styled_lines(doc) -> list[_StyledLine]:
    out: list[_StyledLine] = []
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):  # image blocks have no lines
                spans = [s for s in line["spans"] if s["text"].strip()]
                if not spans:
                    continue
                out.append(_StyledLine(
                    text=" ".join(s["text"].strip() for s in spans),
                    size=max(s["size"] for s in spans),
                    bold=all(s["flags"] & _BOLD_FLAG or "bold" in s["font"].lower()
                             for s in spans),
                ))
    return out


def sections_from_fonts(doc) -> list[ExtractedSection]:
    lines = _styled_lines(doc)
    if not lines:
        return []
    weights: Counter[float] = Counter()
    for ln in lines:
        weights[round(ln.size, 1)] += len(ln.text)
    body_size = weights.most_common(1)[0][0]

    def is_heading(ln: _StyledLine) -> bool:
        if len(ln.text) > MAX_HEADING_CHARS:
            return False
        return ln.size >= body_size * HEADING_SIZE_RATIO or (ln.bold and ln.size >= body_size - 0.5)

    found: list[ExtractedSection] = []
    for i, ln in enumerate(lines):
        stype = classify_heading(ln.text) if is_heading(ln) else None
        if not stype:
            continue
        end = next((j for j in range(i + 1, len(lines)) if is_heading(lines[j])), len(lines))
        content = _clip_body([x.text for x in lines[i + 1:end]])
        if content:
            found.append(ExtractedSection(stype, ln.text, content, "font"))
    return _keep_longest(found)


# ---------------------------------------------------------------------------
# Strategy 3: plain-text heading regex
# ---------------------------------------------------------------------------

def find_sections(text: str) -> list[ExtractedSection]:
    """Locate sections by scanning plain-text lines for headings.

    For each line we test against the known section patterns; on match we
    capture subsequent lines until: another tracked heading, a references /
    appendix heading, a likely generic heading, three blank lines after at
    least 5 captured lines, or the MAX_SECTION_LINES cap.
    """
    lines = text.splitlines()
    found: list[ExtractedSection] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match_type = classify_heading(line)
        if not match_type:
            i += 1
            continue

        body: list[str] = []
        j = i + 1
        blank_streak = 0
        while j < len(lines) and len(body) < MAX_SECTION_LINES:
            raw = lines[j].rstrip()
            stripped = raw.strip()
            if REFS_HEADING.match(stripped) or classify_heading(stripped):
                break
            # Stop at a likely generic heading after a few lines. Exception:
            # long numbered lines ("2. Better calibration under distribution
            # shift across many domains") are enumerated content, not headings.
            if len(body) > 3 and GENERIC_HEADING.match(stripped) and len(stripped) < 80:
                if not (stripped[:1].isdigit() and len(stripped.split()) > 6):
                    break
            body.append(raw)
            blank_streak = blank_streak + 1 if not stripped else 0
            if blank_streak >= 3 and len(body) > 5:
                break
            j += 1

        content = "\n".join(body).strip()
        if content:
            found.append(ExtractedSection(match_type, line, content, "regex"))
        i = max(j, i + 1)
    return _keep_longest(found)


def _regex_strategy(doc) -> list[ExtractedSection]:
    return find_sections("\n".join(page.get_text() for page in doc))


STRATEGIES: list[Callable] = [sections_from_outline, sections_from_fonts, _regex_strategy]


def extract_paper(pdf_path: Path) -> list[ExtractedSection]:
    """Run each strategy in order; a later one only fills section types still missing."""
    found: dict[str, ExtractedSection] = {}
    with pymupdf.open(pdf_path) as doc:
        for strategy in STRATEGIES:
            for s in strategy(doc):
                found.setdefault(s.section_type, s)
    return [found[k] for k in SECTION_ORDER if k in found]


def should_extract(section_rows, *, retry_empty: bool = False) -> bool:
    """The one rule for whether a paper's sections should be (re-)extracted.

    Yes when it has no rows, or only empty placeholders that are an ``error``
    (possibly transient), were written by an older extractor (which may have
    missed what the current strategies find), or `retry_empty` forces it.
    A paper with any real section text is final.
    """
    if not section_rows:
        return True
    if any(r["content"] for r in section_rows):
        return False
    return retry_empty or any(
        r["method"] == "error" or (r["extractor_version"] or 1) < EXTRACTOR_VERSION
        for r in section_rows
    )


def extract_and_store(store: Store, paper_id: str, pdf_path: Path) -> list[ExtractedSection]:
    """Extract a paper's sections into the store, replacing any earlier rows.

    Always leaves at least one row: when nothing is found (method ``empty``)
    or the PDF cannot be parsed (method ``error``), a placeholder with empty
    content is written. Every row records EXTRACTOR_VERSION, so
    `should_extract` can tell a final result from a stale or failed one.
    """
    try:
        secs = extract_paper(pdf_path)
        placeholder = "empty"
    except Exception as e:  # PyMuPDF raises several unrelated types on bad PDFs
        log.warning("extract failed for %s: %s", paper_id, e)
        secs, placeholder = [], "error"
    rows = [
        Section(paper_id, s.section_type, s.heading, s.content, s.method, EXTRACTOR_VERSION)
        for s in secs
    ] or [Section(paper_id, "conclusion", None, "", placeholder, EXTRACTOR_VERSION)]
    store.replace_sections(paper_id, rows)
    return secs


def run_extract(store: Store, *, max_papers: int | None = None,
                retry_empty: bool = False) -> dict[str, int]:
    """Extract every paper that `should_extract` selects (see its rules)."""
    rows = store.papers(needs_extraction=True) + [
        r for r in store.papers(only_placeholders=True)
        if should_extract(store.get_sections(r["id"]), retry_empty=retry_empty)
    ]
    if max_papers:
        rows = rows[:max_papers]
    out = {"attempted": 0, "with_sections": 0, "no_sections": 0}
    for row in rows:
        out["attempted"] += 1
        pdf_path = Path(row["pdf_path"])
        if not pdf_path.exists():
            log.warning("PDF missing on disk: %s", pdf_path)
            continue
        found = extract_and_store(store, row["id"], pdf_path)
        out["with_sections" if found else "no_sections"] += 1
    return out
