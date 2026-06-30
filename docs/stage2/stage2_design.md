# Stage 2 Design Index

Stage 2 is a raw-graph, structure-only NSGA-II experiment implemented through
pymoo. It optimizes three structural objectives on `G_raw` and compares the
selected NSGA-II partition with the frozen Stage 1 `raw_reference_leiden`
baseline.

The current design documents are in `docs/stage2/`:

- [workflow.md](workflow.md):
  end-to-end raw-only pipeline and Stage 1 reuse points.
- [objectives_and_metrics.md](objectives_and_metrics.md):
  strict separation between optimization objectives and post-hoc metrics.
- [experiment_design.md](experiment_design.md):
  subject scope, multi-seed protocol, selection rule, and raw Leiden comparison.
- [encoding_and_operators.md](encoding_and_operators.md):
  label-vector encoding, seeded initialization, operators, and constraints.

Current optimization objectives:

1. minimize inter-cluster coupling;
2. maximize density-based intra-cluster cohesion;
3. minimize cluster-size imbalance.

Stage 2 uses only `G_raw` with `raw_weight`. No alternative Stage 2 input graph
is part of the final design.
