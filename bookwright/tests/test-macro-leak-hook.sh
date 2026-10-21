#!/usr/bin/env bash
# Table-driven test for the LaTeX-macro-leak hook, run the way hooks.json runs it
# (python3 from PATH). Every case builds the hook's stdin with json.dumps and
# checks the exit code: 0 = clean or not applicable, 2 = leak, 1 = clean but the
# macro_package check was skipped because no PyYAML-capable python was found.
# Stub `bash`/`uv` on PATH record every call, to assert the interpreter resolver
# runs only when a config must be read by a python3 without PyYAML.
# All cases run; failures are counted.

set -uo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$PLUGIN_ROOT/hooks/scripts/find_python.sh"
find_python || { echo "FAIL: no python3 with PyYAML (set \$PYTHON, pip install pyyaml, or install uv)"; exit 1; }

"${PY_CMD[@]}" - "$PLUGIN_ROOT/hooks/scripts" <<'PYEOF'
import json, os, subprocess, sys, tempfile
from pathlib import Path

scripts = Path(sys.argv[1])
hook_py = str(scripts / "check_latex_macro_leak.py")

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    project = tmp / "withcfg"
    (project / "docs/superpowers").mkdir(parents=True)
    (project / "docs/superpowers/bookwright.config.yaml").write_text(
        "notebook_stack: none\nmacro_package: alex\n")
    (project / "book/chapters/ch01").mkdir(parents=True)
    bare = tmp / "nocfg/book"
    bare.mkdir(parents=True)
    in_cfg = str(project / "book/chapters/ch01/sec.tex")
    no_cfg = str(bare / "sec.tex")

    def write(path, content):
        return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}

    def edit(path, new):
        return {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": "x", "new_string": new}}

    cases = [
        # (name, expected exit, stdin payload: dict or raw string)
        ("clean prose with math macros", 0, write(no_cfg, "The rate $\\fprate = 0.01$ holds.")),
        ("texttt macro-name leak", 2, write(no_cfg, "Written \\texttt{\\textbackslash fprate} in source.")),
        ("'the macro' phrase", 2, write(no_cfg, "Here the macro expands to a fraction.")),
        ("'rendered as' in ordinary prose is fine", 0, write(no_cfg, "The histogram is rendered as a bar chart.")),
        ("non-.tex file skipped", 0, write(str(tmp / "notes.md"), "\\texttt{\\textbackslash fprate}")),
        ("column-0 comment ignored", 0, write(in_cfg, "% mentions \\texttt{\\textbackslash fprate} and alex.sty\nProse.")),
        ("indented comment ignored", 0, write(in_cfg, "  % uses alex.sty here\nProse.")),
        ("inline comment ignored", 0, edit(in_cfg, "Prose here. % from alex.sty")),
        ("escaped percent is not a comment", 2, write(no_cfg, "A 5\\% rate; here the macro is shown.")),
        ("macro_package from config flags .sty mention", 2, write(in_cfg, "The rates use the alex.sty notation.")),
        ("macro_package mention via Edit", 2, edit(in_cfg, "see alex.sty")),
        ("no config: package mention not checked", 0, write(no_cfg, "The rates use the alex.sty notation.")),
        ("other package name not flagged", 0, write(in_cfg, "Uses the amsmath.sty conventions.")),
        ("relative path resolved against cwd", 2,
         {"cwd": str(project), "tool_input": {"file_path": "book/chapters/ch01/sec.tex", "content": "alex.sty"}}),
        ("preamble.tex skipped", 0, write(str(project / "book/preamble.tex"), "\\RequirePackage{alex} % alex.sty\nthe macro")),
        ("malformed JSON is not an error", 0, "not json"),
        ("missing content is clean", 0, {"tool_input": {"file_path": in_cfg}}),
    ]

    def stub(path, body):
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(0o755)

    # A python3 that cannot import PyYAML (-S drops site-packages).
    noyaml = tmp / "noyaml-python3"
    stub(noyaml, f'exec {sys.executable} -S "$@"\n')
    calls = tmp / "calls.log"
    real_bash = "/bin/bash"
    # recbin: bash/uv record the call, then behave normally (bash) or fail (uv).
    recbin = tmp / "recbin"
    recbin.mkdir()
    stub(recbin / "bash", f'echo bash >> {calls}\nexec {real_bash} "$@"\n')
    stub(recbin / "uv", f'echo uv >> {calls}\nexit 1\n')
    # failbin: the resolver itself fails (no PyYAML-capable python anywhere).
    failbin = tmp / "failbin"
    failbin.mkdir()
    stub(failbin / "bash", f'echo bash >> {calls}\nexit 1\n')

    base_env = {k: v for k, v in os.environ.items() if k != "PYTHON"}
    rec_env = dict(base_env, PATH=f"{recbin}{os.pathsep}{os.environ.get('PATH', '')}")
    fail_env = dict(base_env, PATH=f"{failbin}{os.pathsep}{os.environ.get('PATH', '')}")
    path_python = ["python3", hook_py]          # exactly what hooks.json runs
    noyaml_hook = [str(noyaml), hook_py]
    yaml_hook = [sys.executable, hook_py]       # the test runner's python has PyYAML

    # (name, command, env, expected exit, stderr must contain, payload, resolver calls expected?)
    runs = [(n, path_python, base_env, e, "already happened" if e == 2 else None, p, None)
            for n, e, p in cases]
    runs += [
        ("non-.tex write spawns no resolver", noyaml_hook, rec_env, 0, None,
         write(str(tmp / "mod.py"), "the macro alex.sty"), False),
        ("non-.tex Edit spawns no resolver", noyaml_hook, rec_env, 0, None,
         edit(str(tmp / "notes.md"), "the macro"), False),
        (".tex without config spawns no resolver", noyaml_hook, rec_env, 0, None,
         write(no_cfg, "Clean prose."), False),
        (".tex with config, python has PyYAML: no resolver", yaml_hook, rec_env, 2, "alex.sty",
         write(in_cfg, "The rates use the alex.sty notation."), False),
        (".tex with config, python lacks PyYAML: resolver runs and check still applies",
         noyaml_hook, rec_env, 2, "alex.sty", write(in_cfg, "The rates use the alex.sty notation."), True),
        ("resolver fails: skipped check is reported, not silent", noyaml_hook, fail_env, 1,
         "macro_package check skipped", write(in_cfg, "The rates use the alex.sty notation."), True),
        ("resolver fails: other leaks still flagged, with the skip note", noyaml_hook, fail_env, 2,
         "macro_package check skipped", write(in_cfg, "Here the macro expands."), True),
    ]

    failed = 0
    for name, cmd, env, expected, needle, payload, want_calls in runs:
        stdin = payload if isinstance(payload, str) else json.dumps(payload)
        calls.unlink(missing_ok=True)
        proc = subprocess.run(cmd, input=stdin, capture_output=True, text=True, env=env)
        made_calls = calls.exists() and calls.read_text().strip() != ""
        if want_calls is not None and made_calls != want_calls:
            failed += 1
            print(f"FAIL: {name}: resolver calls {'made' if made_calls else 'not made'}, expected {'some' if want_calls else 'none'}")
        elif proc.returncode != expected:
            failed += 1
            print(f"FAIL: {name}: exit {proc.returncode}, expected {expected}; stderr: {proc.stderr.strip()}")
        elif needle and needle not in proc.stderr:
            failed += 1
            print(f"FAIL: {name}: stderr lacks {needle!r}: {proc.stderr.strip()}")
        elif expected == 0 and proc.stderr.strip():
            failed += 1
            print(f"FAIL: {name}: expected no stderr, got: {proc.stderr.strip()}")

if failed:
    print(f"FAIL: {failed}/{len(runs)} macro-leak cases")
    sys.exit(1)
print(f"PASS: {len(runs)} macro-leak hook cases")
PYEOF
