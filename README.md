# Anvil: Universal Agent Skill for Research, Worldbuilding, and Publishing

> **A portable, agent-agnostic forge for academic research, fiction worldbuilding, technical textbook authoring, software package release, and commercial book publishing.**
>
> Originally created as `queelius/claude-anvil` (a Claude Code plugin marketplace by Alexander Towell), this repository is now structured as a **Universal Agent Skill** compatible across **Google Antigravity**, **OpenCode**, **Claude Code**, and other standard-conforming agentic runtimes.

---

## Overview

Anvil consolidates eleven specialized publishing, authoring, and intelligence tools into a single modular architecture. It replaces proprietary plugin mechanisms with standard Agent Skills conventions centered on progressive disclosure:

- **Single Root Entry Point (`SKILL.md`)**: Defines metadata and a concise domain dispatcher.
- **In-Depth References (`references/`)**: Modular manuals loaded progressively on-demand.
- **Actionable Workflows (`workflows/`)**: Step-by-step procedural runbooks for each domain.
- **Portable Scripts (`scripts/`)**: Standalone CLI utilities (`anvil`) and automated quality gates (LaTeX macro leak checkers, fiction craft pattern auditors).
- **Reusable Assets (`assets/`)**: Project configuration templates and proven exemplars.
- **Universal Personas (`references/agent-roles.md`)**: 40+ specialized agent roles adapted for single-agent or subagent execution.

---

## Core Capabilities Inherited from Anvil

Anvil retains 100% of the capabilities developed across the eleven original plugins:

| Domain | Capabilities & Original Plugins |
| :--- | :--- |
| **Academic Research** | **Vista**: Literature reconnaissance over OpenAlex; automated extraction of *Future Work* & *Limitations* sections from open-access PDFs.<br>**Research-Agent**: Autonomous reasoning loop (decompose, hypothesize, attempt, evaluate, reflect) for proofs, code, simulations, and counterexample hunting.<br>**Papermill**: Multi-angle peer review (Methodology, Logic, Citations, Format, Craft), thesis refinement, and venue selection. |
| **Fiction Worldbuilding** | **Worldsmith**: The "Silmarillion approach" to fiction. Role-based canonical authority documents (`world/timeline.md`, `lore.md`, `characters.md`, `systems.md`), strict downward propagation discipline, and prose craft auditing (cliches, crutch words, filter words, weak verbs, adverb dialogue tags). |
| **Technical Textbooks** | **Bookwright**: Graduate-level textbook authoring combining formal LaTeX manuscripts and paired computational Jupyter notebooks. Atom-outward progression, page budgets, notation package containment, and automated LaTeX macro-leak prevention. |
| **Software Publishing** | **Pub-Pipeline**: Automated pre-flight releases for R packages (CRAN zero-tolerance compliance) and Python packages (PyPI build and verification), plus peer-reviewed software paper drafting for JOSS (Journal of Open Source Software) and JSS. |
| **Amazon KDP Books** | **KDP**: Commercial book publishing lifecycle on Amazon. Interior formatting audits, spine width mathematics, full-wrap print cover rendering via TypeScript/Canvas MCP engine, high-converting blurb copywriting, 7 strategic search keywords, and royalty strategy. |
| **Content Operations** | **Crier**: Multi-platform blog cross-posting (Dev.to, Hashnode, Bluesky, Mastodon, Twitter) with character limit enforcement and two-phase approval.<br>**Repoindex**: MCP-driven local Git catalog intelligence, sprint triage, and activity digests.<br>**Alex-Confidential**: Cryptographic routing across `cryptoid` (Hugo WebCrypto), `pagevault` (HTML packages), and `gpg`.<br>**MF**: Metafunctor Hugo site taxonomy management. |

---

## Skill Architecture & Directory Tree

