---
description: Launch the rewriter orchestrator to apply fixes from a review report
allowed-tools: Read, Write, Glob, Grep, Bash, Agent, AskUserQuestion
argument-hint: "[work-name] [review-path | severity HIGH|MEDIUM|LOW | category consistency|craft|voice|structure]"
---

# /worldsmith:revise

Launch the **rewriter** orchestrator agent to apply fixes from a review report.

The rewriter reads the review findings, triages them (auto-fixable, needs judgment, structural defer), then for each auto-fixable finding:

1. Dispatches the right writer specialist (`scene-writer`, `lore-writer`, or `character-developer`) to apply the fix
2. Dispatches the matching reviewer specialist (`consistency-auditor`, `craft-auditor`, `voice-auditor`, or `structure-auditor`) to verify the fix resolved the original finding without introducing new issues
3. Retries failed fixes up to twice, then flags for human review

The output is a revision report at the same path as the source review, with before/after for every fix and propagation notes for canonical doc updates.

The rewriter cannot ask you anything (Claude Code removes AskUserQuestion from subagents), so it never pauses mid-run. Every needs-judgment finding comes back in its `## Decisions Needed` section, and this command asks you about them afterwards (see "Resolving Decisions").

## Locating the Review Report

If `$ARGUMENTS` contains an explicit path (e.g., `.worldsmith/reviews/2026-03-12/Hemorrhagic/review.md`), use it.

Otherwise locate the latest review report as described under "Report paths" in `${CLAUDE_PLUGIN_ROOT}/skills/worldsmith-methodology/references/work-scoping.md`: sort the date directories by name, not modification time (revising an older review touches its directory), and in a multi-work project take the latest one containing `<work-name>/review.md`.

If no review report exists, do NOT silently launch the rewriter. Tell the user: "No review report found in `.worldsmith/reviews/`. Run `/worldsmith:review` first to produce one." Then stop.

## Filters

`$ARGUMENTS` may contain a severity or category filter that scopes the rewriter to a subset of findings.

Severity filters: `HIGH`, `MEDIUM`, `LOW` (case-insensitive).
- `/worldsmith:revise HIGH` applies only HIGH-severity fixes
- `/worldsmith:revise Hemorrhagic HIGH` filters by both work and severity

Category filters: `consistency`, `craft`, `voice`, `structure`.
- `/worldsmith:revise consistency` applies only consistency-domain fixes
- Multiple filters may be combined: `/worldsmith:revise HIGH consistency`

Forward filter values to the rewriter in the launch prompt. The rewriter's Phase 2 (Triage) already groups findings by severity and domain.

## Multi-Work Awareness

Resolve the target work per `${CLAUDE_PLUGIN_ROOT}/skills/worldsmith-methodology/references/work-scoping.md` (work name in `$ARGUMENTS`, else the primary work, noted in the launch prompt), e.g. `/worldsmith:revise Hemorrhagic HIGH consistency`. Manuscript edits target that work only; shared-lore updates are universe-wide and the rewriter's Phase 5 propagates them across works. The revision report sits next to its review. Pass the resolved work name, review report path, and any filters to the rewriter in the launch prompt.

## Resolving Decisions

After the rewriter returns, read the `deferred-judgments` list from its `## Decisions Needed` section (in the return message, or in the `revision.md` it names). If the list is empty, summarize the revision and stop.

Otherwise follow the asking procedure in `${CLAUDE_PLUGIN_ROOT}/skills/worldsmith-methodology/references/decision-handoff.md`: the >12 meta question, then batched AskUserQuestion calls (max 4 questions per call, 4 options each, related items grouped, recommended option first). Items you could not ask (beyond 16) or the author chose to leave go to `unresolved.md` beside the revision report.

If any decisions were made, launch the rewriter again in final-revise mode, applying ONLY those decisions:

```xml
<mode>final-revise</mode>
<output-dir>{directory of the source review.md}/decisions/</output-dir>
<work-scope>{work name}, manuscript at {path}</work-scope>
<review-report>{path to the source review.md}</review-report>
<fix-guidance>{decisions list: finding_id, location, chosen_option, rationale}</fix-guidance>
```

Then summarize both passes for the author: fixed and verified, decided and applied, structural defers, retry failures, and anything left in `unresolved.md`.
