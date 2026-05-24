# Stage 1 Overview

The pre-experiment compares two class dependency graphs:

- `G_raw`: the raw class dependency graph.
- `G_ssa`: the graph that adds Soot/Shimple SSA-derived flow evidence.

`G_raw` uses type dependency and call dependency evidence.

`G_ssa` adds Soot/Shimple-derived SSA flow evidence to the raw structural evidence.

Stage 1 uses only `G_ssa`. It runs Leiden community detection on `G_ssa` and reports a structural graph clustering baseline.

The Leiden baseline produces class-level assignments with `class_id`, `class_name`, and `cluster_id`.

CargoTracker is the primary experimental subject. JPetStore is retained as a lightweight pipeline validation and debugging subject.

The current repository keeps normalized extraction CSVs and core pre-experiment / Stage 1 baseline outputs as evidence. Previous SSA weight-sweep outputs were removed; the weight sweep is not finalized and will be redesigned and rerun.
