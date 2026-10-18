---
description: Heavy multi-agent editorial review (4 specialist auditors in parallel)
allowed-tools: Read, Glob, Grep, Agent, AskUserQuestion
argument-hint: "[section | chapter | part | book] [name]"
---

# /bookwright:review

Launch the `reviewer` orchestrator. Dispatches all four review specialists in parallel: `spec-auditor`, `quality-auditor`, `math-auditor`, `cross-ref-auditor`. Synthesizes the findings into a unified report.

## Scope

- `section <path>`: one section. Single-pass review by all four auditors.
- `chapter <name>`: all sections of the named chapter.
- `part <name>`: all chapters of the named Part.
- `book`: everything (heavy; do not use casually).

If the reviewer returns a `decisions-needed` YAML block instead of a report (it stops when the scope is ambiguous, since subagents cannot ask questions), ask the author with AskUserQuestion: one question per item, using its `question`, its `options` (label as the option, consequence as the description), and the `recommended` option listed first with "(Recommended)". Batch at most 4 questions per call and group items that touch the same section. Then relaunch the reviewer with the chosen scope.

## Output

A unified review report saved to `docs/superpowers/reviews/YYYY-MM-DD-<scope>.md`, with sections from each auditor: spec compliance, quality (cold-read), math correctness, cross-references. To apply fixes, run `/bookwright:revise` (the rewriter orchestrator: fix-then-verify per finding, paired revision report); `/bookwright:iterate` loops review and revise to convergence. `/bookwright:integrate` is read-only verification, not a fix path.

## Distinction from /bookwright:check and /bookwright:integrate

- `/bookwright:check` is fast, mechanical, no judgment.
- `/bookwright:review` is heavy, editorial, full multi-agent dispatch.
- `/bookwright:revise` applies a review report's findings (fix-then-verify).
- `/bookwright:iterate` loops review and revise until convergence.
- `/bookwright:integrate` is per-Part or full-book verification with a written integration-pass record.
