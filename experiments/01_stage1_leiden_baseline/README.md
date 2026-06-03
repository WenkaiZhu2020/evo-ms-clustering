# Stage 1 Leiden Baseline

This experiment runs the default SSA-informed Leiden baseline for each configured subject.

This folder contains only the formal Stage 1 Leiden baseline runner. Subject-specific diagnostic and sensitivity scripts belong under `experiments/00_pre_experiment/`.

The runner reconstructs the fixed baseline graph from normalized extracted CSV inputs. It does not read mutable Pre-experiment result files and does not automatically select the best DayTrader calibration row.

Inputs:

- `configs/experiments/01_stage1_leiden.yml`
- `configs/subjects/<subject>.yml`
- `data/extracted/<subject>/class_nodes.csv`
- `data/extracted/<subject>/structural_dependencies.csv`
- `data/extracted/<subject>/ssa_flow_edges.csv`

Outputs are written to `results/<subject>/01_stage1_leiden_baseline/`:

- `graph/stage1_edges.csv`
- `clustering/stage1_clusters.csv`
- `metrics/stage1_metrics.csv`
- `summaries/stage1_cluster_summary.csv`
- `baseline_metadata.yml`

The baseline uses explicit fixed settings from `configs/experiments/01_stage1_leiden.yml`, including graph type, SSA lambda, Leiden resolution, and random seed. `graph/stage1_edges.csv` is the exact graph used by Leiden, and `baseline_metadata.yml` records the fixed settings plus the SHA-256 hash of that edge table.

This layer provides the frozen comparison target for later Stage 2 and Stage 3 methods. It may reproduce the same partition as the matching default SSA diagnostic run, but its role is different: Pre-experiment is for diagnostics and sensitivity analysis, while Stage 1 baseline is for fixed reproducible comparison.
