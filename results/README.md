# Results

This directory contains generated outputs from the current Stage 1 experiments. Source inputs are kept under `data/`.

## Main Layout

Pre-experiment outputs are diagnostic and may vary across parameter runs. They are stored under:

```text
results/<subject>/00_pre_experiment/
  graph/
  clustering/
  comparison/
  calibration/    # DayTrader only
  sensitivity/    # Xerces-J only
```

Common subdirectories are:

- `graph/`: generated `G_raw` and `G_ssa` edge tables and graph summaries.
- `clustering/`: Leiden cluster assignments and partition metrics.
- `comparison/`: raw-vs-SSA comparison tables and impact analysis outputs.
- `calibration/`: DayTrader reference-based calibration outputs, when generated.
- `sensitivity/`: Xerces-J scale and sensitivity outputs, when generated.

## Stage 1 Leiden Baseline Layout

The formal Stage 1 Leiden baseline is stored under:

```text
results/<subject>/01_stage1_leiden_baseline/
  graph/
    stage1_edges.csv
  clustering/
    stage1_clusters.csv
  metrics/
    stage1_metrics.csv
  summaries/
    stage1_cluster_summary.csv
  baseline_metadata.yml
```

Typical subdirectories are:

- `graph/` for `stage1_edges.csv`, the exact fixed graph used by Leiden.
- `clustering/` for `stage1_clusters.csv`.
- `metrics/` for `stage1_metrics.csv`.
- `summaries/` for `stage1_cluster_summary.csv`.
- `baseline_metadata.yml` for fixed baseline settings and the SHA-256 hash of `graph/stage1_edges.csv`.

This baseline is a fixed-config formal snapshot reconstructed from normalized extracted CSV inputs, not from mutable Pre-experiment result files. It may reproduce the same partition as the matching default SSA diagnostic run, but the two layers have different responsibilities: Pre-experiment is a diagnostic workspace, while Stage 1 is the frozen baseline for later comparison.

## Subject-Specific Outputs

DayTrader calibration outputs are stored under:

```text
results/daytrader/00_pre_experiment/calibration/
```

This folder contains reference-mapping validation, weight sweep summaries, and ranked candidate settings.

Xerces-J default comparison outputs are stored with the other pre-experiment comparison files under:

```text
results/xerces-j/00_pre_experiment/comparison/
```

Xerces-J sensitivity-specific outputs are stored under:

```text
results/xerces-j/00_pre_experiment/sensitivity/
```

This folder contains cluster-size summary, resolution sweep, and SSA lambda sweep outputs. The older `results/xerces-j/stage1/` tree is a legacy generated-output location and is not the active diagnostic path.

Historical generated outputs may be archived locally under `results/_legacy/`. That archive is local-only and should stay excluded through `.git/info/exclude`, not `.gitignore`.

## Report Location

Human-readable interpretation belongs under `docs/reports/`. Result folders should stay focused on generated CSV or JSON artifacts.
