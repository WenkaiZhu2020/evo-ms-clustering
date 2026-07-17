# Stage 3B embedding provenance

This record freezes the isolated `declaration_method_body_v1` embedding run. It
covers embedding generation and validation only. No nearest-neighbour file,
semantic graph, optimization run, seed run, Hypervolume analysis, or
decomposition-quality evaluation was performed.

## Frozen runtime

- Model: `nomic-ai/nomic-embed-code`
- Model and tokenizer revision: `9a0457648f060c4279d4a3982d2d27a4df6fac59`
- Backend and loader: Sentence Transformers / `SentenceTransformer`
- Pooling: model-packaged `last_token`
- Normalization: model-packaged L2 normalization
- Dimension: 3584
- Maximum sequence length: 32768
- Formal truncation: disabled in the embedding call
- Prompt name and query prompt: none / false
- Device, execution precision, and batch size: MPS, float16, batch 8
- Stored array dtype: float32
- Deterministic seed: 42

The runtime and encode arguments are reused from the frozen Stage 3A pipeline;
the only scientific input change is the frozen declaration-plus-method-body
text. Stage 3B did not use Stage 3A embeddings as a cache or overwrite any
Stage 3A artifact.

## Frozen inputs and outputs

Inputs are read only from
`data/semantic_text/declaration_method_body/<subject>/class_semantic_inputs.csv`.
The authoritative input aggregate hashes are recorded in
`reports/stage3_method_body/method_body_input_hashes.csv` and the generated
manifest.

Canonical outputs are isolated under
`data/embeddings/declaration_method_body/<subject>/`. Each subject contains
the saved embedding array, explicit class mapping, per-class embedding hashes,
metadata, and exact tokenizer-length report. The generation manifest is
`reports/stage3_method_body/embedding_generation_manifest.json`.

The generation source commit was
`33074fe5a2479b9d76605cd6a507c8a66c523a19`; validation was performed after the
diagnostic reporting fix recorded with this task. A second complete generation
used the clean temporary directory `/tmp/stage3b-embedding-repro.pCJKSX`.
Raw array bytes, mappings, per-class hashes, aggregate hashes, and tokenizer
reports were byte-identical across the two runs. Metadata matched after
excluding only run timestamps, elapsed time, output path, and run label.

## Stop boundary

The embedding stage ends after numerical validation, provenance checks,
collision diagnostics, Stage 3A-versus-Stage 3B same-class diagnostics, and
deterministic reproduction. The next graph-construction stage must create its
own artifacts; this task intentionally creates no graph or neighbour output.
