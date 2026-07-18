# Stage 3 reproducibility

## Canonical identity

- Experiment: `stage3_declaration_method_body`
- Representation: `declaration_method_body_v1`
- Subjects: JPetStore (24), DayTrader (53), Xerces (814)
- Seeds: validation seed 0 and formal seeds 1–29
- Graph: true-cosine top-3 with lexicographic tie-breaking and OR symmetrisation

The canonical experiment entry points are under
`experiments/05_stage3_declaration_method_body/`. Reusable semantic and
analysis logic is under `src/evo_ms/semantic/` and `src/evo_ms/analysis/`.

## Reproduction flow

The following commands describe the frozen flow. They are not an instruction
to regenerate accepted artifacts during repository maintenance:

```text
python scripts/stage3/run_stage3.py --help
python experiments/05_stage3_declaration_method_body/run.py --help
python scripts/stage3/validate_stage3.py --help
python experiments/05_stage3_declaration_method_body/run_validation.py --help
python experiments/05_stage3_declaration_method_body/run_formal.py --help
python experiments/05_stage3_declaration_method_body/analyze.py --help
```

Input, embedding, graph, and formal-result manifests record exact hashes,
configuration identity, model revision, class mapping, source commit, and
validation status. Reports are organised under `reports/stage3/` by audience:
tables, figures, analysis, provenance, and validation.

## Scientific non-change rule

Repository restructuring must not regenerate semantic inputs, embeddings,
semantic graphs, optimizer results, or formal seeds. The external pre-refactor
SHA-256 inventory and the final provenance ledger are used to verify byte
identity of accepted scientific artifacts after source and report moves.
