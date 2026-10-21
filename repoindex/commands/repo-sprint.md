---
description: Collection health triage and work-session kickoff (dirty, unpushed, active, release candidates, audit gaps, stale, unpublished).
allowed-tools:
  - mcp__repoindex__get_manifest
  - mcp__repoindex__run_sql
  - Bash(repoindex ops audit:*)
  - Bash(jq:*)
---

# /repo-sprint

"What needs attention, and what's open right now?" The single triage entry point: pulls together the signals that matter across the collection and ends with a prioritized list so you can pick the next thing to work on. Read-only.

## Workflow

### 1. Overview

Call `mcp__repoindex__get_manifest()`. Its `summary` gives the headline counts (`dirty`, `unpushed`, `stale`, `unpublished`); use them as the numbers and the queries below only to name the repos behind them. If `summary.refresh_stale` is true (last refresh over 7 days ago), say so first and suggest `mcp__repoindex__refresh()`.

### 2. Named repos (run these `mcp__repoindex__run_sql` queries in parallel)

Dirty working trees:

```sql
SELECT name, path, language FROM repos
WHERE is_clean = 0
ORDER BY name
```

Unpushed commits:

```sql
SELECT name, ahead, path FROM repos
WHERE ahead > 0
ORDER BY ahead DESC
```

Recent commit activity (last 3 days):

```sql
SELECT r.name, r.language, COUNT(*) AS commits, MAX(e.timestamp) AS last
FROM events e JOIN repos r ON e.repo_id = r.id
WHERE e.type = 'commit' AND e.timestamp > datetime('now', '-3 days')
GROUP BY r.id
ORDER BY last DESC
LIMIT 15
```

Release candidates: published packages with commits newer than the last release tag (timestamps only; no version-string comparison):

```sql
WITH last_tag AS (
  SELECT repo_id, MAX(timestamp) AS tagged FROM events
  WHERE type IN ('git_tag', 'release')
  GROUP BY repo_id
),
recent_commits AS (
  SELECT repo_id, COUNT(*) AS n, MAX(timestamp) AS last_commit
  FROM events
  WHERE type = 'commit' AND timestamp > datetime('now', '-30 days')
  GROUP BY repo_id
)
SELECT r.name, p.registry, p.current_version,
       rc.n AS commits_30d, lt.tagged AS last_release
FROM repos r
JOIN publications p ON p.repo_id = r.id AND p.published = 1
JOIN recent_commits rc ON rc.repo_id = r.id
LEFT JOIN last_tag lt ON lt.repo_id = r.id
WHERE p.registry != 'zenodo'
  AND (lt.tagged IS NULL OR rc.last_commit > lt.tagged)
ORDER BY rc.n DESC
LIMIT 10
```

Stale repos (upstream's `v_stale_repos` view is the one definition of stale; archived repos excluded here):

```sql
SELECT name, language FROM v_stale_repos
WHERE COALESCE(is_archived, 0) = 0
ORDER BY name
LIMIT 20
```

Detected but unpublished packages:

```sql
SELECT r.name, p.registry, p.package_name
FROM publications p JOIN repos r ON p.repo_id = r.id
WHERE COALESCE(p.published, 0) = 0
ORDER BY r.name
```

### 3. Quality gaps (from `ops audit`, not hand-coded checks)

`ops audit` owns the definition of a quality gap: each check has a `check_id`, a category, and a severity. Do not re-derive gaps from `has_*` columns.

Recently active repos, named, with their failing checks:

```bash
repoindex ops audit --json --severity recommended --recent 14d | jq -c 'if .type == "summary" then empty else select(.failed | length > 0) | {name, failed: [.failed[].check_id]} end'
```

Collection-wide counts per check, from the trailing summary record (`checks` maps `check_id` to `{label, category, severity, passed, total}`):

```bash
repoindex ops audit --json --severity recommended | jq -c 'select(.type == "summary") | {total_repos, checks: (.checks | map_values({severity, failing: (.total - .passed)}))}'
```

Look up each failing `check_id`'s severity in the summary's `checks`; never assume one.

## Output

Prioritize, then group:

```
Sprint kickoff  (refresh: 2d ago)

Critical
  Uncommitted    N repos: repo-a, repo-b, ...
  Unpushed       M repos, K commits: repo-c (12), repo-d (3)

Active
  repo-e  (python)  14 commits, last 2h ago
  Release candidates: repo-e pypi 0.15.0, 14 commits since last tag

Important
  Active repos with audit gaps: repo-g license (critical), ci (recommended)
  Collection-wide critical: license 112 repos, readme 31 repos
  Unpublished packages: repo-h (pypi), ...

Maintenance
  Stale (no commit in 180 days): 20 shown, S total
```

Cap each name list at 5 plus a count. Omit empty sections; if everything is empty, say the collection looks quiet. Overlap between sections (a dirty repo with unpushed commits) is fine: it marks the clear priority.

End with one concrete next step per non-empty section, then ask: "Which of these do you want to focus on first?" Do not fix anything: point at the `repo-polish` agent for single-repo fixes, `repoindex ops generate <kind> --dry-run` for deterministic gaps across a filtered subset, and `repoindex ops git push --dry-run` for unpushed repos.

## When to use

- Start of the day, or returning after time away.
- "What needs attention across my repos?" / "triage my repos" / "collection health".
- Contrast with `/repo-status` (one repo or a glanceable dashboard) and `/repo-audit` (the full audit breakdown with filters).
