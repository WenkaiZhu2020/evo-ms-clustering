# Stage 3B artifact boundary

This branch uses the explicit representation identity
`declaration_method_body_v1` and experiment ID
`stage3_declaration_method_body`.

Stage 3A is the frozen declaration-only experiment. Its artifacts remain in
their original namespaces and are read-only from the Stage 3B execution path.

## Allowed Stage 3A read

Stage 3B input construction may read only the explicit frozen declaration CSV
for the requested subject:

```text
data/semantic_inputs/jpetstore_class_declarations.csv
data/semantic_inputs/daytrader_class_declarations.csv
data/semantic_inputs/xerces-j_class_declarations.csv
```

This is the source for byte-exact declaration preservation. Regression tests
may also read Stage 3A metadata to prove isolation. A later evaluation-only
comparison may read saved Stage 3A outputs after Stage 3B is complete.

## Forbidden Stage 3A use

Stage 3B must not use Stage 3A embeddings, semantic graphs, seed results,
generic caches, or report inventories as current-run inputs. A missing Stage
3B artifact is an error; it must never fall back to a populated Stage 3A path.
Stage 3B must never write under `reports/stage3/` or any
`results/<subject>/04_stage3_semantic/` directory.

## Stage 3B namespaces

```text
reports/stage3_method_body/
data/semantic_text/declaration_method_body/
data/embeddings/declaration_method_body/
data/semantic_graphs/declaration_method_body/
results/jpetstore/05_stage3_declaration_method_body/
results/daytrader/05_stage3_declaration_method_body/
results/xerces/05_stage3_declaration_method_body/
```

Every future Stage 3B artifact must carry the representation ID, subject,
input hash, configuration hash, and relevant model/class-mapping identity.
Path checks and metadata checks are implemented in
`scripts/stage3_method_body/isolation.py`.
