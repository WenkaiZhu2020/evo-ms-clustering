# Results

This directory contains generated outputs from the current Stage 1 experiments. Source inputs are kept under `data/`.

## Main Layout

Pre-experiment outputs are stored under:

```text
results/<subject>/00_pre_experiment/
```

Common subdirectories are:

- `graph/`: generated `G_raw` and `G_ssa` edge tables and graph summaries.
- `clustering/`: Leiden cluster assignments and partition metrics.
- `comparison/`: raw-vs-SSA comparison tables and impact analysis outputs.

## Stage 1 Leiden Baseline Layout

Some older Stage 1 Leiden baseline folders use:

```text
results/<subject>/01_stage1_leiden_baseline/
```

Typical subdirectories are:

- `clustering/` for `stage1_clusters.csv`.
- `metrics/` for `stage1_metrics.csv`.
- `summaries/` for `stage1_cluster_summary.csv`.

These folders are still generated outputs. They should be read together with the pre-experiment graph and comparison outputs.

## Subject-Specific Outputs

DayTrader calibration outputs are stored under:

```text
results/daytrader/00_pre_experiment/calibration/
```

This folder contains reference-mapping validation, weight sweep summaries, and ranked candidate settings.

Xerces-J Stage 1 summary and sweep outputs are flat CSV files under:

```text
results/xerces-j/stage1/
```

This folder contains graph summary, Leiden comparison, resolution sweep, and SSA lambda sweep outputs.

## Report Location

Human-readable interpretation belongs under `docs/reports/`. Result folders should stay focused on generated CSV or JSON artifacts.
