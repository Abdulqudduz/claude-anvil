# Workflow: Software and Package Publishing

This runbook guides an AI agent through preparing, auditing, and publishing open-source software packages to R (CRAN) and Python (PyPI), and drafting peer-reviewed software papers for JOSS.

---

## Prerequisites and Setup
1. **Detect or Initialize Project**:
   - Run `python3 scripts/anvil detect`.
   - Ensure author metadata exists in `.anvil/config.local.md` using `assets/templates/user-config-template.md`.
2. **Review Domain Reference**:
   - Consult [software-publishing.md](../references/software-publishing.md) for detailed packaging rules.

---

## Phase 1: Pre-Flight Package Audit

### For R Packages:
1. **Execute Strict CRAN Check**:
   ```bash
   R CMD check --as-cran .
   ```
2. **Verify Zero Tolerances**:
   - 0 Errors, 0 Warnings, 0 Notes.
   - If an unavoidable Note exists (e.g. initial submission), document the explanation in `cran-comments.md`.
3. **Verify DESCRIPTION and Documentation**:
   - Verify all author ORCIDs, title casing, and function Rd files.
   - Run all package vignettes and verify execution time < 5 minutes total.

### For Python Packages:
1. **Verify Configuration**:
   - Check `pyproject.toml` for standard build backend, metadata, license, and dependencies.
2. **Build Distribution Artifacts**:
   ```bash
   uv build
   ```
3. **Audit Distribution**:
   ```bash
   twine check dist/*
   ```

---

## Phase 2: Community and Repository Compliance

1. **Verify Community Files**:
   - `README.md` with clear installation and minimal working code example.
   - `CONTRIBUTING.md` describing pull request and issue guidelines.
   - `CODE_OF_CONDUCT.md` establishing community standards.
   - `LICENSE` file matching package metadata.
2. **Check Test Suite**:
   - Ensure automated unit test coverage across all public API functions.

---

## Phase 3: JOSS Software Paper Drafting (if applicable)

1. **Initialize Paper Files**:
   - Create `paper.md` from `assets/templates/joss-paper-template.md`.
   - Create `paper.bib` with complete citations for all referenced software and theory.
2. **Author Core Sections**:
   - **Statement of Need**: Articulate clearly why this software is needed in the scientific community.
   - **State of the Field**: Compare against existing packages and historical approaches.
3. **Audit against JOSS Criteria**:
   - Review using `assets/exemplars/joss-exemplars.md`.
   - Ensure paper focuses on software utility, architecture, and research application.

---

## Phase 4: Release and Submission

1. **Tag Version**:
   - Ensure semantic versioning bump (`vMAJOR.MINOR.PATCH`).
2. **Publish Package**:
   - For R: Submit tarball via CRAN web form or `devtools::submit_cran()`.
   - For Python: Deploy to TestPyPI first, verify in a clean venv, then deploy to PyPI (`uv publish`).
3. **Submit JOSS Paper**:
   - Open review issue on GitHub `openjournals/joss-reviews`.
