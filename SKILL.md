---
name: anvil
description: >-
  Universal forge for academic research, fiction worldbuilding, technical textbook authoring,
  software package publishing, Amazon KDP book releases, and content operations. Use this skill when:
  (1) conducting academic literature research, autonomous theorem/experiment loops, or drafting
  and reviewing papers (Papermill, Vista, Research-Agent); (2) worldbuilding and drafting fiction
  novels with documentation-first canon authority and prose craft auditing (Worldsmith); (3) writing
  technical non-fiction textbooks with LaTeX and paired Jupyter computational notebooks (Bookwright);
  (4) publishing R (CRAN) or Python (PyPI) packages and JOSS software papers (Pub-Pipeline); (5) preparing
  and publishing books on Amazon KDP with manuscript audits, listing optimization, and automated cover
  wraps (KDP); or (6) running repository intelligence, multi-platform cross-posting, or content encryption.
---

# Anvil: Universal Forge for Research, Fiction, Textbooks, and Publishing

Anvil transforms the capabilities of the eleven specialized publication, research, and authoring tools from `claude-anvil` into a portable, agent-agnostic skill. It enables any compatible AI assistant (Google Antigravity, OpenCode, Claude Code, Codex, Cursor) to manage complex scholarly, creative, and technical workflows with strict domain discipline.

---

## Quick Domain Dispatcher

When activated, identify the user's project domain and consult the corresponding workflow and reference guide:

| Project Domain | Core Capabilities | Primary Workflow | In-Depth Reference |
| :--- | :--- | :--- | :--- |
| **Academic Research** | OpenAlex literature reconnaissance, autonomous proof/simulation loops, thesis drafting, multi-angle peer review | [research-pipeline.md](./workflows/research-pipeline.md) | [academic-research.md](./references/academic-research.md) |
| **Fiction Worldbuilding** | "Silmarillion approach" documentation-first canon tracking, scene drafting, prose craft & cliche auditing | [fiction-worldsmith.md](./workflows/fiction-worldsmith.md) | [fiction-worldbuilding.md](./references/fiction-worldbuilding.md) |
| **Technical Textbook** | Atom-outward LaTeX authoring, paired computational Jupyter notebooks, notation discipline, macro leak checks | [textbook-bookwright.md](./workflows/textbook-bookwright.md) | [textbook-authoring.md](./references/textbook-authoring.md) |
| **Software Publishing** | R/CRAN zero-tolerance verification, Python/PyPI packaging, JOSS/JSS peer-reviewed software papers | [software-publishing.md](./workflows/software-publishing.md) | [software-publishing.md](./references/software-publishing.md) |
| **Amazon KDP Books** | Interior geometry audits, spine width math, print cover wraps, high-converting blurbs, 7 search keywords | [kdp-publishing.md](./workflows/kdp-publishing.md) | [kdp-publishing.md](./references/kdp-publishing.md) |
| **Content Operations** | Multi-platform cross-posting (Dev.to, Bluesky, Mastodon), Git catalog sprint triaging, encryption routing | [content-operations.md](./workflows/content-operations.md) | [content-operations.md](./references/content-operations.md) |

---

## Universal Project Detection and CLI

Anvil provides a portable Python CLI executable at `scripts/anvil`:

```bash
# Detect active project domain and marker files
python3 scripts/anvil detect

# Show repository health, state files, and active git status
python3 scripts/anvil status

# Audit LaTeX files for leaked source macros
python3 scripts/anvil check-latex chapters/*.tex

# Audit fiction manuscripts for cliches, weak verbs, and fancy dialogue tags
python3 scripts/anvil check-prose "chapters/*.md"

# Inspect and manage bundled MCP servers (vista, kdp-cover, crier)
python3 scripts/anvil mcp status
```

---

## Core Domain Operating Instructions

### 1. Academic Research & Paper Lifecycle
1. **Reconnaissance (Vista)**: Query OpenAlex to locate highly-cited papers; extract *Future Work* and *Limitations* sections from open-access PDFs to isolate genuine research gaps.
2. **Autonomous Proofs & Simulations (Research-Agent)**: Formulate hypotheses in `.research/state.md`, implement simulations or LaTeX derivations in `.research/attempts/`, and accumulate verified results in `.research/synthesis.md`.
3. **Paper Authoring & Review (Papermill)**: Maintain `.papermill/state.md`, refine thesis claims, enforce BibTeX resolution, and run multi-angle reviews (Methodology, Logic, Citations, Format, Craft).
4. *Full runbook*: [workflows/research-pipeline.md](./workflows/research-pipeline.md)

