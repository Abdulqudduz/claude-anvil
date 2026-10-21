"""SQLite store. Idempotent writes; safe to re-run pipeline stages."""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from vista import config

if TYPE_CHECKING:
    from vista.sources.openalex import OpenAlexWork

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Curation states a user can put a direction in (mark_direction). "open" is
# the default for freshly stored directions.
USER_STATUSES = ("open", "interesting", "started", "abandoned")

# Columns added after the first release. CREATE TABLE IF NOT EXISTS cannot add
# them to an existing catalog, so init_schema adds whichever are missing.
_ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "papers": {"fetch_failed_at": "TEXT", "analyzed_at": "TEXT"},
    # NULL means "written before versions were recorded" (extractor version 1).
    "sections": {"extractor_version": "INTEGER"},
}


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def connect(db_path: Path | str) -> sqlite3.Connection:
    # check_same_thread=False: the MCP server keeps one long-lived connection
    # and its host may dispatch tool calls from a worker thread. Calls are
    # still serialized; SQLite itself is in serialized threading mode.
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    for table, cols in _ADDED_COLUMNS.items():
        present = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if present:  # table exists from an older schema
            for col, decl in cols.items():
                if col not in present:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()


def direction_key(text: str) -> str:
    """Natural key for a direction: casefolded, whitespace-collapsed, no trailing period.

    Two submissions of the same direction text (differing only in case or
    spacing) refer to the same row, so re-submitting updates it in place
    instead of duplicating it or wiping the user's curation.
    """
    return " ".join(text.casefold().split()).rstrip(".")


@dataclass
class Paper:
    id: str
    title: str
    field: str
    track: str
    doi: str | None = None
    arxiv_id: str | None = None
    authors_json: str | None = None
    year: int | None = None
    venue: str | None = None
    venue_id: str | None = None
    abstract: str | None = None
    cited_by_count: int | None = None
    oa_url: str | None = None
    pdf_url: str | None = None
    pdf_path: str | None = None
    fetched_at: str | None = None
    raw_json: str | None = None

    @classmethod
    def from_work(cls, w: OpenAlexWork, *, field: str, track: str) -> Paper:
        return cls(
            id=w.id,
            doi=w.doi,
            arxiv_id=w.arxiv_id,
            title=w.title,
            authors_json=json.dumps(w.authors, ensure_ascii=False),
            year=w.year,
            venue=w.venue,
            venue_id=w.venue_id,
            abstract=w.abstract,
            cited_by_count=w.cited_by_count,
            field=field,
            track=track,
            oa_url=w.oa_url,
            pdf_url=w.pdf_url,
            raw_json=json.dumps(w.raw, ensure_ascii=False),
        )


@dataclass
class Section:
    paper_id: str
    section_type: str  # future_work | limitations | conclusion | discussion
    heading: str | None
    content: str
    method: str = "regex"  # outline | font | regex | empty | error (older: regex-empty)
    extractor_version: int | None = None  # pipeline.extract.EXTRACTOR_VERSION that wrote it


@dataclass
class Direction:
    paper_id: str
    direction: str
    rationale: str | None = None
    quote: str | None = None
    field_tags_json: str | None = None
    feasibility: str | None = None
    novelty: str | None = None
    dependencies: str | None = None


_DIRECTION_FIELDS = ("rationale", "quote", "feasibility", "novelty", "dependencies")


def _merge_tags(old_json: str | None, new_json: str | None) -> str:
    merged: list[str] = []
    for raw in (old_json, new_json):
        try:
            tags = json.loads(raw or "[]")
        except json.JSONDecodeError:
            tags = []
        for t in tags:
            if t not in merged:
                merged.append(t)
    return json.dumps(merged, ensure_ascii=False)


