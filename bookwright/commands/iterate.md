---
description: Autonomous review-fix-review loop until convergence, plateau, or the iteration cap
allowed-tools: Read, Glob, Grep, Agent, AskUserQuestion
argument-hint: "[section <path> | chapter <N> | part <N> | book] [--max-iterations N] [--threshold substantive|blocking|zero] [--pause-on high|all|none] [--closing-review on|off]"
---

# /bookwright:iterate

Launch the `iterator` orchestrator: alternate `/bookwright:review` and `/bookwright:revise` (via their agents) until the scope is clean.

## Flags

| Flag | Default | Effect |
|------|---------|--------|
| `--max-iterations N` | 5 | Hard cap on rounds |
| `--threshold substantive\|blocking\|zero` | `substantive` | Converged when no findings at this severity or worse remain |
| `--pause-on high\|all\|none` | `high` | Which judgment findings wait for the single end-of-loop checkpoint |
| `--closing-review on\|off` | `on` | Delta-scoped recount after the loop's final fixes so the summary's counts are real |

## Behavior

- Round artifacts (each round's review.md and revision.md) live under `docs/superpowers/reviews/iterate/<timestamp>-<scope>/`; the default reviews directory stays untouched.
- Rounds 2+ are delta-scoped: the reviewer re-audits only the files the prior revision touched and carries forward untouched findings, which cuts the dominant per-round cost.
- Exit reasons are reported honestly: `converged`, `cap`, or `plateau`.

## The end-of-loop checkpoint

Subagents cannot ask questions (Claude Code removes AskUserQuestion from them), so the checkpoint runs here, in the main session, in two launches:

1. Launch the iterator with `<entry>loop</entry>` plus the scope and flags. If it returns a `decisions-needed` block before starting (ambiguous scope), ask as in step 3 and relaunch with the chosen scope.
2. If it finishes without `status: awaiting-decisions`, it already ran the recount and summary: report the summary path and headline numbers. Done.
3. If it returns `status: awaiting-decisions` with a session path and a `decisions-needed` block:
   - Ask the author per `${CLAUDE_PLUGIN_ROOT}/skills/textbook-methodology/references/decision-handoff.md` (including its more-than-8-items triage).
4. Launch the iterator again with `<entry>finalize</entry>`, `<session>` = the session path, and `<decisions>` = each answered item's `id`, `finding`, and `choice` (empty when the author stopped). It applies the decisions, runs the closing recount, writes `summary.md`, and records skipped items as unresolved. Report the summary path and headline numbers.

## Distinction from /bookwright:review and /bookwright:revise

- `/bookwright:review` is one diagnosis pass.
- `/bookwright:revise` is one fix pass.
- `/bookwright:iterate` loops both and accounts for the whole run.
