---
description: Fast mechanical diagnostics on a section, chapter, part, or full book
allowed-tools: Read, Bash, Glob, Grep
argument-hint: "[section | chapter | part | book] [name]"
---

# /bookwright:check

Run mechanical diagnostics. No editorial judgment; checks that can be automated.

## What it runs

1. Build the book: `cd book && make cleanall && make`. Expects exit 0.
2. Cross-reference resolution: `grep "undefined" book/book.log | grep -iE "reference|citation"` (LaTeX writes "LaTeX Warning: Reference `x' on page N undefined", so the literal string "Reference undefined" never appears). Expects only the documented baseline.
3. Per-chapter page-count audit: read `book.toc`, compute per-chapter page spans, compare to the per-chapter targets in the plan files. Expects each chapter within plus-or-minus 30 percent of its target.
4. Running-thread inventory: for each thread named in the master spec, grep chapter files for thread keywords; verify the thread carries across the chapters the spec assigned it to.
5. Banned-phrase audit: grep the in-scope .tex files for each phrase in the banned-phrase list in `book/CLAUDE.md`, and for em-dashes (defense in depth behind the soul plugin's edit-time hook).
6. LaTeX-macro-leak audit: run `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/check_latex_macro_leak.py` on each in-scope .tex file by piping `{"tool_input": {"file_path": <path>, "content": <file text>}}` to it (build the JSON with `python3 -c 'import json,sys; ...'`, never by string concatenation); exit 2 means a leak, and its stderr names it.

## Scope

- `section <path>`: only the named section file.
- `chapter <name>`: all section files in `book/chapters/<chapter>/`.
- `part <name>`: all chapters in the named Part.
- `book`: everything (default if no scope given).

## Output

A short bullet report: each check's PASS/FAIL/NOTE. On FAIL, surface the specific lines or refs. No fix attempted; this is read-only diagnostics.
