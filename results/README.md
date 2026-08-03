# Results layout

Accepted machine-readable outputs are organised first by experimental stage,
then by subject scope. Scientific inputs and frozen semantic artifacts remain
under `data/`; human-readable interpretation is under `docs/<stage>/findings/`.

## Pre-experiment

```text
results/pre_experiment/subjects/<subject>/
  graph/
  clustering/
  comparison/
  calibration/   # DayTrader only
  sensitivity/   # Xerces-J only
```

These are diagnostic graph, calibration, and sensitivity outputs rather than
formal Stage 1 results.

## Stage 1

```text
results/stage1/subjects/<subject>/
  leiden_baseline/
    raw_reference_leiden/
    ssa_selected_leiden/
  seed_robustness/
```

`leiden_baseline/` contains the frozen comparison partitions and metadata;
`seed_robustness/` contains the multi-seed SSA-effect control.

## Stage 2

```text
results/stage2/
  subjects/<subject>/nsga/
    robustness_final_30seeds/
    convergence_diagnostic/
    diagnostics and historical run groups
  cross_subject/
    operating_profile/
    formal_statistics/
    diagnostics/
    sensitivity_analysis/
```

Formal thesis values use `robustness_final_30seeds/`, the frozen 5% profile in
`cross_subject/operating_profile/`, and the declared formal statistical tables.
Diagnostic and sensitivity directories are supporting evidence, not alternate
formal result sources.

## Stage 3

```text
results/stage3/
  subjects/<subject>/declaration_method_body/
    validation/seed_00/
    formal/seed_01..29/
  cross_subject/
    formal_statistics/
    stage2_comparison/
    preference_analysis/
  data_quality/
    semantic_input/
    embedding/
    method_body/
    semantic_graph/
  reproducibility_checks/
    semantic_input/
    embedding/
    semantic_graph/
    formal_runs/
    report/
  provenance/
```

- `cross_subject/` contains evidence combining JPetStore, DayTrader, and
  Xerces-J.
- `data_quality/` describes inputs, embeddings, method-body budgeting, and
  semantic graphs.
- `reproducibility_checks/` records hashes, seed validation, and deterministic
  report checks.
- `provenance/` records scientific identity, manifests, historical relocation,
  and legacy statistics that are never current inputs.

The canonical subject IDs are `jpetstore`, `daytrader`, and `xerces-j`.
