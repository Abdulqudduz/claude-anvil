---
description: Apply fixes from a review report via the rewriter orchestrator (fix-then-verify)
allowed-tools: Read, Glob, Grep, Agent, AskUserQuestion
argument-hint: "[review-report-path] [--scope blocking|substantive|minor|all]"
---

# /bookwright:revise

Launch the `rewriter` orchestrator on a review report produced by `/bookwright:review`.

## Behavior

- With a path argument, use that report. Without one, use the newest `docs/superpowers/reviews/YYYY-MM-DD-*.md` that is not itself a `-revision` file; confirm the choice with the user before dispatching.
- Pass the severity scope through (`--scope`, default `all`).
- The rewriter fixes findings (drafting specialists for content, direct edits for mechanical items), verifies each fix with the auditor that found it, rebuilds the book, and writes `<report-basename>-revision.md` next to the source report.

## Decisions Needed

In its default interactive mode the rewriter fixes every mechanical and specialist finding and defers every judgment call to a `decisions-needed` YAML block, returned in its final message and written into the revision report. If that block is non-empty:

1. Ask the author per `${CLAUDE_PLUGIN_ROOT}/skills/textbook-methodology/references/decision-handoff.md`.
2. Relaunch the rewriter with the same `<report>`, `<prior-revision>` = the first pass's revision report, and a `<decisions>` block listing each answered item as `id`, `finding`, and `choice` (the chosen label). It fixes and verifies only those findings and writes `<report-basename>-revision-decisions.md`.
3. Report both passes' counts. Items the author skips stay open: list them, and note that re-running `/bookwright:revise` on the same report picks them up.

## Distinction from /bookwright:draft and /bookwright:iterate

- `/bookwright:draft` drafts new sections from a chapter plan.
- `/bookwright:revise` is one fix pass over an existing review report.
- `/bookwright:iterate` loops review and revise until convergence.
