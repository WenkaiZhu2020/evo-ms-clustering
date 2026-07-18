# Stage 3A/Stage 3B budgeted semantic

Values are computed from the frozen retained candidate set. A profile is unavailable when no retained candidate meets the stated budget; it is not silently replaced by the conservative profile.

| stage | subject | budget | availability | median gain | IQR | median realised Q loss | ≥5% | ≥10% | ≥20% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| stage3a | daytrader | 0.0% | 0.167 | 0.0126 | 0.0229 | 0.0000 | 0 | 0 | 0 |
| stage3a | daytrader | 1.0% | 0.267 | 0.0190 | 0.0208 | 0.0000 | 0 | 0 | 0 |
| stage3a | daytrader | 2.5% | 0.500 | 0.0150 | 0.0327 | 0.0110 | 0 | 0 | 0 |
| stage3a | daytrader | 5.0% | 0.667 | 0.0056 | 0.0340 | 0.0181 | 0 | 0 | 0 |
| stage3a | daytrader | 10.0% | 0.800 | 0.0056 | 0.0465 | 0.0251 | 1 | 0 | 0 |
| stage3a | jpetstore | 0.0% | 0.933 | -0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| stage3a | jpetstore | 1.0% | 1.000 | -0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| stage3a | jpetstore | 2.5% | 1.000 | -0.0000 | 0.0778 | 0.0000 | 11 | 1 | 0 |
| stage3a | jpetstore | 5.0% | 1.000 | 0.0778 | 0.0453 | 0.0297 | 21 | 4 | 0 |
| stage3a | jpetstore | 10.0% | 1.000 | 0.1102 | 0.0784 | 0.0605 | 28 | 18 | 2 |
| stage3a | xerces | 0.0% | 0.367 | -0.0000 | 0.0050 | 0.0000 | 0 | 0 | 0 |
| stage3a | xerces | 1.0% | 0.967 | 0.0049 | 0.0061 | 0.0013 | 0 | 0 | 0 |
| stage3a | xerces | 2.5% | 1.000 | 0.0049 | 0.0061 | 0.0013 | 0 | 0 | 0 |
| stage3a | xerces | 5.0% | 1.000 | 0.0050 | 0.0062 | 0.0014 | 0 | 0 | 0 |
| stage3a | xerces | 10.0% | 1.000 | 0.0050 | 0.0062 | 0.0014 | 0 | 0 | 0 |
| stage3b | daytrader | 0.0% | 0.133 | 0.0068 | 0.0139 | 0.0000 | 0 | 0 | 0 |
| stage3b | daytrader | 1.0% | 0.300 | 0.0144 | 0.0384 | 0.0038 | 1 | 0 | 0 |
| stage3b | daytrader | 2.5% | 0.333 | 0.0231 | 0.0350 | 0.0042 | 2 | 0 | 0 |
| stage3b | daytrader | 5.0% | 0.633 | 0.0111 | 0.0380 | 0.0296 | 3 | 0 | 0 |
| stage3b | daytrader | 10.0% | 0.800 | 0.0055 | 0.0700 | 0.0358 | 3 | 0 | 0 |
| stage3b | jpetstore | 0.0% | 0.867 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| stage3b | jpetstore | 1.0% | 0.967 | 0.0003 | 0.0003 | 0.0049 | 0 | 0 | 0 |
| stage3b | jpetstore | 2.5% | 1.000 | 0.0910 | 0.0907 | 0.0113 | 17 | 0 | 0 |
| stage3b | jpetstore | 5.0% | 1.000 | 0.0910 | 0.0390 | 0.0268 | 26 | 11 | 0 |
| stage3b | jpetstore | 10.0% | 1.000 | 0.1300 | 0.1196 | 0.0609 | 30 | 22 | 9 |
| stage3b | xerces | 0.0% | 0.267 | 0.0007 | 0.0035 | 0.0000 | 0 | 0 | 0 |
| stage3b | xerces | 1.0% | 0.967 | 0.0042 | 0.0034 | 0.0011 | 0 | 0 | 0 |
| stage3b | xerces | 2.5% | 1.000 | 0.0044 | 0.0033 | 0.0014 | 0 | 0 | 0 |
| stage3b | xerces | 5.0% | 1.000 | 0.0045 | 0.0033 | 0.0014 | 0 | 0 | 0 |
| stage3b | xerces | 10.0% | 1.000 | 0.0045 | 0.0033 | 0.0014 | 0 | 0 | 0 |

The gain column is `gain_semantic`. The budget is a maximum permitted relative modularity loss, not a claim that the selected profile realises the full budget.
