# Software and Package Publishing Reference

This document provides complete domain knowledge for releasing open-source software packages to R (CRAN), Python (PyPI), and authoring peer-reviewed software papers for JOSS (Journal of Open Source Software) and JSS using the Anvil skill (embodying the Pub-Pipeline methodology).

---

## 1. Package Publishing Architecture

Software release workflows require rigorous automated pre-flight audits to prevent upstream rejection:

```
┌────────────────────────────────────────────────────────┐
│ Software Repository (R Package or Python Project)      │
│ Source code • Unit tests • Documentation • Benchmarks  │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│ R / CRAN Release Track    │ │ Python / PyPI Track       │
│ `R CMD check --as-cran`   │ │ `pyproject.toml` + build  │
│ Zero errors/warnings/notes│ │ Wheel verification        │
└─────────────┬─────────────┘ └───────────┬───────────────┘
              └─────────────┬─────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ JOSS Software Paper (`paper.md` + `paper.bib`)         │
│ • Statement of Need & State of the Field               │
│ • Community guidelines (Contributing, Code of Conduct) │
│ • Multi-facet community & software audit               │
└────────────────────────────────────────────────────────┘
```

---

## 2. R Package Release to CRAN

CRAN maintains the most stringent automated and manual review gates in open-source software. Submissions must pass without exception:

### A. Pre-Flight Verification
- Run `R CMD check --as-cran` (or `devtools::check(remote = TRUE, manual = TRUE)`).
- **Mandatory target**: 0 Errors, 0 Warnings, 0 Notes.
- Any unavoidable Note (e.g., new submission note) must be explained in `cran-comments.md`.

### B. `DESCRIPTION` File Invariants
- `Title`: Capitalized title case, under 65 characters, no trailing period.
- `Description`: High-level paragraph explaining what the package does. Do NOT start with "This package..." or the package name.
- `Authors@R`: Valid `person()` statements with full names, email addresses, and active ORCIDs.
- `License`: Standard open-source license string (e.g., `MIT + file LICENSE` or `GPL (>= 3)`).
- `URL` and `BugReports`: Valid public repository links.

### C. Documentation and Examples
- Every exported function must have a complete `.Rd` file generated via `roxygen2`.
- Every example in `@examples` must run in < 5 seconds and cannot modify the user's filesystem without cleanup (`on.exit()`).
- Package must ship at least one comprehensive vignette.

### D. Upstream Dependency Chains
- If your package depends on another custom package you authored, that dependency must be published and live on CRAN *first*.
- Use R-universe (`<user>.r-universe.dev`) to test staging builds and binary distribution.

---

## 3. Python Package Release to PyPI

Modern Python packaging follows standards-based packaging tools:

### A. Configuration (`pyproject.toml`)
- Modern build backend: `hatchling`, `flit_core`, or `setuptools`.
- Metadata: `name`, `version`, `authors`, `description`, `readme`, `requires-python`, `classifiers`, `dependencies`.
- PEP 561 compliance: Ship a `py.typed` marker file if the package is typed.

### B. Build and Publishing Checks
1. Clean build: `uv build` or `python -m build`.
2. Check distribution: `twine check dist/*`.
3. TestPyPI dry-run: Publish to TestPyPI before hitting production PyPI:
   ```bash
   uv publish --publish-url https://test.pypi.org/legacy/
   ```
4. Verify installation in a clean virtual environment:
   ```bash
   uv venv clean-env && source clean-env/bin/activate
   pip install --index-url https://test.pypi.org/simple/ <package-name>
   ```

---

## 4. JOSS (Journal of Open Source Software) Paper Authoring

JOSS is an open-access, peer-reviewed journal for research software. A JOSS submission consists of a short paper (`paper.md`), bibliography (`paper.bib`), and the open-source repository itself.

### A. Core Criteria
1. **Research Application**: The software must have an explicit research application.
2. **Substantial Effort**: Must represent non-trivial development effort (not a minor wrapper).
3. **Open License**: OSI-approved license.
4. **Automated Test Suite**: Reproducible tests with clear documentation on how to run them.

### B. Required Paper Sections (`paper.md`)
- **Summary**: Concise explanation of the software's purpose and target user base.
- **Statement of Need**: Why this software is needed. Must articulate the research gap and compare against existing alternatives.
- **State of the Field**: Scholarly review of competing or related software with full academic citations.
- **Key Features / Architecture**: Algorithmic foundations and API design.

### C. Repository Community Requirements
- `README.md` with clear installation and minimal working example.
- `CONTRIBUTING.md` describing how community members can submit issues and pull requests.
- `CODE_OF_CONDUCT.md` (e.g., Contributor Covenant).
- `LICENSE` file.
- Issue tracker enabled on GitHub/GitLab.

---

## 5. Structured Audit Reports

All software audits produce a structured gap report using the Anvil audit template (`assets/templates/audit-report-template.md`):
- **Critical (Must Fix)**: Compilation failures, CRAN check errors, missing license, failing tests.
- **Warnings (Should Fix)**: Missing docstrings, untyped signatures, unoptimized examples.
- **Passed**: All verified standards.
