# Final Stage 3 provenance boundary

The accepted experiment is `stage3_declaration_method_body` with
representation `declaration_method_body_v1`. Runtime code reads only the
final declaration-plus-method-body input, embedding, graph, and saved result
namespaces, together with the frozen Stage 2 structural inputs.

Before repository restructuring, an external SHA-256 inventory was recorded
at `/tmp/stage3-pre-refactor-hashes-20260718.json`. The inventory covers final
semantic inputs, final embeddings, final graphs, validation seed 0, formal
seeds 1--29, saved Stage 2 results, and valid reference mappings. Its recorded
digest is preserved in the companion JSON file. The inventory is outside Git
so that it remains independent of source-tree moves and deletions.

Restructuring may change source paths, wrappers, documentation, and reports.
It must not change any file covered by the inventory. A final verification
must report every covered file as byte-identical.
