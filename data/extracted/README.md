# Extracted Data

This directory contains normalized Soot/Shimple extraction outputs for each subject system. The Python Stage 1 pipeline reads these CSVs as its graph-construction inputs.

Current subject directories use the same schema:

- `class_nodes.csv`
- `structural_dependencies.csv`
- `ssa_flow_edges.csv`

These files are extraction inputs for the Python graph pipeline. They are separate from generated graph, clustering, comparison, and sweep outputs.

Experiment result tables are written under `results/<subject>/<stage>/`.
