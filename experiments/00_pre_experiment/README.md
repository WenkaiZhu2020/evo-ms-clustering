# Pre-experiment

This experiment builds the raw structural graph (`G_raw`) and the SSA-informed graph (`G_ssa`) for each configured subject, then compares their clustering and graph-level characteristics.

Inputs:

- `configs/experiments/00_pre_experiment.yml`
- `configs/subjects/<subject>.yml`
- `data/extracted/<subject>/class_nodes.csv`
- `data/extracted/<subject>/structural_dependencies.csv`
- `data/extracted/<subject>/ssa_flow_edges.csv`

Outputs are written to `results/<subject>/00_pre_experiment/`:

- `graph/`: raw and SSA edge tables plus graph metrics.
- `clustering/`: Leiden cluster assignments and partition metrics.
- `comparison/`: raw-vs-SSA comparison summaries.
