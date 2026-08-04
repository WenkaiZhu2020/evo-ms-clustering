# Formal Results Index

This index separates frozen evidence from supporting, historical, and failed
outputs. Frozen scientific bytes are preserved under the final stage-oriented
paths below; paths embedded in historical metadata remain historical evidence.

## Formal thesis results

- Subject-level 30-seed outputs:
  - `results/stage2/subjects/jpetstore/nsga/robustness_final_30seeds/`
  - `results/stage2/subjects/daytrader/nsga/robustness_final_30seeds/`
  - `results/stage2/subjects/xerces-j/nsga/robustness_final_30seeds/`
- Cross-subject statistics: `results/stage2/cross_subject/formal_statistics/`
- Formal manifests: each subject's `robustness_final_30seeds/robustness_manifest.json`

These are the only Stage 2 result trees to use for formal thesis numbers.

## Supporting evidence

- Convergence diagnostics: `results/stage2/subjects/<subject>/nsga/convergence_diagnostic/`
- Method and constraint diagnostics: `results/stage2/subjects/<subject>/nsga/diagnostics/`
- Stage 2 audit: `docs/stage2/reproducibility.md`
- Unified provenance verifier: `scripts/reproducibility/verify.py`
- Historical/failed-output cleanup inventory:
  `results/stage2/cross_subject/formal_statistics/historical_output_cleanup_inventory.csv`
- Canonical Stage 2 operating profiles and the required modularity-band
  response analysis:
  `results/stage2/cross_subject/operating_profile/`
- Band sensitivity at 1%, 3%, 5%, and 10%:
  `results/stage2/cross_subject/operating_profile/sensitivity/`
- Current-contract max-cluster replacement at the canonical 5% band:
  `results/stage2/cross_subject/sensitivity_analysis/max_cluster/`
- Current multiple-comparison family metadata:
  `results/stage2/cross_subject/formal_statistics/analysis_metadata.json`
- The band profiles are post-hoc operating-profile results derived from the
  frozen fronts; they are not new search or graph outputs and are not an
  optional appendix-only profile.

Convergence, initialization/constraint diagnostics, and the retained audit are
supporting evidence, not replacements for the formal 30-seed outputs.

## Historical or failed outputs

Obsolete historical/failed derived outputs were removed in the Stage 2 cleanup.
The exact deletion and retention decisions are recorded in:

```text
results/stage2/cross_subject/formal_statistics/historical_output_cleanup_inventory.csv
```

Complete frozen formal fronts, candidate labels, formal manifests, and other
protected scientific source artifacts were retained unchanged. No historical
or failed path listed in the cleanup inventory is a current input to the
verifier or canonical Stage 2 tables.