```
claude-anvil/
├── SKILL.md                          # Primary agent entry point with YAML frontmatter
├── README.md                         # Project documentation and installation guide
├── LICENSE                           # MIT License (Alexander Towell)
│
├── references/                       # In-depth domain manuals (loaded on-demand)
│   ├── academic-research.md          # Vista + Research-Agent + Papermill guide
│   ├── fiction-worldbuilding.md      # Worldsmith methodology & prose craft rules
│   ├── textbook-authoring.md         # Bookwright LaTeX + paired notebook discipline
│   ├── software-publishing.md        # CRAN, PyPI, and JOSS publication standards
│   ├── kdp-publishing.md             # KDP geometry, spine math, and listing craft
│   ├── content-operations.md         # Crier, Repoindex, Alex-Confidential, MF
│   ├── agent-roles.md                # 40+ specialized agent personas & contracts
│   └── cross-agent-compatibility.md  # Multi-agent runtime specs and tool mappings
│
├── workflows/                        # Step-by-step operational runbooks
│   ├── research-pipeline.md          # Literature survey -> Proofs -> Paper drafting
│   ├── fiction-worldsmith.md         # Canon docs -> Scene drafting -> Craft audit
│   ├── textbook-bookwright.md        # Chapter plan -> Notebook -> LaTeX -> Review
│   ├── software-publishing.md        # Pre-flight check -> Package release -> JOSS
│   ├── kdp-publishing.md             # Interior audit -> Listing craft -> Cover wrap
│   └── content-operations.md         # Cross-posting, repo triage, encryption
│
├── assets/                           # Universal templates and exemplars
│   ├── templates/                    # Universal configs, state schemas, plans
│   │   ├── user-config-template.md   # Universal author/KDP/package project config
│   │   ├── paper-state-template.md   # Academic paper state schema
│   │   ├── research-state-template.md# Autonomous research state schema
│   │   ├── worldsmith-project-template.yaml # Fiction project descriptor
│   │   ├── bookwright-plan-template.md      # Textbook chapter design plan
│   │   ├── joss-paper-template.md    # JOSS markdown paper template
│   │   └── audit-report-template.md  # Three-tier audit gap report template
│   └── exemplars/                    # Exemplary references
│       ├── kdp-exemplars.md          # Book blurbs, keywords, Amazon categories
│       ├── joss-exemplars.md         # Sample JOSS papers and review criteria
│       └── patterns.md               # Fiction craft pattern inventory
│
├── scripts/                          # Portable executable CLI utilities
│   ├── anvil                         # Unified Python CLI executable
│   ├── detect_project.py             # Project domain classifier
│   ├── check_latex_macro_leak.py     # Standalone LaTeX macro leak auditor
│   ├── check_fiction_cliches.py      # Standalone fiction craft & cliche auditor
│   ├── count_patterns.py             # Manuscript pattern counter
│   ├── validate_skill.py             # Self-validation test suite
│   └── check-plugins.py              # Upstream Claude Code marketplace validator
│
├── tests/                            # Automated test suite
│   └── test_universal_skill.py       # Pytest suite for universal skill validation
│
├── .agents/skills/anvil/             # Google Antigravity workspace discovery symlink
├── .opencode/skills/anvil/           # OpenCode workspace discovery symlink
│
└── [Original Plugin Directories]     # papermill/, worldsmith/, bookwright/, etc.
```

---

## Installation Guide

### 1. Google Antigravity

Antigravity discovers skills in `.agents/skills/<name>/SKILL.md` (project scope) or `~/.gemini/config/skills/<name>/` (global scope).

#### Option A: Project Scope (In another project on this machine)
Symlink or copy your local Anvil skill directory into your target project:
```bash
cd /path/to/target/project
mkdir -p .agents/skills

# Symlink local checkout (recommended - changes here apply immediately)
ln -s /path/to/claude-anvil .agents/skills/anvil

# Or copy if you prefer a detached snapshot
cp -r /path/to/claude-anvil .agents/skills/anvil
```

