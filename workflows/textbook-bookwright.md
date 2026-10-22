# Workflow: Technical Textbook Authoring (Bookwright)

This runbook guides an AI agent through the Bookwright textbook methodology: atom-outward chapter design, paired computational notebook authoring, formal LaTeX drafting, and dual-track spec/quality auditing.

---

## Prerequisites and Setup
1. **Detect or Initialize Project**:
   - Run `python3 scripts/anvil detect`.
   - Create a chapter plan in `docs/plans/chXX-plan.md` using `assets/templates/bookwright-plan-template.md`.
2. **Review Domain Reference**:
   - Consult [textbook-authoring.md](../references/textbook-authoring.md) for detailed guidelines.

---

## Phase 1: Chapter Design Plan

1. **Deconstruct Topics Atom-Outward**:
   - Break chapter topic into discrete pedagogical atoms. Order them strictly from intuitive fundamentals outward to advanced syntheses.
2. **Establish Fixed Budgets**:
   - Set page budgets for each section (e.g., 2.5 to 4 pages).
   - Assign unique LaTeX labels (`sec:...`, `eq:...`, `fig:...`).
   - Identify required symbols from the project notation package (`notation.sty`).

---

## Phase 2: Paired Computational Notebook Authoring

1. **Implement Runnable Code Cells**:
   - Create `notebooks/chXX.ipynb`.
   - Variable names in code must mirror LaTeX notation symbols directly.
   - Set deterministic random seeds (`np.random.seed(42)`).
2. **Execute and Validate Outputs**:
   - Run notebook top-to-bottom. Ensure all cells execute without errors.
   - Generate publication-quality figures (300 DPI, styled fonts, clear legends).

---

## Phase 3: Formal LaTeX Prose Drafting

1. **Section-by-Section Authoring**:
   - Draft each `.tex` section adhering to the chapter plan content checklist.
   - Never introduce mathematical notation before defining it.
   - Ground abstract equations in intuitive physical/geometric explanations.
2. **Notation Package Discipline**:
   - Use only project-standard notation macros defined in the root notation package.
   - Do NOT define ad-hoc `\newcommand` macros inside chapter files.

---

## Phase 4: Dual-Track Review and Leak Prevention

1. **Track 1: Specification Compliance**:
   - Verify all plan checklist items are fully addressed.
   - Verify page count against the assigned page budget.
2. **Track 2: Quality & Mathematical Derivation**:
   - Audit derivations step by step for mathematical soundness.
   - Confirm that numerical results in prose match notebook execution outputs.
3. **Automated LaTeX Macro-Leak Audit**:
   - Run the automated leak scanner:
     ```bash
     python3 scripts/anvil check-latex "chapters/chXX.tex"
     ```
   - Confirm: zero macro names displayed via `\texttt{\textbackslash ...}`, zero occurrences of "the macro", zero reader-visible references to `.sty` package files.
4. **Integration**:
   - Compile root document (`latexmk -pdf root.tex`).
   - Verify clean build with zero broken cross-references (`\ref` or `\cite`).
