#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_subject "${1:-}"
require_stage2_worktree
require_locked_runtime

run_stage2 \
  --subject "$1" \
  --generate-theoretical-bounds \
  --bounds-config "${STAGE2_BOUNDS}" \
  --config "${STAGE2_CONFIG}"
