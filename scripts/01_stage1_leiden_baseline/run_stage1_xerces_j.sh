#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

PYTHON_BIN="${PYTHON:-.venv/bin/python}"
PYTHONPATH=src "$PYTHON_BIN" experiments/01_stage1_leiden_baseline/run.py --subject xerces-j
