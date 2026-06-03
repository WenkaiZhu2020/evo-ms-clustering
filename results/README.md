# Results

This directory contains generated Stage 1 outputs. Source inputs are under `data/`.

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

Subdirectories:

- `graph/`: generated `G_raw` and `G_ssa` edge tables and graph summaries.
- `clustering/`: Leiden cluster assignments and partition metrics.
- `comparison/`: raw-vs-SSA comparison tables and impact analysis outputs.
- `calibration/`: DayTrader reference-based calibration outputs.
- `sensitivity/`: Xerces-J scale and sensitivity outputs.

## Stage 1 Leiden Baseline Layout

The formal Stage 1 Leiden baseline is stored under:

```text
results/<subject>/01_stage1_leiden_baseline/
  baseline_index.yml
  raw_reference_leiden/
    graph/stage1_edges.csv
    clustering/stage1_clusters.csv
    metrics/stage1_metrics.csv
    summaries/stage1_cluster_summary.csv
    baseline_metadata.yml
  ssa_selected_leiden/
    graph/stage1_edges.csv
    clustering/stage1_clusters.csv
    metrics/stage1_metrics.csv
    summaries/stage1_cluster_summary.csv
    baseline_metadata.yml
```

Contents:

- `raw_reference_leiden/` for the raw structural reference profile.
- `ssa_selected_leiden/` for the selected non-zero SSA-informed comparison profile.
- `baseline_index.yml` for the generated profile list and comparison purpose.
- each profile-level `baseline_metadata.yml` for fixed settings and SHA-256 hashes of `graph/stage1_edges.csv` and extracted inputs.

These baselines are fixed-config snapshots reconstructed from normalized extracted CSV inputs, not from mutable Pre-experiment result files.

## Subject-Specific Outputs

DayTrader calibration outputs are stored under:

```text
results/daytrader/00_pre_experiment/calibration/
```

This folder contains reference-mapping validation, weight sweep summaries, ranked candidate settings, and the selected profile record.

Xerces-J default comparison outputs are stored with the other pre-experiment comparison files under:

```text
results/xerces-j/00_pre_experiment/comparison/
```

Xerces-J sensitivity-specific outputs are stored under:

```text
results/xerces-j/00_pre_experiment/sensitivity/
```

This folder contains cluster-size summary, resolution sweep, and SSA lambda sweep outputs. Xerces-J has no separate active diagnostic output tree outside `00_pre_experiment/sensitivity/`.

Historical generated outputs are not kept in the active results layout.

## Report Location

Human-readable interpretation belongs under `docs/reports/`. Result folders should stay focused on generated CSV or JSON artifacts.
