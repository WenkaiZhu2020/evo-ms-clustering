# Stage 3 reproducibility

## Canonical identity

- Experiment: `stage3_declaration_method_body`
- Representation: `declaration_method_body_v1`
- Subjects: JPetStore (24), DayTrader (53), Xerces (814)
- Seeds: validation seed 0 and formal seeds 1–29
- Graph: true-cosine top-3 with lexicographic tie-breaking and OR symmetrisation

The canonical experiment entry points are under
`experiments/05_stage3_declaration_method_body/`. Thin shell launchers are
under `scripts/05_stage3_declaration_method_body/`. Reusable semantic,
optimization, evaluation, and analysis logic is under `src/evo_ms/`.

## Reproduction flow

The following commands describe the frozen flow. They are not an instruction
to regenerate accepted artifacts during repository maintenance:

```text
scripts/05_stage3_declaration_method_body/prepare_semantic.sh --help
scripts/05_stage3_declaration_method_body/run_stage3.sh --help
python experiments/05_stage3_declaration_method_body/run.py --help
scripts/05_stage3_declaration_method_body/run_robustness.sh --help
scripts/05_stage3_declaration_method_body/analyze.sh --help
python experiments/05_stage3_declaration_method_body/analyze.py --help
python experiments/05_stage3_declaration_method_body/analyze.py --check-reporting
```

Input preparation is a real command and must use a temporary output directory.
It invokes the isolated Soot extractor and compares generated declaration and
semantic-text hashes with the accepted final input. It never overwrites
accepted semantic text by default. Raw project trees and compiled classes are
external local inputs; a missing source directory is an explicit failure.

Graph provenance has two layers. Historical source commits and original config
hashes describe accepted artifact generation. Current regeneration checks the
normalized scientific contract in
`results/cross_subject/05_stage3_declaration_method_body/provenance/final_graph_compatibility_contract.json`; current
Git HEAD is not compared with the historical graph-generation commit.

Input, embedding, graph, and formal-result manifests record exact hashes,
configuration identity, model revision, class mapping, source commit, and
validation status. Machine-readable reports are organised under
`results/cross_subject/05_stage3_declaration_method_body/`; human-readable
findings and thesis figures are under
`docs/stage3/results/`. Historical provenance may
still contain the original `reports/stage3` path by design.

`--check-reporting` deterministically rebuilds the final six-row statistical
family and Chapter 4.3 generated blocks in memory, then fails if committed
reporting outputs differ. `--write-reporting` is the explicit reporting-only
update mode. It reads accepted artifacts and never invokes semantic preparation
or either optimizer.

## Scientific non-change rule

Repository restructuring must not regenerate semantic inputs, embeddings,
semantic graphs, optimizer results, or formal seeds. The external pre-refactor
SHA-256 inventory and the final provenance ledger are used to verify byte
identity of accepted scientific artifacts after source and report moves.