#### Option B: Global Scope (Available across all Antigravity projects)
Symlink your local checkout directly into your global Antigravity configuration directory:
```bash
mkdir -p ~/.gemini/config/skills
ln -s /path/to/claude-anvil ~/.gemini/config/skills/anvil
```
*(If you push this converted skill to your own remote Git repository later, you can also clone it: `git clone <your-repo-url> ~/.gemini/config/skills/anvil`)*

#### In-Repo Development
When opening this checkout directory directly in Antigravity, the repository already contains `.agents/skills/anvil/SKILL.md` pointing to the root skill, so Antigravity discovers it immediately with zero setup.

---

### 2. OpenCode

OpenCode discovers skills from `.opencode/skills/<name>/SKILL.md`, `~/.config/opencode/skills/<name>/`, or `.agents/skills/<name>/`.

#### Option A: Project Scope
```bash
cd /path/to/target/project
mkdir -p .opencode/skills
ln -s /path/to/claude-anvil .opencode/skills/anvil
```

#### Option B: Global Scope
```bash
mkdir -p ~/.config/opencode/skills
ln -s /path/to/claude-anvil ~/.config/opencode/skills/anvil
```
*(Or clone your published repository once pushed: `git clone <your-repo-url> ~/.config/opencode/skills/anvil`)*

---

### 3. Claude Code (Backwards Compatible)

Claude Code users can continue installing via the plugin marketplace:
```bash
# Add marketplace
/plugin marketplace add queelius/claude-anvil

# Install any plugin
/plugin install papermill@queelius-plugins
/plugin install worldsmith@queelius-plugins
/plugin install bookwright@queelius-plugins
```

---

### 4. Codex, Cursor, and Other Compatible Assistants

For assistants supporting custom rules or prompt skills:
- Point your assistant's system instructions or rules file to `SKILL.md`.
- Supporting documentation is referenced relatively from `references/` and `workflows/`.

---

## Usage Examples

### 1. Academic Research & Paper Lifecycle
Instruct your agent:
> *"I'm working on a paper exploring masked likelihood estimation. Use Anvil to search OpenAlex for recent papers citing Smith (2020), extract their Future Work sections with Vista, and set up `.papermill/state.md`."*

The agent activates `anvil`, follows `workflows/research-pipeline.md`, and runs:
```bash
python3 scripts/anvil detect
cd vista && uv run vista discover --query "masked likelihood" --min-citations 30
```

### 2. Fiction Worldbuilding & Scene Drafting
Instruct your agent:
> *"Initialize a Worldsmith fantasy project. Set up our canonical world docs for magic systems and timeline, then audit `chapters/ch01.md` for filter words and fancy dialogue tags."*

The agent consults `workflows/fiction-worldsmith.md` and audits the chapter:
```bash
python3 scripts/anvil check-prose "chapters/*.md"
```

### 3. Technical Textbooks (LaTeX + Notebooks)
Instruct your agent:
> *"Design Chapter 3 on Markov Decision Processes using the Bookwright methodology. Create the design plan, implement the paired Jupyter simulation, draft the LaTeX section, and check for macro leaks."*

The agent creates `docs/plans/ch03-plan.md`, implements `notebooks/ch03.ipynb`, drafts `chapters/ch03.tex`, and verifies clean LaTeX prose:
```bash
python3 scripts/anvil check-latex chapters/ch03.tex
```

### 4. Amazon KDP Publishing
Instruct your agent:
> *"We have a completed 280-page non-fiction manuscript (6x9 white paper). Calculate the KDP spine width, draft an Amazon blurb using the 5-part formula, select 7 strategic keywords, and generate the full-wrap cover PDF."*

The agent uses `workflows/kdp-publishing.md` and the KDP cover engine:
```bash
# Calculate dimensions: 280 * 0.002252 = 0.630" spine width
bash kdp/mcp/run.sh
```

---

## The Portable Anvil CLI

