# Work Scoping

How worldsmith commands and orchestrators pick which work they operate on in a
multi-work universe. This file is the single definition; commands reference it
by path instead of restating it.

## When it applies

A project is multi-work when `.worldsmith/project.yaml` exists. It declares the
universe, a shared `lore` directory, and a `works` list; each work has a
`name`, a `type`, a `manuscript` directory, and optionally its own `lore`
directory. Without `project.yaml` the project is single-work and the manuscript
directory is inferred from convention (`chapters/`, `manuscript/`, `scenes/`,
`stories/`).

## Selecting the work

- If a recognized work name appears in `$ARGUMENTS`, scope to that work. Names
  with spaces may be quoted: `/worldsmith:review "The Policy" chapters 3-5`.
- If no work name is given and several works exist, use the **primary work**
  (the first entry in `works`) and say so: in the launch prompt for agent
  commands, in the report preamble for reports.
- The rest of `$ARGUMENTS` (scope, filters, flags, assignment) is passed
  through after the work name is removed.
- Pass the resolved work name, its manuscript path, and its local lore path (if
  any) to the agent in the launch prompt.

## What is scoped and what is shared

- **Manuscript**: reads and edits target only the selected work's `manuscript`
  directory.
- **Shared lore**: always shared. Every work reads it, and a change to it is
  universe-wide: propagation must check every work's manuscript that may
  reference the changed fact.
- **Local lore**: the selected work's `lore` directory, if set, is read in
  addition to shared lore. Conflict hierarchy: shared lore > local lore >
  manuscript.

## Report paths

| Artifact | Single-work | Multi-work |
|----------|-------------|------------|
| Review | `.worldsmith/reviews/YYYY-MM-DD/review.md` | `.worldsmith/reviews/YYYY-MM-DD/<work>/review.md` |
| Revision | next to its review, `revision.md` | next to its review, `revision.md` |
| Iterate session | `.worldsmith/iterate/<timestamp>/` | `.worldsmith/iterate/<timestamp>/<work>/` |

To find the latest review, sort the date directories by name (ISO dates sort
correctly; modification time does not, because revising an old review touches
its directory): `ls .worldsmith/reviews/ | sort | tail -1`. In a multi-work
project, take the latest date directory that contains `<work>/review.md`.
