#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_subject "${1:-}"
seeds="${2:-0,1}"
if [[ ! "${seeds}" =~ ^[0-9]+(,[0-9]+)*$ ]]; then
  echo "usage: ${0##*/} {jpetstore|daytrader|xerces-j} [comma-separated-seeds]" >&2
  exit 2
fi
require_stage2_worktree
require_locked_runtime

run_stage2 \
  --subject "$1" \
  --seeds "${seeds}" \
  --output-dir "results/$1/03_stage2_nsga/robustness_smoke" \
  --bounds-config "${STAGE2_BOUNDS}" \
  --config "${STAGE2_CONFIG}" \
  --allow-smoke-bounds
