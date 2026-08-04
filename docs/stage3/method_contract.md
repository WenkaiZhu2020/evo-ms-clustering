# Stage 3 method contract

## Purpose and representation

Stage 3 is the Declaration + Method Body Semantic Extension. Each class input
contains the exact frozen declaration text followed by a deterministically
normalised method-body evidence section:

```text
[DECLARATION]
<frozen declaration text>

[METHOD_BODY]
<normalised evidence or <EMPTY>>
```

The representation ID is `declaration_method_body_v1`. Class scope and class
ordering are fixed at 24 JPetStore classes, 53 DayTrader classes, and 814
Xerces classes. Input hashes are SHA-256 values over the exact UTF-8 semantic
text bytes.

## Semantic evidence and exclusions

Body evidence is extracted from the compiled-class Jimple/Shimple view. The
normalizer retains simple invoked-method names, permitted field names,
meaningful locals when genuinely available, exception names, operation words,
and accepted string-literal vocabulary. It splits compound identifiers,
normalises Unicode, lowercases tokens, removes boilerplate and synthetic
locals, caps repeated tokens, and applies a fixed deterministic order.

Package paths, fully qualified names, invocation owners, type-edge
serialisations, descriptors, source paths, offsets, line numbers, raw Jimple
syntax, and generated temporary identifiers are excluded. Type names are not
added merely because a body creates, casts, or receives a type.

## Formal embedding runtime

The pinned Nomic repository is distributed in Sentence Transformers format.
Formal execution therefore uses `SentenceTransformer`. The packaged model
provides the Qwen2Model transformer, last-token pooling, and vector
normalization. No custom pooling implementation is used.

No query prompt is supplied because the task is class-to-class similarity, not
natural-language-query-to-code retrieval. Embeddings contain 3584 values and
cosine similarity is used. Formal input encoding uses the `semantic_text`
column with truncation disabled. Device, dtype, and batch size are frozen in
the accepted runtime metadata.

## Semantic graph

The graph uses true cosine similarity from saved vectors, excludes self
similarity, selects exactly three neighbours per class, and breaks exact ties
by lexicographically ascending `class_id`. OR symmetrisation retains an
undirected edge when either endpoint selected the other. Edge weights are the
stored cosine values; duplicate classes and duplicate vectors remain in scope.

## Semantic objective and selection

For a partition, the semantic cut is one minus the total within-cluster
semantic-edge weight divided by the total semantic-edge weight. Lower is
better. The Stage 2 structural objective definitions and deterministic
representative-selection rule are unchanged. The added semantic coordinate is
used as the frozen fourth objective, while representative selection uses the
documented projected three-objective procedure.

## Interpretation boundary

Saved results are analysed descriptively and with the preregistered formal
tests. Preference-response tables are explicitly labelled **post-hoc
derived comparisons**. The 5% Stage 2 near-best modularity-band profile is
the active canonical operating profile. A valid DayTrader reference mapping is used only for external
evaluation; unavailable subject references remain unavailable.
