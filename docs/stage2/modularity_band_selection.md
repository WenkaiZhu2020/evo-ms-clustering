# Stage 2 modularity-band operating solution

The canonical Stage 2 operating solution is selected post-hoc from the
frozen formal Pareto fronts. The old maximum-weighted-modularity selector is
retired and is not a canonical operating rule.

For each subject and seed, the analysis computes the maximum weighted
modularity among feasible rows in that saved front. A candidate is in a band
of width `b` when its relative loss is at most `b`:

```text
(Q_max - Q_candidate) / |Q_max| <= b
```

Within each band, the deterministic preference order is minimum imbalance,
maximum weighted modularity, minimum coupling, lexicographic solution ID, and
the canonical label tuple. The `b = 0.05` profile is the canonical Stage 2
operating profile. The complete band response is a required post-hoc
structural analysis of the frozen fronts; it is not an optional appendix
profile.

The analysis reads only `pareto_front.csv` from the frozen
`robustness_final_30seeds` directories. It does not rerun NSGA-II, rebuild
graphs, regenerate Pareto fronts or references, or modify the frozen search
artifacts. Generated outputs are under
`results/cross_subject/03_stage2_nsga/modularity_band/`. The downstream
post-hoc metric refresh is written to
`canonical_operating_profile_metrics_per_seed.csv` with source-front,
candidate-label, and selector-contract provenance.
