# Transmission of Additional Evidence across the Candidate Microservice Decomposition Pipeline

This repository contains the prototype and retained evidence for Wenkai Zhu's
MSc dissertation, *Transmission of Additional Evidence across the Candidate
Microservice Decomposition Pipeline*.

Identifying candidate microservices from a Java monolith is difficult because
different evidence sources can support different service boundaries, and new
input evidence does not necessarily remain influential throughout a
decomposition pipeline. The prototype therefore examines both whether
additional evidence supplies new class-level relations and whether its effect
remains visible at the objective, candidate, and final-selection levels.

The repository implements a three-stage candidate microservice decomposition
study. Stage 1 is a graph community-detection comparison; Stages 2 and 3 use
multi-objective evolutionary search. It does not claim that all three stages
use evolutionary search.

## Research pipeline

1. **Stage 1 — structural and SSA evidence with Leiden.** Type dependencies and
   method calls form the raw structural graph. SSA-derived return-value and
   argument-passing relations provide an enriched evidence graph. Leiden is
   applied to the raw and SSA-enriched graphs for comparison and seed-robustness
   analysis.
2. **Stage 2 — structure-only NSGA-II.** The raw structural graph is fixed.
   NSGA-II searches for candidate decompositions using coupling, cohesion, and
   cluster-size imbalance objectives. Retained Pareto candidate sets preserve
   the available structural trade-offs. **Balance** is the primary operating
   preference used to select a representative candidate from the retained
   front.
3. **Stage 3 — semantic extension.** Stage 3 keeps the same structural search
   design and adds a separate graph derived from LLM-based semantic evidence.
   Semantic loss, `f_sem`, is the fourth objective. For Stage 2–Stage 3
   comparison, each retained four-objective Stage 3 front is projected into the
   three structural objectives, deduplicated, and filtered to form the projected
   structural front.

The dissertation finds that SSA-derived and semantic evidence add class-level
relations not already present in the raw structural graph, but that their later
effect is weaker and can change across the objective, candidate, and selection
levels. The retained artefacts in this repository support inspection of those
pipeline stages without requiring the submitted stochastic experiments to be
rerun.

## Research subjects

Primary subjects:

| Subject | Retained classes |
| --- | ---: |
| JPetStore | 24 |
| DayTrader | 53 |
| Xerces-J | 814 |

Supplementary descriptive-validation subjects:

| Subject | Retained classes |
| --- | ---: |
| EasyMock | 105 |
| JFreeChart | 635 |

The supplementary subjects provide descriptive validation and are not members
of the primary inferential families. Their frozen evidence is preserved on the
`stage1-validation-frozen`, `stage2-validation-frozen`, and
`stage3-validation-frozen` tags. The dissertation submission package combines
that tagged evidence with the final primary-subject working tree.

## Main experimental scale

- Stage 1 robustness: 30 seeds per primary subject for both the raw and
  SSA-enriched graphs.
- Stage 2: 30 retained runs per primary subject.
- Stage 3: 30 retained runs per primary subject.
- Supplementary validation: 10 retained Stage 2 runs and 10 retained Stage 3
  runs per supplementary subject.

## Repository structure

| Path | Final repository role |
| --- | --- |
| `src/` | Reusable extraction, graph, clustering, optimisation, semantic, evaluation, analysis, and visualisation code. |
| `experiments/` | Stage-specific Python experiment and deterministic post-processing entry points. |
| `configs/` | Subject scopes, experiment definitions, reproducibility records, and visualisation configuration. |
| `data/` | Retained extracted inputs plus semantic text, embeddings, semantic graphs, and reference evidence. |
| `results/` | Frozen Stage 1–3 runs, fronts, selected candidates, cross-subject analyses, statistics, and provenance. |
| `reports/` | Derived reporting artefacts, figure data, render sources, PDF/SVG outputs, provenance, and the figure manifest. |
| `tests/` | Unit, integration, architecture, provenance, reporting, and reproducibility checks. |
| `scripts/` | User-facing extraction, experiment, verification, and visualisation launchers. |
| `tools/` | The Java 17 Soot/Shimple extractor used to produce structural and SSA evidence. |
| `docs/` | Method, findings, and reproducibility documentation. |
| `provenance/` | Repository-level lineage and integrity records. |

The main experiment implementations are under
`experiments/01_stage1_leiden_baseline/`,
`experiments/02_stage2_nsga_structure_only/`, and
`experiments/05_stage3_declaration_method_body/`.

## Experimental evidence and frozen outputs

`data/` contains retained input and evidence artefacts. `results/` contains the
frozen experimental outputs, candidate/front data, selected-solution evidence,
statistics, and cross-stage analyses used by the dissertation. `reports/`
contains derived reporting artefacts, dissertation-ready figures, their source
data, provenance records, and `reports/figures/manifest.json`.

