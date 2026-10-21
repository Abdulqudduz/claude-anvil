"""vista CLI."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from vista import config
from vista.config import (
    DEFAULT_MODEL,
    FIELDS,
    PREMIUM_MODEL,
    RunConfig,
    ensure_dirs,
    validate_fields,
)
from vista.pipeline.analyze import run_analyze
from vista.pipeline.discover import run_discover
from vista.pipeline.extract import run_extract
from vista.pipeline.fetch import run_fetch
from vista.render.markdown import render_all
from vista.sources.bibtex import discover_bibs, seed_from_bib
from vista.storage.db import Store

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Mine 'future work' sections from highly-cited papers.",
)
console = Console()
ALL_FIELDS = ",".join(FIELDS)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )


def _open_store() -> Store:
    ensure_dirs()
    return Store.open()


def _build_config(fields: str, track: str, per_field: int, legacy_per_field: int,
                  year_min_recent: int, model: str) -> RunConfig:
    try:
        field_list = validate_fields(f.strip() for f in fields.split(",") if f.strip())
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e
    return RunConfig(
        fields=field_list,
        track=track,
        per_field_limit=per_field,
        legacy_per_field_limit=legacy_per_field,
        year_min_recent=year_min_recent,
        model=model,
    )


@app.command()
def discover(
    fields: str = typer.Option(ALL_FIELDS, help="comma-separated"),
    track: str = typer.Option("recent", help="recent | legacy | both"),
    per_field: int = typer.Option(25),
    legacy_per_field: int = typer.Option(8),
    year_min_recent: int = typer.Option(2020),
    verbose: bool = typer.Option(False, "-v"),
):
    """Discover papers via OpenAlex and store metadata."""
    _setup_logging(verbose)
    cfg = _build_config(fields, track, per_field, legacy_per_field, year_min_recent,
                        DEFAULT_MODEL)
    with _open_store() as store:
        run_id = store.begin_run(asdict(cfg))
        counts = run_discover(store, cfg)
        store.finish_run(run_id, notes=json.dumps({"discover": counts}))
    _print_counts("Discovered", counts)


@app.command()
def fetch(
    max_papers: int = typer.Option(0, help="0 = all"),
    retry_failed: bool = typer.Option(False, "--retry-failed",
                                      help="also retry papers whose fetch failed before"),
    verbose: bool = typer.Option(False, "-v"),
):
    """Download PDFs for papers we have arXiv / OA URLs for."""
    _setup_logging(verbose)
    with _open_store() as store:
        counts = run_fetch(store, max_papers=max_papers or None, retry_failed=retry_failed)
    _print_counts("Fetch", counts)


@app.command()
def extract(
    max_papers: int = typer.Option(0, help="0 = all"),
    retry_empty: bool = typer.Option(False, "--retry-empty",
                                     help="also re-extract papers where nothing was found"),
    verbose: bool = typer.Option(False, "-v"),
):
    """Extract Future Work / Limitations / etc. sections from PDFs."""
    _setup_logging(verbose)
    with _open_store() as store:
        counts = run_extract(store, max_papers=max_papers or None, retry_empty=retry_empty)
    _print_counts("Extract", counts)


@app.command()
def analyze(
    max_papers: int = typer.Option(0, help="0 = all"),
    premium: bool = typer.Option(False, "--premium", help="use PREMIUM_MODEL instead of DEFAULT_MODEL"),
    model: str = typer.Option("", help="explicit model id; overrides --premium"),
    verbose: bool = typer.Option(False, "-v"),
):
    """Run the LLM analyzer to extract structured directions."""
    _setup_logging(verbose)
    chosen = model or (PREMIUM_MODEL if premium else DEFAULT_MODEL)
    with _open_store() as store:
        counts = run_analyze(store, model=chosen, max_papers=max_papers or None)
    _print_counts(f"Analyze (model={chosen})", counts)


@app.command()
def render(
    out: Path | None = typer.Option(None, help="output directory (default: VISTA_OUT_DIR)"),
    verbose: bool = typer.Option(False, "-v"),
):
    """Render the store to browseable markdown."""
    _setup_logging(verbose)
    out = out or config.OUT_DIR
    with _open_store() as store:
        counts = render_all(store, out_dir=out)
    _print_counts("Render", counts)
    console.print(f"\nOpen [bold]{out / 'index.md'}[/bold]")


@app.command("seed-bib")
def seed_bib(
    paths: list[Path] = typer.Argument(..., help=".bib files or directories"),
    field: str = typer.Option(..., help="field to assign these seed papers"),
    track: str = typer.Option("seed"),
    verbose: bool = typer.Option(False, "-v"),
):
    """Ingest .bib entries, resolve via OpenAlex, store with track=seed."""
    _setup_logging(verbose)
    bib_files: list[Path] = []
    for p in paths:
        if p.is_dir():
            bib_files.extend(discover_bibs([p]))
        elif p.exists():
            bib_files.append(p)
    if not bib_files:
        raise typer.BadParameter("no .bib files found")
    with _open_store() as store:
        counts = seed_from_bib(store, bib_files, field=field, track=track)
    _print_counts(f"Seed ({len(bib_files)} bib files)", counts)


@app.command()
def status():
    """Show counts of papers, sections, directions per field/track."""
    with _open_store() as store:
        counts = store.status_counts()
    table = Table(title="vista store")
    columns = ("field", "track", "papers", "with_pdf", "with_sections", "with_directions")
    for c in columns:
        table.add_column(c.replace("_", " "), justify="left" if c in ("field", "track") else "right")
    for r in counts["by_field_track"]:
        table.add_row(*(str(r[c] or 0) if c not in ("field", "track") else r[c] for c in columns))
    console.print(table)
    t = counts["totals"]
    console.print(f"papers: {t['papers']}  directions: {t['directions']}")


@app.command()
def pipeline(
    fields: str = typer.Option(ALL_FIELDS),
    track: str = typer.Option("recent"),
    per_field: int = typer.Option(10),
    legacy_per_field: int = typer.Option(5),
    year_min_recent: int = typer.Option(2020),
    skip_analyze: bool = typer.Option(False, "--skip-analyze",
                                       help="run discover/fetch/extract only"),
    premium: bool = typer.Option(False, "--premium"),
    verbose: bool = typer.Option(False, "-v"),
):
    """Run discover -> fetch -> extract -> analyze -> render end-to-end."""
    _setup_logging(verbose)
    cfg = _build_config(fields, track, per_field, legacy_per_field, year_min_recent,
                        model=PREMIUM_MODEL if premium else DEFAULT_MODEL)
    with _open_store() as store:
        run_id = store.begin_run({**asdict(cfg), "skip_analyze": skip_analyze})
        notes: dict = {}
        notes["discover"] = run_discover(store, cfg)
        _print_counts("Discovered", notes["discover"])
        notes["fetch"] = run_fetch(store)
        _print_counts("Fetch", notes["fetch"])
        notes["extract"] = run_extract(store)
        _print_counts("Extract", notes["extract"])
        if not skip_analyze:
            notes["analyze"] = run_analyze(store, model=cfg.model)
            _print_counts(f"Analyze (model={cfg.model})", notes["analyze"])
        notes["render"] = render_all(store)
        _print_counts("Render", notes["render"])
        store.finish_run(run_id, notes=json.dumps(notes))
    console.print(f"\n[green]Done.[/green] Open [bold]{config.OUT_DIR / 'index.md'}[/bold]")


def _print_counts(label: str, counts: dict) -> None:
    console.print(f"\n[bold]{label}:[/bold]")
    for k, v in counts.items():
        console.print(f"  {k}: {v}")


if __name__ == "__main__":
    app()
