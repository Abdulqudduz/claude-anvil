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

If `.worldsmith/project.yaml` exists, this project contains multiple works sharing canonical lore.

**Work selection from `$ARGUMENTS`:**
- If a recognized work name appears in the arguments, scope the draft to that work's manuscript directory.
- If no work name is specified and multiple works exist, default to the **primary work** (first in `project.yaml`) and note this in the launch prompt.
- Arguments can combine work name and assignment: `/worldsmith:draft Hemorrhagic the opening scene` or `/worldsmith:draft "The Policy" chapter 5`.

**Scoping rules:**
- Manuscript output goes to the selected work's `manuscript` directory.
- Canonical docs (shared lore) are always shared. Updates from the draft affect all works that reference the changed lore.
- Work-specific lore (per-work `lore:` directory in `project.yaml`, if present) is also available to the writer.
- For single-work projects (no `project.yaml`), the writer infers the manuscript directory from common conventions (`chapters/`, `manuscript/`, `scenes/`).

Pass the resolved work name, manuscript path, and assignment to the writer agent in the launch prompt.

## Resolving Decisions

The writer and its specialists cannot ask questions (Claude Code removes AskUserQuestion from subagents), so they return judgment calls in a `## Decisions Needed` section. After the writer returns, read its `deferred-judgments` list. If it is empty, present the writer's summary and stop. Otherwise ask with AskUserQuestion following `${CLAUDE_PLUGIN_ROOT}/skills/worldsmith-methodology/references/decision-handoff.md` (max 4 questions per call, 4 options each, recommended option first), then:

- **Scope items** (`scope-<n>`, returned before anything was written): relaunch the writer with the original assignment rewritten to reflect the author's answers.
- **Provisional creative choices** (`lore-`, `char-`, `plot-` items): the draft already uses each item's `provisional` option. Drop items where the author picked that option. If any remain, relaunch the writer with the original assignment plus:

```xml
<decisions>{list of finding_id, location, chosen_option, rationale}</decisions>
```

  The writer runs its Decision Pass: it revises only the affected passages and docs, and propagates.

Report which provisional choices were confirmed and which were changed.
