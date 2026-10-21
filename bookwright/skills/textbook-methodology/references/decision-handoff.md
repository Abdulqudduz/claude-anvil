# Decision handoff (bookwright)

Subagents cannot ask the author anything: Claude Code removes `AskUserQuestion` from every subagent, even when it is listed in `tools`. Judgment calls therefore travel as data. An agent that needs the author stops (or finishes what it can), and returns a `## Decisions Needed` section holding one fenced `decisions-needed` YAML block, both in its report file (when it writes one) and verbatim in its final message. The command that launched it runs in the main session, asks the author, and relaunches the agent with a `<decisions>` block.

## Schema

```yaml
decisions-needed:
  - id: D1                     # stable within this report: D1, D2, ...
    finding: S3                # the source review finding id (omit for scope questions)
    title: "Variance bound used before the coupling argument"   # the source finding's title, verbatim (omit for scope questions)
    severity: SUBSTANTIVE      # BLOCKING | SUBSTANTIVE | MINOR (omit for scope questions)
    stake: high                # high | medium | low (omit for scope questions)
    location: book/chapters/ch05/sec-5-3.tex:142   # omit for scope questions
    question: "Should the coupling argument move ahead of the variance bound?"
    options:                   # 2 to 4 options
      - label: "Move it ahead"
        consequence: "Matches the plan's dependency order; rewrites the opening of 5.3"
      - label: "Keep the current order"
        consequence: "Preserves the draft; add a forward reference to the bound"
    recommended: "Move it ahead"   # must equal one option's label
```

Scope questions (writer, reviewer, iterator setup) use only `id`, `question`, `options`, and `recommended`; the options are the concrete candidate scopes found with Glob.

The iterator keys each deferred finding as `{file, title}`: `location` without its line number, plus `title`. Ids are only unique within one report, so the key is what lets later rounds recognize an already-deferred finding. The iterator's aggregated `decisions-needed.md` renumbers ids D1..Dn across rounds and adds `round: N` to each item.

## Stake

- `high`: changes a theorem or definition statement, cuts or adds planned content, or alters chapter structure.
- `medium`: picks between substantively different explanations or examples within the plan.
- `low`: local wording, framing, or ordering choices that leave the plan's content intact.

## Asking procedure (main-session commands)

1. If the block has more than 8 items, first ask how to proceed: resolve them individually, accept every recommended option, or stop and leave them unresolved.
2. To resolve individually, call AskUserQuestion with one question per item: its `question`, its `options` (label as the option, consequence as the description), and the `recommended` option listed first with "(Recommended)". Batch at most 4 questions per call and group items that touch the same section.
3. Relaunch the agent with the original arguments plus a `<decisions>` block: a list of `{id, finding, choice}` where `choice` is the chosen label (omit `finding` for scope questions). Items the author skipped are left out; the agent records them as unresolved.

Every command that asks must list `AskUserQuestion` in its `allowed-tools`.
