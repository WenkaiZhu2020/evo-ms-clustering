# Objectives and Metrics

This document separates **optimization objectives** from **post-hoc evaluation
metrics**. Only the optimization objectives enter NSGA-II fitness. Evaluation
metrics are computed after search.

## Optimization Objectives

Stage 2 optimizes exactly three objectives:

| Objective | Direction | Definition | Complexity |
| --- | --- | --- | --- |
| Coupling | minimize | `W_external / W_total` | O(E) |
| Cohesion | maximize | average cluster density | O(E) |
| Imbalance | minimize | `std(cluster_sizes) / mean(cluster_sizes)` | O(k) |

Coupling is the fraction of edge weight crossing cluster boundaries:

```text
coupling = W_external / W_total
```

Cohesion uses density, not the internal-weight ratio, because that ratio is
redundant with coupling. For each cluster `c`:

```text
cohesion(c) = 2 * W_internal(c) / (|c| * (|c| - 1))
```

The objective value is the average of `cohesion(c)` across clusters. Singleton
clusters must avoid division by zero during implementation.

Imbalance is:

```text
imbalance = std(cluster_sizes) / mean(cluster_sizes)
```

pymoo minimizes by default, so the eventual Problem wrapper must emit:

```text
F = [coupling, -cohesion, imbalance]
```

Objective computation must stay in the O(E) family and reuse the Stage 1
`_edge_weight_split(edges, cluster_by_class, weight_column)` primitive for the
shared internal/external split. `_weighted_modularity` is O(n^2) and must not be
used in the optimization loop.

## Hard Constraints

The anti-degeneration constraints are not objectives. They are handled through
pymoo constraints or repair operators:

- `max_cluster_ratio <= 0.40`
- `k >= 2`

Cluster-size balance is intentionally both a soft optimization objective
through `imbalance` and part of hard admissibility through the max-cluster
constraint. `singleton_ratio` is retained as a diagnostic metric only.
Candidate labels are bounded by `0..n-1`, but the formal problem has no separate
hard constraint requiring `k <= n-1`.

## Post-Hoc Metrics Only

| Metric | Reuse point | Role |
| --- | --- | --- |
| Weighted modularity | `_weighted_modularity` | Report competitiveness against Leiden. |
| Hypervolume | pymoo metric | Main Pareto-front quality summary across seeds. |
| MoJoFM / Pairwise F1 | `calculate_reference_metrics` | DayTrader-only reference check. |
| ARI / NMI vs Leiden | `partition_similarity` | Compare solutions with frozen Leiden baselines. |

Modularity, MoJoFM, Pairwise F1, and Hypervolume are evaluation-only metrics.
They must not become optimization objectives.

Hypervolume must use a fixed, consistent reference point for each subject. The
same reference or nadir point must be used across all seeds for that subject, so
Hypervolume values are comparable across seeds. The implementation must record
the selected reference point and how it was chosen in the Stage 2 metadata before
reporting Hypervolume.

## RQ2 Interpretation

RQ2 asks whether structure-only NSGA-II is competitive with Leiden while
providing a Pareto front. The claim is based on Pareto-front quality,
Hypervolume, and comparison with frozen Leiden points, not on outperforming
Leiden in modularity.

Because Stage 2 uses heuristic seeding, RQ2 reporting must separate injected
seed solutions from non-seed evolved solutions. Preserving an injected Leiden
seed only establishes competitiveness with the heuristic starting point. The
stronger Pareto-front claim depends on non-seed solutions that expose trade-offs
Leiden does not provide, especially DayTrader solutions whose MoJoFM or
Pairwise F1 improves over the frozen Leiden reference comparison.
