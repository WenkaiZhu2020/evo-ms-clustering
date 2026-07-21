# Cross-Subject Stage 2 Results

This directory follows the canonical results layout:

```text
results/<scope>/<stage>/<artifact-kind>/
```

`cross_subject` is the scope for evidence aggregated across JPetStore,
DayTrader, and Xerces-J. Subject-specific formal outputs remain under:

```text
results/<subject>/03_stage2_nsga/robustness_final_30seeds/
```

## Contents

- `final_statistics/`: final paired statistics and final-aligned post-hoc
  diagnostics derived from the formal 30-seed outputs.
- `final_statistics/` is the only cross-subject Stage 2 evidence directory in
  this formal repository.
- `final_statistics/historical_output_cleanup_inventory.csv`: machine-readable
  record of each deleted historical/failed output and retained historical
  evidence.
- `modularity_band/sensitivity/`: post-hoc 1%, 3%, 5%, and 10% band response
  profiles, summaries, transitions, and figures; the 5% row remains canonical.
- `final_statistics/max_cluster_posthoc_sensitivity_current_band/`: separate
  max-cluster constraint sensitivity under the current 5% selector contract.

## Relocation Note

Pre-final cross-subject robustness tables from the former
`results/stage2_robustness/` path were moved to the external
`evo-ms-clustering-stage2-diagnostics-archive` repository. They are retained
there only as superseded provenance and are not final Stage 2 evidence.
Historical command logs and audit manifests that were only tied to removed
diagnostic outputs were removed with them. The current-contract max-cluster
replacement is separate from the modularity-band sensitivity dimension. Final
conclusions must use the current canonical profile refresh manifest, the current
`final_statistics/` tables, and the subject-level
`robustness_final_30seeds/` outputs instead.
