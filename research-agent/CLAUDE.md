# CLAUDE.md: Research Agent Plugin

## What This Is

An autonomous research agent plugin for Claude Code. Given a goal, an optional eval script, and an optional budget, the agent runs a reasoning loop: decomposing, hypothesizing, attempting (proofs, code, simulations, counterexample search), evaluating, and reflecting, until the goal is met, it stalls, its budget runs out, or it is asked to stop. It works directly in the target project directory, creating a `.research/` directory for its artifacts.

## Plugin Structure

```
research-agent/
  .claude-plugin/plugin.json    # Plugin manifest
  skills/research/SKILL.md      # /research-agent:research: parse goal + eval + budget, spawn agent
  skills/status/SKILL.md        # /research-agent:status: read-only status (no agent dispatch)
  skills/resume/SKILL.md        # /research-agent:resume: continue an interrupted run or branch
  skills/synthesize/SKILL.md    # /research-agent:synthesize: signal a live run to stop, or dispatch synthesis
  skills/branch/SKILL.md        # /research-agent:branch: fork a run into a named branch in a git worktree
  agents/researcher.md          # The autonomous research agent (mode-aware)
  CLAUDE.md                     # This file
```

There is no `commands/` directory on purpose. Each skill is the slash command (`argument-hint` and `$ARGUMENTS` in its frontmatter and body). Inside a plugin a same-name command shadows the skill entirely (verified on Claude Code 2.1.306), so do not add `commands/<name>.md` wrappers.

## How It Works

The agent has four modes, selected by the XML tags the launching skill passes:

- **fresh**: `<goal>` plus `<eval>`, optional `<budget>`. Used by `/research-agent:research`. Creates `.research/`, writes goal.md and run.json, optionally runs the eval baseline, then begins DECOMPOSE. Refuses (never archives) if `.research/` exists.
- **resume**: `<mode>resume</mode>`, optional `<branch>`, `<budget>`, `<reopen/>`. Used by `/research-agent:resume`. Reloads the structured state (migrating legacy prose-only runs once) and continues from `current_focus`. A concluded run is reopened only with `<reopen/>`, which the skill passes after asking the user.
- **branch**: `<mode>branch</mode>` plus `<branch>`, optional `<branch-focus>`, `<budget>`. Used by `/research-agent:branch`, launched with `isolation: "worktree"` in git repos. Forks into `.research/branches/<name>/`; code changes live in the worktree, committed once per cycle.
- **synthesize**: `<mode>synthesize</mode>`, optional `<branch>`. Used by `/research-agent:synthesize` only when no researcher is live. Finalizes statuses, writes synthesis.md (with a Branch Comparison on the main line), and exits.

Skills pass only tags; the step-by-step behavior of each mode lives once, in the agent's Initialization section. Do not re-spell those steps in skill launch templates.

The status skill is **not** an agent dispatch: it reads `.research/` files directly. This is faster, cheaper, and deterministic, and it never accidentally restarts the agent.

### Run control and liveness

`run.json` is the cross-process control channel. A run is **live** when `status` is `running` or `stopping` and `heartbeat` is younger than `stale_after_minutes`. The agent refreshes the heartbeat every cycle and whenever it checks a background job.

- research and resume refuse to launch over a live run (resume allows a user-confirmed override when the earlier session is known to be gone).
- synthesize on a live run does not dispatch a second agent: it Edits `status` to `stopping`, and the live agent runs its Termination Protocol at the next cycle boundary.
- Budget (`max_cycles` total, `max_hours` per launch) is persisted in run.json and honored on resume; a resume `<budget>` replaces it. Exhausting it triggers the Termination Protocol.
- While running, run.json is changed only by single-field Edits so a concurrent `stopping` request is never overwritten.

## The `.research/` Artifact Contract

The agent operates on the **target project's** working directory (not on this plugin). Every mode coordinates through this directory; treat it as the cross-mode interface. The full schemas are in the agent's "Run Files" section; that is the single source, and skills read the fields named there.

