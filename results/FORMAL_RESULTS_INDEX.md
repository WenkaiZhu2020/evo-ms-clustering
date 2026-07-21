# Formal Results Index

This index separates frozen evidence from supporting, historical, and failed
outputs. Existing frozen paths are intentionally unchanged.

## Formal thesis results

- Subject-level 30-seed outputs:
  - `results/jpetstore/03_stage2_nsga/robustness_final_30seeds/`
  - `results/daytrader/03_stage2_nsga/robustness_final_30seeds/`
  - `results/xerces-j/03_stage2_nsga/robustness_final_30seeds/`
- Cross-subject statistics: `results/cross_subject/03_stage2_nsga/final_statistics/`
- Formal manifests: each subject's `robustness_final_30seeds/robustness_manifest.json`

These are the only Stage 2 result trees to use for formal thesis numbers.

## Supporting evidence

- Convergence diagnostics: `results/<subject>/03_stage2_nsga/convergence_diagnostic/`
- Method and constraint diagnostics: `results/<subject>/03_stage2_nsga/diagnostics/`
- Stage 2 audit: `docs/stage2/reproducibility.md`
- Unified provenance verifier: `scripts/reproducibility/verify.py`
- Historical/failed-output cleanup inventory:
  `results/cross_subject/03_stage2_nsga/final_statistics/historical_output_cleanup_inventory.csv`
- Canonical Stage 2 operating profiles and the required modularity-band
  response analysis:
  `results/cross_subject/03_stage2_nsga/modularity_band/`
- Band sensitivity at 1%, 3%, 5%, and 10%:
  `results/cross_subject/03_stage2_nsga/modularity_band/sensitivity/`
- Current-contract max-cluster replacement at the canonical 5% band:
  `results/cross_subject/03_stage2_nsga/final_statistics/max_cluster_posthoc_sensitivity_current_band/`
- Current multiple-comparison family metadata:
  `results/cross_subject/03_stage2_nsga/final_statistics/analysis_metadata.json`
- The band profiles are post-hoc operating-profile results derived from the
  frozen fronts; they are not new search or graph outputs and are not an
  optional appendix-only profile.

Convergence, initialization/constraint diagnostics, and the retained audit are
supporting evidence, not replacements for the formal 30-seed outputs.

## Historical or failed outputs

Obsolete historical/failed derived outputs were removed in the Stage 2 cleanup.
The exact deletion and retention decisions are recorded in:

```text
results/cross_subject/03_stage2_nsga/final_statistics/historical_output_cleanup_inventory.csv
```

Complete frozen formal fronts, candidate labels, formal manifests, and other
protected scientific source artifacts were retained unchanged. No historical
or failed path listed in the cleanup inventory is a current input to the
verifier or canonical Stage 2 tables.
