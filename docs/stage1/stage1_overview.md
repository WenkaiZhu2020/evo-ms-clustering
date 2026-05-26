# Stage 1 Overview

Stage 1 is the structural baseline for the current repository. It starts from Soot/Shimple extraction, builds class-level graphs, and evaluates Leiden clustering before later NSGA-II and semantic experiments.

## Graphs

The pre-experiment compares two class dependency graphs:

- `G_raw`: the raw class dependency graph.
- `G_ssa`: the graph that adds Soot/Shimple SSA-derived flow evidence.

`G_raw` uses type dependency and call dependency evidence.

`G_ssa` adds Soot/Shimple-derived SSA flow evidence to the raw structural evidence.

## Leiden Baseline

Stage 1 uses only `G_ssa`. It runs Leiden community detection on `G_ssa` and reports a structural graph clustering baseline.

The Leiden baseline produces class-level assignments with `class_id`, `class_name`, and `cluster_id`.

## Subjects

- JPetStore: lightweight pipeline validation and debugging subject.
- DayTrader: calibration subject for reference-based sensitivity analysis.
- Xerces-J: larger technical remodularization benchmark for transfer and scalability checks.

## Evidence Layout

Normalized extraction CSVs live under `data/extracted/<subject>/`.

Generated pre-experiment, Stage 1 baseline, calibration, and sensitivity outputs live under `results/<subject>/`.

Cross-case human-readable summaries live under `reports/`.