Anvil includes a standalone Python CLI (`scripts/anvil`) requiring only standard Python 3.10+:

```text
Usage: anvil <command> [options]

Commands:
  detect [path]            Detects project type (paper, fiction, textbook, package, book)
  status [path]            Displays detected domain, state files, and Git status
  check-latex [files...]   Scans LaTeX files for internal macro leaks
  check-prose [files...]   Scans fiction prose for cliches, weak verbs, and stock reactions
  count-patterns <glob>    Counts craft pattern frequencies across manuscript files
  mcp [status|info|run]    Inspects or launches bundled MCP servers (vista, kdp-cover, crier)
  validate                 Executes full self-validation suite
```

---

## Dependencies & Environment Requirements

### Minimum Requirements
- **Python 3.10+** (Standard library runs core scripts: `anvil`, `detect_project.py`, `check_latex_macro_leak.py`, `check_fiction_cliches.py`).
- **Git** (for repository version control).

### Optional Tool Integrations
- **uv** (Recommended): Fast Python package runner for Vista literature searches (`uv run --project vista vista-mcp`) and PyYAML.
- **Node.js 18+ and npm**: Required only if using the KDP automated cover generation MCP server (`kdp/mcp`).
- **R and devtools**: Required only if executing `R CMD check --as-cran` for R package publishing.

### Environment Variables
- `OPENAI_API_KEY`: Required if using generative AI cover art in the KDP cover engine.
- `ANVIL_AUTHOR_NAME`, `ANVIL_AUTHOR_EMAIL`, `ORCID`: Fallback author metadata if `.anvil/config.local.md` is omitted.

---

## Troubleshooting

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| `LaTeX-macro-leak flagged file.tex` (exit 2) | Text contains `\texttt{\textbackslash foo}`, `"the macro"`, or references to `.sty` in reader prose. | Rewrite text to describe the mathematical concept or algorithm rather than the LaTeX macro. Source macros belong only in source comments. |
| `Fiction cliche check failed` (exit 2) | Manuscript contains stock physiological reactions (`heart raced`, `eyes widened`) or banned dialogue tags. | Rewrite to show character somatic response through concrete physical action and behavioral detail. |
| `No module named 'yaml'` | Running standalone Python without PyYAML installed. | Use `uv run --with pyyaml python <script>` or install PyYAML via `pip install pyyaml`. Anvil scripts include a fallback parser for basic execution. |
| `vitest: command not found` in `kdp/mcp` | Node dependencies have not been installed. | Run `cd kdp/mcp && npm ci`. |

---

## Validation & Testing

Run the test and validation suites:

```bash
# 1. Anvil universal skill validator (metadata, links, scripts, detection)
python3 scripts/anvil validate

# 2. Automated pytest suite
uv run --with pyyaml --with pytest pytest tests/

# 3. Upstream Claude Code marketplace validator
uv run --with pyyaml python scripts/check-plugins.py

# 4. Vista and KDP test suites
(cd vista && uv run pytest -q)
(cd kdp/mcp && npm test)

# 5. Shell hook regression tests
for t in worldsmith/tests/*.sh bookwright/tests/*.sh; do bash "$t"; done
```

---

## Upstream Synchronization and Maintenance

This repository remains directly trackable against `queelius/claude-anvil`. Because Anvil layers the universal skill structure (`SKILL.md`, `references/`, `workflows/`, `scripts/anvil`) on top of the original working tree without removing plugin directories, upstream changes can be pulled and merged seamlessly:

```bash
git fetch upstream master
git merge upstream/master
python3 scripts/anvil validate
```

---

## License & Attribution

- **Original Project**: [claude-anvil](https://github.com/queelius/claude-anvil)
- **Author**: Alexander Towell (`lex@metafunctor.com`)
- **License**: MIT License (see [LICENSE](LICENSE))
- **Universal Skill Conversion**: Antigravity & OpenCode Compatible Architecture (2026)
