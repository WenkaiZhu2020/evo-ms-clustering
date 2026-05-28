# SSA Weight Adjustment Log

This document records how SSA weight sensitivity is handled in the current Stage 1 repository.

## Current Evidence

- DayTrader calibration outputs are under `results/daytrader/00_pre_experiment/calibration/`.
- Xerces-J Stage 1 sensitivity outputs are under `results/xerces-j/stage1/`.
- Cross-case interpretation is summarized in `docs/reports/02_stage1_cross_case_summary.md`.

DayTrader has a reference mapping, so its sweep can include reference-based metrics such as MoJoFM and pairwise F1. Xerces-J has no business reference mapping in this repository, so its lambda sweep is used for transfer and scalability analysis with internal graph and partition metrics.

## Weight Rule

The default `G_ssa` weight is:

```text
g_ssa_weight = type_weight + call_weight + ssa_flow_weight
```

The sensitivity form is:

```text
g_ssa_weight(lambda) = type_weight + call_weight + lambda * ssa_flow_weight
```

`lambda = 0` is the raw-structure baseline. Low lambda values test SSA as a weak behavioural signal. Higher lambda values test whether SSA begins to dominate graph boundaries.

## What the Sweeps Are For

The sweeps are used to detect a useful range of SSA influence. They are not used to claim that `G_ssa` is always better than `G_raw`.

The main questions are:

- Does SSA add non-trivial graph evidence?
- Does SSA change the Leiden partition?
- Does stronger SSA improve or reduce internal structural metrics under the current setting?
- Does stronger SSA create oversized clusters, high singleton ratios, or hub-like over-aggregation?
- Does a non-raw setting remain reasonable compared with the raw baseline and reference metrics where available?

## Recorded Fields

Current sweep outputs may record:

- subject
- `ssa_lambda`
- Leiden resolution
- `raw_edge_count`
- `g_ssa_edge_count`
- `new_ssa_edge_count`
- `ssa_weight_share`
- cluster count and cluster-size balance metrics
- weighted modularity
- internal edge weight ratio
- raw-vs-SSA ARI and NMI
- reference-based metrics for DayTrader

## Interpretation Boundary

SSA weight is treated as a sensitivity parameter and possible controlled evidence channel. Stage 1 does not prove that SSA is better than raw structure. It shows where SSA changes the graph, where it may help, and where it may create over-aggregation or hub effects that later stages need to control.
