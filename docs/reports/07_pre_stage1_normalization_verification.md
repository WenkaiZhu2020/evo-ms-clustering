# Pre / Stage 1 Normalization Verification

## 1. Purpose

This report records the local archival, regeneration, and validation of the canonical Pre-experiment and Stage 1 Leiden baseline outputs after the experiment-layer normalization. The goal is to confirm that regenerated edge tables use unique undirected class pairs, that SSA self-loops are removed, and that the formal Stage 1 baseline is reproducible from extracted data rather than mutable Pre-experiment outputs.

## 2. Commands Executed

Environment and CLI inspection:

```bash
git branch --show-current
git status --short
PYTHONPATH=src .venv/bin/python experiments/00_pre_experiment/run.py --help
PYTHONPATH=src .venv/bin/python experiments/00_pre_experiment/run_daytrader_calibration.py --help
PYTHONPATH=src .venv/bin/python experiments/00_pre_experiment/run_xerces_j_sensitivity.py --help
PYTHONPATH=src .venv/bin/python experiments/01_stage1_leiden_baseline/run.py --help
```

Local archive and regeneration:

```bash
mkdir -p results/_legacy/20260603T084001Z_before_pre_stage1_normalization
cp -a results/jpetstore results/daytrader results/xerces-j results/_legacy/20260603T084001Z_before_pre_stage1_normalization/
rm -rf results/jpetstore results/daytrader results/xerces-j
PYTHONPATH=src .venv/bin/python experiments/00_pre_experiment/run.py --subject jpetstore
PYTHONPATH=src .venv/bin/python experiments/00_pre_experiment/run.py --subject daytrader
PYTHONPATH=src .venv/bin/python experiments/00_pre_experiment/run.py --subject xerces-j
PYTHONPATH=src .venv/bin/python experiments/00_pre_experiment/run_daytrader_calibration.py --subject daytrader
PYTHONPATH=src .venv/bin/python experiments/00_pre_experiment/run_xerces_j_sensitivity.py
PYTHONPATH=src .venv/bin/python experiments/01_stage1_leiden_baseline/run.py --subject jpetstore
PYTHONPATH=src .venv/bin/python experiments/01_stage1_leiden_baseline/run.py --subject daytrader
PYTHONPATH=src .venv/bin/python experiments/01_stage1_leiden_baseline/run.py --subject xerces-j
```

Validation:

```bash
.venv/bin/python -m pytest tests/test_pre_experiment_runner.py tests/test_stage1_runner.py tests/test_graph_builder.py
.venv/bin/python -m pytest
.venv/bin/python -m py_compile experiments/00_pre_experiment/run.py experiments/00_pre_experiment/run_daytrader_calibration.py experiments/00_pre_experiment/run_xerces_j_sensitivity.py experiments/01_stage1_leiden_baseline/run.py
git diff --check
```

## 3. Local-Only Archive Path

Archived active outputs were copied to:

```text
results/_legacy/20260603T084001Z_before_pre_stage1_normalization/
```

The archive contains the previous active `jpetstore`, `daytrader`, and `xerces-j` result trees. `results/_legacy/` is excluded through `.git/info/exclude` and is not staged.

## 4. Regenerated Subjects

The following subjects were regenerated:

| subject | Pre-experiment | subject-specific diagnostics | Stage 1 baseline |
| --- | --- | --- | --- |
| jpetstore | regenerated | not applicable | regenerated |
| daytrader | regenerated | calibration regenerated | regenerated |
| xerces-j | regenerated | sensitivity regenerated | regenerated |

## 5. Old vs New Edge Counts

| subject | old raw edges | new raw edges | old G_ssa edges | new G_ssa edges | old Stage 1 edges | new Stage 1 edges |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| jpetstore | 53 | 53 | 72 | 60 | not present | 60 |
| daytrader | 277 | 267 | 329 | 275 | not present | 275 |
| xerces-j | 3780 | 3780 | 4148 | 4148 | not present | 4148 |

Source: archived CSVs under `results/_legacy/20260603T084001Z_before_pre_stage1_normalization/`; regenerated CSVs under `results/<subject>/00_pre_experiment/graph/` and `results/<subject>/01_stage1_leiden_baseline/graph/`.

The old Stage 1 runner did not save `graph/stage1_edges.csv`, so old Stage 1 edge counts are recorded as `not present`.

## 6. Reverse-Edge Duplicate Removal Check

| subject | edge file | rows | unique undirected pairs | duplicate pairs | canonical order violations | metric edge_count match |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| jpetstore | Pre raw | 53 | 53 | 0 | 0 | true |
| jpetstore | Pre G_ssa | 60 | 60 | 0 | 0 | true |
| jpetstore | Stage 1 | 60 | 60 | 0 | 0 | n/a |
| daytrader | Pre raw | 267 | 267 | 0 | 0 | true |
| daytrader | Pre G_ssa | 275 | 275 | 0 | 0 | true |
| daytrader | Stage 1 | 275 | 275 | 0 | 0 | n/a |
| xerces-j | Pre raw | 3780 | 3780 | 0 | 0 | true |
| xerces-j | Pre G_ssa | 4148 | 4148 | 0 | 0 | true |
| xerces-j | Stage 1 | 4148 | 4148 | 0 | 0 | n/a |

