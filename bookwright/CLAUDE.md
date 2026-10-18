# CLAUDE.md (bookwright plugin)

This file is internal to the bookwright plugin. It is consumed by Claude Code when working ON the plugin (developing it), not when the plugin is invoked by an end user.

## Repository context

bookwright is one plugin in the `~/github/alex-claude-plugins/` (`claude-anvil`) monorepo. Sibling plugins include `worldsmith` (fiction) and `papermill` (academic papers). The `soul` plugin (voice reference and banned-phrase hooks) is NOT a sibling: it ships from its own `soul` marketplace (`queelius/soul`), and bookwright only assumes it is installed alongside.

## Development conventions

- Plugin component files (commands, agents, skills) are Markdown with YAML frontmatter.
- All command names use the `/bookwright:NAME` prefix in user-facing docs.
- Commit messages to this repo use the root convention: conventional prefixes scoped to the plugin, e.g. `feat(bookwright):`, `fix(bookwright):`. (The `bookwright:` subject prefix in agent prompts is for commits the agents make in the user's book repo, not here.)
- The plugin's design spec is at `docs/superpowers/specs/2026-05-28-bookwright-design.md`.
- v0.2 ships 11 agents: the v0.1 nine plus `rewriter` (fix-then-verify from a review report, via `/bookwright:revise`) and `iterator` (review-fix-review loop, via `/bookwright:iterate`).

## Decision handoff invariant

No bookwright agent asks the author anything: Claude Code removes `AskUserQuestion` from every subagent, even when listed in `tools`, so never add it to an agent. Judgment calls travel as data. An agent that needs the author returns a `## Decisions Needed` section holding one `decisions-needed` YAML block (the format is defined once, in `agents/rewriter.md`), in both its report file and its final message. The command that launched it, which runs in the main session, asks via AskUserQuestion and relaunches the agent with a `<decisions>` block. Entry points: `/bookwright:draft` and `/bookwright:review` (ambiguous scope), `/bookwright:revise` (rewriter judgment calls; a decisions pass writes `-revision-decisions.md`), and `/bookwright:iterate` (iterator `loop` entry hands off, `finalize` entry applies). Commands that ask must list `AskUserQuestion` in `allowed-tools`.

## Testing

`tests/` contains shell smoke tests. To run all:

```bash
cd ~/github/alex-claude-plugins/bookwright/tests && bash test-init.sh && bash test-check.sh && bash test-macro-leak-hook.sh
```

## Validation

Before releasing, run `plugin-dev:plugin-validator` against this plugin.
