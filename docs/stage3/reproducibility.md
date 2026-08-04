# Stage 3 reproducibility

## Canonical identity

- Experiment: `stage3_declaration_method_body`
- Representation: `declaration_method_body_v1`
- Subjects: JPetStore (24), DayTrader (53), Xerces-J (814; semantic ID `xerces`)
- Seeds: validation seed 0 and formal seeds 1–29
- Graph: true-cosine top-3 with lexicographic tie-breaking and OR symmetrisation

The canonical experiment entry points are under
`experiments/05_stage3_declaration_method_body/`. Thin shell launchers are
under `scripts/05_stage3_declaration_method_body/`. Reusable semantic,
optimization, evaluation, and analysis logic is under `src/evo_ms/`.

## Supported environment

The final branch has one supported environment for all three stages. Install it
from the repository root with the frozen uv lock:

```bash
uv sync --frozen
```

Run validation commands through `uv run --frozen`. The Stage 2 branch remains
the authority for the environment that generated the historical Stage 2
artifacts; the final lock is a compatible Stage 1--3 reproduction and
inspection environment, not a rewritten historical claim.

## Reproduction flow

The following commands describe the frozen flow. They are not an instruction
to regenerate accepted artifacts during repository maintenance:

```text
uv run --frozen scripts/05_stage3_declaration_method_body/prepare_semantic.sh --help
uv run --frozen scripts/05_stage3_declaration_method_body/run_stage3.sh --help
uv run --frozen python experiments/05_stage3_declaration_method_body/run.py --help
uv run --frozen scripts/05_stage3_declaration_method_body/run_robustness.sh --help
uv run --frozen scripts/05_stage3_declaration_method_body/analyze.sh --help
uv run --frozen python experiments/05_stage3_declaration_method_body/analyze.py --help
uv run --frozen python experiments/05_stage3_declaration_method_body/analyze.py --check-reporting
```

Input preparation is a real command and must use a temporary output directory.
It invokes the isolated Soot extractor and compares generated declaration and
semantic-text hashes with the accepted final input. It never overwrites
accepted semantic text by default. Raw project trees and compiled classes are
external local inputs; a missing source directory is an explicit failure.

Graph provenance has two layers. Historical source commits and original config
hashes describe accepted artifact generation. Current regeneration checks the
normalized scientific contract in
`results/stage3/provenance/final_graph_compatibility_contract.json`; current
Git HEAD is not compared with the historical graph-generation commit.

Input, embedding, graph, and formal-result manifests record exact hashes,
configuration identity, model revision, class mapping, source commit, and
validation status. Machine-readable reports are organised under
`results/stage3/`; human-readable
findings and thesis figures are under
`docs/stage3/findings/`. Historical provenance may
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
