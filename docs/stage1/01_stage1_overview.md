
# Stage 1 Overview

Stage 1 is the first implemented research stage. It evaluates class-level extraction, graph construction, raw-vs-SSA comparison, and Leiden baseline profiles.

It does not claim that the generated clusters are final microservice boundaries. Its role is to establish a reproducible structural baseline before the later NSGA-II and semantic stages.

## Experiment Layers

| Layer | Role | Output |
| --- | --- | --- |
| Pre-experiment | diagnostics, calibration, and sensitivity analysis | `results/<subject>/00_pre_experiment/` |
| Formal Stage 1 | frozen Leiden baseline profiles | `results/<subject>/01_stage1_leiden_baseline/` |

The Pre-experiment layer is used to inspect how graph settings affect the result. Its outputs may change across parameter runs.

The formal Stage 1 layer uses fixed profiles. These profiles are retained as reproducible comparison targets for later stages.

## Graph Settings

| Graph | Evidence | Weight Column |
| --- | --- | --- |
| `G_raw` | type dependencies and method calls | `raw_weight` |
| `G_ssa` | `G_raw` plus scoped return-value and argument-passing flows | `g_ssa_weight` |

`G_raw` provides the basic structural representation.

`G_ssa` adds selected SSA-derived flow evidence. This evidence is treated as a controlled extension rather than an assumed improvement.

## Subject Roles

| Subject | Role |
| --- | --- |
| JPetStore | small pipeline-validation case |
| DayTrader | calibration case with reference mapping |
| Xerces-J | larger-scale sensitivity case |

JPetStore is used to verify the complete pipeline. DayTrader supports reference-based calibration. Xerces-J is used to inspect scale and sensitivity under the same workflow.

CargoTracker is inactive in the current subject set. PiggyMetrics is not used as an input subject.

## Frozen Leiden Profiles

| Profile | Graph Type | Lambda | Resolution | Seed | Role |
| --- | --- | ---: | ---: | ---: | --- |
| `raw_reference_leiden` | raw | 0.0 | 1.25 | 42 | selected raw structural reference |
| `ssa_selected_leiden` | ssa | 0.25 | 1.5 | 42 | selected non-zero SSA comparison profile |

The raw profile remains the stronger structural reference in the current DayTrader calibration.

The selected SSA profile is still retained because it provides a controlled non-zero setting for evaluating the effect of behavioural enrichment.

Both formal profiles use seed 42 for reproducibility; Stage 1 does not claim multi-seed stability.

## Link to Later Stages

Stage 2 should compare NSGA-II results against the frozen Leiden profiles rather than against mutable diagnostic runs.

Stage 3 can then introduce semantic evidence as an additional information channel.
