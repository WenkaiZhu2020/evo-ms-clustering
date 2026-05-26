#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-.venv/bin/python}"
PYTHONPATH=src "$PYTHON_BIN" experiments/00_pre_experiment/run_weight_sweep.py --subject daytrader