class Store:
    """Thin wrapper over sqlite. Methods are idempotent."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @classmethod
    def open(cls, db_path: Path | str | None = None) -> Store:
        conn = connect(db_path if db_path is not None else config.DB_PATH)
        init_schema(conn)
        return cls(conn)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def db_file(self) -> str | None:
        """Path of the main database file, or None for an in-memory store."""
        return self.conn.execute("PRAGMA database_list").fetchone()["file"] or None

    @contextmanager
    def tx(self):
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # --- papers ----------------------------------------------------------

    def upsert_paper(self, p: Paper) -> None:
        d = asdict(p)
        cols = list(d.keys())
        placeholders = ",".join(":" + c for c in cols)
        # pdf_path/fetched_at are owned by the fetch stage; a re-discover (or a
        # live MCP cache_work) builds Papers with pdf_path=None and must not
        # reset fetch provenance on already-fetched rows.
        updates = ",".join(
            (f"{c}=COALESCE(excluded.{c}, papers.{c})"
             if c in ("pdf_path", "fetched_at")
             else f"{c}=excluded.{c}")
            for c in cols if c not in ("id", "discovered_at")
        )
        sql = (
            f"INSERT INTO papers ({','.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}"
        )
        with self.tx():
            self.conn.execute(sql, d)

    def mark_fetched(self, paper_id: str, pdf_path: str) -> None:
        with self.tx():
            self.conn.execute(
                "UPDATE papers SET pdf_path=?, fetched_at=?, fetch_failed_at=NULL WHERE id=?",
                (pdf_path, utc_now(), paper_id),
            )

    def mark_fetch_failed(self, paper_id: str) -> None:
        """Negative cache: bulk fetch skips the paper until retried explicitly."""
        with self.tx():
            self.conn.execute(
                "UPDATE papers SET fetch_failed_at=? WHERE id=?", (utc_now(), paper_id)
            )

    def clear_fetch_failures(self) -> int:
        with self.tx():
            return self.conn.execute(
                "UPDATE papers SET fetch_failed_at=NULL WHERE fetch_failed_at IS NOT NULL"
            ).rowcount

    def mark_analyzed(self, paper_id: str) -> None:
        """Record that the analyzer ran, even if it produced zero directions."""
        with self.tx():
            self.conn.execute(
                "UPDATE papers SET analyzed_at=? WHERE id=?", (utc_now(), paper_id)
            )

    def papers(self, *, field: str | None = None, track: str | None = None,
               needs_pdf: bool = False, needs_extraction: bool = False,
               only_placeholders: bool = False,
               needs_analysis: bool = False) -> list[sqlite3.Row]:
        """Papers filtered by pipeline progress.

        needs_extraction: has a PDF and no sections row at all.
        only_placeholders: has a PDF and section rows, all with empty content
        (extraction ran and found nothing, or failed); whether such a paper is
        re-extracted is decided by pipeline.extract.should_extract.
        """
        clauses, params = [], []
        if field:
            clauses.append("field = ?")
            params.append(field)
        if track:
            clauses.append("track = ?")
            params.append(track)
        if needs_pdf:
            clauses.append(
                "pdf_path IS NULL AND fetch_failed_at IS NULL "
                "AND (oa_url IS NOT NULL OR pdf_url IS NOT NULL OR arxiv_id IS NOT NULL)"
            )
        if needs_extraction:
            clauses.append(
                "pdf_path IS NOT NULL AND id NOT IN (SELECT paper_id FROM sections)"
            )
        if only_placeholders:
            clauses.append(
                "pdf_path IS NOT NULL AND id IN (SELECT paper_id FROM sections "
                "GROUP BY paper_id HAVING MAX(COALESCE(content, '') <> '') = 0)"
            )
        if needs_analysis:
            clauses.append(
                "analyzed_at IS NULL "
                "AND id IN (SELECT paper_id FROM sections WHERE content <> '') "
                "AND id NOT IN (SELECT paper_id FROM directions)"
            )
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM papers{where} ORDER BY cited_by_count DESC NULLS LAST"
        return list(self.conn.execute(sql, params))

    def get_paper(self, paper_id: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM papers WHERE id=?", (paper_id,)).fetchone()

    # --- sections --------------------------------------------------------

    def upsert_sections(self, sections: Iterable[Section]) -> None:
        with self.tx():
            self._upsert_sections(sections)

    def replace_sections(self, paper_id: str, sections: Iterable[Section]) -> None:
        """Make the paper's section rows exactly `sections` (used on re-extraction,
        so a stale placeholder never lingers next to real sections)."""
        with self.tx():
            self.conn.execute("DELETE FROM sections WHERE paper_id=?", (paper_id,))
            self._upsert_sections(sections)

    def _upsert_sections(self, sections: Iterable[Section]) -> None:
        sql = (
            "INSERT INTO sections "
            "(paper_id, section_type, heading, content, method, extractor_version) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(paper_id, section_type) DO UPDATE SET "
            "heading=excluded.heading, content=excluded.content, method=excluded.method, "
            "extractor_version=excluded.extractor_version, extracted_at=CURRENT_TIMESTAMP"
        )
        self.conn.executemany(sql, [
            (s.paper_id, s.section_type, s.heading, s.content, s.method, s.extractor_version)
            for s in sections
        ])

    def get_sections(self, paper_id: str) -> list[sqlite3.Row]:
        return list(self.conn.execute(
            "SELECT * FROM sections WHERE paper_id=? ORDER BY section_type",
            (paper_id,),
        ))

    # --- directions ------------------------------------------------------

    def upsert_directions(self, paper_id: str, directions: Iterable[Direction]) -> int:
        """Add directions, updating any with the same natural key in place.

        Matching rows keep their id, user_status, and user_notes; new non-empty
        fields overwrite old ones and field tags are unioned. Returns the
        number of directions written.
        """
        with self.tx():
            return self._upsert_directions(paper_id, list(directions))

    def replace_directions(self, paper_id: str, directions: Iterable[Direction]) -> int:
        """Make the paper's direction set equal `directions`, except curated rows.

        Rows not in the new set are deleted only when uncurated
        (user_status 'open' and no user_notes); curated rows always survive.
        """
        directions = list(directions)
        keep = {direction_key(d.direction) for d in directions}
        with self.tx():
            n = self._upsert_directions(paper_id, directions)
            for row in self.conn.execute(
                "SELECT id, direction, user_status, user_notes FROM directions WHERE paper_id=?",
                (paper_id,),
            ).fetchall():
                curated = (row["user_status"] or "open") != "open" or row["user_notes"]
                if direction_key(row["direction"]) not in keep and not curated:
                    self.conn.execute("DELETE FROM directions WHERE id=?", (row["id"],))
            return n

    def _upsert_directions(self, paper_id: str, directions: list[Direction]) -> int:
        existing = {
            direction_key(r["direction"]): r
            for r in self.conn.execute("SELECT * FROM directions WHERE paper_id=?", (paper_id,))
        }
        for d in directions:
            old = existing.get(direction_key(d.direction))
            if old is None:
                cur = self.conn.execute(
                    "INSERT INTO directions "
                    "(paper_id, direction, rationale, quote, field_tags_json, "
                    " feasibility, novelty, dependencies) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (paper_id, d.direction, d.rationale, d.quote, d.field_tags_json,
                     d.feasibility, d.novelty, d.dependencies),
                )
                existing[direction_key(d.direction)] = self.conn.execute(
                    "SELECT * FROM directions WHERE id=?", (cur.lastrowid,)
                ).fetchone()
                continue
            merged = {f: getattr(d, f) or old[f] for f in _DIRECTION_FIELDS}
            self.conn.execute(
                "UPDATE directions SET direction=?, rationale=?, quote=?, feasibility=?, "
                "novelty=?, dependencies=?, field_tags_json=?, analyzed_at=CURRENT_TIMESTAMP "
                "WHERE id=?",
                (d.direction, merged["rationale"], merged["quote"], merged["feasibility"],
                 merged["novelty"], merged["dependencies"],
                 _merge_tags(old["field_tags_json"], d.field_tags_json), old["id"]),
            )
        return len(directions)

    def get_directions(self, paper_id: str) -> list[sqlite3.Row]:
        return list(self.conn.execute(
            "SELECT * FROM directions WHERE paper_id=? ORDER BY id", (paper_id,)
        ))

    def set_direction_status(self, direction_id: int, status: str,
                             notes: str | None = None) -> bool:
        """Curate a direction. Returns False if no direction has that id."""
        if status not in USER_STATUSES:
            raise ValueError(f"invalid status {status!r}; valid: {list(USER_STATUSES)}")
        with self.tx():
            cur = self.conn.execute(
                "UPDATE directions SET user_status=?, user_notes=COALESCE(?, user_notes) "
                "WHERE id=?",
                (status, notes, direction_id),
            )
        return cur.rowcount > 0

    # --- reporting -------------------------------------------------------

    def status_counts(self) -> dict[str, Any]:
        """Per (field, track) pipeline progress plus overall totals."""
        rows = [dict(r) for r in self.conn.execute(
            """
            SELECT p.field, p.track,
                   COUNT(*) AS papers,
                   SUM(p.pdf_path IS NOT NULL) AS with_pdf,
                   SUM(EXISTS(SELECT 1 FROM sections s
                              WHERE s.paper_id=p.id AND s.content <> '')) AS with_sections,
                   SUM(EXISTS(SELECT 1 FROM directions d WHERE d.paper_id=p.id)) AS with_directions
            FROM papers p
            GROUP BY p.field, p.track
            ORDER BY p.field, p.track
            """
        )]
        totals = dict(self.conn.execute(
            "SELECT (SELECT COUNT(*) FROM papers) AS papers, "
            "       (SELECT COUNT(*) FROM directions) AS directions"
        ).fetchone())
        return {"totals": totals, "by_field_track": rows}

    # --- runs ------------------------------------------------------------

    def begin_run(self, config_: dict[str, Any]) -> int:
        with self.tx():
            cur = self.conn.execute(
                "INSERT INTO runs (config_json) VALUES (?)", (json.dumps(config_),)
            )
            return cur.lastrowid or 0

    def finish_run(self, run_id: int, notes: str = "") -> None:
        with self.tx():
            self.conn.execute(
                "UPDATE runs SET finished_at=CURRENT_TIMESTAMP, notes=? WHERE id=?",
                (notes, run_id),
            )
