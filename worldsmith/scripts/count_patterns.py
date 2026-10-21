#!/usr/bin/env python3
"""Count or check prose patterns defined in a patterns.md file.

Audit mode (default) counts every category across manuscript files:

    count_patterns.py <manuscript-glob> [patterns-file]
    count_patterns.py "chapters/*.md"
    count_patterns.py "manuscript/*.tex" my-patterns.md

Check mode reads prose on stdin and reports matches of the hook-enforced
categories (`<!-- hook: block -->`). Exit 2 with the report on stderr when
anything matches, else exit 0. Used by the cliche PostToolUse hook:

    count_patterns.py --check-text [--project-dir DIR] [--label FILE] [patterns-file]

Patterns file resolution: explicit argument > <project-dir>/.worldsmith/patterns.md
> the bundled scripts/patterns.md. In check mode, an override that declares no
hook-enforced category falls back to the bundled hook categories.
"""

import argparse
import glob
import os
import re
import sys
from dataclasses import dataclass, field

BUNDLED_PATTERNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patterns.md")

DIRECTIVE = re.compile(r"^<!--\s*([a-z-]+)\s*:\s*(.*?)\s*-->$")

# Typographic punctuation folded to ASCII so curly-quote manuscripts match.
TYPOGRAPHIC = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


@dataclass
class Pattern:
    kind: str  # "literal" | "regex"
    text: str

    def compile(self) -> "re.Pattern[str]":
        if self.kind == "regex":
            return re.compile(self.text, re.IGNORECASE)
        return re.compile(r"\b" + re.escape(self.text) + r"\b", re.IGNORECASE)

    @property
    def label(self) -> str:
        return f"/{self.text}/" if self.kind == "regex" else self.text


@dataclass
class Category:
    name: str
    patterns: list = field(default_factory=list)
    hook: bool = False
    hint: str = ""
    scope: str = "all"  # "all" | "dialogue-lines"


def parse_patterns(path):
    """Parse a patterns.md file into a list of Category."""
    categories = []
    current = None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line.startswith("## "):
                current = Category(name=line[3:].strip())
                categories.append(current)
                continue
            if current is None or not line or line.startswith("#"):
                continue
            directive = DIRECTIVE.match(line)
            if directive:
                key, value = directive.groups()
                if key == "regex":
                    current.patterns.append(Pattern("regex", value))
                elif key == "hook":
                    current.hook = value == "block"
                elif key == "hint":
                    current.hint = value
                elif key == "scope":
                    current.scope = value
                continue
            if line.startswith("<!--"):
                continue
            current.patterns.extend(Pattern("literal", p.strip()) for p in line.split(",") if p.strip())
    return categories


def find_patterns_file(explicit=None, project_dir="."):
    """Resolve patterns file: explicit arg > project override > bundled default."""
    if explicit:
        return explicit
    override = os.path.join(project_dir, ".worldsmith", "patterns.md")
    if os.path.isfile(override):
        return override
    return BUNDLED_PATTERNS


def hook_categories(patterns_path):
    """Hook-enforced categories, falling back to the bundled ones if none declared."""
    cats = [c for c in parse_patterns(patterns_path) if c.hook]
    if not cats and os.path.abspath(patterns_path) != BUNDLED_PATTERNS:
        cats = [c for c in parse_patterns(BUNDLED_PATTERNS) if c.hook]
    return cats


def check_text(text, categories):
    """Return [(category, pattern)] for every hook pattern that matches text."""
    text = text.translate(TYPOGRAPHIC)
    dialogue = "\n".join(line for line in text.splitlines() if '"' in line)
    hits = []
    for cat in categories:
        target = dialogue if cat.scope == "dialogue-lines" else text
        if not target:
            continue
        for pat in cat.patterns:
            if pat.compile().search(target):
                hits.append((cat, pat))
    return hits


def format_violations(label, hits):
    lines = [f"Fiction cliche check failed on {label}:"]
    for cat, pat in hits:
        hint = f" ({cat.hint})" if cat.hint else ""
        lines.append(f'- "{pat.text}"{hint}')
    lines.append("")
    lines.append(
        "Rewrite to show the sensation through physical detail or action. "
        "See the worldsmith prose-craft skill."
    )
    return "\n".join(lines)


def count_pattern(files_text, pattern):
    rx = pattern.compile()
    return sum(len(rx.findall(text)) for text in files_text)


def run_audit(manuscript_glob, patterns_path):
    files = sorted(glob.glob(manuscript_glob, recursive=True))
    if not files:
        print(f"No files matching: {manuscript_glob}", file=sys.stderr)
        return 1
    files_text = []
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                files_text.append(f.read().translate(TYPOGRAPHIC))
        except (OSError, UnicodeDecodeError):
            continue

    print("=== Prose Pattern Audit ===")
    print(f"Patterns: {patterns_path}")
    print(f"Files: {len(files)}")
    print()
    for cat in parse_patterns(patterns_path):
        print(f"--- {cat.name} ---")
        for pat in cat.patterns:
            count = count_pattern(files_text, pat)
            if count > 0:
                print(f"  {pat.label:<24s} {count}")
        print()
    total_words = sum(len(text.split()) for text in files_text)
    print("--- Manuscript Size ---")
    print(f"  Total words: ~{total_words}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Count or check prose patterns.")
    parser.add_argument("--check-text", action="store_true",
                        help="Check stdin against hook-enforced categories (exit 2 on match)")
    parser.add_argument("--project-dir", default=".",
                        help="Project root for the .worldsmith/patterns.md override")
    parser.add_argument("--label", default="<stdin>", help="File name shown in the check report")
    parser.add_argument("args", nargs="*", help="audit: <manuscript-glob> [patterns-file]; check: [patterns-file]")
    ns = parser.parse_args(argv)

    if ns.check_text:
        if len(ns.args) > 1:
            parser.error("--check-text takes at most one positional argument (patterns-file)")
        patterns_path = find_patterns_file(ns.args[0] if ns.args else None, ns.project_dir)
        if not os.path.isfile(patterns_path):
            print(f"Patterns file not found: {patterns_path}", file=sys.stderr)
            return 1
        hits = check_text(sys.stdin.read(), hook_categories(patterns_path))
        if hits:
            print(format_violations(ns.label, hits), file=sys.stderr)
            return 2
        return 0

    if not ns.args or len(ns.args) > 2:
        print("Usage: count_patterns.py <manuscript-glob> [patterns.md]", file=sys.stderr)
        return 1
    patterns_path = find_patterns_file(ns.args[1] if len(ns.args) == 2 else None, ns.project_dir)
    if not os.path.isfile(patterns_path):
        print(f"Patterns file not found: {patterns_path}", file=sys.stderr)
        return 1
    return run_audit(ns.args[0], patterns_path)


if __name__ == "__main__":
    sys.exit(main())
