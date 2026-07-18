# Formal paired statistical tests

The frozen paired protocol is two-sided Wilcoxon signed-rank tests on the 30 paired seed values, with arithmetic delta defined as right representation minus left representation. Holm correction is applied separately within each planned comparison family (six rows: three subjects × two primary metrics). The primary metrics are projected 3D Hypervolume and selected semantic objective. Rank-biserial effect sizes and deterministic 10,000-resample bootstrap mean-delta intervals are descriptive supplements.

| comparison | subject | metric | p | Holm p | rank-biserial | status |
|---|---|---|---:|---:|---:|---|
| stage2_vs_stage3 | jpetstore | projected_hv | 9.22009e-06 | 5.53206e-05 | -0.845161 | tested |
| stage2_vs_stage3 | jpetstore | selected_f_semantic | 1 | 1 | 0 | tested |
| stage2_vs_stage3 | daytrader | projected_hv | 0.404495 | 1 | 0.178495 | tested |
| stage2_vs_stage3 | daytrader | selected_f_semantic | 0.404495 | 1 | -0.178495 | tested |
| stage2_vs_stage3 | xerces | projected_hv | 0.839393 | 1 | 0.0451613 | tested |
| stage2_vs_stage3 | xerces | selected_f_semantic | 0.000143609 | 0.000718043 | -0.905797 | tested |
