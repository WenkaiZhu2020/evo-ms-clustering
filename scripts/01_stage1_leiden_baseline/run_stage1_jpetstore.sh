#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

UV_BIN="${UV:-uv}"
PYTHONPATH=src "$UV_BIN" run --frozen python experiments/01_stage1_leiden_baseline/run.py --subject jpetstore
