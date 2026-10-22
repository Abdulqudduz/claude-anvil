#!/usr/bin/env python3
"""Portable LaTeX Macro-Leak Auditor for Anvil.

Audits LaTeX (.tex) files to prevent internal source-tool detail from leaking
into reader-visible prose.

Checks:
- \\texttt{\\textbackslash foo} macro literals in prose
- The phrase "the macro" in prose
- Reader-visible references to the project notation package (<macro_package>.sty)

Usage Modes:
1. Direct CLI arguments:
     python3 scripts/check_latex_macro_leak.py chapter1.tex chapter2.tex
2. Stdin text:
     cat chapter1.tex | python3 scripts/check_latex_macro_leak.py --stdin
3. Hook mode (stdin JSON):
     echo '{"tool_input": {"file_path": "ch.tex", "content": "..."}}' | python3 scripts/check_latex_macro_leak.py --hook

Exit codes:
- 0: Clean (no leaks found)
- 2: Leak detected (details printed to stderr)
- 1: Invocation error
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import List, Optional

# A '%' not preceded by a backslash starts a comment that runs to end of line
COMMENT = re.compile(r"(?<!\\)%.*$", re.MULTILINE)
TEXTTT_MACRO = re.compile(r"\\texttt\{\\textbackslash ?[A-Za-z]")
THE_MACRO = re.compile(r"\bthe macro\b", re.IGNORECASE)
SKIP_BASENAMES = {"preamble.tex"}


def find_macro_package(file_path: Path) -> Optional[str]:
    """Find macro_package from nearest bookwright.config.yaml or notation package."""
    for parent in file_path.parents:
        config_path = parent / "docs/superpowers/bookwright.config.yaml"
        if not config_path.is_file():
            config_path = parent / "bookwright.config.yaml"
        if config_path.is_file():
            try:
                import yaml
                data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict) and "macro_package" in data:
                    return str(data["macro_package"]).removesuffix(".sty")
            except Exception:
                pass
    return None


def audit_text(prose: str, macro_package: Optional[str] = None) -> List[str]:
    """Audits clean prose (comments stripped) for macro leaks."""
    leaks = []
    if TEXTTT_MACRO.search(prose):
        leaks.append("Macro name in \\texttt{\\textbackslash ...} reveals LaTeX macro to reader")
    if THE_MACRO.search(prose):
        leaks.append("'the macro' phrase reveals LaTeX implementation detail in prose")
    if macro_package and re.search(rf"\b{re.escape(macro_package)}\.sty\b", prose):
        leaks.append(f"Mention of '{macro_package}.sty' belongs in source comments only")
    return leaks


def audit_file(file_path: Path) -> List[str]:
    if file_path.name in SKIP_BASENAMES or not file_path.name.endswith(".tex"):
        return []
    try:
        raw = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [f"Unable to read {file_path}: {e}"]

    prose = COMMENT.sub("", raw)
    macro_pkg = find_macro_package(file_path.resolve())
    return audit_text(prose, macro_pkg)


def main() -> int:
    args = sys.argv[1:]

    # Hook mode or stdin mode
    if "--hook" in args or "--stdin" in args or (not args and not sys.stdin.isatty()):
        try:
            stdin_content = sys.stdin.read()
            if not stdin_content.strip():
                return 0
            # Try parsing as JSON hook
            try:
                payload = json.loads(stdin_content)
                if isinstance(payload, dict):
                    tool_input = payload.get("tool_input") or {}
                    raw_path = tool_input.get("file_path") or ""
                    if not raw_path.endswith(".tex") or Path(raw_path).name in SKIP_BASENAMES:
                        return 0
                    content = tool_input.get("content") or tool_input.get("new_string") or ""
                    prose = COMMENT.sub("", content)
                    macro_pkg = find_macro_package(Path(raw_path).resolve()) if raw_path else None
                    leaks = audit_text(prose, macro_pkg)
                    if leaks:
                        print(f"LaTeX-macro-leak flagged {raw_path}:", file=sys.stderr)
                        for leak in leaks:
                            print(f"- {leak}", file=sys.stderr)
                        return 2
                    return 0
            except json.JSONDecodeError:
                # Plain text on stdin
                prose = COMMENT.sub("", stdin_content)
                leaks = audit_text(prose)
                if leaks:
                    print("LaTeX-macro-leak flagged text from stdin:", file=sys.stderr)
                    for leak in leaks:
                        print(f"- {leak}", file=sys.stderr)
                    return 2
                return 0
        except Exception as e:
            print(f"Error processing hook stdin: {e}", file=sys.stderr)
            return 0

    # Direct file argument mode
    files_to_check = [Path(a) for a in args if not a.startswith("--")]
    if not files_to_check:
        print("Usage: check_latex_macro_leak.py <file1.tex> [file2.tex ...]", file=sys.stderr)
        return 0

    total_leaks = 0
    for path in files_to_check:
        leaks = audit_file(path)
        if leaks:
            total_leaks += len(leaks)
            print(f"LaTeX-macro-leak flagged {path}:", file=sys.stderr)
            for leak in leaks:
                print(f"- {leak}", file=sys.stderr)

    if total_leaks > 0:
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
