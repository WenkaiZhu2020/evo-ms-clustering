# Graph Enrichment

Graph enrichment adds SSA-inspired data-flow evidence to the raw class dependency graph. This is not a full SSA implementation. It uses selected flow relationships as additional class-level evidence.

Raw edge weights use type and call evidence:

```text
raw_weight = type_weight + call_weight
```

Enriched edge weights add flow evidence:

```text
enriched_weight = type_weight + call_weight + flow_weight
```

Flow evidence includes:

- Return value flow
- Parameter passing flow
- Shared domain object

The combined `flow_weight` is the sum of these flow evidence weights for a class pair.
