#!/usr/bin/env bash
# Shared safeguards for Stage 2 command wrappers. Source this file; do not run it directly.

set -euo pipefail

STAGE2_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE2_ROOT="$(cd "${STAGE2_SCRIPT_DIR}/../.." && pwd)"
STAGE2_CONFIG="configs/experiments/02_stage2_nsga_structure_only.yml"
STAGE2_BOUNDS="configs/experiments/stage2_robustness_bounds.yml"
STAGE2_RUNNER="experiments/02_stage2_nsga_structure_only/run_robustness.py"
FORMAL_SEEDS="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29"

UV_BIN="${UV:-uv}"

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
  if [[ "${branch}" != "stage2-nsga" && "${branch}" != "stage3-Declaration+Method-Body" ]]; then
    echo "ERROR: Stage 2 commands require stage2-nsga or the final Stage 3 branch, got ${branch}" >&2
    exit 1
  fi
}

require_locked_runtime() {
  (
    cd "${STAGE2_ROOT}"
    "${UV_BIN}" run --frozen python scripts/reproducibility/verify.py \
      --stage stage2 \
      --environment-only
  )
}

require_pytest() {
  if ! (cd "${STAGE2_ROOT}" && "${UV_BIN}" run --frozen python -c "import pytest" >/dev/null 2>&1); then
    echo "ERROR: pytest is not installed in the uv environment." >&2
    exit 1
  fi
}

run_stage2() {
  (
    cd "${STAGE2_ROOT}"
    PYTHONPATH=src "${UV_BIN}" run --frozen python "${STAGE2_RUNNER}" "$@"
  )
}
