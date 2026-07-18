# Stage 2 budgeted balance

Values are computed from the frozen retained candidate set. A profile is unavailable when no retained candidate meets the stated budget; it is not silently replaced by the conservative profile.

| stage | subject | budget | availability | median gain | IQR | median realised Q loss | ≥5% | ≥10% | ≥20% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| stage2 | daytrader | 0.0% | 0.200 | 0.0478 | 0.0920 | 0.0000 | 3 | 2 | 0 |
| stage2 | daytrader | 1.0% | 0.267 | 0.1059 | 0.1211 | 0.0000 | 5 | 4 | 0 |
| stage2 | daytrader | 2.5% | 0.300 | 0.1617 | 0.1211 | 0.0000 | 6 | 5 | 0 |
| stage2 | daytrader | 5.0% | 0.433 | 0.1665 | 0.1267 | 0.0191 | 11 | 8 | 2 |
| stage2 | daytrader | 10.0% | 0.533 | 0.2758 | 0.1703 | 0.0598 | 14 | 12 | 10 |
| stage2 | jpetstore | 0.0% | 1.000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| stage2 | jpetstore | 1.0% | 1.000 | 0.0000 | 0.0000 | 0.0000 | 7 | 7 | 7 |
| stage2 | jpetstore | 2.5% | 1.000 | 0.4226 | 0.5774 | 0.0122 | 30 | 30 | 30 |
| stage2 | jpetstore | 5.0% | 1.000 | 1.0000 | 0.0000 | 0.0324 | 30 | 30 | 30 |
| stage2 | jpetstore | 10.0% | 1.000 | 1.0000 | 0.0000 | 0.0324 | 30 | 30 | 30 |
| stage2 | xerces | 0.0% | 0.800 | 0.0000 | 0.0243 | 0.0000 | 2 | 0 | 0 |
| stage2 | xerces | 1.0% | 0.900 | 0.0244 | 0.0229 | 0.0010 | 3 | 0 | 0 |
| stage2 | xerces | 2.5% | 1.000 | 0.0413 | 0.0285 | 0.0174 | 12 | 1 | 0 |
| stage2 | xerces | 5.0% | 1.000 | 0.0794 | 0.0327 | 0.0386 | 24 | 2 | 0 |
| stage2 | xerces | 10.0% | 1.000 | 0.1092 | 0.0415 | 0.0883 | 29 | 18 | 0 |

The gain column is `gain_imbalance`. The budget is a maximum permitted relative modularity loss, not a claim that the selected profile realises the full budget.
