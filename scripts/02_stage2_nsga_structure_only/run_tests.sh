#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_stage2_worktree
require_locked_runtime
require_pytest
(
  cd "${STAGE2_ROOT}"
  PYTHONPATH=src "${UV_BIN}" run --frozen pytest tests/test_stage2_robustness.py -q
  PYTHONPATH=src "${UV_BIN}" run --frozen pytest -q
)
