"""Unit and integration test suite for the Anvil Universal Agent Skill."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))


def test_skill_frontmatter():
    skill_file = ROOT / "SKILL.md"
    assert skill_file.is_file(), "SKILL.md must exist at root"
    text = skill_file.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "SKILL.md must start with ---"
    end = text.find("\n---", 4)
    assert end != -1, "SKILL.md must close YAML frontmatter"

    fm_lines = text[4:end].splitlines()
    keys = {}
    for line in fm_lines:
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            keys[k.strip()] = v.strip()

    assert keys.get("name") == "anvil"
    assert "description" in keys


def test_references_and_workflows_exist():
    expected_references = [
        "academic-research.md",
        "fiction-worldbuilding.md",
        "textbook-authoring.md",
        "software-publishing.md",
        "kdp-publishing.md",
        "content-operations.md",
        "agent-roles.md",
        "cross-agent-compatibility.md",
    ]
    for ref in expected_references:
        path = ROOT / "references" / ref
        assert path.is_file(), f"Missing reference: {ref}"
        assert path.stat().st_size > 500, f"Reference too short: {ref}"

    expected_workflows = [
        "research-pipeline.md",
        "fiction-worldsmith.md",
        "textbook-bookwright.md",
        "software-publishing.md",
        "kdp-publishing.md",
        "content-operations.md",
    ]
    for wf in expected_workflows:
        path = ROOT / "workflows" / wf
        assert path.is_file(), f"Missing workflow: {wf}"
        assert path.stat().st_size > 500, f"Workflow too short: {wf}"


def test_assets_exist():
    expected_templates = [
        "user-config-template.md",
        "paper-state-template.md",
        "research-state-template.md",
        "worldsmith-project-template.yaml",
        "bookwright-plan-template.md",
        "joss-paper-template.md",
        "audit-report-template.md",
    ]
    for tpl in expected_templates:
        path = ROOT / "assets/templates" / tpl
        assert path.is_file(), f"Missing template: {tpl}"

    expected_exemplars = [
        "kdp-exemplars.md",
        "joss-exemplars.md",
        "patterns.md",
    ]
    for ex in expected_exemplars:
        path = ROOT / "assets/exemplars" / ex
        assert path.is_file(), f"Missing exemplar: {ex}"


def test_discovery_paths():
    antigravity_skill = ROOT / ".agents/skills/anvil/SKILL.md"
    opencode_skill = ROOT / ".opencode/skills/anvil/SKILL.md"
    assert antigravity_skill.is_file(), "Antigravity discovery path must exist"
    assert opencode_skill.is_file(), "OpenCode discovery path must exist"


def test_detect_project():
    from scripts.detect_project import detect_project_type
    assert detect_project_type(ROOT / "papermill")["primary_type"] == "academic-paper"
    assert detect_project_type(ROOT / "worldsmith")["primary_type"] == "fiction-novel"
    assert detect_project_type(ROOT / "bookwright")["primary_type"] == "technical-textbook"
    assert detect_project_type(ROOT / "pub-pipeline")["primary_type"] == "software-package"


def test_latex_macro_leak_checker():
    # Leak case
    p1 = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_latex_macro_leak.py"), "--stdin"],
        input=r"\texttt{\textbackslash testmacro}",
        text=True, capture_output=True,
    )
    assert p1.returncode == 2, "Must flag \\texttt{\\textbackslash ...} as leak"

    # Clean case
    p2 = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_latex_macro_leak.py"), "--stdin"],
        input=r"Clean exposition of Theorem 1: $f(x) = x^2$.",
        text=True, capture_output=True,
    )
    assert p2.returncode == 0, "Clean text must pass without error"


def test_fiction_cliche_checker():
    # Stock reaction case
    p1 = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_fiction_cliches.py"), "--hook"],
        input='{"tool_input": {"file_path": "chapters/01.md", "content": "Her heart pounded wildly."}}',
        text=True, capture_output=True,
    )
    assert p1.returncode == 2, "Must flag stock reaction 'heart pounded'"

    # Clean case
    p2 = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_fiction_cliches.py"), "--hook"],
        input='{"tool_input": {"file_path": "chapters/01.md", "content": "The stone tower loomed above the foggy shore."}}',
        text=True, capture_output=True,
    )
    assert p2.returncode == 0, "Clean prose must pass"


def test_anvil_cli_commands():
    # detect
    p_det = subprocess.run([sys.executable, str(SCRIPTS / "anvil"), "detect"], capture_output=True, text=True)
    assert p_det.returncode == 0
    assert "Project Path:" in p_det.stdout

    # status
    p_stat = subprocess.run([sys.executable, str(SCRIPTS / "anvil"), "status"], capture_output=True, text=True)
    assert p_stat.returncode == 0
    assert "Anvil Workspace Status" in p_stat.stdout

    # mcp status
    p_mcp = subprocess.run([sys.executable, str(SCRIPTS / "anvil"), "mcp", "status"], capture_output=True, text=True)
    assert p_mcp.returncode == 0
    assert "vista" in p_mcp.stdout
    assert "kdp-cover" in p_mcp.stdout


def test_upstream_check_plugins():
    res = subprocess.run(
        ["uv", "run", "--with", "pyyaml", "python", str(SCRIPTS / "check-plugins.py")],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    assert res.returncode == 0, f"Upstream check-plugins.py failed: {res.stdout} {res.stderr}"
    assert "11 plugins checked, 0 problem(s)" in res.stdout
