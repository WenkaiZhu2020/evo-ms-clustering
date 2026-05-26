#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-.venv/bin/python}"
PYTHONPATH=src "$PYTHON_BIN" experiments/01_stage1_leiden_baseline/run_xerces_j_stage1_analysis.py
