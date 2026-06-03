# Pre-experiment

This folder is the diagnostic and sensitivity layer for Stage 1. It validates that normalized extracted CSVs can be loaded, builds the raw structural graph (`G_raw`) and the SSA-informed graph (`G_ssa`), then compares their clustering and graph-level characteristics.

Inputs:

- `configs/experiments/00_pre_experiment.yml`
- `configs/subjects/<subject>.yml`
- `data/extracted/<subject>/class_nodes.csv`
- `data/extracted/<subject>/structural_dependencies.csv`
- `data/extracted/<subject>/ssa_flow_edges.csv`

Outputs are written to `results/<subject>/00_pre_experiment/`:

- `graph/`: raw and SSA edge tables plus graph metrics.
- `clustering/`: Leiden cluster assignments and partition metrics.
- `comparison/`: raw-vs-SSA comparison summaries, SSA-added edge tables, SSA-strengthened edge tables, and changed-membership inspection outputs.
- `calibration/`: DayTrader reference-based calibration outputs from `run_daytrader_calibration.py`.
- `sensitivity/`: Xerces-J resolution, lambda, and cluster-size sensitivity outputs from `run_xerces_j_sensitivity.py`.

Scripts:

- `run.py`: generic diagnostic workflow for `G_raw` / `G_ssa` construction, raw-vs-SSA Leiden comparison, and SSA impact inspection.
- `run_daytrader_calibration.py`: DayTrader reference-based resolution and SSA-weight calibration.
- `run_xerces_j_sensitivity.py`: Xerces-J scale and sensitivity validation.

Pre-experiment outputs may vary across diagnostic parameter runs. They are evidence for calibration, sensitivity analysis, and inspection; they are not the frozen comparison target for later Stage 2 or Stage 3 methods.
