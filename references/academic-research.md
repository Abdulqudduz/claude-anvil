# Academic Research and Paper Lifecycle Reference

This document provides complete domain knowledge for conducting academic research, literature reconnaissance, autonomous experimentation, and scholarly paper publication using the Anvil skill.

---

## 1. The Three-Stage Research Pipeline

The Anvil research architecture separates academic research into three clear, progressive stages:

```
┌─────────────────────────────────┐
│ 1. Reconnaissance (Vista)       │ Find the questions by mining Future Work &
│                                 │ Limitations sections of highly-cited literature.
└───────────────┬─────────────────┘
                │ Candidate Research Directions
                ▼
┌─────────────────────────────────┐
│ 2. Autonomous Attack (Research) │ Decompose, hypothesize, attempt, simulate,
│                                 │ and prove. Logs kept in `.research/`.
└───────────────┬─────────────────┘
                │ Working Results & Synthesis
                ▼
┌─────────────────────────────────┐
│ 3. Paper Lifecycle (Papermill)  │ Thesis refinement, prior art mapping, drafting,
│                                 │ multi-angle review, and venue submission.
└─────────────────────────────────┘
```

> [!NOTE]
> **Synthesis Trap**: Vista synthesizes *other scholars'* stated future work. Research-Agent synthesizes *its own* attempt results. Papermill documents the final verified claims for publication.

---

## 2. Stage 1: Literature Reconnaissance (Vista)

Vista is a mechanical reconnaissance pipeline over published scholarly literature. It connects live OpenAlex discovery with local PDF section extraction to surface actionable research gaps.

### Key Capabilities
- **OpenAlex Discovery**: Queries scholarly works by concept, venue, or citation count.
- **Section Extraction**: Mines PDF text specifically targeting sections often overlooked:
  - *Future Work*
  - *Limitations*
  - *Discussion & Open Problems*
  - *Conclusion*
- **CLI Commands**:
  - `vista discover --query "concept" --min-citations 50`: Ingests metadata into SQLite catalog.
  - `vista fetch`: Downloads open-access PDFs and arXiv preprints.
  - `vista extract`: Uses PyMuPDF heuristics to extract future work sections.
  - `vista analyze`: Synthesizes candidate directions.
  - `vista render`: Emits human-readable Markdown digests.

### Operating Rules
- Vista's MCP server is mechanical: it returns structured JSON with raw text and citation metadata.
- The synthesizing agent reads the extracted section text to isolate concrete open problems rather than vague ideas.
- Prioritize high-impact papers with clear limitation disclosures.

---

## 3. Stage 2: Autonomous Problem Solving (Research-Agent)

Research-Agent attacks a specified technical claim or open problem autonomously. It is designed for multi-step investigation combining formal reasoning, code implementation, simulations, and counterexample hunting.

### Core Loop
1. **Decompose**: Break the primary research question into falsifiable sub-hypotheses.
2. **Hypothesize**: Formulate precise mathematical, algorithmic, or empirical statements.
3. **Attempt**:
   - Write proofs in LaTeX or Lean/formal systems.
   - Implement computational scripts (Python/R/Julia).
   - Execute benchmarks and simulations.
4. **Evaluate**: Check outcomes against hypotheses. Hunt for edge cases and counterexamples.
5. **Reflect & Log**: Persist every attempt in `.research/` on disk. Update status to prevent duplicated work.

### On-Disk State Architecture
All autonomous state is kept inside the target project under `.research/`:
- `.research/state.md`: Working hypotheses, active branch, iteration counters, and budget limits.
- `.research/attempts/<NNN>-<slug>/`: Self-contained directory for each attempt containing:
  - `hypothesis.md`: What was tested.
  - `code/`: Executable scripts and simulation parameters.
  - `output/`: Raw logs, simulation artifacts, and data tables.
  - `reflection.md`: What succeeded, what failed, and why.
- `.research/synthesis.md`: Final accumulated insights ready to feed into the paper drafting stage.

---

## 4. Stage 3: Paper Authoring and Lifecycle (Papermill)

Papermill guides the paper from working results to camera-ready submission. It supports LaTeX, Markdown, and RMarkdown/Quarto projects.

### State Tracking (`.papermill/state.md`)
Every paper project maintains an authoritative state file recording:
- Current stage: `idea` -> `thesis` -> `literature` -> `outlining` -> `drafting` -> `review` -> `submission`
- Claim and novelty statement
- Confirmed prior art references categorized by relationship
- Experiment and simulation execution history
- Target venue constraints and submission checklists

### Multi-Angle Review System
Papermill employs specialized review angles to ensure rigorous peer-review readiness before submission:

| Review Angle | Purpose | Critical Checks |
|--------------|---------|-----------------|
| **Methodology** | Scientific validity | Soundness of statistical models, baseline fairness, control variables |
| **Logic & Proof** | Formal rigor | Correct theorem statements, non-circular arguments, lemma dependencies |
| **Novelty** | Scholarly contribution | Differentiation from foundational and competing prior art |
| **Citations** | Academic integrity | BibTeX key resolution, author name spelling, non-hallucinated citations |
| **Prose & Craft** | Rhetorical clarity | Reader navigation, paragraph transitions, absence of vague hype words |
| **Format & Specs**| Venue compliance | Page limits, font sizes, anonymization rules, required appendix sections |

### Prior Art Classification Discipline
When surveying literature, classify each confirmed paper into exactly one category:
1. **Foundational**: The bedrock on which this work builds (the theoretical framework or primary problem setting).
2. **Competing**: Solves the same problem. You must benchmark directly against it or detail why your assumptions differ.
3. **Complementary**: Solves an orthogonal problem that can be combined with this work.
4. **Tangential**: Addresses a similar-sounding problem in a different domain; cited to prevent reviewer confusion.

---

## 5. Artifact and Citation Verification

- All references in manuscripts must match a verified BibTeX entry in the project's bibliography file (`.bib`).
- Never invent citations. If a citation is uncertain, verify via OpenAlex, Crossref, or Semantic Scholar before committing.
- Authors must be cross-checked against author metadata in `.anvil/config.local.md` or `.papermill/state.md`.
