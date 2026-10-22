#!/usr/bin/env python3
"""Project type classifier for the Anvil universal agent skill.

Classifies a project directory into one of:
- academic-paper
- fiction-novel
- technical-textbook
- software-package
- kdp-book
- content-site
- general-repo
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, List


def detect_project_type(target_dir: str | Path = ".") -> Dict[str, Any]:
    path = Path(target_dir).resolve()

    signals: Dict[str, List[str]] = {
        "academic-paper": [],
        "fiction-novel": [],
        "technical-textbook": [],
        "software-package": [],
        "kdp-book": [],
        "content-site": [],
    }

    # 1. Academic Paper signals
    if (path / ".papermill").is_dir() or (path / "papermill").is_dir() or "papermill" in path.name.lower():
        signals["academic-paper"].append("Papermill markers")
    if (path / "paper.tex").is_file() or (path / "paper.md").is_file():
        signals["academic-paper"].append("paper.tex / paper.md")
    if list(path.glob("*.bib")):
        signals["academic-paper"].append("BibTeX bibliography")

    # 2. Fiction Novel signals
    if (path / ".worldsmith").is_dir() or "worldsmith" in path.name.lower():
        signals["fiction-novel"].append("Worldsmith markers")
    if (path / "project.yaml").is_file() or (path / "world/timeline.md").is_file() or (path / "world/lore.md").is_file():
        signals["fiction-novel"].append("worldsmith project.yaml or world/ docs")
    if (path / "timeline.md").is_file():
        signals["fiction-novel"].append("timeline.md")

    # 3. Technical Textbook signals
    if (path / "bookwright.config.yaml").is_file() or "bookwright" in path.name.lower():
        signals["technical-textbook"].append("Bookwright markers")
    if (path / "docs/superpowers/plans").is_dir():
        signals["technical-textbook"].append("superpowers design plans")
    if list(path.glob("notebooks/*.ipynb")) and list(path.glob("chapters/*.tex")):
        signals["technical-textbook"].append("paired notebooks and LaTeX chapters")

    # 4. Software Package signals
    if (path / "DESCRIPTION").is_file():
        signals["software-package"].append("R DESCRIPTION file")
    if (path / "pyproject.toml").is_file():
        signals["software-package"].append("pyproject.toml")
    if "pub-pipeline" in path.name.lower() or (path / "pub-pipeline").is_dir():
        signals["software-package"].append("pub-pipeline publication workflow")
    if (path / "paper.md").is_file() and ((path / "DESCRIPTION").is_file() or (path / "pyproject.toml").is_file()):
        signals["software-package"].append("JOSS candidate paper")

    # 5. KDP Book signals
    if (path / ".claude/kdp.local.md").is_file() or (path / ".anvil/kdp.local.md").is_file() or "kdp" in path.name.lower():
        signals["kdp-book"].append("KDP markers / configuration")

    # 6. Static / Content Site signals
    if (path / "config.toml").is_file() or (path / "hugo.toml").is_file() or (path / "content").is_dir():
        signals["content-site"].append("Hugo static site configuration")

    # Universal Anvil config
    if (path / ".anvil/config.local.md").is_file():
        # Check sections in .anvil/config.local.md
        text = (path / ".anvil/config.local.md").read_text(encoding="utf-8", errors="ignore")
        if "kdp:" in text:
            signals["kdp-book"].append(".anvil/config.local.md [kdp]")
        if "publication:" in text or "r_package:" in text:
            signals["software-package"].append(".anvil/config.local.md [publication/r_package]")

    # Score categories
    ranked = sorted(signals.items(), key=lambda kv: len(kv[1]), reverse=True)
    best_type, best_signals = ranked[0]

    if not best_signals:
        primary_type = "general-repo"
        confidence = "low"
    elif len(best_signals) >= 2:
        primary_type = best_type
        confidence = "high"
    else:
        primary_type = best_type
        confidence = "medium"

    return {
        "primary_type": primary_type,
        "confidence": confidence,
        "signals": {k: v for k, v in signals.items() if v},
        "target_path": str(path),
    }


if __name__ == "__main__":
    import sys
    import json
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    result = detect_project_type(target)
    print(json.dumps(result, indent=2))
