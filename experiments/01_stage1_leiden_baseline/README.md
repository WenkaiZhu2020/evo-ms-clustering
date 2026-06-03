# Stage 1 Leiden Baseline

This folder contains the formal Stage 1 Leiden baseline runner. Diagnostic, calibration, and sensitivity scripts belong under `experiments/00_pre_experiment/`.

The runner reconstructs fixed baseline graphs from normalized extracted CSV inputs. It does not read `results/<subject>/00_pre_experiment/` and does not automatically select the best DayTrader calibration row.

Formal profiles:

- `raw_reference_leiden`: `graph_type=raw`, `ssa_lambda=0.0`, `resolution=1.0`, `seed=42`.
- `ssa_selected_leiden`: `graph_type=ssa`, `ssa_lambda=2.0`, `resolution=1.25`, `seed=42`.

Inputs:

- `configs/experiments/01_stage1_leiden.yml`
- `configs/subjects/<subject>.yml`
- `data/extracted/<subject>/class_nodes.csv`
- `data/extracted/<subject>/structural_dependencies.csv`
- `data/extracted/<subject>/ssa_flow_edges.csv`

Outputs are written to `results/<subject>/01_stage1_leiden_baseline/`:

- `baseline_index.yml`
- `raw_reference_leiden/graph/stage1_edges.csv`
- `raw_reference_leiden/clustering/stage1_clusters.csv`
- `raw_reference_leiden/metrics/stage1_metrics.csv`
- `raw_reference_leiden/summaries/stage1_cluster_summary.csv`
- `raw_reference_leiden/baseline_metadata.yml`
- `ssa_selected_leiden/graph/stage1_edges.csv`
- `ssa_selected_leiden/clustering/stage1_clusters.csv`
- `ssa_selected_leiden/metrics/stage1_metrics.csv`
- `ssa_selected_leiden/summaries/stage1_cluster_summary.csv`
- `ssa_selected_leiden/baseline_metadata.yml`

Each profile saves the exact graph used by Leiden and records fixed settings plus SHA-256 hashes for the edge table and extracted inputs.

This layer provides frozen comparison targets for later Stage 2 and Stage 3 methods.
