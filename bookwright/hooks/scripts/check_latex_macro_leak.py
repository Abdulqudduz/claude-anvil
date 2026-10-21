#!/usr/bin/env python3
"""PostToolUse hook (Write|Edit): flag LaTeX source-tool detail in reader-visible .tex prose.

Reads the hook JSON on stdin. Exit 0 when clean or not applicable; exit 2 with a
plain-text explanation on stderr when a leak is found. This is a PostToolUse hook,
so the write has already happened: exit 2 feeds the explanation back to Claude,
which should revise the text.

Checks run on the written text with LaTeX comments removed:
  - a macro name shown to the reader via \\texttt{\\textbackslash foo}
  - the phrase "the macro"
  - a mention of the project's notation package (`<macro_package>.sty`), where
    `macro_package` comes from docs/superpowers/bookwright.config.yaml, found by
    walking up from the edited file. Without a config this check does not apply.

Runs under plain python3 (stdlib only), so non-.tex writes exit before anything
else is spawned. Only when a config must be read and this interpreter lacks
PyYAML does it resolve one through find_python.sh (which may try
`uv run --with pyyaml`) and use it for that single read. If that fails too, the
check is skipped and one note says so on stderr with exit 1 (a non-blocking hook
error the user sees), so the skip is never silent.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
RESOLVER = SCRIPTS / "find_python.sh"
RESOLVE_TIMEOUT = 7  # seconds; the hook's own timeout is 10
# Prints the config's macro_package as JSON (null when absent or unreadable).
READ_CONFIG = (
    "import json, sys, yaml\n"
    "try:\n"
    "    d = yaml.safe_load(open(sys.argv[1])) or {}\n"
    "except Exception:\n"
    "    d = {}\n"
    "print(json.dumps(d.get('macro_package') if isinstance(d, dict) else None))\n"
)
CONFIG_REL = Path("docs/superpowers/bookwright.config.yaml")
SKIP_BASENAMES = {"preamble.tex"}

# A '%' not preceded by a backslash starts a comment that runs to end of line.
COMMENT = re.compile(r"(?<!\\)%.*$", re.MULTILINE)
TEXTTT_MACRO = re.compile(r"\\texttt\{\\textbackslash ?[A-Za-z]")
THE_MACRO = re.compile(r"\bthe macro\b", re.IGNORECASE)


def written_text(tool_input: dict) -> str:
    """The text this tool call put into the file (Write content or Edit replacement)."""
    if "content" in tool_input:
        return tool_input["content"] or ""
    if "new_string" in tool_input:
        return tool_input["new_string"] or ""
    edits = tool_input.get("edits") or []
    return "\n".join(e.get("new_string", "") for e in edits if isinstance(e, dict))


class YamlUnavailable(Exception):
    """A bookwright config exists but PyYAML is not importable."""


def read_with_resolved_python(config: Path):
    """Read macro_package via a PyYAML-capable interpreter from find_python.sh."""
    try:
        resolved = subprocess.run(
            ["bash", "-c", 'source "$1" && find_python && printf "%s\\0" "${PY_CMD[@]}"', "_", str(RESOLVER)],
            capture_output=True, text=True, timeout=RESOLVE_TIMEOUT,
        )
        argv = [a for a in resolved.stdout.split("\0") if a]
        if resolved.returncode != 0 or not argv:
            raise YamlUnavailable(str(config))
        read = subprocess.run(
            argv + ["-c", READ_CONFIG, str(config)],
            capture_output=True, text=True, timeout=RESOLVE_TIMEOUT,
        )
        if read.returncode != 0:
            raise YamlUnavailable(str(config))
        return json.loads(read.stdout or "null")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        raise YamlUnavailable(str(config)) from e


def find_macro_package(file_path: Path) -> str | None:
    """Read macro_package from the nearest bookwright.config.yaml above file_path."""
    for directory in file_path.parents:
        config = directory / CONFIG_REL
        if config.is_file():
            try:
                import yaml  # PyYAML, if this interpreter has it
            except ImportError:
                value = read_with_resolved_python(config)
            else:
                try:
                    data = yaml.safe_load(config.read_text()) or {}
                except (OSError, yaml.YAMLError):
                    return None
                value = data.get("macro_package") if isinstance(data, dict) else None
            return str(value).removesuffix(".sty") if value else None
    return None


def find_leaks(prose: str, macro_package: str | None) -> list[str]:
    leaks = []
    if TEXTTT_MACRO.search(prose):
        leaks.append(
            "macro name in \\texttt{\\textbackslash ...}: shows a LaTeX macro to the reader"
        )
    if THE_MACRO.search(prose):
        leaks.append("'the macro' phrase reveals LaTeX implementation detail")
    if macro_package and re.search(rf"\b{re.escape(macro_package)}\.sty\b", prose):
        leaks.append(
            f"mention of '{macro_package}.sty': the notation package belongs in source comments only"
        )
    return leaks


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0
    tool_input = payload.get("tool_input") or {}
    raw_path = tool_input.get("file_path") or ""
    if not raw_path.endswith(".tex"):
        return 0
    file_path = Path(raw_path)
    if not file_path.is_absolute():
        file_path = Path(payload.get("cwd") or ".") / file_path
    if file_path.name in SKIP_BASENAMES:
        return 0

    prose = COMMENT.sub("", written_text(tool_input))
    skipped_note = None
    try:
        macro_package = find_macro_package(file_path.resolve())
    except YamlUnavailable as e:
        macro_package = None
        skipped_note = (
            f"bookwright macro-leak hook: macro_package check skipped for {raw_path}: "
            f"no PyYAML-capable python could read {e} (install pyyaml for python3, or put uv on PATH)."
        )
    leaks = find_leaks(prose, macro_package)
    if not leaks:
        if skipped_note:
            print(skipped_note, file=sys.stderr)
            return 1
        return 0
    print(
        f"LaTeX-macro-leak hook flagged {raw_path} (the write already happened; revise it). "
        "Reader-facing prose must not reveal LaTeX source-tool detail. Found:",
        file=sys.stderr,
    )
    for leak in leaks:
        print(f"- {leak}", file=sys.stderr)
    if skipped_note:
        print(skipped_note, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