```
.research/
  goal.md         # YAML frontmatter {eval, created} + verbatim goal body. Written once; never edited.
  run.json        # {status, mode, launched, heartbeat, stale_after_minutes, budget, policy, worktree}.
  state.md        # YAML frontmatter {cycle, current_focus, subproblems[], hypotheses[]} + prose body
                  # (Outcome so far, Notes). The frontmatter is the source of truth for "where am I?".
  cycles.jsonl    # One record per cycle: {cycle, ts, hypothesis, modality, attempt, result, score, decision}.
  scores.jsonl    # One record per eval run: {cycle, attempt, exit, score, ts}; baseline is cycle 0, attempt null.
  log.md          # Append-only human narrative. Never parsed by skills except as a legacy fallback.
  attempts/       # One subdirectory per attempt: NNN-<slug>/notes.md plus artifacts.
  findings/       # Confirmed results promoted out of attempts/.
  synthesis.md    # Final deliverable. Presence => concluded. Older versions kept as synthesis-<ts>.md.
  branches/<name>/  # Each branch is its own run root: run.json (with worktree), state.md,
                    # cycles.jsonl, scores.jsonl, log.md, attempts/, findings/, synthesis.md.
                    # Branches never write the parent's files; promotion into the parent's
                    # findings/ happens only at a main-line synthesis, with a provenance note.
```

Invariants: log.md and the jsonl files are append-only; goal.md is written once; synthesis.md is the single document a future reader relies on; machine state lives in run.json, the state.md frontmatter, and the jsonl files, never in prose that skills must grep. Runs from older plugin versions (prose-only state.md, no run.json or cycles.jsonl) are handled by explicit legacy fallbacks in status and resume, and the agent migrates them once on resume or synthesize. Any new mode must respect these invariants and extend this section if it adds files.

## Editing Guidelines

- The agent prompt (`agents/researcher.md`) contains the full research methodology, the file schemas, and mode dispatch. It is intentionally large. Keep sections well-organized with clear headers.
- Each skill is thin: parse user intent, check liveness and preconditions, and pass the right XML tags (or, for status, read files directly). Do not put research methodology in skills.
- Skills that dispatch the researcher use `subagent_type: research-agent:researcher`. Any new mode that runs the agent must use the same subagent_type.
- The agent uses `model: inherit`, so it runs on whatever model the session selected. Choose Fable for the longest runs with `/model fable`; the 1M context window comes with a Fable or Opus-1M session. Pinning `model: fable` in frontmatter is avoided on purpose: a subagent spawn that explicitly requests Fable can be rejected by an availableModels policy, account access, or an older Claude Code version, whereas `inherit` honors the user's choice. Long runs still need the on-disk state because very long runs may compress earlier history; the disk is always the source of truth.

When adding a new mode, edit in lockstep: (1) a new `skills/<mode>/SKILL.md` (with `argument-hint` if it takes arguments), (2) a new section in the agent's Initialization block documenting the mode and its trigger tags, and (3) the mode list in "How It Works" above. If the mode reads or writes `.research/`, also extend the agent's Run Files section and the Artifact Contract above.

## Capabilities

The researcher has three categories of tools:

1. **File and shell**: `Bash`, `Monitor`, `TaskStop`, `ToolSearch`, `Read`, `Write`, `Edit`, `Glob`, `Grep`. Long experiments run with `Bash` `run_in_background: true` (output redirected into the attempt directory and recorded in log.md), are watched with `Monitor` or by reading the output file, and are ended with `TaskStop`. Monitor, TaskStop, WebSearch, and WebFetch may be deferred tools in a subagent, so `ToolSearch` is granted to load them. A subagent's run ends when its turn ends, so the agent must never end its turn with a background job pending: it collects or TaskStops each one first and logs the output path. (`BashOutput` no longer exists; `KillShell` is a legacy alias of `TaskStop`.)
2. **Research**: `WebSearch`, `WebFetch` for prior-art lookups, paper retrieval, and reference verification.
3. **Delegation**: `Agent` for spawning child sub-agents that pursue parallel approaches. Children are general-purpose agents (never `research-agent:researcher`, whose mode dispatch would treat `.research/` as its own run), write only to the attempt directory the researcher pre-creates for them, and run with `isolation: "worktree"` when they modify project code.

Note the two-level use of `Agent`. The launching skills use it with `subagent_type: research-agent:researcher` to spawn the *top-level* researcher; the researcher uses it for *child* sub-agents. Nesting depth: the researcher is layer 1 below the main session and its children layer 2, within Claude Code's default limit of 3 (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`).

When extending the agent, prefer giving it more capability in these existing categories over adding new ones.
