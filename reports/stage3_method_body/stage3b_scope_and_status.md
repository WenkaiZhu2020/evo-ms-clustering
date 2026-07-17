# Stage 3B scope and status

## Representation status

Stage 3A remains the completed confirmatory declaration-level experiment.

Stage 3B is a post-hoc exploratory extension that preserves the complete
Stage 3A declaration input and appends normalized method-body evidence.

Stage 3B does not replace or retroactively modify Stage 3A.

The required representation is:

```text
[DECLARATION]
<exact Stage 3A semantic text>

[METHOD_BODY]
<deterministic normalized method-body evidence>
```

## Isolation

Stage 3B artifacts will use the isolated `reports/stage3_method_body/`,
`data/semantic_text/declaration_method_body/`,
`data/embeddings/declaration_method_body/`,
`data/semantic_graphs/declaration_method_body/`, and
`results/*/05_stage3_declaration_method_body/` namespaces. Existing Stage 3A
inputs, embeddings, semantic graphs, validation reports, paired reports, and
formal results are frozen and must not be overwritten.

## Frozen downstream components

The Stage 3A model, tokenizer, inference runtime, true-cosine graph builder,
top-k value, edge weighting, semantic-cut objective, structural objectives,
NSGA-II settings, initialization, seeds, Hypervolume bounds, selection rule,
and validation architecture remain unchanged. Only the semantic input layer is
extended.

Stage 3B must be frozen as exploratory before formal multi-seed outcomes are
inspected. Any later comparison is exploratory and must keep separate
Stage 3B-versus-Stage 3A and Stage 3B-versus-Stage 2 statistical families.
