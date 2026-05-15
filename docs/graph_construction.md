# Graph Construction

Stage 1 builds class-level graphs from normalized extraction outputs.

`G_raw` uses structural type and call dependency evidence:

```text
raw_weight = type_weight + call_weight
```

`G_ssa` adds Soot/Shimple-derived SSA flow evidence:

```text
G_ssa_weight = raw_weight + ssa_flow_weight
```

The current scoped SSA flow evidence includes only:

- `return_value_flow`
- `argument_passing_flow`

This is a scoped Soot-based SSA extraction plan, not a full program-wide SSA implementation.
