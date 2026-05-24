# Results

This directory contains generated outputs from the Stage 1 experiments.

Outputs are organized as:

```text
results/<subject>/<stage>/
```

CSV and JSON files in this directory are generated experiment outputs. Source inputs are kept under `data/`.

Pre-experiment directories use:

- `graph/` for generated `G_raw` and `G_ssa` edge tables and graph metrics.
- `clustering/` for Leiden cluster assignments and partition metrics.
- `comparison/` for raw-vs-SSA comparison tables.
- `summaries/` for human-readable cluster summaries.

Stage 1 Leiden baseline directories use:

- `clustering/` for `stage1_clusters.csv`.
- `metrics/` for `stage1_metrics.csv`.
- `summaries/` for `stage1_cluster_summary.csv`.
