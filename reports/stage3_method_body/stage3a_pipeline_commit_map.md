# Stage 3A pipeline commit map for Stage 3B reuse

Stage 3B starts from the exact `stage3-declaration-final` commit. This map
records the Stage 3A implementation sequence and the action taken for the
isolated exploratory extension.

| Pipeline stage | Stage 3A commit(s) | Stage 3A inputs | Stage 3A outputs | Stage 3B action |
|---|---|---|---|---|
| Semantic input construction | `423243f`, `1724498`, `48cf46` | Soot/extracted class declarations and frozen method contract | `data/semantic_inputs/*_class_declarations.csv` | extend input only; preserve declaration bytes |
| Input-quality validation | `d2ba96d`, `078e04c` | Stage 3A declaration CSVs and pinned tokenizer | `reports/stage3/input_quality_summary.md` and quality artifacts | rerun validation on isolated Body V1 inputs |
| Toolchain/reproducibility freeze | `b05e094`, `a8b03d0`, `26e8482` | Python/runtime/model/tokenizer contracts | requirements, runtime records, verifier | reuse unchanged |
| Embedding generation | `c4c8e92` | Stage 3A semantic text and frozen Nomic runtime | `results/*/04_stage3_semantic/embeddings/` | regenerate derived artifact in isolated Stage 3B namespace |
| Embedding-quality validation | `ecb3b20`, `2343862` | saved float32 embeddings | quality and similarity diagnostics | rerun validation; compare collisions descriptively |
| Semantic graph construction | `e876755`, `7b8062c` | embeddings, class IDs, frozen k=3 graph contract | `results/*/04_stage3_semantic/graph/` | regenerate derived artifact in isolated Stage 3B namespace |
| Graph-quality/random baseline | `9f9c7fe`, `f0cec25` | Stage 3A graph and frozen structural/reference diagnostics | graph quality, random-baseline, go/no-go reports | rerun validation with isolated graph; no scientific tuning |
| Four-objective NSGA-II | `b228927`, `d819b2d` | raw graph, semantic graph, frozen Stage 2 optimizer | Stage 3A four-objective runner and projection | reuse unchanged; only graph/input path changes |
| Single-seed validation | `fac74e5` | seed 0 and frozen validation gates | `reports/stage3/day5_single_seed_validation.md` | rerun seed 0 against isolated Body V1 graph |
| Pilot execution | `4109bf7`, `f0cec25` | fixed pilot seeds and Stage 3A formal configuration | pilot validation summaries | rerun fixed pilot seeds 0–4 for engineering only |
| Formal 30-seed execution | seed-result commits `241a2a8` through `26231b6` | frozen Stage 3A inputs and seed IDs 0–29 | `results/*/04_stage3_semantic/{validation,formal}/` | rerun isolated Stage 3B formal seeds; do not cherry-pick |
| Formal validation | `d3abbc8`, `d9dd552`, `4109bf7` | all saved formal seed outputs | inventory, summaries, alignment reports | reuse validator architecture on Stage 3B paths |
| Stage 2 vs Stage 3 paired analysis | `bb546ac`, `698f38d`, `b6ada92`, `5ae6d19` | saved Stage 2 and Stage 3A representatives | paired CSVs, statistics, report, manifest | reuse implementation; separate Stage 3B-vs-Stage 3A family |
| External saved-partition evaluation | `8bc51eb`, `963f456`, `bf42a01` | saved partitions and valid DayTrader reference | external evaluation CSV and updated paired reports | reuse implementation for Stage 3B comparisons |

The Stage 3A implementation, graph settings, model runtime, optimizer,
selection rule, and validation standards are reused unchanged. Only the
representation-specific input/embedding/graph/result namespaces and the
corresponding exploratory comparisons are regenerated.
