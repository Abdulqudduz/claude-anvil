#!/usr/bin/env python3
"""Portable Fiction Cliche and Craft Auditor for Anvil.

Audits fiction manuscripts (Markdown, LaTeX, text) for prohibited cliches,
stock body reactions, dead metaphors, and adverb dialogue tags.

Usage:
  python3 scripts/check_fiction_cliches.py "chapters/*.md"
  python3 scripts/check_fiction_cliches.py chapter1.md chapter2.md
  cat chapter1.md | python3 scripts/check_fiction_cliches.py --stdin
  echo '{"tool_input": {"file_path": "ch1.md", "content": "..."}}' | python3 scripts/check_fiction_cliches.py --hook

Exit codes:
  0: Clean (no cliches found or non-manuscript file)
  2: Cliche violation found
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent

def find_patterns_file(project_dir: Path) -> Path:
    # 1. Project-local override
    local_patterns = project_dir / ".worldsmith/patterns.md"
    if local_patterns.is_file():
        return local_patterns
    # 2. Anvil assets
    anvil_patterns = ROOT / "assets/exemplars/patterns.md"
    if anvil_patterns.is_file():
        return anvil_patterns
    # 3. Bundled fallback
    fallback = ROOT / "worldsmith/scripts/patterns.md"
    return fallback


def is_manuscript_path(file_path: Path) -> bool:
    name = file_path.name.lower()
    # Skip non-manuscript files
    if name in {"readme.md", "claude.md", "skill.md", "license", "todo.md", "project.yaml"}:
        return False
    parts = [p.lower() for p in file_path.parts]
    if "docs" in parts or "plans" in parts or "world" in parts or ".worldsmith" in parts:
        return False
    ext = file_path.suffix.lower()
    return ext in {".md", ".tex", ".txt", ".markdown"}


def check_text_with_count_patterns(text: str, label: str, patterns_path: Path) -> int:
    import subprocess
    cmd = [
        sys.executable,
        str(ROOT / "scripts/count_patterns.py"),
        "--check-text",
        "--label", label,
        str(patterns_path),
    ]
    proc = subprocess.run(cmd, input=text, text=True, capture_output=True)
    if proc.returncode != 0:
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        if proc.stdout:
            sys.stdout.write(proc.stdout)
        return proc.returncode
    return 0


def main() -> int:
    args = sys.argv[1:]
    project_dir = Path(".").resolve()
    patterns_file = find_patterns_file(project_dir)

    # Hook mode (JSON on stdin)
    if "--hook" in args or (not args and not sys.stdin.isatty()):
        try:
            content = sys.stdin.read()
            if not content.strip():
                return 0
            try:
                payload = json.loads(content)
                if isinstance(payload, dict):
                    tool_input = payload.get("tool_input") or {}
                    raw_path = tool_input.get("file_path") or ""
                    file_path = Path(raw_path)
                    if not is_manuscript_path(file_path):
                        return 0
                    text = tool_input.get("content") or tool_input.get("new_string") or ""
                    return check_text_with_count_patterns(text, raw_path, patterns_file)
            except json.JSONDecodeError:
                # Plain text
                return check_text_with_count_patterns(content, "stdin", patterns_file)
        except Exception as e:
            print(f"Error processing cliche hook stdin: {e}", file=sys.stderr)
            return 0

    # Direct files or glob pattern
    patterns_to_check = [a for a in args if not a.startswith("--")]
    if not patterns_to_check:
        print("Usage: check_fiction_cliches.py <files-or-glob>", file=sys.stderr)
        return 0

    files: List[Path] = []
    for pat in patterns_to_check:
        matched = [Path(p) for p in glob.glob(pat, recursive=True)]
        if matched:
            files.extend(matched)
        else:
            files.append(Path(pat))

    has_violation = False
    for path in files:
        if not path.is_file():
            continue
        if not is_manuscript_path(path):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rc = check_text_with_count_patterns(text, str(path), patterns_file)
        if rc != 0:
            has_violation = True

    return 2 if has_violation else 0


if __name__ == "__main__":
    sys.exit(main())
