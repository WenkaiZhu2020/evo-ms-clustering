#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

UV_BIN="${UV:-uv}"

PYTHONPATH=src "$UV_BIN" run --frozen python experiments/00_pre_experiment/run.py --subject xerces-j
