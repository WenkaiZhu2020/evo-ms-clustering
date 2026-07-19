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
- Historical selector-cleanup inventory:
  `results/cross_subject/03_stage2_nsga/final_statistics/historical_selector_cleanup_inventory.csv`
- Canonical Stage 2 operating profiles and the required modularity-band
  response analysis:
  `results/cross_subject/03_stage2_nsga/modularity_band/`
- The band profiles are post-hoc operating-profile results derived from the
  frozen fronts; they are not new search or graph outputs and are not an
  optional appendix-only profile.

Convergence, initialization/constraint diagnostics, and the retained audit are
supporting evidence, not replacements for the formal 30-seed outputs.

## Historical or failed outputs

- Earlier runs: `results/<subject>/03_stage2_nsga/raw/`
- Superseded robustness runs: `results/<subject>/03_stage2_nsga/robustness/`
- Smoke and failed-bound directories retain only protected front, label,
  metadata, manifest, and status evidence; temporary selected summaries were
  removed.

These paths remain in place because they are part of the recorded repository
history and are not formal thesis results. Their local status files explain
the classification. None is used by the unified verifier or current canonical
Stage 2 result tables.
