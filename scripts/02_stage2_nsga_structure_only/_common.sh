#!/usr/bin/env bash
# Shared safeguards for Stage 2 command wrappers. Source this file; do not run it directly.

set -euo pipefail

STAGE2_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE2_ROOT="$(cd "${STAGE2_SCRIPT_DIR}/../.." && pwd)"
STAGE2_CONFIG="configs/experiments/02_stage2_nsga_structure_only.yml"
STAGE2_BOUNDS="configs/experiments/stage2_robustness_bounds.yml"
STAGE2_RUNNER="experiments/02_stage2_nsga_structure_only/run_robustness.py"
FORMAL_SEEDS="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29"

DEFAULT_STAGE2_PYTHON="${HOME}/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
PYTHON_BIN="${PYTHON:-${STAGE2_PYTHON:-${DEFAULT_STAGE2_PYTHON}}}"

usage_subject() {
  echo "usage: $1 {jpetstore|daytrader|xerces-j}" >&2
  exit 2
}

require_subject() {
  case "${1:-}" in
    jpetstore|daytrader|xerces-j) ;;
    *) usage_subject "${0##*/}" ;;
  esac
}

require_stage2_worktree() {
  local top_level branch
  top_level="$(git -C "${STAGE2_ROOT}" rev-parse --show-toplevel)"
  branch="$(git -C "${STAGE2_ROOT}" branch --show-current)"
  if [[ "${top_level}" != "${STAGE2_ROOT}" ]]; then
    echo "ERROR: expected repository root ${STAGE2_ROOT}, got ${top_level}" >&2
    exit 1
  fi
  if [[ "${branch}" != "stage2-nsga" ]]; then
    echo "ERROR: Stage 2 commands require branch stage2-nsga, got ${branch}" >&2
    exit 1
  fi
}

require_locked_runtime() {
  if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "ERROR: Python interpreter not executable: ${PYTHON_BIN}" >&2
    echo "Set PYTHON or STAGE2_PYTHON to the locked Stage 2 interpreter." >&2
    exit 1
  fi
  "${PYTHON_BIN}" - <<'PY'
import importlib.metadata as metadata
import sys

expected = {
    "igraph": "1.0.0",
    "leidenalg": "0.12.0",
    "numpy": "2.3.5",
    "pandas": "2.2.3",
    "pymoo": "0.6.2",
}
observed = {name: metadata.version(name) for name in expected}
print("python=" + sys.version.split()[0])
for name in expected:
    print(f"{name}={observed[name]}")
incorrect = {name: (expected[name], observed[name]) for name in expected if observed[name] != expected[name]}
if incorrect:
    for name, (wanted, actual) in incorrect.items():
        print(f"ERROR: {name} must be {wanted}, got {actual}", file=sys.stderr)
    raise SystemExit(1)
PY
}

require_pytest() {
  if ! "${PYTHON_BIN}" -c "import pytest" >/dev/null 2>&1; then
    echo "ERROR: pytest is not installed in ${PYTHON_BIN}." >&2
    echo "Install the pinned test dependency in the locked environment before running this wrapper." >&2
    exit 1
  fi
}

run_stage2() {
  (
    cd "${STAGE2_ROOT}"
    PYTHONPATH=src "${PYTHON_BIN}" "${STAGE2_RUNNER}" "$@"
  )
}
