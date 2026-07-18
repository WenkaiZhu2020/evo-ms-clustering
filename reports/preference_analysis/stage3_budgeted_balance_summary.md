# Stage 3A/Stage 3B budgeted balance

Values are computed from the frozen retained candidate set. A profile is unavailable when no retained candidate meets the stated budget; it is not silently replaced by the conservative profile.

| stage | subject | budget | availability | median gain | IQR | median realised Q loss | ≥5% | ≥10% | ≥20% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| stage3a | daytrader | 0.0% | 0.167 | 0.1475 | 0.1116 | 0.0000 | 4 | 3 | 0 |
| stage3a | daytrader | 1.0% | 0.267 | 0.1012 | 0.1140 | 0.0000 | 6 | 4 | 1 |
| stage3a | daytrader | 2.5% | 0.500 | 0.0751 | 0.1636 | 0.0110 | 10 | 7 | 4 |
| stage3a | daytrader | 5.0% | 0.667 | 0.1090 | 0.1521 | 0.0210 | 14 | 10 | 5 |
| stage3a | daytrader | 10.0% | 0.800 | 0.1358 | 0.1478 | 0.0436 | 20 | 16 | 8 |
| stage3a | jpetstore | 0.0% | 0.933 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| stage3a | jpetstore | 1.0% | 1.000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| stage3a | jpetstore | 2.5% | 1.000 | 0.0000 | 0.1835 | 0.0024 | 13 | 13 | 4 |
| stage3a | jpetstore | 5.0% | 1.000 | 0.3031 | 0.2391 | 0.0148 | 23 | 23 | 15 |
| stage3a | jpetstore | 10.0% | 1.000 | 0.4226 | 0.2391 | 0.0391 | 27 | 27 | 19 |
| stage3a | xerces | 0.0% | 0.367 | 0.0226 | 0.0240 | 0.0000 | 1 | 0 | 0 |
| stage3a | xerces | 1.0% | 0.967 | 0.0054 | 0.0254 | 0.0018 | 1 | 0 | 0 |
| stage3a | xerces | 2.5% | 1.000 | 0.0495 | 0.0394 | 0.0166 | 15 | 0 | 0 |
| stage3a | xerces | 5.0% | 1.000 | 0.0730 | 0.0281 | 0.0352 | 24 | 6 | 0 |
| stage3a | xerces | 10.0% | 1.000 | 0.1033 | 0.0309 | 0.0840 | 30 | 18 | 0 |
| stage3b | daytrader | 0.0% | 0.133 | 0.1184 | 0.0663 | 0.0000 | 4 | 4 | 1 |
| stage3b | daytrader | 1.0% | 0.300 | 0.1033 | 0.0976 | 0.0038 | 6 | 6 | 1 |
| stage3b | daytrader | 2.5% | 0.333 | 0.1184 | 0.0879 | 0.0066 | 8 | 7 | 2 |
| stage3b | daytrader | 5.0% | 0.633 | 0.1184 | 0.0819 | 0.0324 | 17 | 12 | 4 |
| stage3b | daytrader | 10.0% | 0.800 | 0.1909 | 0.1757 | 0.0621 | 22 | 19 | 12 |
| stage3b | jpetstore | 0.0% | 0.867 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| stage3b | jpetstore | 1.0% | 0.967 | 0.0000 | 0.0000 | 0.0000 | 3 | 3 | 3 |
| stage3b | jpetstore | 2.5% | 1.000 | 0.1835 | 0.2391 | 0.0113 | 23 | 23 | 11 |
| stage3b | jpetstore | 5.0% | 1.000 | 0.4226 | 0.2391 | 0.0119 | 25 | 25 | 18 |
| stage3b | jpetstore | 10.0% | 1.000 | 0.4226 | 0.7638 | 0.0237 | 28 | 28 | 23 |
| stage3b | xerces | 0.0% | 0.267 | 0.0227 | 0.0329 | 0.0000 | 2 | 0 | 0 |
| stage3b | xerces | 1.0% | 0.967 | 0.0058 | 0.0332 | 0.0028 | 5 | 0 | 0 |
| stage3b | xerces | 2.5% | 1.000 | 0.0514 | 0.0348 | 0.0187 | 15 | 0 | 0 |
| stage3b | xerces | 5.0% | 1.000 | 0.0826 | 0.0345 | 0.0393 | 26 | 8 | 0 |
| stage3b | xerces | 10.0% | 1.000 | 0.1164 | 0.0367 | 0.0889 | 30 | 22 | 0 |

The gain column is `gain_imbalance`. The budget is a maximum permitted relative modularity loss, not a claim that the selected profile realises the full budget.
