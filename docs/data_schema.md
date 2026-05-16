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

Later Stage 1 steps may write derived graph, clustering, and metric outputs. These files are not normalized Soot extraction inputs.

### `leiden_clusters.csv`

- `class_id`
- `class_name`
- `cluster_id`

### `graph_metrics.csv`

- `subject`
- `graph_type`
- `node_count`
- `edge_count`
- `density`
- `average_degree`

### `stage1_metrics.csv`

- `subject`
- `algorithm`
- `graph_type`
- `cluster_count`
- `modularity`
- `average_cluster_size`
- `max_cluster_size`
- `min_cluster_size`
