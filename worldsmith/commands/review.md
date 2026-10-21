---
description: Launch multi-agent editorial review (consistency, craft, voice, structure auditors in parallel)
allowed-tools: Read, Write, Glob, Grep, Bash, Agent
argument-hint: "[work-name] [scope: full manuscript, or specific chapters e.g. 'chapters 3-5']"
---

# /worldsmith:review

Launch the **reviewer** orchestrator agent for a deep, multi-agent editorial review.

This spawns 4 specialist auditors in parallel (consistency, craft, voice, structure), cross-verifies critical findings, and produces a unified report to `.worldsmith/reviews/YYYY-MM-DD/`.

Pass `$ARGUMENTS` as the review scope. If no scope is specified, review the full manuscript. Also pass the plugin root (`${CLAUDE_PLUGIN_ROOT}`, as expanded here) as `<plugin_root>`, which the reviewer forwards to the craft-auditor for `count_patterns.py`.

This is the thorough review. For a lighter single-pass diagnostic, use `/worldsmith:check`.

## Multi-Work Awareness

Resolve the target work per `${CLAUDE_PLUGIN_ROOT}/skills/worldsmith-methodology/references/work-scoping.md` (work name in `$ARGUMENTS`, else the primary work, noted in the report preamble), e.g. `/worldsmith:review "The Policy" chapters 3-5`. Pass the resolved work name and manuscript path to the reviewer in the launch prompt; the report goes to `.worldsmith/reviews/YYYY-MM-DD/<work-name>/`.
