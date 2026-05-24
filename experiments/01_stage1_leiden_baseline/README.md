# Stage 1 Leiden Baseline

Runs Leiden community detection on `G_ssa` for configured subjects.

Inputs:

- `configs/experiments/01_stage1_leiden.yml`
- `configs/subjects/<subject>.yml`
- `data/extracted/<subject>/class_nodes.csv`
- `results/<subject>/00_pre_experiment/graph/ssa_edges.csv`

Outputs are written to `results/<subject>/01_stage1_leiden_baseline/`:

- `clustering/stage1_clusters.csv`
- `metrics/stage1_metrics.csv`
- `summaries/stage1_cluster_summary.csv`
