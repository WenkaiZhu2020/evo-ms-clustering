# Results

This directory contains generated Stage 0, Stage 1, and Stage 2 outputs. The
formal Stage 2 index is [FORMAL_RESULTS_INDEX.md](FORMAL_RESULTS_INDEX.md).
Source inputs are under `data/`.

## Classification

- **FORMAL**: `results/<subject>/03_stage2_nsga/robustness_final_30seeds/` and
  `results/cross_subject/03_stage2_nsga/final_statistics/`.
- **SUPPORTING DIAGNOSTIC**: `convergence_diagnostic/`, retained diagnostics,
  and the Stage 2 audit evidence.
- **HISTORICAL / FAILED CLEANUP**: obsolete raw, smoke, failed-bound, and
  superseded diagnostic derived outputs were removed; the exact inventory is
  `cross_subject/03_stage2_nsga/final_statistics/historical_output_cleanup_inventory.csv`.

Only the FORMAL paths are suitable for thesis result numbers. Protected source
artifacts and compact provenance records are retained separately and are not
used by the formal verifier or current canonical Stage 2 result tables.

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
- `calibration/`: DayTrader constrained internal-primary calibration outputs with reference-based sanity checks.
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

## Stage 2 Layout

The canonical results layout is `results/<scope>/<stage>/<artifact-kind>/`.
`<scope>` is one of the three individual subjects or `cross_subject` for
aggregated evidence. The final Stage 2 formal output for each subject is:

```text
results/<subject>/03_stage2_nsga/robustness_final_30seeds/
```

Each final directory contains `seed_00` through `seed_29`, the complete
per-seed Pareto outputs, run metadata, and a robustness manifest. The
canonical post-hoc operating-profile metrics are under:

```text
results/cross_subject/03_stage2_nsga/modularity_band/
```

Final cross-subject statistics are under:

```text
results/cross_subject/03_stage2_nsga/final_statistics/
```

`convergence_diagnostic/` is a final supporting diagnostic. Other existing
sibling directories under `03_stage2_nsga/` are current formal outputs or
supporting evidence, not replacements for the final formal outputs:

- `robustness_final_30seeds/`: frozen formal evidence.
- `diagnostics/`: supplementary checks.

Pre-final cross-subject robustness tables and the DayTrader
`final_config_smoke/` output were moved to the external
`evo-ms-clustering-stage2-diagnostics-archive` repository. They are not final
Stage 2 evidence. Historical raw, smoke, failed-bound, and superseded
DayTrader audit outputs are recorded in the cleanup inventory and are not
available as active result paths.

Consumers of final Stage 2 findings must use `robustness_final_30seeds/` and
the associated `cross_subject/03_stage2_nsga/final_statistics/` directory, not
a historical sibling.

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

The historical/failed-output cleanup inventory is maintained at:

```text
results/cross_subject/03_stage2_nsga/final_statistics/historical_output_cleanup_inventory.csv
```

## Report Location

Human-readable interpretation belongs under `docs/reports/`. Result folders should stay focused on generated CSV or JSON artifacts.
