#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_subject "${1:-}"
resume_args=()
if [[ $# -eq 2 && "$2" == "--resume" ]]; then
  resume_args=(--resume)
elif [[ $# -ne 1 ]]; then
  echo "usage: ${0##*/} {jpetstore|daytrader|xerces-j} [--resume]" >&2
  exit 2
fi
require_stage2_worktree
require_locked_runtime

run_stage2 \
  --subject "$1" \
  --seeds "${FORMAL_SEEDS}" \
  --bounds-config "${STAGE2_BOUNDS}" \
  --config "${STAGE2_CONFIG}" \
  "${resume_args[@]}"
