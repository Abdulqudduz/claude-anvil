# Decision Handoff

How worldsmith agents surface creative judgment calls to the author, and how
commands resolve them. This file is the single definition: agent prompts and
commands reference it by path (`${CLAUDE_PLUGIN_ROOT}` is substituted in agent
and command bodies) rather than copying the schema.

## Why

Claude Code removes `AskUserQuestion` from every subagent, even when an agent
lists it in `tools`. So agents (writer, rewriter, iterator, and their
specialists) can never ask the author anything. They record the question and
return it; the slash command, which runs in the main session where
`AskUserQuestion` works, does the asking and re-dispatches.

## The decision record

Agents emit a `## Decisions Needed` section, in their report file (when they
write one) AND verbatim in their final return message, containing one fenced
YAML block:

```yaml
deferred-judgments:
  - finding-id: <stable unique id, e.g. R002-F07, lore-1, char-2, scope-1>
    location: <file:line, or doc and section; "n/a" for scope questions>
    severity: HIGH|MEDIUM|LOW        # review findings only; omit otherwise
    stake: low|medium|high
    question: <one sentence the author can answer>
    original-finding: <the review finding, or the context that raised the question>
    suggested-options:
      - label: <short label, about 5 words max>
        consequence: <what choosing it does to the story or world>
      - label: <...>
        consequence: <...>
    recommended: <label of the recommended option>
    provisional: <label the draft currently uses; drafting only, omit otherwise>
```

Rules:

- 2 to 4 options per item (AskUserQuestion's limit). The recommended option
  must be one of them.
- An empty list means nothing needs the author: write `deferred-judgments: []`.
- `finding-id` must be unique within one return. The iterator prefixes each
  round's ids with the round (`R002-`) when it aggregates.

## Resolving decisions (commands only)

After an agent returns, a command that dispatched it:

1. Reads the `deferred-judgments` list from the return message (or from the
   report file the agent names). If the list is empty, the command is done.
2. If more than 12 items are pending, first asks one meta question with three
   options: resolve individually; best-guess all (use every item's
   `recommended` option and document it); stop and leave them for manual
   review (write them to an `unresolved.md` next to the report).
3. Otherwise (or after "resolve individually"), batches the items into
   AskUserQuestion calls: at most 4 questions per call, related items (same
   location or category) grouped in the same call, at most 4 calls (16
   questions). Items beyond 16 go to `unresolved.md`.
   - question: the item's `question`, plus its `location`
   - header: a label of 12 characters or fewer, from the category or id
   - options: the item's `suggested-options` (label, consequence as the
     description), the recommended one first with " (Recommended)" appended
4. Builds a decisions list, one entry per answered item:
   `{finding_id, location, chosen_option, rationale}`. A free-text "Other"
   answer becomes the `chosen_option` verbatim. Best-guess-all entries use the
   `recommended` label with rationale "best guess: author delegated".
5. Re-dispatches to apply ONLY those decisions, as the command specifies
   (rewriter `final-revise` mode with `<fix-guidance>`, iterator `finalize`
   mode, or writer with `<decisions>`). For drafting, items whose answer equals
   their `provisional` label need no re-dispatch: the draft already uses it.
