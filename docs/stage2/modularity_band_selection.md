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
`results/stage2/cross_subject/operating_profile/`. The downstream
post-hoc metric refresh is written to
`canonical_operating_profile_metrics_per_seed.csv` with source-front,
candidate-label, and selector-contract provenance.

## Modularity-band sensitivity

The canonical profile remains the `5%` band. A separate sensitivity analysis
uses the same selector at `1%`, `3%`, `5%`, and `10%`. The existing complete
profile table already covered `1%`, `5%`, and `10%`; only the `3%` budget was
new. The sensitivity rows are stored in
`results/stage2/cross_subject/operating_profile/sensitivity/` and are
post-hoc evaluations of the frozen fronts. `Q_max` anchors band membership;
all scientific comparisons below use the fixed Stage 1 Leiden baseline.

Positive imbalance improvement means lower imbalance than Leiden. Positive
coupling change means higher coupling than Leiden and is therefore a cost.
Positive cohesion change means higher cohesion than Leiden. ARI and NMI are
partition similarity to Leiden, not external-reference scores.

| Subject | Band | Median modularity loss vs Leiden | Median imbalance improvement | Median coupling change | Median cohesion change | Median cluster-count change | Median max-ratio change | Median ARI/NMI vs Leiden | Same as Leiden |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DayTrader | 1% | 8.5% | 22.5% | +2.9% | +8.6% | -2.0 | +0.000 | 0.850 / 0.897 | 1/30 |
| DayTrader | 3% | 8.5% | 24.0% | +3.7% | +8.5% | -2.0 | +0.000 | 0.850 / 0.893 | 1/30 |
| DayTrader | 5% | 9.3% | 24.3% | +4.5% | +8.6% | -2.0 | +0.000 | 0.830 / 0.883 | 1/30 |
| DayTrader | 10% | 12.5% | 30.3% | +6.7% | +10.3% | -2.0 | +0.000 | 0.739 / 0.828 | 1/30 |
| JPetStore | 1% | 0.0% | 0.0% | +0.0% | +0.0% | +0.0 | +0.000 | 1.000 / 1.000 | 23/30 |
| JPetStore | 3% | 1.2% | 42.3% | +0.0% | -10.4% | +0.0 | +0.000 | 0.792 / 0.836 | 0/30 |
| JPetStore | 5% | 3.2% | 100.0% | +8.8% | -10.5% | +0.0 | -0.042 | 0.676 / 0.752 | 0/30 |
| JPetStore | 10% | 3.2% | 100.0% | +8.8% | -10.5% | +0.0 | -0.042 | 0.676 / 0.752 | 0/30 |
| Xerces-J | 1% | 0.2% | 2.5% | +0.7% | +1.5% | -1.0 | +0.000 | 0.995 / 0.995 | 5/30 |
| Xerces-J | 3% | 2.3% | 4.7% | +8.2% | +0.8% | -1.0 | -0.001 | 0.969 / 0.970 | 0/30 |
| Xerces-J | 5% | 4.0% | 7.9% | +14.2% | +2.3% | -2.0 | -0.002 | 0.961 / 0.961 | 0/30 |
| Xerces-J | 10% | 8.8% | 10.9% | +31.1% | -52.9% | -3.0 | -0.004 | 0.933 / 0.923 | 0/30 |

The full mean/median/standard-deviation/range and better/tie/worse counts are
in `sensitivity_metric_summary.csv`. Adjacent-budget increments are in
`budget_response_transitions.csv`. External metrics are available for
DayTrader's accepted reference mapping (30/30 rows per budget); they are
recorded as unavailable for JPetStore and Xerces-J.

At the subject level, DayTrader gains most of its additional balance by 10%,
but pays a larger modularity and coupling cost. JPetStore changes sharply by
3% and then saturates: 10% adds no median change. Xerces-J changes gradually
through 5%, while 10% adds substantial coupling cost and a large cohesion
decline. Thus 3% is close to 5% for DayTrader and Xerces-J on balance, but 5%
remains the predeclared canonical compromise; 10% is not justified as the
operating choice by this sensitivity.

Figures are deterministic views of the machine-readable summary tables:

- `sensitivity/modularity_loss_vs_imbalance_improvement.png`
- `sensitivity/modularity_loss_vs_coupling_change.png`
- `sensitivity/budget_vs_cluster_count_change.png`

Historical max-cluster tables are not current evidence. The current-contract
replacement at the fixed canonical 5% band is under
`results/stage2/cross_subject/sensitivity_analysis/max_cluster/`; the two
dimensions are intentionally kept separate.
