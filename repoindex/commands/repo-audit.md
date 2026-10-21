---
description: Read-only quality audit summary via `repoindex ops audit`. Shows failing checks by severity without fixing anything.
argument-hint: "[--language X | --tag T | --recent 7d | --dirty | --category essentials | --severity critical]"
allowed-tools:
  - Bash(repoindex ops audit:*)
  - Bash(jq:*)
---

# /repo-audit

Run `repoindex ops audit` with the given filters and summarize the results. Read-only: this command surfaces gaps, it does not fix them.

## Arguments

Forward any arguments directly to the CLI. Common filters:

| Flag | Purpose |
|------|---------|
| `--language python` | Only Python repos |
| `--tag work/active` | Only repos with a matching tag |
| `--recent 7d` | Only repos with commits in the last 7 days |
| `--dirty` | Only repos with uncommitted changes |
| `--category essentials` | Scope to one category: essentials, development, discoverability, or documentation |
| `--severity critical` | Minimum severity: `critical`, `recommended` (critical + recommended), or `suggested` (all) |

## Output format of `ops audit --json`

JSONL. Every line but the last is one repo: `{name, path, score, passed, total, categories, failed, fix_commands}`, where each `failed` entry is `{check_id, passed, fix_hint, fix_command?}` and carries **no severity**. The last line is a summary record: `{"type": "summary", total_repos, overall_score, checks, categories}`, where `checks` maps each `check_id` to `{label, category, severity, passed, total}`. Severity comes only from the summary's `checks`.

## Workflow

### Step 1: Run the audit and project it

```bash
repoindex ops audit --json <forwarded args> | jq -c 'if .type == "summary" then {summary: (.checks | map_values({label, severity, failing: (.total - .passed)})), total_repos} else select(.failed | length > 0) | {name, failed: [.failed[].check_id]} end'
```

This keeps only repos with failures (name plus failing `check_id`s) and the per-check counts, which is far smaller than the raw output.

### Step 2: Aggregate

From the projected output:

- Total repos audited: `total_repos`.
- Per check: `failing` count and `severity` from the summary; repo names from the per-repo lines whose `failed` contains that `check_id`.
- Repos with no failures: `total_repos` minus the number of per-repo lines.
- Worst offenders: repos with the most failing checks, broken down by severity via the summary lookup.

### Step 3: Summarize

```
Audit summary (N repos, filters: ...)

Critical
  license (LICENSE)        112 repos: foo, bar, baz, ... (+109)
  readme (README)           31 repos: ...
Recommended
  ci (CI/CD)               152 repos: ...
Suggested
  citation (Citation file)  ...

No gaps:  4 repos
Worst offenders:
  repo-a   2 critical, 5 recommended
```

Use the real `check_id` and `label`. Omit severity tiers with no failures. Cap each repo list at 5 names plus a count.

### Step 4: Offer follow-ups

Suggest, do not execute:

- Deterministic gaps across a subset: `repoindex ops generate <kind> --dry-run` filtered with `--language`/`--tag`/`--recent`/`--dirty` (see each failure's `fix_command`).
- One repo in depth: the `repo-polish` agent.
- Tighter scope: `/repo-audit --severity critical --category essentials`.

## When to use

- Pre-release overview across a subset (for example `/repo-audit --language python`).
- Contrast with `/repo-sprint`: sprint is the cross-cutting triage (git state, activity, stale, unpublished) and uses only the audit summary; `/repo-audit` is the full per-check breakdown with filters.
- Contrast with the `repo-polish` agent: that is single-repo release prep and writes files.