The submitted repository retains the experimental outputs used for the
dissertation. Formal optimisation outputs are evidence, not disposable build
products. Routine reporting and figure regeneration should read these retained
outputs rather than silently replacing them with newly rerun stochastic
experiments. Where supported, later reporting can be rebuilt deterministically
from the frozen outputs without rerunning Stage 1, Stage 2, or Stage 3.

The current selector-dependent reporting bundle is
`results/stage3/cross_subject/operating_preference_analysis/`. Balance is the
primary dissertation operating preference. Modularity-anchor, coupling,
cohesion, and semantic preferences are retained for descriptive sensitivity
analysis.

## Retained environment

The final supported environment and the hardware recorded in the dissertation
are:

- macOS 26.5, arm64;
- Apple M5 Pro, 18-core CPU and 20-core integrated GPU;
- 48 GB unified memory;
- Python 3.13.7;
- pymoo 0.6.2;
- NumPy 2.4.4;
- PyTorch 2.13.0;
- sentence-transformers 5.6.0;
- transformers 5.14.1;
- `nomic-ai/nomic-embed-code`, revision
  `9a0457648f060c4279d4a3982d2d27a4df6fac59`.

`pyproject.toml`, `uv.lock`, and
`configs/reproducibility/environments.json` define the supported final Python
environment. With `uv` installed, create the locked environment and activate it
with:

```bash
uv sync --frozen
source .venv/bin/activate
```

The supported final environment records `igraph` 1.0.0 and `leidenalg` 0.12.0.
The exact historical versions used when the original Stage 1 formal outputs
were computed were not retained, so these supported versions must not be
presented as retrospective Stage 1 runtime versions.

The supplementary-subject source identities and run policy are recorded in
`configs/reproducibility/validation_subjects.lock.yaml`; their captured build
and extraction environment is recorded in
`configs/reproducibility/validation_environment.snapshot.yaml`.

## Execution and reproducibility

### Read-only repository verification

The normal integrity check does not run an experiment:

```bash
PYTHONPATH=src python scripts/reproducibility/verify.py --stage all
```

Validate the retained Stage 3 operating-preference bundle without rewriting it:

```bash
PYTHONPATH=src python experiments/05_stage3_declaration_method_body/build_operating_preference_analysis.py --check
```

Run the test suite:

```bash
PYTHONPATH=src pytest
```

### Deterministic reporting and figure generation

Validate or list the figure catalogue:

```bash
PYTHONPATH=src python scripts/visualization/build_figures.py --validate-config
PYTHONPATH=src python scripts/visualization/build_figures.py --list
```

Regenerate one registered figure from its retained inputs:

```bash
PYTHONPATH=src python scripts/visualization/build_figures.py --figure FIGURE_ID
```

Use `--output-dir` when a separate verification output is required. Figure IDs
are obtained from `--list`. The figure registry and hashes are recorded in
`reports/figures/manifest.json`.

### Formal experiment entry points

The commands below are execution entry points and may create new stochastic
outputs. They are documented for reproducibility, but they are not required for
normal inspection or reporting from the submitted frozen results.

Extraction requires the relevant Java source checkout under
`data/raw_projects/<subject>/`. Subject-specific preparation and extraction
wrappers are provided, for example:

```bash
bash scripts/extraction/prepare_jpetstore.sh
bash scripts/extraction/extract_soot_jpetstore.sh
```

Equivalent wrappers exist for DayTrader and Xerces-J. Formal Stage 1 wrappers
are subject-specific:

```bash
PYTHONPATH=src python experiments/01_stage1_leiden_baseline/run.py --subject jpetstore
PYTHONPATH=src python experiments/01_stage1_leiden_baseline/run.py --subject daytrader
PYTHONPATH=src python experiments/01_stage1_leiden_baseline/run.py --subject xerces-j
```

Stage 2 and Stage 3 implementations expose their accepted arguments through:

```bash
PYTHONPATH=src python experiments/02_stage2_nsga_structure_only/run.py --help
PYTHONPATH=src python experiments/02_stage2_nsga_structure_only/run_robustness.py --help
PYTHONPATH=src python experiments/05_stage3_declaration_method_body/prepare_semantic.py --help
PYTHONPATH=src python experiments/05_stage3_declaration_method_body/run.py --help
PYTHONPATH=src python experiments/05_stage3_declaration_method_body/run_robustness.py --help
```

Accepted formal result directories are protected evidence. Any intentional
rerun must use a separate output location and must not overwrite the retained
results. Read `docs/stage3/reproducibility.md` before regenerating semantic or
optimiser artefacts.

## Repository

Canonical GitHub repository:
https://github.com/WenkaiZhu2020/evo-ms-clustering
