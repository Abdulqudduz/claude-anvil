# pub-pipeline

A Claude Code plugin for publication workflows:

- **R packages**: CRAN (and R-universe status), then JOSS, then optionally JSS
- **Python packages**: PyPI, via trusted publishing

## Skills

Each skill is also a slash command.

| Command | Purpose |
|---------|---------|
| `/pub-pipeline:r-publish` | Orchestrate the full R pipeline: CRAN, JOSS, optional JSS |
| `/pub-pipeline:cran-audit` | Audit an R package against CRAN Repository Policy |
| `/pub-pipeline:joss-audit` | Review a package and `paper.md` against the JOSS reviewer checklist |
| `/pub-pipeline:joss-draft` | Draft `paper.md` and `paper.bib` for JOSS |
| `/pub-pipeline:pypi-publish` | Audit, build, and publish to PyPI |

Saying "publish my R package" or "publish my Python package" also triggers the matching skill.

## Multi-Agent JOSS System

`/pub-pipeline:joss-draft` and `/pub-pipeline:joss-audit` dispatch two orchestrator agents and relay their questions back to you:

- **joss-writer** drafts `paper.md` and `paper.bib`, spawning **field-scout** to map competing packages (BibTeX sourced from DOIs; unverified entries are labeled).
- **joss-reviewer** spawns **software-auditor**, **community-auditor**, and **field-scout** in parallel, then synthesizes one gap report.

## Configuration

Copy `docs/user-config-template.md` to `.claude/pub-pipeline.local.md` in your project:

```yaml
author:
  name: "Your Name"
  orcid: "0000-0000-0000-0000"
  email: "you@example.com"
  affiliation: "Your Institution"
```

The config holds author metadata, competing packages, the R-universe user, AI usage disclosure, and related work.

## Installation

```bash
/plugin marketplace add queelius/claude-anvil
/plugin install pub-pipeline@queelius-plugins
```

## Prerequisites

- **R packages**: R with `devtools`, `covr`, `testthat`, `urlchecker`, `rhub`; `gh` CLI
- **JOSS papers**: `pandoc`; Docker for the `openjournals/inara` build (optional)
- **Python packages**: `build` and `twine>=6.1` (or `uv`), `pytest`; `gh` CLI for trusted-publisher releases

## Reference Documents

- `docs/user-config-template.md`: shared user configuration template
- `docs/cran-reference.md`: CRAN Repository Policy and submission checklist
- `docs/joss-reference.md`: JOSS requirements and reviewer checklist
- `docs/joss-exemplars.md`: a JOSS paper in the current required format, analyzed
- `docs/pypi-reference.md`: PyPI metadata, trusted publisher workflow, token fallback

## License

MIT
