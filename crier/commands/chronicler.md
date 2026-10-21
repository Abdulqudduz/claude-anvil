---
name: chronicler
description: Weekly catch-up on cross-posting. Scans recent metafunctor posts, finds platform gaps, proposes cross-posts with rewrites for short-form. Opinionated defaults so you don't have to choose.
argument-hint: "[since, e.g. 2w|1m] [--dry] [--long-form|--short-form]"
---

# /crier:chronicler

Make "did I cross-post the recent stuff?" a one-prompt workflow. This is the
date-scoped batch version of the `crier` skill: follow that skill for every rule
it defines (target and limit discovery, rewrites and their budget, the two-step
publish, manual/import platforms, failures). This command adds only scope, the
proposal format, and batching.

Arguments: `$ARGUMENTS`

## Scope

- Window: default `2w`; any `since` value `crier_search` accepts (`3d`, `1m`, `6w`).
- `--long-form` (or `longform`): only targets whose `is_short_form` is false.
- `--short-form` (or `social`): only short-form targets.
- `--dry`: run steps 1-3 and stop after the proposal.
- A single file: use `/crier:crier <file>` instead.

## 1. Scan

1. Get targets from `crier_doctor()` and limits from `crier://platforms`, as the
   skill says. Batch mode covers API targets only; list `manual_mode` and
   `import_mode` platforms at the end of the proposal as optional manual follow-ups.
2. `crier_search(since=<window>)` for recent files. It has no draft field: skip
   a file only if `Read` shows `draft: true` in its front matter.
3. `crier_missing(platforms=<targets>)` for registry gaps, plus
   `crier_article(<file>)` for each search result not in that list ("Article not
   found" means it is on no platform).
4. Skip files already on every target, and files where `crier_check` reports errors.

## 2. Propose

Draft the rewrites for short-form gaps (skill rules), then present one item per
post, never per platform, and never list an already-posted platform as an action:

```
3 posts to cross-post (8 platform actions total):

1. "Intelligence is a Shape, Not a Scalar" (2026-04-05, 2393w)
   -> devto, hashnode (full body)
   -> bluesky (198/228 chars): "Chollet says intelligence is a ball that's already round. ..."
   -> mastodon (402/428 chars): "..."

2. "Posthumous: A Federated Dead Man's Switch" (2026-02-14, 1298w)
   -> devto, hashnode (full body)
   -> mastodon (236/428 chars): "..."

Manual follow-ups available: twitter (manual), medium (import)

Approve all (a) | Approve some (e.g. 1,3) | Edit rewrite (e <num> <platform>) | Skip <num> (s <num>) | Abort (q)
```

Show each rewrite's length against its URL-aware budget. Regenerate any bland
rewrite before the user sees it.

## 3. Approve

Never publish without explicit approval; if the answer is unclear, abort. If the
approved set is large (more than ~5 posts or ~15 platform actions), offer to
dispatch the `cross-poster` agent with the approved posts, platforms, and
rewrites as its explicit scope.

## 4. Execute

Run the skill's two-step publish for each approved post and platform, in
parallel where possible. A failure does not abort the batch: handle it as the
skill's "Failures" section says and continue.

## 5. Report

```
Cross-posted:
  Intelligence is a Shape   devto: https://dev.to/...   hashnode: https://...   bluesky: https://...
  dapple                    devto: ok   hashnode: FAILED (rate limited)   bluesky: ok

Failures (1):
  dapple -> hashnode: API rate limit (retry: see the crier skill's "Failures")
```

## Other tools

- "What should I cross-post?" with no date scope, performance or failure analysis:
  dispatch the `auditor` agent.
