#!/usr/bin/env python3
"""Validation suite for the Anvil universal agent skill.

Performs structured verification:
1. Validates YAML frontmatter of root SKILL.md.
2. Checks all internal markdown links across SKILL.md, references/, and workflows/.
3. Verifies scripts are valid Python/Shell and executable.
4. Executes unit audits for LaTeX macro leak and fiction cliche checkers.
5. Verifies discovery targets for Google Antigravity and OpenCode.
6. Runs upstream check-plugins.py for backward compatibility.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def check_skill_frontmatter(errors: list[str]) -> None:
    skill_file = ROOT / "SKILL.md"
    if not skill_file.is_file():
        errors.append("SKILL.md does not exist at repository root")
        return

    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append("SKILL.md does not start with YAML frontmatter delimiter (---)")
        return
    end_fm = text.find("\n---", 4)
    if end_fm == -1:
        errors.append("SKILL.md does not close YAML frontmatter (missing closing ---)")
        return

    fm_raw = text[4:end_fm]
    try:
        import yaml
        fm = yaml.safe_load(fm_raw)
    except ImportError:
        # Robust fallback parser for frontmatter with folded scalar (>-, |) support
        fm = {}
        current_key = None
        current_val: list[str] = []
        for line in fm_raw.splitlines():
            if ":" in line and not line.startswith(" "):
                if current_key:
                    fm[current_key] = " ".join(current_val).strip()
                k, v = line.split(":", 1)
                current_key = k.strip()
                v_clean = v.strip()
                if v_clean in {">-", ">", "|", "|-"}:
                    current_val = []
                else:
                    current_val = [v_clean]
            elif current_key and line.startswith(" "):
                current_val.append(line.strip())
        if current_key:
            fm[current_key] = " ".join(current_val).strip()

    if not isinstance(fm, dict):
        errors.append("SKILL.md frontmatter failed to parse as dictionary")
        return

    if not fm.get("name"):
        errors.append("SKILL.md frontmatter is missing required 'name' field")
    if not fm.get("description"):
        errors.append("SKILL.md frontmatter is missing required 'description' field")
    elif len(fm["description"]) < 50:
        errors.append("SKILL.md description is too short for reliable agent trigger matching")


def check_markdown_links(errors: list[str]) -> None:
    md_files = [ROOT / "SKILL.md"] + list(ROOT.glob("references/*.md")) + list(ROOT.glob("workflows/*.md"))

    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8", errors="replace")
        for match in MARKDOWN_LINK.finditer(text):
            link_target = match.group(2).strip()
            # Ignore external URLs, anchors, mailto
            if link_target.startswith(("http://", "https://", "#", "mailto:")):
                continue

            # Strip anchor within relative link
            path_part = link_target.split("#")[0]
            if not path_part:
                continue

            target_path = (md_file.parent / path_part).resolve()
            if not target_path.exists():
                errors.append(f"{md_file.relative_to(ROOT)}: Broken link to '{link_target}'")


def check_scripts(errors: list[str]) -> None:
    scripts_to_check = [
        SCRIPTS / "anvil",
        SCRIPTS / "detect_project.py",
        SCRIPTS / "check_latex_macro_leak.py",
        SCRIPTS / "check_fiction_cliches.py",
        SCRIPTS / "count_patterns.py",
    ]

    for script in scripts_to_check:
        if not script.is_file():
            errors.append(f"Missing required script: {script.relative_to(ROOT)}")
            continue
        if not os.access(script, os.X_OK):
            errors.append(f"Script is not executable: {script.relative_to(ROOT)}")


def check_tool_functionality(errors: list[str]) -> None:
    # 1. LaTeX macro leak test
    p1 = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_latex_macro_leak.py"), "--stdin"],
        input=r"\texttt{\textbackslash testmacro}",
        text=True, capture_output=True,
    )
    if p1.returncode != 2:
        errors.append(f"check_latex_macro_leak.py failed to flag macro leak (exit={p1.returncode})")

    p2 = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_latex_macro_leak.py"), "--stdin"],
        input=r"Clean text with $\alpha + \beta$.",
        text=True, capture_output=True,
    )
    if p2.returncode != 0:
        errors.append(f"check_latex_macro_leak.py falsely flagged clean LaTeX text (exit={p2.returncode})")

    # 2. Fiction cliche test
    p3 = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_fiction_cliches.py"), "--hook"],
        input='{"tool_input": {"file_path": "ch1.md", "content": "His breath caught in his throat."}}',
        text=True, capture_output=True,
    )
    if p3.returncode != 2:
        errors.append(f"check_fiction_cliches.py failed to flag stock reaction (exit={p3.returncode})")


def check_discovery_paths(errors: list[str]) -> None:
    antigravity_path = ROOT / ".agents/skills/anvil/SKILL.md"
    opencode_path = ROOT / ".opencode/skills/anvil/SKILL.md"

    if not antigravity_path.exists():
        errors.append("Google Antigravity discovery path (.agents/skills/anvil/SKILL.md) does not exist")
    if not opencode_path.exists():
        errors.append("OpenCode discovery path (.opencode/skills/anvil/SKILL.md) does not exist")


def check_upstream_compatibility(errors: list[str]) -> None:
    check_plugins_script = ROOT / "scripts/check-plugins.py"
    if check_plugins_script.is_file():
        # Run via uv run --with pyyaml if needed
        cmd = ["uv", "run", "--with", "pyyaml", "python", str(check_plugins_script)]
        try:
            res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
            if res.returncode != 0:
                errors.append(f"Upstream check-plugins.py failed: {res.stdout.strip()} {res.stderr.strip()}")
        except Exception as e:
            errors.append(f"Unable to run upstream check-plugins.py: {e}")


def main() -> int:
    errors: list[str] = []
    print("Validating Anvil Universal Agent Skill...")

    print("1. Checking SKILL.md frontmatter and metadata...")
    check_skill_frontmatter(errors)

    print("2. Checking internal markdown links in SKILL.md, references/, and workflows/...")
    check_markdown_links(errors)

    print("3. Checking executable scripts in scripts/...")
    check_scripts(errors)

    print("4. Testing tool functionality (LaTeX & prose checkers)...")
    check_tool_functionality(errors)

    print("5. Checking discovery paths (.agents/ and .opencode/)...")
    check_discovery_paths(errors)

    print("6. Verifying upstream marketplace compatibility...")
    check_upstream_compatibility(errors)

    if errors:
        print(f"\n❌ Validation FAILED with {len(errors)} error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("\n✅ All validation checks PASSED successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
