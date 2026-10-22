# Technical Non-Fiction and Textbook Authoring Reference

This document provides complete domain knowledge for authoring graduate-level technical textbooks, monographs, and instructional manuals combining LaTeX and paired Jupyter computational notebooks using the Anvil skill (embodying the Bookwright methodology).

---

## 1. The Bookwright Philosophy

Technical textbooks fail when mathematics, exposition, and runnable code drift out of alignment. Bookwright treats technical textbook authoring with the same rigor as safety-critical software engineering:

1. **LaTeX + Paired Computational Notebooks**: Every theoretical chapter is accompanied by an executable Jupyter notebook where every formula, algorithm, and simulation is verified and interactive.
2. **Atom-Outward Design**: Every complex topic is decomposed into atomic units (minimal self-contained ideas). Chapters build from fundamental atoms outward to complex syntheses.
3. **Strict Deferral Discipline**: Never rely on a technical concept before it has been formally defined. If a concept must be previewed, signpost the deferral explicitly.
4. **Running Threads**: Maintain 1-3 continuous pedagogical threads (e.g., an evolving dataset or an engineering challenge) that recur across chapters to anchor abstract concepts.
5. **Page Budgets**: Enforce strict page limits at both chapter and section grain to maintain technical density and avoid rambling prose.

```
┌────────────────────────────────────────────────────────┐
│ Chapter Design Plan (`docs/plans/chXX-plan.md`)        │
│ Pedagogical goals, section page budgets, label schemas │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│ Paired Computational      │ │ Formal LaTeX Manuscript   │
│ Jupyter Notebook (`.ipynb`)│ │ Prose & Equations (`.tex`)│
│ Executable algorithms     │ │ Atom-outward exposition   │
└─────────────┬─────────────┘ └───────────┬───────────────┘
              └─────────────┬─────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ Dual-Track Review & Audit                              │
│ • Spec compliance (page budgets, notation consistency) │
│ • Quality & Math audit (code matches math formulas)    │
│ • LaTeX Macro-Leak prevention                          │
└────────────────────────────────────────────────────────┘
```

---

## 2. Chapter Design Plan Specification

Before writing any text, author a design plan (`docs/superpowers/plans/chXX-plan.md` or `docs/plans/`):
- **Pedagogical Objectives**: What formal lemmas will the reader prove? What will they implement?
- **Section Breakdown**:
  - `id`: Unique identifier (e.g., `sec02-03`).
  - `title`: Descriptive heading.
  - `type`: `prose`, `notebook-paired`, or `source-reformulation`.
  - `page_budget`: Precise page allocation (e.g., 3.5 pages).
  - `labels`: Defined LaTeX `\label{...}` anchors (e.g., `sec:mle_derivation`).
  - `notation`: Required symbols from the project notation package.
  - `content_checklist`: Step-by-step concepts that must be covered.

---

## 3. Notation Package Discipline

Every Bookwright project defines a project-wide LaTeX notation package (e.g., `notation.sty` or specified via `macro_package` in `bookwright.config.yaml`):
- **Universal Symbols**: All math notation must be defined in the project notation package.
- **No In-Chapter Redefinitions**: Never define ad-hoc `\newcommand` or `\def` inside chapter files.
- **Consistent Semantic Macros**: Use `\Expectation{\cdot}`, `\Covariance{\cdot}`, `\Matrix{A}` rather than raw TeX symbols.

---

## 4. LaTeX Macro-Leak Prevention

Authors writing about mathematics and algorithms frequently leak source code tooling details into reader prose. Anvil enforces strict automated checks against these leaks:

### Prohibited Patterns in Reader Prose
1. **Macro Literals**: Displaying macro names to readers via `\texttt{\textbackslash foo}` or `\texttt{\foo}`.
2. **Tooling Phrases**: The phrase "the macro" in prose (e.g., "The macro expands to..."). Explain the mathematical operation, not the LaTeX implementation.
3. **Notation Package References**: Mentioning the notation package file (e.g., `notation.sty`) in reader text. Such references belong strictly in source comments.

The automated leak checker `scripts/check_latex_macro_leak.py` strips LaTeX comments and audits `.tex` files, exiting 2 if violations are found.

---

## 5. Paired Computational Notebook Discipline

When a section is paired with a computational notebook:
1. **Variable Mirroring**: Variable names in Python/R code must mirror LaTeX notation (e.g., `theta_hat` for $\hat{\theta}$, `Sigma` for $\Sigma$).
2. **Deterministic Execution**: All random number seeds must be explicitly set (`np.random.seed(42)`).
3. **Self-Contained Imports**: Each chapter notebook must run top-to-bottom without external side effects or undocumented dependencies.
4. **Visual Rigor**: All plots must have labeled axes, units, legends, and high DPI output suitable for print.

---

## 6. Per-Section Drafting and Review Cadence

Drafting proceeds incrementally to preserve context and maintain quality:
1. **Design**: Review the section's entry in the chapter plan.
2. **Notebook Implementation**: Write and execute the computational code and figure generation.
3. **Prose Drafting**: Author the `.tex` manuscript section adhering to atom-outward progression and page budgets.
4. **Spec Compliance Audit**: Verify labels, content checklist, and page budget.
5. **Quality & Math Audit**: Verify derivations, mathematical validity, and notebook alignment.
6. **Leak & Cliche Check**: Run `check_latex_macro_leak.py`.
7. **Integration**: Commit to chapter build and verify clean PDF compilation.