Source: regenerated edge tables and graph metric files under `results/<subject>/00_pre_experiment/graph/`; Stage 1 edge tables under `results/<subject>/01_stage1_leiden_baseline/graph/stage1_edges.csv`.

## 7. Self-Loop Removal Check

| subject | Pre raw self-loops | Pre G_ssa self-loops | Stage 1 self-loops |
| --- | ---: | ---: | ---: |
| jpetstore | 0 | 0 | 0 |
| daytrader | 0 | 0 | 0 |
| xerces-j | 0 | 0 | 0 |

All regenerated edge tables satisfy the no-self-loop invariant.

## 8. Canonical Output Structure

For each subject, the following Pre-experiment files exist:

```text
results/<subject>/00_pre_experiment/
  graph/raw_edges.csv
  graph/ssa_edges.csv
  graph/raw_graph_metrics.csv
  graph/ssa_graph_metrics.csv
  clustering/leiden_raw_clusters.csv
  clustering/leiden_ssa_clusters.csv
  clustering/leiden_raw_partition_metrics.csv
  clustering/leiden_ssa_partition_metrics.csv
  comparison/metrics_summary.csv
  comparison/pre_experiment_summary.csv
  comparison/top_new_ssa_edges.csv
  comparison/top_weight_increased_edges.csv
  comparison/top_moved_classes.csv
```

For each subject, the following Stage 1 baseline files exist:

```text
results/<subject>/01_stage1_leiden_baseline/
  graph/stage1_edges.csv
  clustering/stage1_clusters.csv
  metrics/stage1_metrics.csv
  summaries/stage1_cluster_summary.csv
  baseline_metadata.yml
```

DayTrader calibration outputs were regenerated under `results/daytrader/00_pre_experiment/calibration/`. Xerces-J sensitivity outputs were regenerated under `results/xerces-j/00_pre_experiment/sensitivity/`. No active `results/xerces-j/stage1/` directory remains.

## 9. Stage 1 Metadata and SHA-256 Validation

| subject | role ok | baseline name ok | graph_type | ssa_lambda | resolution | seed | source path ok | edge table ok | SHA-256 ok | cluster schema ok |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| jpetstore | true | true | ssa | 1.0 | 1.0 | 42 | true | true | true | true |
| daytrader | true | true | ssa | 1.0 | 1.0 | 42 | true | true | true | true |
| xerces-j | true | true | ssa | 1.0 | 1.0 | 42 | true | true | true | true |

Source: `results/<subject>/01_stage1_leiden_baseline/baseline_metadata.yml`, `results/<subject>/01_stage1_leiden_baseline/graph/stage1_edges.csv`, and `results/<subject>/01_stage1_leiden_baseline/clustering/stage1_clusters.csv`.

## 10. Pre vs Stage 1 Expected-Equivalence Check

| subject | Pre SSA cluster rows | Stage 1 cluster rows | same class set | same cluster assignments | result |
| --- | ---: | ---: | --- | --- | --- |
| jpetstore | 24 | 24 | true | true | formal baseline reproduction from the same fixed setting |
| daytrader | 121 | 121 | true | true | formal baseline reproduction from the same fixed setting |
| xerces-j | 814 | 814 | true | true | formal baseline reproduction from the same fixed setting |

Source: `results/<subject>/00_pre_experiment/clustering/leiden_ssa_clusters.csv` and `results/<subject>/01_stage1_leiden_baseline/clustering/stage1_clusters.csv`.

This equality is expected because both layers use the same fixed default SSA-informed setting. Their responsibilities remain different: Pre-experiment is the diagnostic workspace, while Stage 1 is the frozen reproducible baseline for later comparison.

## 11. Validation Results

| check | result | notes |
| --- | --- | --- |
| relevant experiment, Stage 1, and graph-builder tests | passed | `30 passed`; 3 expected warnings from test self-loop fixtures |
| full pytest suite | passed | `72 passed`; same 3 expected self-loop warnings |
| Python syntax checks | passed | `py_compile` passed for changed experiment scripts |
| diff whitespace check | passed | `git diff --check` returned no output |
| current branch | stage1-baseline | branch rule preserved |

## 12. Remaining Warnings or Issues

- The old active Xerces-J diagnostic tree `results/xerces-j/stage1/` was removed from the active result layout after being archived locally.
- Historical old outputs are available only in the local `_legacy` archive and should not be committed.
- The regenerated Stage 1 baselines use the fixed default settings recorded in `configs/experiments/01_stage1_leiden.yml`: `graph_type=ssa`, `ssa_lambda=1.0`, `resolution=1.0`, `seed=42`.
- Stage 2 and Stage 3 are not implemented by this regeneration step.
