# Graph Construction

Stage 1 builds class-level graphs from normalized extraction outputs.

`G_raw` uses structural type and call dependency evidence:

```text
raw_weight = type_weight + call_weight
```

`G_ssa` adds Soot/Shimple-derived SSA flow evidence:

```text
ssa_flow_weight = return_flow_weight + argument_flow_weight
g_ssa_weight = type_weight + call_weight + ssa_flow_weight
```

The current scoped SSA flow evidence includes only:

- `return_value_flow`
- `argument_passing_flow`

The current graph construction uses scoped Soot-based SSA evidence rather than full program-wide SSA evidence.

## `raw_edges.csv`

`raw_edges.csv` is produced by grouping `structural_dependencies.csv` by class-level
`source` and `target`:

- `type_weight`: sum of `type` dependency weights
- `call_weight`: sum of `call` dependency weights
- `raw_weight`: `type_weight + call_weight`

Self-loops are removed before graph construction.

## `ssa_edges.csv`

`ssa_edges.csv` combines `raw_edges.csv` with grouped `ssa_flow_edges.csv`.

Required columns:

- `source`
- `target`
- `type_weight`
- `call_weight`
- `return_flow_weight`
- `argument_flow_weight`
- `ssa_flow_weight`
- `g_ssa_weight`

Flow type mapping:

- `return_value_flow` contributes to `return_flow_weight`
- `argument_passing_flow` contributes to `argument_flow_weight`

SSA-flow-only edges are retained with `type_weight = 0` and `call_weight = 0`.
Shared-domain-object evidence is outside the Stage 1 graph construction schema.
