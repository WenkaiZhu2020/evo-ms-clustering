# Seed-robustness control: jpetstore

Seeds: 0..29 (30 seeds, 435 raw-vs-raw pairs). resolution=1.0, raw lambda=0.0, ssa lambda=0.25, n_iterations=-1.

| distribution | ARI mean +/- std | distance (1-ARI) mean +/- std |
| --- | --- | --- |
| SSA effect ARI(raw_i, ssa_i) | 0.8766 +/- 0.0000 | 0.1234 +/- 0.0000 |
| Seed noise ARI(raw_i, raw_j) | 1.0000 +/- 0.0000 | 0.0000 +/- 0.0000 |

Raw-partition seed stability: 1 distinct raw partitions across 30 seeds; 100% of reseed pairs are identical; 0% of reseeds move the raw partition at least as much as the mean SSA effect.

Mann-Whitney U (SSA-effect distance vs seed-noise distance): U=13050.0, p=0 (distinguishable at p<0.05: True). Note: the two samples share the raw partitions, so independence is approximate and the p-value is a guideline alongside the effect-size/overlap view above.

Verdict: Raw clustering is seed-stable (seed-noise distance = 0 across all pairs), so the fixed SSA distance 0.1234 registers as 'outside' zero noise. This is the seed-trivial small-graph case; Mann-Whitney p=0 (separable) is degenerate here.
