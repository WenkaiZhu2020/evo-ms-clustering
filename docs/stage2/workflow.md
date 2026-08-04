# Stage 2 Workflow

This document describes the raw-only Stage 2 pipeline and the Stage 1 reuse
points. Reuse means importing or reading existing Stage 1 artifacts without
changing Stage 1 behavior, frozen outputs, or existing tests.

## Pipeline Overview

```text
data/extracted/<subject>/
  -> load_extracted_subject
  -> build_raw_edges                 # G_raw, raw_weight
  -> NSGA-II search through pymoo
       initialization: raw-Leiden seed, raw-graph perturbations, graph groupings,
                       then random fill
       encoding: integer label vector over classes
       objectives: coupling down, cohesion up, imbalance down
       constraints: max cluster ratio, minimum cluster count
  -> Pareto front across fixed random seeds
  -> select canonical operating profile post hoc:
       feasible retained front -> 5% modularity-loss band -> deterministic
       structural tie-break rule
  -> post-hoc evaluation only
       modularity, Hypervolume, MoJoFM, Pairwise F1
  -> compare selected solution with frozen Stage 1 raw_reference_leiden
  -> frozen formal results/stage2/subjects/<subject>/nsga/robustness_final_30seeds/
```

The Stage 2 runner writes Pareto fronts, label vectors, post-hoc metrics,
Stage 1 raw Leiden comparison tables, Hypervolume summaries, and metadata.
The retired selected-solution files are not an active result interface. For
the frozen formal results, the canonical
operating solution is the 5% relative modularity-band profile in
`results/stage2/cross_subject/operating_profile/`; the former
max-weighted-modularity selected-solution artifacts are retired.

## Input Rule

Stage 2 rebuilds `G_raw` from `data/extracted/<subject>/`, matching the Stage 1
runner. It must not read mutable graph artifacts from `results/`.

## Stage 1 Reuse Points

| Pipeline step | Stage 1 symbol or artifact | File | Role |
| --- | --- | --- | --- |
| Load input | `load_extracted_subject` | `extraction/dependency_extractor.py` | Load and validate normalized CSV inputs. |
| Build raw graph | `build_raw_edges` | `graph/raw_graph_builder.py` | Produce raw structural edge weights. |
| Objective primitive | `_edge_weight_split` | `evaluation/partition_metrics.py` | O(E) internal/external edge-weight split. |
| Raw Leiden baseline | `results/stage1/subjects/<subject>/leiden_baseline/raw_reference_leiden/` | frozen Stage 1 results | Comparison target. |
| Solution comparison | `partition_similarity` | `evaluation/partition_metrics.py` | ARI/NMI against frozen raw Leiden. |
| Reference check | `load_reference_mapping`, `calculate_reference_metrics` | `evaluation/reference_metrics.py` | DayTrader-only post-hoc MoJoFM/F1 checks. |

## Stage 2 Modules

| Module | Role |
| --- | --- |
| `src/evo_ms/optimization/encoding.py` | Label-vector conversion, partition DataFrame conversion, and canonical relabeling. |
| `src/evo_ms/optimization/objectives.py` | Three structural objectives and hard anti-degeneration constraints. |
| `src/evo_ms/optimization/problem.py` | Lazy-import pymoo Problem wrapper with `F = [coupling, -cohesion, imbalance]`. |
| `experiments/02_stage2_nsga_structure_only/run.py` | Runner that wires raw inputs, seeded initialization, multi-seed search, Pareto output, and raw Leiden comparison. |

## Output

The frozen formal output layer is:

```text
results/stage2/subjects/<subject>/nsga/robustness_final_30seeds/
```

Expected files:

- `pareto_front.csv`: objective values, feasibility, labels, and seed provenance.
- `pareto_labels.csv.xz`: class-to-cluster assignments for each Pareto solution (xz-compressed; long-format and large for big subjects). Read with `pandas.read_csv(..., compression="xz")`.
- `run_metrics.json`: formal per-seed search summary.
- `run_metadata.json`: formal input, configuration, environment, and source provenance.
- `robustness_manifest.json`: formal 30-seed completeness and integrity manifest.

The former 10-seed `raw/` derived summaries were historical and have been
removed. A compact set of source front/label/metadata files remains only for
historical provenance. Derived selected-profile metrics are maintained
separately under `results/stage2/cross_subject/operating_profile/`.

`pareto_front.csv` records seeded-initialization provenance:

- `is_injected_seed`
- `injected_seed_name`
- `injected_seed_category`

These columns support reporting about whether the Pareto front contains newly
evolved non-seed solutions, not only injected heuristic seeds.

The canonical 30-seed operating-profile metrics and provenance are maintained
at `results/stage2/cross_subject/operating_profile/`
`canonical_operating_profile_metrics_per_seed.csv`. Refresh them with
`experiments/02_stage2_nsga_structure_only/refresh_modularity_band_downstream.py`;
the command is post hoc only and does not rerun any seed.
