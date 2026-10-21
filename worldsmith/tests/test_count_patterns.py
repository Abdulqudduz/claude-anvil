"""Tests for scripts/count_patterns.py (audit and --check-text modes).

Run: python3 -m pytest tests/
"""

import io
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import count_patterns as cp  # noqa: E402


def hook_hits(text, patterns_path=cp.BUNDLED_PATTERNS):
    return [p.text for _, p in cp.check_text(text, cp.hook_categories(patterns_path))]


def run_check(text, monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))
    code = cp.main(["--check-text", *args])
    return code, capsys.readouterr().err


# --- parsing ---------------------------------------------------------------

def test_bundled_file_parses_with_hook_categories():
    cats = {c.name: c for c in cp.parse_patterns(cp.BUNDLED_PATTERNS)}
    assert not cats["Crutch Words"].hook
    hooked = [c.name for c in cats.values() if c.hook]
    assert set(hooked) == {
        "Stock Body Reactions", "Dead Metaphors", "Emotional Labeling",
        "Redundant Adverbs", "Fancy Dialogue Tags",
    }
    assert cats["Fancy Dialogue Tags"].scope == "dialogue-lines"
    assert all(c.hint for c in cats.values() if c.hook)


def test_regex_directive_and_literals(tmp_path):
    f = tmp_path / "p.md"
    f.write_text("## A\n<!-- regex: fo+ -->\nbar, baz qux\n<!-- some comment -->\n")
    (cat,) = cp.parse_patterns(str(f))
    assert [(p.kind, p.text) for p in cat.patterns] == [
        ("regex", "fo+"), ("literal", "bar"), ("literal", "baz qux")]
    assert not cat.hook


# --- word-boundary matching -----------------------------------------------

@pytest.mark.parametrize("text", [
    '"Fine," she said, amused.',
    '"Fine," she said, bemused.',
    '"It was an undeclared war," he said.',
    '"Remarkably calm," she said.',
])
def test_no_substring_false_positives(text):
    assert hook_hits(text) == []


@pytest.mark.parametrize("text,phrase", [
    ("Her heart raced.", "heart raced"),
    ("HIS EYES WIDENED.", "eyes widened"),
    ('"Go," she whispered quietly.', "whispered quietly"),
    ('"Fine," she mused.', "mused"),
    ("She couldn’t help but notice.", "couldn't help but notice"),
])
def test_cliches_flagged(text, phrase):
    assert phrase in hook_hits(text)


def test_dialogue_tags_only_on_dialogue_lines():
    assert hook_hits("The king declared war.") == []
    assert hook_hits("“War,” the king declared.") == ["declared"]


# --- adverb dialogue tag regex (audit category) ----------------------------

@pytest.mark.parametrize("text,count", [
    ("she said carefully", 1),
    ("she said cheerfully", 1),
    ("she said quietly", 1),
    ("asked Sally", 0),
    ("said Billy", 0),
    ("said nothing", 0),
])
def test_adverb_dialogue_tag_regex(text, count):
    cats = {c.name: c for c in cp.parse_patterns(cp.BUNDLED_PATTERNS)}
    (pat,) = cats["Adverb Dialogue Tags"].patterns
    assert cp.count_pattern([text], pat) == count


# --- CLI and overrides -----------------------------------------------------

def test_check_text_exit_codes(monkeypatch, capsys):
    code, err = run_check("Her heart raced.", monkeypatch, capsys, "--label", "ch1.md")
    assert code == 2
    assert "ch1.md" in err and '"heart raced"' in err
    code, err = run_check("The rain tapped.", monkeypatch, capsys)
    assert (code, err) == (0, "")


def test_project_override_replaces_hook_list(tmp_path, monkeypatch, capsys):
    (tmp_path / ".worldsmith").mkdir()
    (tmp_path / ".worldsmith" / "patterns.md").write_text(
        "## Mine\n<!-- hook: block -->\nfoo\n")
    code, _ = run_check("Her heart raced.", monkeypatch, capsys, "--project-dir", str(tmp_path))
    assert code == 0
    code, err = run_check("foo bar", monkeypatch, capsys, "--project-dir", str(tmp_path))
    assert code == 2 and '"foo"' in err


def test_override_without_hook_categories_falls_back(tmp_path, monkeypatch, capsys):
    (tmp_path / ".worldsmith").mkdir()
    (tmp_path / ".worldsmith" / "patterns.md").write_text("## Crutch Words\njust\n")
    code, _ = run_check("Her heart raced.", monkeypatch, capsys, "--project-dir", str(tmp_path))
    assert code == 2


def test_empty_hook_category_disables_hook(tmp_path, monkeypatch, capsys):
    (tmp_path / ".worldsmith").mkdir()
    (tmp_path / ".worldsmith" / "patterns.md").write_text("## Off\n<!-- hook: block -->\n")
    code, _ = run_check("Her heart raced.", monkeypatch, capsys, "--project-dir", str(tmp_path))
    assert code == 0


def test_audit_mode_counts(tmp_path, capsys):
    ch = tmp_path / "ch1.md"
    ch.write_text("It was just very quiet. Her heart raced. She just left.")
    assert cp.main([str(tmp_path / "*.md")]) == 0
    out = capsys.readouterr().out
    assert "just" in out and "heart raced" in out and "Total words" in out


def test_audit_mode_no_files(tmp_path, capsys):
    assert cp.main([str(tmp_path / "*.md")]) == 1
