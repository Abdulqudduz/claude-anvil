# Workflow: End-to-End Academic Research Pipeline

This runbook guides an AI agent through the complete research pipeline: from surveying the literature with Vista, to conducting autonomous proofs and simulations with Research-Agent, to drafting and peer-reviewing an academic paper with Papermill.

---

## Prerequisites and Setup
1. **Detect or Initialize Project**:
   - Check for `.papermill/state.md` or run `python3 scripts/anvil detect`.
   - If missing, copy `assets/templates/paper-state-template.md` to `.papermill/state.md` or `.anvil/state.md`.
2. **Review Domain Reference**:
   - Consult [academic-research.md](../references/academic-research.md) for detailed guidelines.

---

## Phase 1: Literature Reconnaissance (Vista)

1. **Query Scholarly Publications**:
   - Discover highly-cited works in the target domain:
     ```bash
     cd vista && uv run vista discover --query "<topic or concept>" --min-citations 50
     ```
2. **Fetch and Extract Sections**:
   - Download open-access PDFs and extract Future Work & Limitations:
     ```bash
     uv run vista fetch
     uv run vista extract
     ```
3. **Synthesize Opportunities**:
   - Run `uv run vista analyze` or inspect extracted sections to isolate 2-3 high-value, unaddressed open problems.

---

## Phase 2: Autonomous Problem Solving (Research-Agent)

1. **Initialize Research State**:
   - Create `.research/state.md` from `assets/templates/research-state-template.md`.
   - Set the primary research claim or theorem to investigate.
2. **Execute Autonomous Investigation Loop**:
   - **Step A: Formulate Hypothesis**: State the lemma, algorithm, or empirical outcome explicitly in `.research/attempts/<NNN>/hypothesis.md`.
   - **Step B: Implement & Simulate**: Author simulation scripts or formal proofs in Python/R/LaTeX. Run benchmarks.
   - **Step C: Evaluate & Reflect**: Record actual outputs vs expectations. If the attempt fails, document counterexamples.
3. **Consolidate Deliverable**:
   - Write accumulated lemmas, findings, and figures to `.research/synthesis.md`.

---

## Phase 3: Paper Authoring (Papermill)

1. **Thesis Refinement**:
   - Refine the core claim and novelty statement. Record in state file.
2. **Prior Art Mapping**:
   - Classify references into Foundational, Competing, Complementary, or Tangential.
   - Verify every citation resolves to a valid BibTeX key in `references.bib`.
3. **Section-by-Section Drafting**:
   - Draft Abstract, Introduction, Formal Method, Theoretical Analysis, Empirical Results, and Discussion.
   - Ensure continuous pedagogical flow and consistent notation.

---

## Phase 4: Multi-Angle Peer Review

1. **Dispatch Parallel Audits**:
   - **Methodology Audit**: Validate experimental baselines, statistical significance, and controls.
   - **Logic & Proof Check**: Audit mathematical derivations line by line for gaps or circular reasoning.
   - **Citation Verification**: Check author spellings, publication years, and ensure no hallucinated references exist.
   - **Venue & Format Validation**: Verify page limits, margins, anonymization, and font styling.
2. **Collate Review Report**:
   - Generate structured gap report using `assets/templates/audit-report-template.md`.
   - Resolve all Critical issues prior to final camera-ready compilation.
