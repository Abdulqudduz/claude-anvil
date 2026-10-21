---
description: Per-Part or full-book integration check with a written integration-pass record
allowed-tools: Read, Write, Bash, Glob, Grep, Agent
argument-hint: "[part | book] [name]"
---

# /bookwright:integrate

Close out a Part or the full book with a verified, committed integration-pass record.

## What it does

1. Perform every check in `${CLAUDE_PLUGIN_ROOT}/commands/check.md` (build, cross-reference resolution, page counts, running threads, banned phrases, macro leaks) at this scope, and capture the results. For a Part, also total the per-Part pages against the spec target.
2. Dispatch `bookwright:cross-ref-auditor` (Agent tool) over the in-scope sections: labels defined exactly once, expected forward refs match the baseline, no unexpected unresolved refs. It also returns the cross-reference map for the record.
3. Write an integration-pass record to `docs/superpowers/plans/YYYY-MM-DD-<scope>-integration-pass.md` with:
   - Date, plan reference, HEAD SHA at integration time.
   - Verification results table (one row per check, PASS/FAIL/NOTE).
   - The cross-reference map.
   - Known deferred items (documented forward refs that resolve in later work); this is the expected-unresolved baseline later checks compare against.
   - Open follow-ups for the polish plan.
4. Commit the record with subject `book: integration pass <scope>`.

## When to run it

- After completing the last chapter of a Part.
- After completing the full book draft (full-book scope).
- Before publishing, to verify the deferred-items list is empty or appropriately documented.
