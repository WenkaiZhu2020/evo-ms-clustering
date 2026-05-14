# Data Schema

The early pipeline expects CSV files with the following schemas.

## `class_nodes.csv`

- `class_id`
- `class_name`
- `package`
- `file_path`

## `raw_edges.csv`

- `source`
- `target`
- `type_weight`
- `call_weight`
- `raw_weight`

## `enriched_edges.csv`

- `source`
- `target`
- `type_weight`
- `call_weight`
- `return_flow_weight`
- `parameter_flow_weight`
- `shared_domain_weight`
- `flow_weight`
- `enriched_weight`

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
