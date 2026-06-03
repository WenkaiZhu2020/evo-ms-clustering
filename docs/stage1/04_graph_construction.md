
# Graph Construction

Stage 1 builds undirected class-level graphs from normalized extracted CSV files.

Each node represents one in-scope application class. Edges represent aggregated dependency evidence between class pairs.

## Evidence Weights

| Evidence Channel | Embedded Row Weight |
| --- | ---: |
| Type dependency | 1.0 |
| Method call | 2.0 |
| `return_value_flow` | 3.0 |
| `argument_passing_flow` | 3.0 |

These values are stored in the extracted CSV rows.

The config block:

```text
expected_extracted_evidence_weights
````

is used only to validate the extracted data. It does not silently replace or rescale existing CSV weights.

## `G_raw`

`G_raw` contains structural evidence only:

```text
raw_weight
=
type_weight
+
call_weight
```

`type_weight` is the sum of type-dependency rows between the same class pair.

`call_weight` is the sum of method-call rows between the same class pair.

## `G_ssa`

`G_ssa` extends `G_raw` with scoped SSA-derived flow evidence:

```text
ssa_flow_weight
=
return_flow_weight
+
argument_flow_weight
```

```text
g_ssa_weight
=
raw_weight
+
ssa_lambda * ssa_flow_weight
```

Only two SSA flow types are currently used:

```text
return_value_flow
argument_passing_flow
```

`ssa_lambda` controls the overall contribution of SSA-derived evidence after extraction. It does not change the embedded row weights.

## Aggregation Rules

The graph-construction layer applies the following rules:

* `A-B` and `B-A` are normalized into one undirected class pair.
* Repeated evidence rows for the same class pair are summed.
* Self-loops are removed from both `G_raw` and final `G_ssa`.
* SSA-only class pairs are retained in `G_ssa`.
* For SSA-only edges, `type_weight = 0` and `call_weight = 0`.
* When `ssa_lambda = 0`, SSA-only edges are removed because their final `g_ssa_weight` becomes zero.

## Frozen Stage 1 Profiles

| Profile                | Graph Type | Lambda | Resolution | Seed |
| ---------------------- | ---------- | -----: | ---------: | ---: |
| `raw_reference_leiden` | raw        |    0.0 |        1.0 |   42 |
| `ssa_selected_leiden`  | ssa        |    2.0 |       1.25 |   42 |

`raw_reference_leiden` is the strongest admissible raw structural reference identified through DayTrader calibration.

`ssa_selected_leiden` is the strongest admissible non-zero SSA-informed profile retained for controlled comparison.

## Output Columns

`raw_edges.csv`:

```text
source,target,type_weight,call_weight,raw_weight
```

`ssa_edges.csv`:

```text
source,target,type_weight,call_weight,return_flow_weight,argument_flow_weight,ssa_flow_weight,g_ssa_weight
```

The SSA Stage 1 profile uses the same edge-table structure as `ssa_edges.csv`.
