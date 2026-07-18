# JPetStore 100% imbalance-gain audit

The classification rules were fixed before inspecting cases: A means no singleton clusters and max/min size ratio <=4; B means high fragmentation; C means singleton-driven; D means metric degeneracy; E is unresolved. The frozen imbalance formula was not changed.

The audit found 422 selected rows across all saved profile reports. Classification counts: `{"A_balanced_non_pathological": 422}`. Thesis treatment: **main text with explicit structural-cost caveat**.

A 100% relative gain means that the selected partition reaches the baseline imbalance value of zero; it is not by itself evidence of good decomposition. The complete rows, including Q loss, coupling, cohesion, cluster sizes, singleton counts, and ARI/NMI, are in `jpetstore_100pct_imbalance_per_seed.csv`.

## Observed structural pattern

```csv
stage,classification,rows
stage2,A_balanced_non_pathological,218
stage3a,A_balanced_non_pathological,90
stage3b,A_balanced_non_pathological,114
```
