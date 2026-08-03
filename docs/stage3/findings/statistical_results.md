# Formal paired statistical tests

The confirmatory family contains exactly six rows: three subjects × projected
3D Hypervolume and selected `f_semantic`. Differences are Stage 3 − Stage 2.
Tests are paired two-sided Wilcoxon signed-rank tests with SciPy
`zero_method="wilcox"`; Holm adjustment covers these six rows only at
family-wise alpha 0.05. Rank-biserial signs follow the arithmetic difference,
so a negative value is favourable for lower-is-better `selected_f_semantic`.

Projected-HV pairs are read unchanged from the accepted
`stage2_vs_stage3/paired_per_seed.csv`. Selected `f_semantic` uses the active
Stage 2 5% modularity-band profile and the final Stage 3 selected operating
solution, evaluated on the same final Declaration + Method Body semantic graph.

| subject | metric | raw p | Holm p | rank-biserial | better/tie/worse | corrected significant |
|---|---|---:|---:|---:|---:|---|
| jpetstore | projected_hypervolume | 9.22009349e-06 | 4.61004674e-05 | -0.845161 | 4/0/26 | yes |
| jpetstore | selected_f_semantic | 0.136610163 | 0.546440651 | -0.307527 | 13/0/17 | no |
| daytrader | projected_hypervolume | 0.404494504 | 0.808989007 | 0.178495 | 16/0/14 | no |
| daytrader | selected_f_semantic | 0.236652344 | 0.709957033 | -0.251613 | 16/0/14 | no |
| xerces | projected_hypervolume | 0.839392744 | 0.839392744 | 0.0451613 | 13/0/17 | no |
| xerces | selected_f_semantic | 1.86264515e-09 | 1.11758709e-08 | -1 | 30/0/0 | yes |

The machine-readable authority is
`results/stage3/cross_subject/formal_statistics/formal_statistical_tests.csv`.
Exploratory structural-profile and preference-response tests are separate
families and do not enter this Holm adjustment.
