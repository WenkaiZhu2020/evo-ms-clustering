# Pre-experiment

This folder is the diagnostic and sensitivity layer for Stage 1.

Responsibilities:

- validate normalized extracted CSV loading
- construct `G_raw` and `G_ssa`
- compare raw and SSA graph settings
- inspect SSA-added and SSA-strengthened edges
- run DayTrader reference-based calibration
- run Xerces-J scale and sensitivity analysis
- store outputs that may vary across diagnostic parameter settings

Inputs:

- `configs/experiments/00_pre_experiment.yml`
- `configs/subjects/<subject>.yml`
- `data/extracted/<subject>/class_nodes.csv`
- `data/extracted/<subject>/structural_dependencies.csv`
- `data/extracted/<subject>/ssa_flow_edges.csv`

Base evidence weights are embedded in the normalized extracted CSV rows. `expected_extracted_evidence_weights` validates those row weights; it does not reweight an existing extracted dataset. `ssa_lambda` controls the total SSA contribution after extraction.

Outputs are written to `results/<subject>/00_pre_experiment/`:

- `graph/`: raw and SSA edge tables plus graph metrics.
- `clustering/`: Leiden cluster assignments and partition metrics.
- `comparison/`: raw-vs-SSA comparison summaries, SSA-added edge tables, SSA-strengthened edge tables, and changed-membership inspection outputs.
- `calibration/`: DayTrader reference-based calibration outputs from `run_daytrader_calibration.py`.
- `sensitivity/`: Xerces-J resolution, lambda, and cluster-size sensitivity outputs from `run_xerces_j_sensitivity.py`.

Scripts:

- `run.py`: generic diagnostic workflow for `G_raw` / `G_ssa` construction, raw-vs-SSA Leiden comparison, and SSA impact inspection.
- `run_daytrader_calibration.py`: DayTrader reference-based resolution and SSA-weight calibration.
- `run_xerces_j_sensitivity.py`: Xerces-J scale and sensitivity validation. It writes CSV outputs only and does not generate Markdown reports.

Pre-experiment outputs are not the frozen comparison target for later Stage 2 or Stage 3 methods.
