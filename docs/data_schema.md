# Data Schema

The early pipeline expects CSV files with the following schemas.

## `class_nodes.csv`

- `class_id`
- `class_name`
- `package`
- `file_path`

## `structural_dependencies.csv`

- `source`
- `target`
- `dependency_type`
- `weight`

Allowed `dependency_type` values:

- `type`
- `call`

## `ssa_flow_edges.csv`

- `source`
- `target`
- `flow_type`
- `weight`
- `evidence`

Allowed `flow_type` values:

- `return_value_flow`
- `argument_passing_flow`

## `graph_edges.csv`

- `source`
- `target`
- `raw_weight`
- `ssa_flow_weight`
- `G_ssa_weight`

## `leiden_clusters.csv`

- `class_id`
- `class_name`
- `cluster_id`

## `graph_metrics.csv`

- `subject`
- `graph_type`
- `node_count`
- `edge_count`
- `density`
- `average_degree`

## `stage1_metrics.csv`

- `subject`
- `algorithm`
- `graph_type`
- `cluster_count`
- `modularity`
- `average_cluster_size`
- `max_cluster_size`
- `min_cluster_size`
