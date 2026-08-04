# Evolutionary Software Clustering — Final Stage 3 Repository

This repository contains the complete three-stage experimental pipeline for
evolutionary class-level software clustering. The canonical final branch is
`stage3-Declaration+Method-Body`, which adds declaration and normalized method
body semantic evidence to the frozen structural experiments.

## Experimental stages

1. **Stage 1 — Leiden baseline.** Builds class-level structural and SSA-enriched
   graphs, runs Leiden clustering, and records the frozen baseline partitions
   and seed-robustness evidence.
2. **Stage 2 — structure-only NSGA-II.** Optimizes coupling, cohesion, and
   cluster-size imbalance on the frozen raw structural graph. Its formal
   30-seed fronts and canonical modularity-band operating profiles are retained
   as the structural comparison baseline.
3. **Stage 3 — Declaration + Method Body semantic extension.** Uses the frozen
   `declaration_method_body_v1` representation, code-model embeddings, and a
   true-cosine top-3 semantic graph. Four-objective NSGA-II optimizes the three
   Stage 2 structural objectives plus semantic cut ratio.

The three subject systems are JPetStore, DayTrader, and Xerces-J. Each formal
stage uses 30 accepted seed outputs per subject where required by its protocol.
For Stage 3, seed 0 is the accepted validation run and seeds 1–29 are the formal
runs, giving 90 validated Stage 3 runs in total.

## Stage 3 scientific contract

- Experiment ID: `stage3_declaration_method_body`
- Representation: `declaration_method_body_v1`
- Subjects: JPetStore (24 classes), DayTrader (53), Xerces-J (814)
- Embedding model: `nomic-ai/nomic-embed-code` at the pinned revision in the
  Stage 3 configuration
- Semantic graph: true-cosine top-3, lexicographic tie-breaking, OR
  symmetrisation
- Search: four-objective NSGA-II
- Comparison: project the Stage 3 front to the original three structural
  objectives and reuse the frozen Stage 2 selection and Hypervolume contracts

The accepted semantic inputs, embeddings, semantic graphs, optimizer outputs,
and provenance are immutable scientific artifacts during repository
maintenance. Regeneration commands require explicit output destinations and do
not overwrite accepted artifacts by default.

## Main locations

| Purpose | Location |
| --- | --- |
| Stage 1 experiment | `experiments/01_stage1_leiden_baseline/` |
| Stage 2 experiment | `experiments/02_stage2_nsga_structure_only/` |
| Stage 3 experiment | `experiments/05_stage3_declaration_method_body/` |
| Stage 3 launchers | `scripts/05_stage3_declaration_method_body/` |
| Reusable implementation | `src/evo_ms/` |
| Stage 3 configuration | `configs/experiments/05_stage3_declaration_method_body.yml` |
| Semantic text | `data/semantic_text/declaration_method_body/` |
| Embeddings | `data/embeddings/declaration_method_body/` |
| Semantic graphs | `data/semantic_graphs/declaration_method_body/` |
| Pre-experiment results | `results/pre_experiment/subjects/<subject>/` |
| Stage 1 results | `results/stage1/subjects/<subject>/` |
| Stage 2 subject results | `results/stage2/subjects/<subject>/nsga/` |
| Stage 2 cross-subject results | `results/stage2/cross_subject/` |
| Per-subject Stage 3 results | `results/stage3/subjects/<subject>/declaration_method_body/` |
| Stage 3 cross-subject analysis | `results/stage3/cross_subject/` |
| Stage 3 data quality | `results/stage3/data_quality/` |
| Stage 3 reproducibility checks | `results/stage3/reproducibility_checks/` |
| Stage 3 provenance | `results/stage3/provenance/` |
| Human-readable Stage 3 findings | `docs/stage3/findings/` |
| Stage 3 reproducibility guide | `docs/stage3/reproducibility.md` |

## Environment

The final repository has one supported Python environment for Stage 1–3:
`pyproject.toml` plus `uv.lock`. It requires Python 3.13.7. From the repository
root run:

```bash
uv sync --frozen
```

The formal embedding configuration records an Apple Silicon MPS runtime. Saved
artifacts can be inspected and validated without regenerating embeddings or
rerunning the formal NSGA-II experiment.

## Validation and common commands

Run the complete test suite:

```bash
uv run --frozen pytest
```

Inspect the supported Stage 3 commands:

```bash
uv run --frozen python experiments/05_stage3_declaration_method_body/prepare_semantic.py --help
uv run --frozen python experiments/05_stage3_declaration_method_body/run.py --help
uv run --frozen python experiments/05_stage3_declaration_method_body/run_robustness.py --help
uv run --frozen python experiments/05_stage3_declaration_method_body/analyze.py --help
uv run --frozen python experiments/05_stage3_declaration_method_body/synchronize_stage2_operating_profile.py --help
```

Equivalent shell launchers are available under
`scripts/05_stage3_declaration_method_body/`. Read
`docs/stage3/reproducibility.md` before any regeneration or optimizer run.

## Repository structure

```text
configs/       Subject and experiment contracts.
data/          Extracted structural data and frozen semantic artifacts.
docs/          Stage documentation, reproducibility guidance, and findings.
experiments/   Stage-specific orchestration and analysis entry points.
results/       Accepted per-subject and cross-subject experiment evidence.
provenance/    Repository lineage, migration inventories, and integrity ledgers.
scripts/       Thin shell launchers and extraction helpers.
src/           Reusable extraction, graph, optimization, semantic, and analysis code.
tests/         Unit, integration, architecture, provenance, and reproducibility tests.
tools/         Java Soot/Shimple extractor.
```
