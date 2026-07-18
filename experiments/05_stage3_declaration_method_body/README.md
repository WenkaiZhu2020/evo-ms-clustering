# Stage 3: Declaration + Method Body Semantic Extension

This is the canonical final Stage 3 experiment. It uses the frozen
`declaration_method_body_v1` representation and the accepted semantic inputs,
embeddings, graphs, and formal results. The runner delegates reusable logic
to `src/evo_ms`; it does not define a second declaration-only experiment.

Validation-only commands read saved artifacts. Embedding, graph, and formal
generation commands remain explicitly separate and must not overwrite the
accepted artifact roots.
