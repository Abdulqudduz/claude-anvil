# CLAUDE.md: Papermill Plugin

## What This Is

Papermill is a Claude Code plugin for academic research paper lifecycle management. It provides skills (interactive workflows, each also a `/papermill:<name>` slash command) and agents (autonomous subprocesses) that cover the full pipeline from idea to submission, including three multi-agent systems: writing, reviewing, and revising.

## Plugin Structure

```
papermill/
├── .claude-plugin/plugin.json    # Plugin manifest
├── skills/                       # Skills: the core logic AND the slash entry points
│   ├── init/SKILL.md             # Initialize paper project
│   ├── status/SKILL.md           # Paper state dashboard
│   ├── thesis/SKILL.md           # Extract/refine central claim
│   ├── prior-art/SKILL.md        # Literature survey
│   ├── outline/SKILL.md          # Paper structure
│   ├── draft/SKILL.md            # Multi-agent paper drafting
│   ├── review/SKILL.md           # Multi-agent editorial review
│   ├── revise/SKILL.md           # Multi-agent revision from review findings
│   ├── venue/SKILL.md            # Publication venue matching
│   ├── experiment/SKILL.md       # Experiment design
│   ├── simulation/SKILL.md       # Monte Carlo methodology
│   ├── proof/SKILL.md            # Proof development
│   └── polish/SKILL.md           # Submission preparation
├── agents/                       # Autonomous agents
│   ├── writer.md                 # Writing orchestrator (lead author)
│   ├── literature-writer.md      # Related work & background specialist
│   ├── formal-writer.md          # Mathematical content specialist
│   ├── method-writer.md          # Methodology & algorithms specialist
│   ├── results-writer.md         # Results & discussion specialist
│   ├── reviewer.md               # Review orchestrator (area chair)
│   ├── reviser.md                # Revision orchestrator (fix-then-verify)
│   ├── surveyor.md               # Literature survey agent
│   ├── literature-scout-broad.md # Broad field survey (shared by writer & reviewer)
│   ├── literature-scout-targeted.md # Direct comparison finder (shared by writer & reviewer)
│   ├── logic-checker.md          # Proof and argument verification
│   ├── novelty-assessor.md       # Contribution evaluation against literature
│   ├── methodology-auditor.md    # Experimental design and statistical rigor
│   ├── prose-auditor.md          # Writing quality and narrative structure
│   ├── citation-verifier.md      # Reference accuracy and completeness
│   └── format-validator.md       # Build verification and venue compliance (shared)
├── docs/
│   └── state-schema.md           # Canonical .papermill/state.md schema (skills reference it)
└── CLAUDE.md                     # This file
```

## File Formats

**Skills** (`skills/<name>/SKILL.md`): YAML frontmatter with `name` and `description` (third-person with trigger phrases), optionally `argument-hint`, followed by a markdown body with imperative-form instructions and tool annotations. Each skill is invoked directly as `/papermill:<name>`; there is no `commands/` directory. Do not add a `commands/<name>.md` with the same name as a skill: inside a plugin the command shadows the skill, so the skill's description and body never load. Arguments reach the skill as `$ARGUMENTS`.

**Agents** (`agents/<name>.md`): YAML frontmatter with `name`, `description`, `tools`, `model`, and `color`, followed by a system prompt. Only the user-facing orchestrators (writer, reviewer, reviser, surveyor) carry rich descriptions with `<example>` blocks; the twelve internal specialists use a one-sentence description with no examples, because orchestrators dispatch them by hardcoded name and every agent description loads into every session's context (see the root CLAUDE.md agent description policy).

## State File

Skills read and write `.papermill/state.md` in each paper repo: YAML frontmatter (structured project state) plus a markdown body (session notes, the `## Outline` section). `docs/state-schema.md` is the single source of truth for its fields; skills reference it rather than restating it. Skills own state updates; agents return results and never edit the state file.

The `.papermill/` directory also contains:
- `reviews/YYYY-MM-DD-HHMM/`: multi-agent review output (unified `review.md` with stable finding ids F1, F2, ..., individual specialist reports, and the paired `revision.md`). One directory per run (local time of the run), so same-day runs never collide; older projects may also have plain `YYYY-MM-DD/` directories, which sort before same-day `-HHMM` ones, so "newest by name" stays correct
- `drafts/YYYY-MM-DD-HHMM/`: multi-agent draft output (section drafts, writing plan, literature context)
- `survey-results.md`: surveyor agent output

Legacy: older projects may have a `.papermill.md` file in the project root. The init skill migrates it to `.papermill/state.md`.

## Multi-Agent Writing System

