"""Configuration: fields, citation thresholds, model choices, paths.

Paths are module attributes read at call time (`config.DB_PATH`, not a
`from vista.config import DB_PATH` snapshot), so tests and callers can redirect
storage by patching this module.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from platformdirs import user_data_dir


# Data and output live in a user-scoped directory, not the package directory,
# so the catalog survives plugin updates and is shared between the CLI and
# the MCP server. Override with VISTA_DATA_DIR or VISTA_OUT_DIR for a project-
# local store (e.g., when running the CLI from a checkout).
def _path_from_env_or(default: Path, env: str) -> Path:
    val = os.environ.get(env)
    return Path(val).expanduser().resolve() if val else default


DEFAULT_DATA_DIR = Path(user_data_dir("vista", appauthor="queelius"))
DATA_DIR = _path_from_env_or(DEFAULT_DATA_DIR, "VISTA_DATA_DIR")
PDF_DIR = DATA_DIR / "pdfs"
DB_PATH = DATA_DIR / "papers.db"
OUT_DIR = _path_from_env_or(DATA_DIR / "out", "VISTA_OUT_DIR")


def _package_version() -> str:
    try:
        return version("vista")
    except PackageNotFoundError:  # running from a bare checkout without install
        return "0+unknown"


VERSION = _package_version()
CONTACT_EMAIL = "lex@metafunctor.com"
USER_AGENT = f"vista/{VERSION} (mailto:{CONTACT_EMAIL})"


# OpenAlex API key. Optional: keyless requests work, but share one small daily
# budget per IP address; a free key (https://openalex.org/settings/api) gives
# its own budget, 10x larger. Read at client construction, not import, so a key
# exported after import (or patched in tests) is honored.
def openalex_api_key() -> str | None:
    return os.environ.get("OPENALEX_API_KEY") or None


# OpenAlex concept and source IDs (verified against api.openalex.org May 2026).
#
# Concepts are hierarchical; we filter by concept and (optionally) restrict to
# canonical venues. Some venues like IEEE S&P, CCS, AAAI year proceedings are
# fragmented across yearly sources in OpenAlex, so rather than enumerate every
# year, we fall back to concept + keyword filtering for those fields.
# OpenAlex's `is_oa` flag is conservative: NeurIPS / ICML etc. papers aren't
# flagged OA even though arXiv mirrors exist. We therefore don't pre-filter by
# is_oa. Instead each field declares a `fulltext_filter` strategy:
#   - "arxiv-required": require the work to also live on arXiv (S4306400194).
#     Reliable PDF access. Best for ML/AI, where most major papers preprint.
#   - "venue-only":     filter by canonical venues only; accept paywalls and
#                       skip at fetch time.
#   - "any":            no extra filter; rely on whatever pdf_url / oa_url
#                       OpenAlex returns. Used for ransomware-style topical
#                       searches.
ARXIV_SOURCE_ID = "S4306400194"

FIELDS: dict[str, dict] = {
    "ml": {
        "label": "Machine Learning",
        "concept_ids": ["C119857082"],  # Machine learning
        "fulltext_filter": "arxiv-required",
        "min_citations_recent": 200,
        "min_citations_legacy": 2000,
    },
    "ai": {
        "label": "Artificial Intelligence",
        "concept_ids": ["C154945302"],  # Artificial intelligence
        "fulltext_filter": "arxiv-required",
        "min_citations_recent": 150,
        "min_citations_legacy": 1500,
    },
    "stats": {
        "label": "Statistics",
        "concept_ids": ["C105795698", "C160234255"],  # Statistics, Bayesian inference
        "venue_ids": [
            "S4394736638",  # JASA
            "S119757635",   # Annals of Statistics
            "S172180718",   # Biometrika
            "S145009937",   # JRSS-B
        ],
        "fulltext_filter": "venue-only",
        "min_citations_recent": 30,
        "min_citations_legacy": 300,
    },
    "ransomware": {
        "label": "Ransomware / Backup-based defenses",
        "concept_ids": ["C38652104"],  # Computer security
        # IEEE S&P, CCS are fragmented across year-specific sources; rely on
        # keyword search across abstracts/titles instead.
        "keywords": "ransomware",
        "fulltext_filter": "any",
        "min_citations_recent": 20,
        "min_citations_legacy": 100,
    },
}


def validate_fields(names: Iterable[str]) -> list[str]:
    """Return `names` as a list, raising ValueError on any key not in FIELDS."""
    names = list(names)
    unknown = [n for n in names if n not in FIELDS]
    if unknown:
        raise ValueError(f"unknown field(s) {unknown}; valid: {sorted(FIELDS)}")
    return names


def concept_ids_for(names: Iterable[str]) -> list[str]:
    """Concept ids for the given FIELDS keys (validated)."""
    return [cid for n in validate_fields(names) for cid in FIELDS[n].get("concept_ids", [])]


# Anthropic model defaults for the unattended analyzer path. Default to current
# Sonnet for cost, escalate to Fable for premium runs (--premium flag in CLI).
# Each is overridable by environment variable; the first variable set wins.
# FOLLOWUPS_MODEL is the legacy name for VISTA_MODEL and is still honored.
def _model_from_env(env_vars: tuple[str, ...], default: str) -> str:
    for var in env_vars:
        if val := os.environ.get(var):
            return val
    return default


DEFAULT_MODEL = _model_from_env(("VISTA_MODEL", "FOLLOWUPS_MODEL"), "claude-sonnet-5-5")
PREMIUM_MODEL = _model_from_env(("VISTA_PREMIUM_MODEL",), "claude-fable-5-1")


@dataclass
class RunConfig:
    fields: list[str] = field(default_factory=lambda: list(FIELDS.keys()))
    track: str = "recent"  # recent | legacy | both
    year_min_recent: int = 2020
    year_max_legacy: int = 2019
    year_min_legacy: int = 2005
    per_field_limit: int = 25
    legacy_per_field_limit: int = 8
    model: str = DEFAULT_MODEL


def ensure_dirs() -> None:
    for p in (DATA_DIR, PDF_DIR, OUT_DIR):
        p.mkdir(parents=True, exist_ok=True)
