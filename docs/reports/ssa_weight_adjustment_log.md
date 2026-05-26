# SSA Weight Adjustment Log

This document records where SSA weight and sensitivity evidence is stored for Stage 1.

## Current Evidence

- DayTrader calibration outputs are under `results/daytrader/00_pre_experiment/calibration/`.
- Xerces-J sensitivity outputs are under `results/xerces-j/stage1/`.
- Cross-case interpretation is summarized in `docs/reports/stage1_cross_case_summary.md`.

## Recorded Fields

Current sweep outputs record:

- subject
- graph input
- raw weight rule
- SSA flow weight rule
- lambda / scaling setting
- Leiden resolution
- random seed
- output path
- main metric observations
- interpretation

## Interpretation Boundary

SSA weight is treated as a sensitivity parameter, not as proof that `G_ssa` is always better than `G_raw`. DayTrader is the calibration case because it has a reference mapping. Xerces-J is used as a larger technical transfer check.
