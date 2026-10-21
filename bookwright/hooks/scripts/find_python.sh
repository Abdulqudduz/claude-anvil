# Sourced, not executed. Resolves a Python interpreter that can import PyYAML.
# Single copy shared by the tests and check_latex_macro_leak.py (which calls it
# only when it must read a config and its own interpreter lacks PyYAML).
#
# find_python sets the global array PY_CMD and returns 0, or returns 1 if no
# candidate works. Candidates, in order (first hit wins, so the common case
# costs one or two quick probes):
#   1. $PYTHON (explicit override)
#   2. python3 on PATH
#   3. /usr/bin/python3
#   4. uv run --quiet --no-project --with pyyaml python3   (only if uv is on PATH)
find_python() {
    local cand
    for cand in "${PYTHON:-}" python3 /usr/bin/python3; do
        [ -n "$cand" ] || continue
        if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import yaml' >/dev/null 2>&1; then
            PY_CMD=("$cand")
            return 0
        fi
    done
    if command -v uv >/dev/null 2>&1; then
        local uvcmd=(uv run --quiet --no-project --with pyyaml python3)
        if "${uvcmd[@]}" -c 'import yaml' >/dev/null 2>&1; then
            PY_CMD=("${uvcmd[@]}")
            return 0
        fi
    fi
    return 1
}
