---
description: Draft and execute the paired notebook for a chapter (separable from prose drafting)
allowed-tools: Read, Glob, Agent
argument-hint: "<chapter-name-or-number>"
---

# /bookwright:notebook

Dispatch `bookwright:notebook-author` (Agent tool) with the chapter argument and the path of that chapter's plan under `docs/superpowers/plans/`. It reads the stack from `docs/superpowers/bookwright.config.yaml`, drafts or refreshes the notebook, executes it from a fresh kernel, and commits only when every sanity target passes. This is separate from `/bookwright:draft` so notebooks can be refreshed without re-drafting prose.

Relay its report: exit code, commit SHA, and the sanity-target table. If execution failed or any target missed, surface the discrepancy for the author to judge (the prose, the notebook, or the plan target may be wrong).
