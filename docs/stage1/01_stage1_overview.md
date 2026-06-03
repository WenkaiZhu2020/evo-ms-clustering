# Stage 1 Overview

Stage 1 is the current implemented stage of this repository. It evaluates the extraction and graph-clustering evidence pipeline before later NSGA-II and semantic embedding stages.

The stage does not claim that a produced partition is a final microservice design. It prepares a measured baseline, checks whether SSA evidence changes the graph, and records how sensitive Leiden clustering is to key parameters.

## Graphs

The pre-experiment compares two class dependency graphs:

- `G_raw`: a class-level graph built from structural type and call dependency evidence.
- `G_ssa`: the same structural graph with scoped Soot/Shimple SSA flow evidence added.

`G_raw` uses `raw_weight`, which is based on type and call evidence.

`G_ssa` uses `g_ssa_weight`, which adds scoped `return_value_flow` and `argument_passing_flow` evidence. The current SSA scope is intentionally narrow. It is used as a controlled evidence channel, not as a general claim that all SSA relations improve decomposition.

## Subject Design

Stage 1 uses three active subjects:

- JPetStore: small smoke-test subject. It verifies extraction, CSV loading, graph construction, Leiden execution, and basic metrics.
- DayTrader: calibration and reference-based subject. It has a reference-service mapping, so it supports resolution and SSA-weight sensitivity checks with external metrics.
- Xerces-J: larger technical remodularization benchmark. It checks whether the same pipeline scales beyond small business-style systems.

CargoTracker is inactive in the current Stage 1 subject set. PiggyMetrics is not used as an input subject.

## Why Resolution Sweep Is Used

Leiden resolution controls clustering granularity. A low resolution can merge many classes into large clusters, while a high resolution can split the graph into many smaller clusters.

A single default resolution may hide whether a result is stable or only a parameter effect. Stage 1 therefore records how cluster count, modularity, internal edge weight ratio, and cluster-size balance change across resolution values.

This also creates a fairer baseline for Stage 2. Later NSGA-II results should be compared against both default Leiden and tuned Leiden, not only against one default run.

## Why Lambda / SSA-Weight Sweep Is Used

Lambda controls how strongly SSA flow evidence contributes to `G_ssa`:

```text
g_ssa_weight(lambda) = type_weight + call_weight + lambda * ssa_flow_weight
```

`lambda = 0` is the raw-structure baseline. Low lambda values test SSA as a weak behavioural signal. Higher values test whether SSA begins to dominate graph boundaries.

The sweep is not used to overfit each subject. It is used to find a safer range where SSA may add useful evidence without causing over-aggregation, hub effects, or lower structural compactness.

## Link to Later Stages

Stage 2 should first compare structure-only NSGA-II against the Leiden baselines. This keeps the direct comparison clear because Leiden is also graph-structure based.

SSA can remain as a controlled graph input, or it can later become a separate objective or penalty term. Stage 3 can then add semantic embeddings as another independent evidence channel. The intended later comparison is therefore structure-only, structure plus SSA, and structure plus SSA plus semantics.

The Pre-experiment layer provides diagnostics, parameter sweeps, and evidence inspection. The Stage 1 Leiden baseline layer reconstructs one fixed SSA-informed graph directly from extracted CSVs and saves the edge table plus metadata for reproducible comparison.

## Evidence Layout

Normalized extraction CSVs live under `data/extracted/<subject>/`.

Generated pre-experiment, Stage 1 baseline, calibration, and sensitivity outputs live under `results/<subject>/`.

Human-readable Stage 1 documentation and reports live under `docs/stage1/` and `docs/reports/`.