`/papermill:draft` launches the `writer` orchestrator (lead author):

1. **Comprehension**: read state, outline, thesis, existing content
2. **Writing plan**: map outline sections to specialist writers
3. **Literature grounding**: 2 scouts (broad + targeted) in parallel
4. **Section drafting**: 4 specialist writers in parallel, each assigned specific sections
5. **Integration**: merge sections, unify notation, write transitions
6. **Bookend sections**: abstract, introduction, conclusion (require the full draft)
7. **Verification**: format-validator checks the build
8. **Output**: manuscript plus section drafts in `.papermill/drafts/`; the skill then updates state

### Section Writer Specialists

| Agent | Content Type | Assigned Sections |
|-------|-------------|-------------------|
| `literature-writer` | Narrative synthesis of prior work | Related Work, Background, State of the Art |
| `formal-writer` | Mathematical rigor | Preliminaries, Theory, Proofs, Formal Analysis |
| `method-writer` | Technical procedure | Method, Algorithm Design, Experimental Setup |
| `results-writer` | Evidence interpretation | Results, Analysis, Discussion, Evaluation |

Writers receive XML-tagged input: `<assignment>`, `<outline>`, `<thesis>`, `<literature_context>`, `<existing_content>`, `<prior_sections>`, `<format>`, `<venue>`. When the reviser dispatches them instead, they receive `<finding>`, `<current_text>`, `<instruction>` and return replacement text only (each writer's "Revision Mode" section).

### Shared Agents

The writing and review systems share `literature-scout-broad`, `literature-scout-targeted`, and `format-validator`. `format-validator` owns the build recipe for every format; polish and the reviser dispatch it rather than carrying their own build commands.

## Multi-Agent Review System

`/papermill:review` launches the `reviewer` orchestrator (area chair):

1. **Comprehension**: read paper and state
2. **Literature grounding**: 2 scouts in parallel
3. **Specialist review**: 6 reviewers in parallel, each receiving literature context
4. **Cross-verification**: critical or low-confidence findings get second opinions
5. **Synthesis**: deduplicate, resolve conflicts, verify quotes, calibrate severity, check blind spots, assign finding ids
6. **Report**: unified report plus specialist reports in `.papermill/reviews/YYYY-MM-DD-HHMM/`
7. **Return**: report path, recommendation, counts (the skill records them in state)

Review specialists receive `<paper>`, `<literature_context>`, `<state>`. When the reviser sends a `<verify>` block instead, they answer with a short `verdict: resolved | unresolved | regressed` (each specialist's "Verification Mode" section).

## Multi-Agent Revision System

`/papermill:revise` launches the `reviser` orchestrator on an existing review report. It parses the findings by their report ids, fixes mechanical items directly, dispatches the four section writers for technical rewrites (routed by the finding's source specialist), verifies every Critical/Major fix with the review specialist that owns that domain, and writes `revision.md` next to the source `review.md`. The skill then stamps the matching review_history entry with `revised` + `findings_fixed`, which the status dashboard uses to compute remaining unresolved findings. Reviews diagnose; revisions repair; a follow-up review confirms.

**Decision handoff invariant.** No papermill agent asks the author anything: Claude Code removes `AskUserQuestion` from every subagent, even when listed in `tools`, so never add it to an agent. Judgment calls travel as data. The reviser returns a machine-readable `decisions-needed` YAML block keyed by finding id; the revise skill (main session) asks via AskUserQuestion and relaunches the reviser with the same report, paper, and scope plus `<decisions>`, which fixes, verifies, and appends only those findings to the same `revision.md`. Follow the same pattern for any future agent that needs the author's judgment.

## Typical Workflow

```
/papermill:init          → Set up the project
/papermill:thesis        → Crystallize the central claim
/papermill:prior-art     → Survey the literature
/papermill:outline       → Design paper structure
/papermill:draft         → Multi-agent paper drafting
/papermill:review        → Multi-agent editorial review
/papermill:revise        → Apply review findings (fix-then-verify)
/papermill:proof         → Verify mathematical content
/papermill:experiment    → Design experiments
/papermill:simulation    → Design Monte Carlo studies
/papermill:venue         → Find publication venues
/papermill:polish        → Pre-submission preparation
/papermill:status        → Project dashboard
```

## Editing Guidelines

- Skills should be self-contained: each skill works independently
- Skills read `.papermill/state.md` for context but work gracefully if it doesn't exist
- `stage` only moves forward: skills advance it when it is earlier in the enum, never backward
- Agents produce structured output that the calling skill integrates; skills own the state file
- Keep prompts focused: one skill = one activity
- Avoid em-dashes in prose; use colons, commas, or parentheses
