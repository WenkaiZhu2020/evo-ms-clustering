# Stage 3: Declaration + Method Body Semantic Extension

Stage 3 is the final semantic extension of the frozen Stage 2 experiment. It
uses the representation `declaration_method_body_v1` and the experiment ID
`stage3_declaration_method_body`.

The pipeline reads the isolated semantic text under
`data/semantic_text/declaration_method_body/`, saved embeddings under
`data/embeddings/declaration_method_body/`, and saved top-3 semantic graphs
under `data/semantic_graphs/declaration_method_body/`. The accepted optimizer
results remain under `results/<subject>/05_stage3_declaration_method_body/`.

The implementation boundary is `experiments/05_stage3_declaration_method_body/`.
Its only scripts are thin launchers under
`scripts/05_stage3_declaration_method_body/`; reusable numerical behaviour is
under `src/evo_ms/`.

The semantic objective is the frozen fourth objective. Structural objectives,
population, generations, seeds, projected Hypervolume, representative
selection, and statistical conventions remain unchanged from the formal
protocol. This repository does not treat an earlier development
representation as a second permanent experimental method.

See [method_contract.md](method_contract.md) for the scientific contract and
[reproducibility.md](reproducibility.md) for the reproducible command flow.
