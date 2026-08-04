# Seed-robustness control: daytrader

Seeds: 0..29 (30 seeds, 435 raw-vs-raw pairs). resolution=1.0, raw lambda=0.0, ssa lambda=0.25, n_iterations=-1.

| distribution | ARI mean +/- std | distance (1-ARI) mean +/- std |
| --- | --- | --- |
| SSA effect ARI(raw_i, ssa_i) | 0.8914 +/- 0.0941 | 0.1086 +/- 0.0941 |
| Seed noise ARI(raw_i, raw_j) | 0.9345 +/- 0.1445 | 0.0655 +/- 0.1445 |

Raw-partition seed stability: 4 distinct raw partitions across 30 seeds; 81% of reseed pairs are identical; 19% of reseeds move the raw partition at least as much as the mean SSA effect.

Mann-Whitney U (SSA-effect distance vs seed-noise distance): U=10614.0, p=2.687e-14 (distinguishable at p<0.05: True). Note: the two samples share the raw partitions, so independence is approximate and the p-value is a guideline alongside the effect-size/overlap view above.

Verdict: SSA-effect distance 0.1086 vs seed-noise 0.0655+/-0.1445: same order of magnitude, and SSA-effect lies within the seed-noise +/-2std band [-0.2235, 0.3545]. 19% of pure reseeds move the raw partition >= the mean SSA effect (81% of reseed pairs are identical). Mann-Whitney p=2.69e-14: distributions separable by shape, but effect magnitudes overlap -> SSA effect is comparable to seed noise, not clearly beyond it.
