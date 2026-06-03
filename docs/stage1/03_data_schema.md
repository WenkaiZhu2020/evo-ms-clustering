# Data Schema

Stage 1 consumes normalized class-level CSVs under `data/extracted/<subject>/`.

## Extracted Inputs

### `class_nodes.csv`

| Column | Meaning |
| --- | --- |
| `class_id` | class identifier used by graph construction |
| `class_name` | fully qualified class name |
| `package` | package name |
| `class_file_path` | analyzed `.class` file path |

### `structural_dependencies.csv`

| Column | Meaning |
| --- | --- |
| `source` | source class id |
| `target` | target class id |
| `dependency_type` | `type` or `call` |
| `weight` | embedded extracted row weight |
| `evidence_kind` | structural evidence kind |
| `evidence_location` | class, method, or statement location |

Allowed `evidence_kind` values:

- `extends_type_reference`
- `implements_type_reference`
- `field_type_reference`
- `method_parameter_type_reference`
- `method_return_type_reference`
- `method_call`

### `ssa_flow_edges.csv`

| Column | Meaning |
| --- | --- |
| `source` | source class id |
| `target` | target class id |
| `flow_type` | `return_value_flow` or `argument_passing_flow` |
| `weight` | embedded extracted row weight |
| `evidence_method` | method where evidence was observed |
| `evidence_statement` | statement where evidence was observed |

## Pre-Experiment Outputs

```text
results/<subject>/00_pre_experiment/
  graph/raw_edges.csv
  graph/ssa_edges.csv
  graph/raw_graph_metrics.csv
  graph/ssa_graph_metrics.csv
  clustering/leiden_raw_clusters.csv
  clustering/leiden_ssa_clusters.csv
  clustering/leiden_raw_partition_metrics.csv
  clustering/leiden_ssa_partition_metrics.csv
  comparison/metrics_summary.csv
  comparison/pre_experiment_summary.csv
  comparison/top_new_ssa_edges.csv
  comparison/top_weight_increased_edges.csv
  comparison/top_moved_classes.csv
```

DayTrader calibration outputs are under `results/daytrader/00_pre_experiment/calibration/`. Xerces-J sensitivity outputs are under `results/xerces-j/00_pre_experiment/sensitivity/`.

## Formal Stage 1 Outputs

```text
results/<subject>/01_stage1_leiden_baseline/
  baseline_index.yml
  raw_reference_leiden/
    graph/stage1_edges.csv
    clustering/stage1_clusters.csv
    metrics/stage1_metrics.csv
    summaries/stage1_cluster_summary.csv
    baseline_metadata.yml
  ssa_selected_leiden/
    graph/stage1_edges.csv
    clustering/stage1_clusters.csv
    metrics/stage1_metrics.csv
    summaries/stage1_cluster_summary.csv
    baseline_metadata.yml
```

Cluster files use:

```text
class_id,class_name,cluster_id
```

Profile metadata records profile settings, extracted input hashes, and the SHA-256 hash of `graph/stage1_edges.csv`.
