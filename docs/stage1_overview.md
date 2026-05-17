# Stage 1 Overview

The pre-experiment compares two class dependency graphs:

- `G_raw`: the raw class dependency graph.
- `G_ssa`: the SSA-enhanced class dependency graph.

`G_raw` uses type dependency and call dependency evidence.

`G_ssa` adds Soot/Shimple-derived SSA flow evidence to the raw structural evidence.

Stage 1 uses only `G_ssa`. It runs Leiden community detection on the SSA-enhanced graph and reports a structural graph clustering baseline.

Multi-objective search and semantic enrichment are later dissertation work outside the current Stage 1 implementation.
