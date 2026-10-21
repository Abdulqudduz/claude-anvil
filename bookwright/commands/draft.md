---
description: Launch the writer orchestrator for prose drafting (whole chapter or single section)
allowed-tools: Read, Glob, Grep, Agent, AskUserQuestion
argument-hint: "<chapter-name | section-path>"
---

# /bookwright:draft

Launch the `bookwright:writer` orchestrator (Agent tool) with the argument: a whole chapter (all of its plan's section tasks) or a single section path (one task end-to-end). Relay its report: files, commit SHAs, word counts, and any deferred MINOR findings.

## Scope questions

If the scope is ambiguous the writer stops before drafting and returns a `decisions-needed` YAML block. Ask and relaunch per `${CLAUDE_PLUGIN_ROOT}/skills/textbook-methodology/references/decision-handoff.md`.

## When to use what

- `/bookwright:draft chapter5` runs ALL section tasks of chapter 5 (scaffold first; independent sections may run in parallel, dependent ones wait for their prerequisites).
- `/bookwright:draft ch05/bloom-from-scratch.tex` runs only that one section task.

For per-Part or full-book integration verification, use `/bookwright:integrate` instead. For editorial review of an existing chapter (no drafting), use `/bookwright:review`.
