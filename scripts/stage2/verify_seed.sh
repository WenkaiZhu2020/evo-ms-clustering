#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_subject "${1:-}"
seed="${2:-0}"
if [[ ! "${seed}" =~ ^[0-9]+$ ]]; then
  echo "usage: ${0##*/} {jpetstore|daytrader|xerces-j} [seed]" >&2
  exit 2
fi
require_stage2_worktree
require_locked_runtime

common_args=(
  --subject "$1"
  --seeds "${seed}"
  --bounds-config "${STAGE2_BOUNDS}"
  --config "${STAGE2_CONFIG}"
)
run_stage2 "${common_args[@]}" --verify
run_stage2 "${common_args[@]}" --verify-subprocess
