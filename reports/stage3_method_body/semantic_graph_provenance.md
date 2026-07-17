# Stage 3B semantic-graph provenance

This record freezes the isolated `declaration_method_body_v1` top-3 semantic
graph stage. It stops after graph construction, graph correctness checks,
structural/random diagnostics, and descriptive comparison with the frozen
Stage 3A graph.

## Frozen construction contract

- Similarity: true cosine from `scripts/stage3/similarity.py`.
- Candidate set: all non-self nodes in the same subject.
- Selection: three neighbours per node.
- Ranking: descending cosine, then lexicographic ascending `class_id`.
- Symmetrisation: OR; reciprocal selections become one undirected edge.
- Self-loops and duplicate final edges: forbidden.
- Edge weights: the symmetric true-cosine value, with no threshold.
- Serialization: `.17g`, with numerical zero written as `0`.
- Duplicate-text and duplicate-vector classes remain ordinary candidates; no
  filtering, merging, down-weighting, or forced edges is applied.

The implementation reuses the frozen Stage 3A graph builder and similarity
helper. Stage 3B loaders require the representation ID, subject, class
mapping, input aggregate, embedding aggregate, model revision, source commit,
and passed embedding validation status before construction.

## Provenance and diagnostics

Canonical graphs are under
`data/semantic_graphs/declaration_method_body/<subject>/`. The graph
generation manifest is
`reports/stage3_method_body/semantic_graph_generation_manifest.json`.
Structural diagnostics use the frozen extracted `class_nodes.csv` and
`structural_dependencies.csv` files with canonical undirected endpoints,
self-loop removal, and duplicate-pair merging. The random baseline is the
pre-registered 1000-repetition uniform simple undirected G(n,m) procedure with
subject seed bases 42000, 52000, and 62000.

Canonical and independent temporary graph generations were byte-identical for
all graph artifacts. The observed structural overlap exceeded the fixed random
p95 for JPetStore, DayTrader, and Xerces.

## Stop boundary

No Stage 3B graph was loaded into NSGA-II. No seed 0, pilot seed, formal seed,
Hypervolume, representative selection, MoJoFM, or decomposition-quality
analysis was run. The next task may perform controlled single-seed optimizer
validation.
