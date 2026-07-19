# Formal Results Index

This index separates frozen evidence from supporting, historical, and failed
outputs. Existing frozen paths are intentionally unchanged.

## Formal thesis results

- Subject-level 30-seed outputs:
  - `results/jpetstore/03_stage2_nsga/robustness_final_30seeds/`
  - `results/daytrader/03_stage2_nsga/robustness_final_30seeds/`
  - `results/xerces-j/03_stage2_nsga/robustness_final_30seeds/`
- Cross-subject statistics: `results/cross_subject/03_stage2_nsga/final_statistics/`
- Formal checksum: `results/cross_subject/03_stage2_nsga/final_statistics/formal_output_sha256sums.txt`
- Formal manifests: each subject's `robustness_final_30seeds/robustness_manifest.json`

These are the only Stage 2 result trees to use for formal thesis numbers.

## Supporting evidence

- Convergence diagnostics: `results/<subject>/03_stage2_nsga/convergence_diagnostic/`
- Method and constraint diagnostics: `results/<subject>/03_stage2_nsga/diagnostics/`
- Stage 2 audit: `docs/stage2/reproducibility.md`
- Unified provenance verifier: `scripts/reproducibility/verify.py`
- Canonical Stage 2 operating profiles:
  `results/cross_subject/03_stage2_nsga/modularity_band/`
- Preference profiles are derived supporting evidence and must not be treated
  as new search or graph outputs.

Convergence, initialization/constraint diagnostics, and the retained audit are
supporting evidence, not replacements for the formal 30-seed outputs.

## Historical or failed outputs

- Earlier runs: `results/<subject>/03_stage2_nsga/raw/`
- Superseded robustness runs: `results/<subject>/03_stage2_nsga/robustness/`
- Smoke runs: `results/<subject>/03_stage2_nsga/robustness_smoke/`
- Failed empirical-bounds attempt: `results/jpetstore/03_stage2_nsga/robustness_failed_empirical_bounds/`

These paths remain in place because they are part of the recorded repository
history and are not formal thesis results. Their local status files explain
the classification. None is used by the unified verifier or the formal
checksum.
