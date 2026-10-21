# research-agent

An autonomous research agent for Claude Code. Give it a goal, optionally an eval
script, and optionally a budget; it runs a reasoning loop, decomposing the
problem, forming hypotheses, attempting solutions (proofs, code, simulations,
counterexample search), evaluating results, and reflecting on what to try next.
It is fire-and-forget: the agent works on its own and writes everything to disk.

## Install

```
/plugin install research-agent@queelius-plugins
```

## Commands

| Command | What it does |
|---------|--------------|
| `/research-agent:research <goal> [eval script at ./eval.sh] [budget: N cycles, H hours]` | Launch a fresh run. Without a budget it runs until it concludes on its own. |
| `/research-agent:status` | Read-only progress: liveness, cycles and budget, current focus, eval trend, branches. |
| `/research-agent:resume [branch] [budget]` | Continue an interrupted run (or a branch) after a session restart. |
| `/research-agent:synthesize [branch]` | Conclude now: asks a live run to wrap up, or writes the synthesis itself. A main-line synthesis compares branches. |
| `/research-agent:branch <name> [focus]` | Fork the run at its checkpoint into a branch pursuing a competing strategy, in its own git worktree. |

## Example

```
/research-agent:research Prove or disprove that every even number greater than 2
is the sum of two primes. eval script at ./goldbach_check.sh, budget: 30 cycles
```

Then, while it runs:

```
/research-agent:status        # check cycle progress and eval trend
/research-agent:synthesize    # ask it to wrap up once results are good enough
```

## The eval contract (optional)

If you pass an eval script, the agent runs it from the project directory with no
arguments. Exit 0 means the goal is achieved; exit 1 means not yet (and if the
last stdout line is `score: <float>`, that float is recorded); any other exit
code is treated as a script error and the agent self-evaluates that cycle.
Results accumulate in `.research/scores.jsonl`. Without a script, the agent
self-evaluates throughout.

## Where output lands

The agent works in your **target project's** directory (not in the plugin) and
maintains a `.research/` directory:

```
.research/
  goal.md         the goal, plus eval path in frontmatter; written once
  run.json        liveness, budget, and stop control
  state.md        current beliefs (structured frontmatter) and a rolling outcome summary
  cycles.jsonl    one record per research cycle
  scores.jsonl    one record per eval run
  log.md          append-only narrative log
  attempts/       one subdirectory per attempt, with notes and artifacts
  findings/       confirmed results promoted out of attempts/
  synthesis.md    the final deliverable; its presence means the run concluded
  branches/<name>/  forked strategy lines, each with its own state and log;
                    their code changes live in a separate git worktree
```

The disk is the source of truth: very long runs may compress earlier
conversation history, so the agent (and `/research-agent:resume`) reorients from
these files. The single document a future reader relies on is `synthesis.md`.

## Notes

- The agent runs on `model: inherit`, so it uses your session's model. Pick Fable
  for long autonomous runs with `/model fable` (its 1M context window comes with
  the session).
- For internal and editing details, see `CLAUDE.md`.
