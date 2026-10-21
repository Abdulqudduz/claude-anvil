---
description: Autonomous review-fix-review loop until convergence or iteration cap
allowed-tools: Read, Write, Glob, Grep, Agent, AskUserQuestion
argument-hint: "[work-name] [--max-iterations N] [--threshold high|medium|zero] [--pause-on high|all|none] [--closing-review on|off]"
---

# /worldsmith:iterate

Launch the **iterator** orchestrator agent to drive a manuscript toward clean autonomously.

The iterator composes `/worldsmith:review` and `/worldsmith:revise` in a loop:

1. Run the reviewer (4 specialists in parallel)
2. Count findings; check convergence
3. If not converged, run the rewriter in iterate-mode (best-guess on routine creative calls, defer high-stake judgments)
4. Repeat until convergence, regression-plateau, or iteration cap
5. At the end, return any deferred high-stake judgments to this command, which asks the author in one batched `AskUserQuestion` checkpoint
6. Relaunch the iterator in finalize mode to apply the answers in one final revision pass
7. Write a summary report

The author resumes control only at the end-of-loop checkpoint, not per-finding. Use this for finishing-pass work on manuscripts that already have a complete draft.

## Running the Checkpoint

The iterator cannot ask questions itself (Claude Code removes AskUserQuestion from subagents), so this command runs the checkpoint between two launches:

1. Launch the iterator with the resolved work name, flags, and `<plugin_root>` (`${CLAUDE_PLUGIN_ROOT}`, as expanded here; loop mode is the default).
2. If it returns `status: complete`, present its summary and stop.
3. If it returns `status: awaiting-decisions`, read the `deferred-judgments` list from its `## Decisions Needed` section (or `<session>/decisions-needed.md`). Follow the asking procedure in `${CLAUDE_PLUGIN_ROOT}/skills/worldsmith-methodology/references/decision-handoff.md`:
   - More than 12 items: ask the meta question first. "Best-guess all" turns every item into a decision using its `recommended` option (rationale "best guess: author delegated"). "Stop here" makes every item unresolved.
   - Otherwise batch AskUserQuestion calls (max 4 questions per call, 4 options each, related items grouped, recommended first, at most 16 questions). Items beyond 16 are unresolved.
4. Relaunch the iterator to finish the session:

```xml
<mode>finalize</mode>
<session>{session directory from the loop's return}</session>
<decisions>{list of finding_id, location, chosen_option, rationale}</decisions>
<unresolved>{finding ids not decided, or empty}</unresolved>
```

5. Present the finalize run's summary and the path to `summary.md`.

## Defaults

| Flag | Default | Meaning |
|------|---------|---------|
| `--max-iterations N` | 8 | Hard cap on rounds |
| `--threshold high\|medium\|zero` | `high` | Stop when no findings remain at this severity or worse |
| `--pause-on high\|all\|none` | `high` | Which judgments to defer to the end-of-loop checkpoint |
| `--closing-review on\|off` | `on` | Run one delta-scoped review after the loop's final fixes so the summary's remaining-finding counts are real, not pre-fix |

Default behavior is aggressive: iterate until zero HIGH findings remain (up to 8 rounds), best-guess routine creative judgments, only pause for plot/character/world-stakes decisions.

## Cost Warning

A full iterate run with defaults costs roughly 80-150 specialist agent invocations and several million tokens. This is the most expensive single command in the worldsmith plugin. Use it for finishing passes on real drafts, not every-edit cleanup.

The summary report includes a best-effort cost estimate so future runs can be calibrated.

## Stopping early

The iterator stops earlier than the cap when:

- **Converged**: no open findings at the configured threshold remain (findings already deferred to you do not count; the loop cannot fix them)
- **Plateau**: a round produces zero new fixes and zero new deferred judgments (no further progress possible; a re-reported, already-deferred finding is not progress)

Both are reported in the final summary with the reason.

Rounds 2+ are delta-scoped: the reviewer re-audits only the files the prior
round's revision touched (at full manuscript context) and carries forward
untouched findings, which cuts the dominant per-round reviewer cost. Each
deferred judgment is asked once at the checkpoint, however many rounds re-report it.

## Output

All session artifacts live under `.worldsmith/iterate/<timestamp>/` (multi-work: `.worldsmith/iterate/<timestamp>/<work>/`):

- `state.md`: run configuration and per-round log
- `summary.md`: final user-facing summary with cost estimate
- `round-NNN/review.md` + `round-NNN/revision.md`: per-round artifacts
- `final-revision/revision.md`: post-checkpoint revision (if user answered any deferred judgments)
- `decisions-needed.md`: the deferred judgments the loop handed to this command (only if any were deferred)
- `unresolved.md`: judgments not decided at the checkpoint (beyond 16, or the author chose "stop here")

The default `.worldsmith/reviews/` directory is untouched. Direct `/worldsmith:review` invocations still write there as before.

## Multi-Work Awareness

Resolve the target work per `${CLAUDE_PLUGIN_ROOT}/skills/worldsmith-methodology/references/work-scoping.md` (work name in `$ARGUMENTS`, else the primary work, noted in the launch prompt), e.g. `/worldsmith:iterate Hemorrhagic --max-iterations 12 --pause-on all`. Manuscript edits target that work only; shared-lore updates propagate across works via the rewriter's Phase 5. Pass the resolved work name and all flags to the iterator in the launch prompt.

## When NOT to use iterate

- **Active drafting.** Iterate is for finishing passes on existing drafts. Use `/worldsmith:draft` to add new content.
- **Single bug fix.** If you know exactly what to change, edit directly or use `/worldsmith:change`.
- **Per-finding interactivity.** If you want to make creative decisions on every judgment, use `/worldsmith:revise` instead. Iterate is for autonomous runs that surface only the highest-stakes calls.
