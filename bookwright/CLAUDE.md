# CLAUDE.md (bookwright plugin)

This file is internal to the bookwright plugin. It is consumed by Claude Code when working ON the plugin (developing it), not when the plugin is invoked by an end user.

## Repository context

bookwright is one plugin in the `~/github/alex-claude-plugins/` (`claude-anvil`) monorepo. Sibling plugins include `worldsmith` (fiction) and `papermill` (academic papers). The `soul` plugin (voice reference and banned-phrase hooks) is NOT a sibling: it ships from its own `soul` marketplace (`queelius/soul`), and bookwright only assumes it is installed alongside.

## Development conventions

- Plugin component files (commands, agents, skills) are Markdown with YAML frontmatter.
- All command names use the `/bookwright:NAME` prefix in user-facing docs.
- Commit messages to this repo use the root convention: conventional prefixes scoped to the plugin, e.g. `feat(bookwright):`, `fix(bookwright):`. (The `book:` subject prefix in agent prompts is for commits the agents make in the user's book repo, not here.)
- 11 agents: orchestrators `writer`, `reviewer`, `rewriter`, `iterator`; drafting specialists `section-writer`, `notebook-author`, `source-reformulator`; auditors `spec-auditor`, `quality-auditor`, `math-auditor`, `cross-ref-auditor`. The original design spec and v0.1 implementation plan were removed; git history keeps them.
- Shared contracts, each defined once: the auditor verdict enum `PASS / MINOR / SUBSTANTIVE / BLOCKING` (every auditor's report ends with it); the rewriter's `revision-summary` YAML block (`agents/rewriter.md`, read by name by the iterator); notebook execution commands (`agents/notebook-author.md`); the header comment block template (`skills/cross-reference-discipline/SKILL.md`).
- Project-specific facts (macro package, known corrections, banned phrases, forward-ref baselines) live in the user's book repo (`docs/superpowers/bookwright.config.yaml`, `docs/superpowers/known-corrections.yaml`, `book/CLAUDE.md`, integration-pass records), never in plugin prompts.

## Decision handoff invariant

No bookwright agent asks the author anything: Claude Code removes `AskUserQuestion` from every subagent, even when listed in `tools`, so never add it to an agent. Judgment calls travel as data. An agent that needs the author returns a `## Decisions Needed` section holding one `decisions-needed` YAML block (schema and asking procedure defined once, in `skills/textbook-methodology/references/decision-handoff.md`; commands point to it rather than restating it), in both its report file and its final message. The command that launched it, which runs in the main session, asks via AskUserQuestion and relaunches the agent with a `<decisions>` block. Entry points: `/bookwright:draft` and `/bookwright:review` (ambiguous scope), `/bookwright:revise` (rewriter judgment calls; a decisions pass writes `-revision-decisions.md`), and `/bookwright:iterate` (iterator `loop` entry hands off, `finalize` entry applies). Commands that ask must list `AskUserQuestion` in `allowed-tools`.

## Testing

`tests/` contains shell tests. They glob the component files (no hand-kept lists), so adding an agent, command, or skill needs no test edit. The tests and the macro-leak hook (only when it must read a config and its own python3 lacks PyYAML) share one interpreter resolver, `hooks/scripts/find_python.sh` (`$PYTHON`, `python3`, `/usr/bin/python3`, then `uv run --no-project --with pyyaml`). To run all:

```bash
cd ~/github/alex-claude-plugins/bookwright/tests && for t in test-*.sh; do bash "$t" || exit 1; done
```

## Validation

Before releasing, run `plugin-dev:plugin-validator` against this plugin.
