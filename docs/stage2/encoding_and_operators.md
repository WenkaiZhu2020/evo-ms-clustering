# Encoding and Operators

## Individual Encoding

An individual is a length-N integer label vector:

```text
labels[i] = cluster id for the i-th class in class_nodes order
```

The number of clusters `k` is variable and is not fixed before search. The
encoding maps to Stage 1 formats:

- `labels` -> `encoding.to_cluster_by_class` ->
  `{class_id: cluster_id}` for `_edge_weight_split`;
- `labels` -> `encoding.to_clusters_frame` ->
  `DataFrame[class_id, class_name, cluster_id]` for `partition_similarity`,
  `calculate_reference_metrics`, and future persistence.

## Label Symmetry

The same partition can have multiple label assignments, such as `[0, 0, 1]`
and `[1, 1, 0]`. Genetic operators must handle this symmetry.

The scaffold reserves `encoding.canonical_relabel` for this purpose. After
initialization, crossover, and mutation, labels should be remapped in first-seen
order to `0..k-1`. This keeps equivalent partitions in one canonical form.

## Initialization

Stage 2 uses structure-aware heuristic seeding before filling the rest of the
initial population with random label vectors. This is standard practice for
metaheuristics when a strong, cheap heuristic solution is available and the
random search basin is difficult to reach.

The injected seed set is deterministic for each NSGA-II random seed and is
built on the raw graph basis:

- the frozen `raw_reference_leiden` partition;
- small graph-local perturbations of that raw Leiden partition, where selected
  classes are moved toward neighboring clusters in `G_raw`;
- strongest-edge grouping seeds, where high-weight raw edges are merged first
  until target cluster counts near the raw Leiden cluster count are reached.

The diagnosis behind this choice is that pure random initialization explored
high-cluster-count partitions, but those partitions were incoherent and had
very high coupling. On Xerces-J, a random-initialized run at `population=100`
and `generations=100` found best modularity around `0.158` with about 10
clusters, while frozen raw Leiden had 31 clusters and modularity around
`0.662`. A seeded probe with the same budget retained the high-modularity basin
and produced non-seed variants near it.

Every Pareto-front solution records whether it exactly matches an injected
seed. RQ2 reporting must distinguish injected-seed solutions from newly evolved
non-seed solutions.

## Genetic Operators

The implemented operators are intentionally simple:

- crossover: uniform label crossover followed by canonical relabeling and
  admissibility repair;
- mutation: selected classes are reassigned to an existing cluster or one new
  cluster, followed by canonical relabeling and admissibility repair;
- repair: oversized clusters are split and the minimum cluster count is
  enforced. Singleton clusters are not merged by repair.

## Constraints and Repair

Stage 2 retains two formal validity controls:

- `max_cluster_ratio <= 0.40`
- `k >= 2`

They are implemented through pymoo constraints and repair. Singleton ratio is
retained as a diagnostic metric, not as a hard constraint or repair condition.
Candidate labels are bounded by `0..n-1`, but the formal problem does not define
a separate hard constraint requiring `k <= n-1`; label bounds are not an
equivalent cluster-count constraint.

Balance is also represented as the soft objective
`std(cluster_sizes) / mean(cluster_sizes)`, so it appears in objective space
while the max-cluster threshold prevents giant-cluster degeneration.
`singleton_ratio` remains a post-hoc diagnostic.

## pymoo Wiring

pymoo minimizes by default. The Problem wrapper must convert the objective
tuple from:

```text
(coupling, cohesion, imbalance)
```

to:

```text
F = [coupling, -cohesion, imbalance]
```

The Problem instance should keep `edges` and `weight_column` fixed so objective
evaluation does not rebuild graph inputs.
