# Cross-Subject Stage 2 Results

This directory contains evidence aggregated across JPetStore, DayTrader, and
Xerces-J. Subject-specific formal outputs remain under:

```text
results/stage2/subjects/<subject>/nsga/robustness_final_30seeds/
```

## Contents

- `operating_profile/`: frozen 5% modularity-band operating solution per seed,
  plus post-hoc 1%, 3%, 5%, and 10% band-response profiles under
  `sensitivity/`. The 5% profile remains canonical.
- `formal_statistics/`: declared paired statistics, current family audit, and
  the machine-readable inventory of superseded output cleanup decisions.
- `diagnostics/daytrader_tradeoff/`: current-profile structural trade-off
  diagnostics; these are supporting evidence rather than alternate results.
- `sensitivity_analysis/max_cluster/`: the separate max-cluster constraint
  sensitivity evaluated under the current 5% selector contract.

## Relocation Note

Pre-final cross-subject robustness tables from the former
`results/stage2_robustness/` path were moved to the external
`evo-ms-clustering-stage2-diagnostics-archive` repository. They are retained
there only as superseded provenance and are not final Stage 2 evidence.
Historical command logs and audit manifests may retain their former paths
because they record the location at the time a diagnostic was generated.

Final conclusions must use the canonical profile refresh manifest,
`operating_profile/`, `formal_statistics/`, and the subject-level
`robustness_final_30seeds/` outputs. Diagnostic and sensitivity subtrees are
explicitly supporting evidence, and the max-cluster study is distinct from the
modularity-band sensitivity dimension.
