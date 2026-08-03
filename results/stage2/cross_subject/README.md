# Cross-Subject Stage 2 Results

This directory contains evidence aggregated across JPetStore, DayTrader, and
Xerces-J. Subject-specific formal outputs remain under:

```text
results/stage2/subjects/<subject>/nsga/robustness_final_30seeds/
```

## Contents

- `operating_profile/`: frozen 5% modularity-band operating solution per seed.
- `formal_statistics/`: declared paired statistics and summary evidence.
- `diagnostics/`: supporting diagnostics that are not alternate formal results.
- `sensitivity_analysis/`: post-hoc sensitivity evidence.

## Relocation Note

Pre-final cross-subject robustness tables from the former
`results/stage2_robustness/` path were moved to the external
`evo-ms-clustering-stage2-diagnostics-archive` repository. They are retained
there only as superseded provenance and are not final Stage 2 evidence.
Historical command logs and audit manifests may retain their former paths
because they record the location at the time a diagnostic was generated.

Final conclusions must use `operating_profile/`, `formal_statistics/`, and the
subject-level `robustness_final_30seeds/` outputs. Diagnostic and sensitivity
subtrees are explicitly supporting evidence.
