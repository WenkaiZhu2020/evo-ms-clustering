# Results

This directory contains generated Stage 1 experiment outputs only.

Outputs are organized as:

```text
results/<subject>/<stage>/
```

Current committed evidence should be limited to core pre-experiment outputs and Stage 1 Leiden baseline outputs. CSV and JSON files here are experiment evidence, not source inputs.

Pre-experiment directories use:

- `graph/` for generated `G_raw` and `G_ssa` edge tables and graph metrics.
- `clustering/` for Leiden cluster assignments and partition metrics.
- `comparison/` for raw-vs-SSA comparison tables.
- `summaries/` for human-readable cluster summaries.

Stage 1 Leiden baseline directories use:

- `clustering/` for `stage1_clusters.csv`.
- `metrics/` for `stage1_metrics.csv`.
- `summaries/` for `stage1_cluster_summary.csv`.

Old SSA weight-sweep outputs have been removed. The weight sweep is not finalized and will be redesigned and rerun before any new sweep evidence is committed.
