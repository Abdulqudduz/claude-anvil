---
description: Weekly activity summary across the repo collection (commits, releases, top churn) via `repoindex digest`.
argument-hint: "[window, e.g. 7d, 30d, 1w, or YYYY-MM-DD; default 7d]"
allowed-tools:
  - Bash(repoindex digest:*)
---

# /repo-week

Thin wrapper around `repoindex digest`, which computes the activity rollup. Do not recompute it with SQL.

## Workflow

### Step 1: Run the digest

```bash
repoindex digest --json --top 10 --since <window>
```

Pass the argument as `<window>` unchanged, or `7d` if none was given. The CLI validates it; if it exits with `cannot parse time spec`, rerun with `7d` and say so at the top.

### Step 2: Render

The JSON has:

- `period`: `{since, until, days}`
- `summary`: `{repos_active, total_commits, total_tags, total_merges}` (collection-wide, not limited by `--top`)
- `projects`: top repos by commit count, each `{name, language, commits, by_type, scopes, recent_messages, tags, is_dirty}`
- `releases`: `{repo, tag, timestamp}`, newest first (from git tags)
- `languages`: `[[language, active_repo_count], ...]`

Layout:

```
Week in review (since..until)

Commits: total_commits across repos_active repos, total_tags tags, total_merges merges

Top churn
  repo-a  (python)  42 commits  feat 20, fix 12  [dirty]
          "most representative recent message"
  ...

Releases
  repo-a   v0.16.0   2 days ago
  ...

Languages: Python 29, Rust 3, ...
```

Show `by_type` only when it has more than the `other` bucket, and one recent message per project. If `summary.total_commits` is 0, say it was a quiet period and stop.

## When to use

- Weekly review at the start of the work week; `30d` for a monthly retrospective.
- Contrast with `/repo-sprint`, which is health triage rather than an activity summary.
