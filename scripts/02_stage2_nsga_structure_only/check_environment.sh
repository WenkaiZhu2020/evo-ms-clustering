#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_stage2_worktree
require_locked_runtime
echo "repository=${STAGE2_ROOT}"
echo "branch=$(git -C "${STAGE2_ROOT}" branch --show-current)"
echo "config=${STAGE2_CONFIG}"
echo "bounds=${STAGE2_BOUNDS}"
