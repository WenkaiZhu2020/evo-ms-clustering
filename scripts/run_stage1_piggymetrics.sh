#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python experiments/01_stage1_leiden_baseline/run.py --subject piggymetrics
