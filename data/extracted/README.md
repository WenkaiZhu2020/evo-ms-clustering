# Extracted Data

This directory contains normalized Soot/Shimple extraction outputs for each subject system. The Python Stage 1 pipeline reads these CSVs as its graph-construction inputs.

Each subject directory contains:

- `class_nodes.csv`
- `structural_dependencies.csv`
- `ssa_flow_edges.csv`

Experiment result tables are written under `results/<subject>/<stage>/`.
