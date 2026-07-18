# Preference-response analysis conclusions

This is a post-hoc analysis of the saved retained final feasible fronts for 30 paired seeds. It does not replace the frozen conservative selector, rerun an optimizer, or establish a global Pareto frontier. Reported capability is attainable within the saved retained candidate set, which is limited by population size, crowding truncation, duplicate handling, evolutionary trajectory, and finite generations.

## Conservative-profile result

The existing selected solution remains the highest-weighted-modularity feasible solution under the frozen selection rule. No selected result was changed.

## Retained-front capability and preference sensitivity

- stage2_balance: balance capability is reported with availability and realised modularity loss for all subjects; the complete eight-budget curve is in the CSV and figure data.
- stage3_balance: balance capability is reported with availability and realised modularity loss for all subjects; the complete eight-budget curve is in the CSV and figure data.

Stage 3A and Stage 3B semantic profiles are evaluated on their native semantic graphs. Cross-graph values are kept separate and are descriptive matched-partition checks, not direct comparisons of raw objective values.

## Structural costs, external quality, and stability

Secondary changes in coupling, cohesion, cluster count, and singleton ratio are reported per seed. DayTrader is the only subject with a complete frozen external reference; JPetStore and Xerces-J are marked unavailable rather than assigned invented references. External metrics are post-hoc and did not influence selection.

Cross-seed ARI/NMI stability is reported for conservative, budgeted, knee, and extreme retained-front profiles. Extreme profiles are capability bounds, not deployment recommendations.

## Subject dependence

JPetStore, DayTrader, and Xerces-J are reported separately. The analysis does not force a universal positive conclusion across subjects or preference families.
