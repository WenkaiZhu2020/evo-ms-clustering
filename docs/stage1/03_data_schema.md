# Data Schema

The Stage 1 pipeline consumes normalized CSV files produced from Soot-based extraction. These files live under `data/extracted/<subject>/`.

The normalized extraction schema is intentionally class-level. Every `source` and `target` value must refer to an application class listed in `class_nodes.csv`.

## `data/extracted/<subject>/class_nodes.csv`

Class inventory for the Java subject system.

Columns:

- `class_id`
- `class_name`
- `package`
- `class_file_path`

`class_id` is the stable identifier used by graph construction. `class_file_path` points to the compiled `.class` file used for Soot analysis.

## `data/extracted/<subject>/structural_dependencies.csv`

Structural class dependencies used to build `G_raw`.

Columns:

- `source`
- `target`
- `dependency_type`
- `weight`
- `evidence_kind`
- `evidence_location`

Allowed `dependency_type` values:

- `type`
- `call`

`evidence_kind` records the kind of structural evidence observed. `evidence_location` records where the evidence was found, such as a class, method, or source/bytecode location when available.

Allowed `evidence_kind` values:

- `extends_type_reference`
- `implements_type_reference`
- `field_type_reference`
- `method_parameter_type_reference`
- `method_return_type_reference`
- `method_call`

## `data/extracted/<subject>/ssa_flow_edges.csv`

Soot/Shimple-derived SSA flow evidence used to extend `G_raw` into `G_ssa`.

Columns:

- `source`
- `target`
- `flow_type`
- `weight`
- `evidence_method`
- `evidence_statement`

Allowed `flow_type` values:

- `return_value_flow`
- `argument_passing_flow`

SSA flow evidence must remain separate from structural dependencies. The current Stage 1 schema does not include shared domain object evidence.

## Graph Inputs

`G_raw` is built from `structural_dependencies.csv`.

`G_ssa` is built from `structural_dependencies.csv` plus `ssa_flow_edges.csv`.

The final graph remains class-level. Method and statement fields are evidence metadata only; they do not change the graph node granularity.

## Downstream Outputs

Generated graph, clustering, and metric outputs live under `results/<subject>/<stage>/`. These files are not normalized Soot extraction inputs.

### `graph/raw_edges.csv`

- `source`
- `target`
- `type_weight`
- `call_weight`
- `raw_weight`

### `graph/ssa_edges.csv`

- `source`
- `target`
- `type_weight`
- `call_weight`
- `return_flow_weight`
- `argument_flow_weight`
- `ssa_flow_weight`
- `g_ssa_weight`

Stage 1 baseline stores the exact fixed graph used by Leiden as `graph/stage1_edges.csv`. It uses the same columns as `graph/ssa_edges.csv`.

### Cluster assignment files

- `class_id`
- `class_name`
- `cluster_id`

Pre-experiment cluster files are written under `clustering/` and named `leiden_raw_clusters.csv` and `leiden_ssa_clusters.csv`. Stage 1 baseline cluster output is written to `clustering/stage1_clusters.csv`.

### Graph metric files

- `subject`
- `graph_type`
- `node_count`
- `edge_count`
- `density`
- `average_degree`

Pre-experiment graph metric files are written under `graph/` and named `raw_graph_metrics.csv` and `ssa_graph_metrics.csv`.

### Partition metric files

- `subject`
- `algorithm`
- `graph_type`
- `cluster_count`
- `modularity`
- `average_cluster_size`
- `max_cluster_size`
- `min_cluster_size`
- `max_cluster_ratio`
- `singleton_ratio`
- `internal_external_edge_ratio`
- `internal_edge_weight_ratio`

Pre-experiment partition metric files are written under `clustering/` and named `leiden_raw_partition_metrics.csv` and `leiden_ssa_partition_metrics.csv`. Stage 1 baseline partition metrics are written to `metrics/stage1_metrics.csv`.

### Stage 1 baseline metadata

`baseline_metadata.yml` records the fixed default SSA-informed Leiden baseline settings, the extracted input path, the saved edge table path, and the SHA-256 hash of `graph/stage1_edges.csv`.

### Raw-vs-SSA comparison files

`comparison/metrics_summary.csv` records one row per subject run. Current columns include:

- input scale: `class_count`, `raw_edge_count`, `g_ssa_edge_count`, `ssa_flow_evidence_count`
- SSA impact: `new_ssa_edge_count`, `new_ssa_edge_ratio`, `ssa_weight_share`, `cross_raw_cluster_ssa_edge_ratio`
- partition change: `raw_cluster_count`, `ssa_cluster_count`, `cluster_count_delta`, `ari_raw_vs_ssa`, `nmi_raw_vs_ssa`
- balance: `raw_max_cluster_ratio`, `ssa_max_cluster_ratio`, `raw_singleton_ratio`, `ssa_singleton_ratio`
- structure: `raw_weighted_modularity`, `ssa_weighted_modularity`, `raw_internal_edge_weight_ratio`, `ssa_internal_edge_weight_ratio`
