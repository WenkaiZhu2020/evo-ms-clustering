# Formal paired statistical tests

The frozen paired protocol is two-sided Wilcoxon signed-rank tests on the 30 paired seed values, with arithmetic delta defined as right representation minus left representation. Holm correction is applied separately within each planned comparison family (six rows: three subjects × two primary metrics). The primary metrics are projected 3D Hypervolume and selected semantic objective. Rank-biserial effect sizes and deterministic 10,000-resample bootstrap mean-delta intervals are descriptive supplements.

| comparison | subject | metric | p | Holm p | rank-biserial | status |
|---|---|---|---:|---:|---:|---|
| stage2_vs_stage3b | jpetstore | projected_hv | 9.22009e-06 | 5.53206e-05 | -0.845161 | tested |
| stage2_vs_stage3b | jpetstore | selected_f_semantic | 1 | 1 | 0 | tested |
| stage2_vs_stage3b | daytrader | projected_hv | 0.404495 | 1 | 0.178495 | tested |
| stage2_vs_stage3b | daytrader | selected_f_semantic | 0.404495 | 1 | -0.178495 | tested |
| stage2_vs_stage3b | xerces | projected_hv | 0.839393 | 1 | 0.0451613 | tested |
| stage2_vs_stage3b | xerces | selected_f_semantic | 0.000143609 | 0.000718043 | -0.905797 | tested |
| stage3a_vs_stage3b | jpetstore | projected_hv | 0.000152871 | 0.000611484 | 0.746237 | tested |
| stage3a_vs_stage3b | jpetstore | selected_f_semantic | 3.34921e-07 | 2.00953e-06 | -1 | tested |
| stage3a_vs_stage3b | daytrader | projected_hv | 0.253436 | 0.760308 | 0.243011 | tested |
| stage3a_vs_stage3b | daytrader | selected_f_semantic | 0.464545 | 0.92909 | 0.156989 | tested |
| stage3a_vs_stage3b | xerces | projected_hv | 0.792159 | 0.92909 | -0.0580645 | tested |
| stage3a_vs_stage3b | xerces | selected_f_semantic | 3.79048e-06 | 1.89524e-05 | 0.870968 | tested |
