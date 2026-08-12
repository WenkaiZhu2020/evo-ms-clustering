# LLM-Guided Multi-Objective Microservice Decomposition

Class-level decomposition of Java monoliths using structural dependencies,
SSA-derived data-flow evidence, LLM-derived semantic relations, Leiden
community detection, and NSGA-II multi-objective search.

## Overview

This repository implements and preserves a three-stage experimental pipeline
for identifying candidate microservice partitions. It compares a graph
community-detection baseline with structure-only and semantic-guided
multi-objective search while retaining the configurations, accepted run
artefacts, derived analyses, and provenance used for dissertation reporting.

## Research pipeline

1. **Stage 1 — Leiden baseline.** Class-level type and call dependencies form
   the raw structural graph. SSA-derived return-value and argument-passing
   relations provide additional data-flow evidence for the enriched graph.
   Leiden supplies the frozen baseline partitions and robustness evidence.
2. **Stage 2 — structure-only NSGA-II.** Search optimises coupling, cohesion,
   and cluster-size imbalance over the structural graph. The retained Pareto
   fronts preserve alternative feasible decompositions rather than only one
   partition.
3. **Stage 3 — semantic-guided NSGA-II.** Declaration and bounded method-body
   evidence is embedded with `nomic-ai/nomic-embed-code` and converted into a
   semantic graph. The semantic cut objective extends Stage 2 to four
   objectives. For structural comparison, each retained four-dimensional
   Stage 3 front is projected to the original three structural objectives,
   deduplicated, and filtered for three-dimensional non-dominance.

## Experimental subjects

The primary experiments use JPetStore, DayTrader, and Xerces-J, with 30
accepted observations per subject where required by the formal protocol.
EasyMock and JFreeChart are supplementary subjects used only for descriptive
validation. They are not members of the primary inferential families; their
frozen evidence is retained on the corresponding validation branches and tags.

## Repository structure

| Path | Role |
| --- | --- |
| `src/` | Reusable extraction, graph, clustering, optimisation, semantic, evaluation, analysis, and visualisation code. |
| `experiments/` | Stage-specific Python entry points and deterministic post-processing. |
| `data/` | Extracted class-level inputs and frozen semantic text, embeddings, and graphs. |
| `results/` | Accepted subject runs, cross-subject analyses, statistics, and provenance manifests. |
| `configs/` | Subject, experiment, reproducibility, and visualisation contracts. |
| `reports/` | Current figure catalogue, source data, render sources, previews, and PDFs. |
| `tests/` | Unit, integration, architecture, provenance, reporting, and reproducibility checks. |
| `docs/` | Stage documentation, findings, and reproducibility guidance. |
| `scripts/` | Thin experiment, extraction, validation, and visualisation launchers. |
| `provenance/` | Repository-level lineage and integrity records. |

The primary experiment entry points are
`experiments/01_stage1_leiden_baseline/`,
`experiments/02_stage2_nsga_structure_only/`, and
`experiments/05_stage3_declaration_method_body/`.

## Reproducibility and provenance

The supported Python environment is specified by `pyproject.toml` and
`uv.lock`. Subject and experiment YAML files record fixed configurations and
seeds. Accepted experimental outputs are frozen; manifests, source hashes,
configuration snapshots, validation tests, and figure provenance record how
the reporting artefacts relate to those outputs. The Stage 3 embedding runtime
is additionally documented in `results/stage3/provenance/` and
`docs/stage3/reproducibility.md`.

These records support validation and deterministic post-processing of the
retained artefacts. Regenerating embeddings or optimisation runs can depend on
the recorded model/runtime environment and is not part of routine reporting
validation.

## Current operating-preference reporting

`BALANCE` is the primary dissertation operating preference. Candidates are
admitted when their proportional weighted-modularity loss from the current
front-best value is at most 5%; `BALANCE` then selects minimum imbalance, with
deterministic structural tie-breaking. `MODULARITY_ANCHOR` (MAX-Q) is retained
as a reference profile. `COUPLING`, `COHESION`, and `SEMANTIC` are descriptive
sensitivity profiles. Modularity loss relative to Leiden is a separate
descriptive comparison and is not the 5% admission denominator.

The authoritative selector-dependent reporting bundle is
`results/stage3/cross_subject/operating_preference_analysis/`.

## Visualisation and reporting outputs

The current figure registry is `reports/figures/manifest.json`, with figure
configuration in `configs/visualization/figures.yml`. Registered outputs are
stored under `reports/figures/pdf/`; their source data, render sources,
previews, and provenance records are kept in the adjacent `data/`, `source/`,
and `preview/` directories. Human-readable Stage 3 reporting notes are under
`docs/stage3/findings/`.

## Running and validation

With the repository environment already created, validate the current
operating-preference bundle without rewriting it:

```bash
.venv/bin/python experiments/05_stage3_declaration_method_body/build_operating_preference_analysis.py --check
```

Validate and list the current figure catalogue:

```bash
.venv/bin/python scripts/visualization/build_figures.py --validate-config
.venv/bin/python scripts/visualization/build_figures.py --list
```

Run the reporting, provenance, and selector checks:

```bash
.venv/bin/pytest \
  tests/test_preference_analysis_audit.py \
  tests/test_stage3_preference_analysis.py \
  tests/test_stage3_reporting_contract.py \
  tests/test_stage3_provenance.py \
  tests/test_stage3_reproducibility.py
```

Read `docs/stage3/reproducibility.md` before any intentional regeneration of
semantic or optimiser artefacts.

## Dissertation context

This repository accompanies an MSc dissertation on class-level candidate
microservice decomposition using structural, data-flow, and LLM-derived
semantic evidence.
