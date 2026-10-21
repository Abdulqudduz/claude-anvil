---
description: Launch the writer orchestrator to draft scenes, chapters, lore, or character work
allowed-tools: Read, Glob, Grep, Agent, AskUserQuestion
argument-hint: "[work-name] [assignment, e.g. 'chapter 5', 'Greymoor battle scene', 'develop the Ashwalker culture']"
---

# /worldsmith:draft

Launch the **writer** orchestrator agent to produce new content for the project.

The writer plans the assignment, then dispatches specialist agents in parallel:

- `lore-writer` for history, mythology, cultures, systems
- `scene-writer` for prose scenes with craft discipline
- `character-developer` for voice patterns, arcs, relationships

It integrates their output, propagates new facts into the canonical doc ecosystem, and writes manuscript content to the appropriate directory.

For revising existing prose against a review report, use `/worldsmith:revise` instead. This command is for creating new content.

## Assignment

Pass `$ARGUMENTS` to the writer as the assignment. The writer classifies it (lore, scene, character, multi-specialist) during its Phase 2. The command does not pre-classify.

Examples of valid assignments:
- `chapter 5`
- `the opening scene where Maren confronts her mother`
- `Greymoor battle scene`
- `develop the Ashwalker culture`
- `flesh out Sera's backstory`

If `$ARGUMENTS` is empty or ambiguous, the writer stops before writing and returns scope questions instead of guessing (see "Resolving Decisions").

## Multi-Work Awareness

Resolve the target work per `${CLAUDE_PLUGIN_ROOT}/skills/worldsmith-methodology/references/work-scoping.md` (work name in `$ARGUMENTS`, else the primary work), e.g. `/worldsmith:draft Hemorrhagic the opening scene`. Manuscript output goes to that work's `manuscript` directory; shared-lore updates from the draft are universe-wide. Pass the resolved work name, manuscript path, local lore path, and the assignment to the writer in the launch prompt.

## Resolving Decisions

The writer and its specialists cannot ask questions (Claude Code removes AskUserQuestion from subagents), so they return judgment calls in a `## Decisions Needed` section. After the writer returns, read its `deferred-judgments` list. If it is empty, present the writer's summary and stop. Otherwise ask with AskUserQuestion following `${CLAUDE_PLUGIN_ROOT}/skills/worldsmith-methodology/references/decision-handoff.md` (max 4 questions per call, 4 options each, recommended option first), then:

- **Scope items** (`scope-<n>`, returned before anything was written): relaunch the writer with the original assignment rewritten to reflect the author's answers.
- **Provisional creative choices** (`lore-`, `char-`, `plot-` items): the draft already uses each item's `provisional` option. Drop items where the author picked that option. If any remain, relaunch the writer with the original assignment plus:

```xml
<decisions>{list of finding_id, location, chosen_option, rationale}</decisions>
```

  The writer runs its Decision Pass: it revises only the affected passages and docs, and propagates.

Report which provisional choices were confirmed and which were changed.
