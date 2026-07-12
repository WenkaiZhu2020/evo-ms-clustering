#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_stage2_worktree
require_locked_runtime
require_pytest
(
  cd "${STAGE2_ROOT}"
  PYTHONPATH=src "${PYTHON_BIN}" -m pytest tests/test_stage2_robustness.py -q
  PYTHONPATH=src "${PYTHON_BIN}" -m pytest -q
)