### 2. Fiction Worldbuilding & Novel Writing
1. **The Silmarillion Approach**: Establish canonical authority documents (`world/timeline.md`, `lore.md`, `characters.md`, `systems.md`, `conventions.md`) before writing chapter prose.
2. **Propagation Invariant**: When creative changes occur, update canonical documents *before* modifying manuscript chapters.
3. **Prose Craft Standards**: Eliminate crutch words (`just`, `very`), sensory filter words (`could see`), weak verbs (`started to`), and adverb dialogue tags (`said angrily`).
4. *Full runbook*: [workflows/fiction-worldsmith.md](./workflows/fiction-worldsmith.md)

### 3. Technical Textbooks with LaTeX & Notebooks
1. **Atom-Outward Design**: Write chapter design plans (`docs/plans/chXX-plan.md`) decomposing topics into atomic pedagogical units with fixed page budgets.
2. **Paired Computational Notebooks**: Mirror mathematical equations in runnable Jupyter notebook code cells (`notebooks/chXX.ipynb`) with deterministic seeds.
3. **Macro-Leak Guard**: Never display internal macro names (`\texttt{\textbackslash foo}`) or refer to "the macro" in reader prose. Run `scripts/anvil check-latex`.
4. *Full runbook*: [workflows/textbook-bookwright.md](./workflows/textbook-bookwright.md)

### 4. Software Package Publishing & JOSS
1. **R (CRAN)**: Run `R CMD check --as-cran` aiming for 0 errors, 0 warnings, 0 notes. Verify `DESCRIPTION` metadata and vignette execution.
2. **Python (PyPI)**: Build wheels via `uv build` or `python -m build`, verify with `twine check`, and dry-run on TestPyPI.
3. **JOSS Paper**: Author `paper.md` with explicit *Statement of Need* and *State of the Field* citing competing packages.
4. *Full runbook*: [workflows/software-publishing.md](./workflows/software-publishing.md)

### 5. Amazon KDP Commercial Publishing
1. **Spine Geometry**: Calculate exact spine width: $\text{Pages} \times \text{Paper Factor}$ (e.g. 0.002252 for white, 0.0025 for cream) plus 0.125" bleed.
2. **Listing Copywriting**: Author 5-part blurbs (Hook -> Premise -> Conflict -> Stakes -> CTA), 7 strategic search keyword phrases (< 50 chars), and 3 browse categories.
3. **Automated Cover Wrap**: Generate print-ready full-wrap PDFs via the bundled TypeScript cover engine (`kdp/mcp/run.sh`).
4. *Full runbook*: [workflows/kdp-publishing.md](./workflows/kdp-publishing.md)

### 6. Content Operations & Cryptography
1. **Cross-Posting (Crier)**: Adapt blog posts for Dev.to, Hashnode, Bluesky (300 char limit), and Mastodon (500 char limit). Use two-phase approval.
2. **Repository Intelligence (Repoindex)**: Run collection-wide sprint triage for dirty checkouts, unpushed commits, and audit gaps.
3. **Encryption Routing (Alex-Confidential)**: Route Hugo posts to `cryptoid`, standalone HTML to `pagevault`, and raw developer files/keys to `gpg`.
4. *Full runbook*: [workflows/content-operations.md](./workflows/content-operations.md)

---

## Agent Roles and Decision Handoff

- **40+ Specialized Agent Personas**: Detailed system prompts, input/output schemas, and tool permissions for orchestrators, content producers, and specialized auditors are cataloged in [references/agent-roles.md](./references/agent-roles.md).
- **Decision Handoff Protocol**: When creative or technical direction requires author input, format a structured `Decisions Needed` block listing the dilemma, 2-4 concrete options with trade-offs, and your recommended choice. Never guess canon or make silent assumptions.

---

## Cross-Agent Installation and Setup

- **Google Antigravity**: Discovered via `.agents/skills/anvil/SKILL.md` (workspace) or `~/.gemini/config/skills/anvil/` (global).
- **OpenCode**: Discovered via `.opencode/skills/anvil/SKILL.md` or `~/.config/opencode/skills/anvil/`.
- **Claude Code**: Backward-compatible with marketplace manifest `.claude-plugin/marketplace.json` and individual plugin directories.
- For complete setup instructions, MCP server registration, and tool mapping details, see [references/cross-agent-compatibility.md](./references/cross-agent-compatibility.md).
