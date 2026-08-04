# Seed-robustness control: xerces-j

Seeds: 0..29 (30 seeds, 435 raw-vs-raw pairs). resolution=1.0, raw lambda=0.0, ssa lambda=0.25, n_iterations=-1.

| distribution | ARI mean +/- std | distance (1-ARI) mean +/- std |
| --- | --- | --- |
| SSA effect ARI(raw_i, ssa_i) | 0.7175 +/- 0.0642 | 0.2825 +/- 0.0642 |
| Seed noise ARI(raw_i, raw_j) | 0.7842 +/- 0.1089 | 0.2158 +/- 0.1089 |

Raw-partition seed stability: 28 distinct raw partitions across 30 seeds; 3% of reseed pairs are identical; 37% of reseeds move the raw partition at least as much as the mean SSA effect.

Mann-Whitney U (SSA-effect distance vs seed-noise distance): U=8658.0, p=0.002738 (distinguishable at p<0.05: True). Note: the two samples share the raw partitions, so independence is approximate and the p-value is a guideline alongside the effect-size/overlap view above.

Verdict: SSA-effect distance 0.2825 vs seed-noise 0.2158+/-0.1089: same order of magnitude, and SSA-effect lies within the seed-noise +/-2std band [-0.0020, 0.4335]. 37% of pure reseeds move the raw partition >= the mean SSA effect (3% of reseed pairs are identical). Mann-Whitney p=0.00274: distributions separable by shape, but effect magnitudes overlap -> SSA effect is comparable to seed noise, not clearly beyond it.
