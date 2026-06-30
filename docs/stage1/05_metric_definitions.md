
# Metric Definitions

Stage 1 metrics describe graph scale, SSA impact, partition change, structural quality, and DayTrader calibration.

They are used to compare graph settings and Leiden outputs. They do not prove final microservice correctness.

## Notation

The formulas below use the following notation:

| Symbol | Meaning |
| --- | --- |
| `V` | extracted class set |
| `n = |V|` | number of extracted classes |
| `E_raw` | unique undirected class-pair edges in `G_raw` |
| `E_ssa` | unique undirected class-pair edges in `G_ssa` |
| `w_e` | active edge weight for edge `e`; `raw_weight` on `G_raw`, `g_ssa_weight` on `G_ssa` |
| `C` | clustering/partition, mapping each class to a cluster |
| `k = |C|` | number of clusters |
| `size(c)` | number of classes in cluster `c` |
| `W_internal` | sum of weights for edges whose endpoints are in the same cluster |
| `W_external` | sum of weights for edges whose endpoints are in different clusters |
| `W_total = W_internal + W_external` | total active edge weight considered by the metric |
| `choose2(x) = x * (x - 1) / 2` | unordered pair count |

## Graph Scale

| Metric | Meaning | Formula / calculation |
| --- | --- | --- |
| `class_count` | number of extracted application classes | `|V|` |
| `raw_edge_count` | number of unique undirected edges in `G_raw` | `|E_raw|` after self-loop removal and undirected aggregation |
| `g_ssa_edge_count` | number of unique undirected edges in `G_ssa` | `|E_ssa|` after raw/SSA outer join, self-loop removal, and zero-weight filtering |
| `ssa_flow_evidence_count` | number of raw SSA flow evidence rows | `len(ssa_flow_edges)` |
| `node_count` | number of graph nodes | `|V|` in the NetworkX graph |
| `edge_count` | number of graph edges | `|E|` in the undirected graph view |
| `density` | graph density | `2 * |E| / (n * (n - 1))` for an undirected simple graph |
| `average_degree` | average undirected graph degree | `sum(degree(v) for v in V) / n`; `0.0` when `n = 0` |

Stage 1 edge weights are:

```text
raw_weight = type_weight + call_weight
ssa_flow_weight = ssa_lambda * (return_flow_weight + argument_flow_weight)
g_ssa_weight = raw_weight + ssa_flow_weight
```

## SSA Graph Impact

| Metric | Meaning | Formula / calculation |
| --- | --- | --- |
| `new_ssa_edge_count` | `G_ssa` edges that do not exist in `G_raw` | `|E_ssa - E_raw|` |
| `new_ssa_edge_ratio` | share of `G_ssa` edges introduced only by SSA evidence | `new_ssa_edge_count / g_ssa_edge_count`; `0.0` if the denominator is `0` |
| `ssa_weight_share` | SSA flow contribution divided by total `g_ssa_weight` | `sum(ssa_flow_weight) / sum(g_ssa_weight)` over `E_ssa`; `0.0` if the denominator is `0` |
| `cross_raw_cluster_ssa_edge_ratio` | `G_ssa` edges that cross raw Leiden clusters | `count((u, v) in E_ssa where C_raw(u) != C_raw(v)) / |E_ssa|`; `0.0` if `E_ssa` is empty |

## Partition Change

| Metric | Meaning | Formula / calculation |
| --- | --- | --- |
| `raw_cluster_count` | number of Leiden clusters on `G_raw` | `|C_raw|` |
| `ssa_cluster_count` | number of Leiden clusters on `G_ssa` | `|C_ssa|` |
| `cluster_count_delta` | change in cluster count after adding SSA evidence | `ssa_cluster_count - raw_cluster_count` |
| `ari_raw_vs_ssa` | adjusted Rand index between raw and SSA partitions | `ARI(C_raw, C_ssa)` using the formula below |
| `nmi_raw_vs_ssa` | normalized mutual information between raw and SSA partitions | `NMI(C_raw, C_ssa)` using the formula below |
| `changed_partition_ratio` | share of classes whose same-cluster membership set changes | `count(v in V where neighbors_C_raw(v) != neighbors_C_ssa(v)) / |V|` |

For two partitions `A` and `B`, with contingency counts `n_ij`, row sums `a_i`,
column sums `b_j`, and `N = choose2(n)`:

```text
index = sum_ij choose2(n_ij)
expected_index = sum_i choose2(a_i) * sum_j choose2(b_j) / N
max_index = (sum_i choose2(a_i) + sum_j choose2(b_j)) / 2
ARI = (index - expected_index) / (max_index - expected_index)
```

If the ARI denominator is `0`, Stage 1 returns `1.0`.

For NMI, with natural logarithms:

```text
MI(A, B) = sum_ij (n_ij / n) * log((n_ij * n) / (a_i * b_j))
H(A) = -sum_i (a_i / n) * log(a_i / n)
H(B) = -sum_j (b_j / n) * log(b_j / n)
NMI(A, B) = MI(A, B) / sqrt(H(A) * H(B))
```

If both entropies are `0`, Stage 1 returns `1.0`; if only the denominator is
`0`, Stage 1 returns `0.0`.

## Structural Quality

| Metric | Meaning | Formula / calculation |
| --- | --- | --- |
| `weighted_modularity` / `modularity` | weighted Leiden modularity on the corresponding graph representation | `(1 / (2m)) * sum_ij [A_ij - (degree_i * degree_j / (2m))] * same_cluster(i, j)` |
| `internal_edge_weight_ratio` | internal edge weight divided by total edge weight | `W_internal / W_total`; `0.0` if `W_total = 0` |
| `internal_external_edge_ratio` | internal edge weight divided by external edge weight | `W_internal / W_external`; if `W_external = 0`, returns `W_internal` when positive, otherwise `0.0` |

For weighted modularity:

```text
m = sum of undirected edge weights
2m = doubled total edge weight in the symmetric adjacency view
A_ij = active weight between classes i and j, or 0 if no edge exists
degree_i = sum_j A_ij
same_cluster(i, j) = 1 if C(i) = C(j), otherwise 0
```

For `G_raw`, structural metrics use:

```text
raw_weight
```

For `G_ssa`, structural metrics use:

```text
g_ssa_weight
```

Raw and SSA modularity values are descriptive diagnostics for their corresponding weighted graphs. They should not be treated as a strict direct ranking across two different graph representations.

## Granularity and Balance

| Metric | Meaning | Formula / calculation |
| --- | --- | --- |
| `cluster_count` | number of clusters | `k = |C|` |
| `average_cluster_size` | average number of classes per cluster | `n / k`; `0.0` if `k = 0` |
| `max_cluster_size` | size of the largest cluster | `max(size(c) for c in C)`; `0` if no clusters exist |
| `min_cluster_size` | size of the smallest cluster | `min(size(c) for c in C)`; `0` if no clusters exist |
| `cluster_size_distribution` | cluster-size frequency map serialized for CSV output | `{size: count_of_clusters_with_that_size}` |
| `max_cluster_ratio` | largest cluster size divided by total class count | `max_cluster_size / n`; `0.0` if `n = 0` |
| `singleton_ratio` | singleton clusters divided by total class count | `count(c in C where size(c) = 1) / n`; `0.0` if `n = 0` |

## DayTrader Reference Metrics

| Metric | Meaning | Formula / calculation |
| --- | --- | --- |
| `mojofm_vs_reference` | MoJoFM against the domain-informed proxy reference partition | `max(0, min(100, (1 - MoJo(candidate, reference) / MaxMoJo(reference)) * 100))` |
| `pairwise_precision` | same-service precision | `TP / |candidate_same_cluster_pairs|`; `0.0` if the denominator is `0` |
| `pairwise_recall` | same-service recall | `TP / |reference_same_service_pairs|`; `0.0` if the denominator is `0` |
| `pairwise_f1` | same-service F1 | `2 * precision * recall / (precision + recall)`; `0.0` if `precision + recall = 0` |
| `ari_vs_reference` | ARI against the domain-informed proxy reference partition | `ARI(candidate, reference)` on mapped classes |
| `nmi_vs_reference` | NMI against the domain-informed proxy reference partition | `NMI(candidate, reference)` on mapped classes |
| `reference_coverage_ratio` | mapped extracted classes divided by extracted classes | `mapped_class_count / extracted_class_count`; `0.0` if no extracted classes exist |

Reference metrics are calculated only on mapped classes.

The pairwise metrics use:

```text
candidate_same_cluster_pairs = {(u, v): candidate(u) = candidate(v)}
reference_same_service_pairs = {(u, v): reference(u) = reference(v)}
TP = |candidate_same_cluster_pairs intersect reference_same_service_pairs|
```

The MoJoFM implementation computes the directional Move/Join distance from the
candidate partition to the reference partition. If `MaxMoJo(reference) <= 0`,
Stage 1 returns `100.0` for an exact zero-distance match and `0.0` otherwise.

## Seed Robustness Metrics

| Metric | Meaning | Formula / calculation |
| --- | --- | --- |
| `ssa_effect_ari_mean` | average raw-vs-SSA similarity over matched seeds | `mean(ARI(C_raw_seed_i, C_ssa_seed_i))` |
| `ssa_effect_ari_std` | sample standard deviation of raw-vs-SSA ARI values | `std(ARI(C_raw_seed_i, C_ssa_seed_i), ddof=1)`; `0.0` with fewer than two values |
| `ssa_effect_dist_mean` | average raw-vs-SSA distance over matched seeds | `mean(1 - ARI(C_raw_seed_i, C_ssa_seed_i))` |
| `ssa_effect_dist_std` | sample standard deviation of raw-vs-SSA distances | `std(1 - ARI(C_raw_seed_i, C_ssa_seed_i), ddof=1)`; `0.0` with fewer than two values |
| `seed_noise_ari_mean` | average raw-vs-raw similarity over seed pairs | `mean(ARI(C_raw_seed_i, C_raw_seed_j))` for all `i < j` |
| `seed_noise_ari_std` | sample standard deviation of raw-vs-raw ARI values | `std(ARI(C_raw_seed_i, C_raw_seed_j), ddof=1)` for all `i < j`; `0.0` with fewer than two values |
| `seed_noise_dist_mean` | average raw-vs-raw seed-noise distance | `mean(1 - ARI(C_raw_seed_i, C_raw_seed_j))` for all `i < j` |
| `seed_noise_dist_std` | sample standard deviation of raw-vs-raw seed-noise distances | `std(1 - ARI(C_raw_seed_i, C_raw_seed_j), ddof=1)` for all `i < j`; `0.0` with fewer than two values |
| `seed_noise_dist_2std_low` | lower two-standard-deviation seed-noise band | `seed_noise_dist_mean - 2 * seed_noise_dist_std` |
| `seed_noise_dist_2std_high` | upper two-standard-deviation seed-noise band | `seed_noise_dist_mean + 2 * seed_noise_dist_std` |
| `ssa_effect_dist_in_seed_noise_band` | whether the SSA effect is within the seed-noise band | `seed_noise_dist_2std_low <= ssa_effect_dist_mean <= seed_noise_dist_2std_high` |
| `seed_noise_identical_pair_frac` | fraction of raw reseed pairs with identical partitions | `count(seed_noise_ari = 1.0) / n_seed_noise_pairs` |
| `reseeds_ge_mean_ssa_effect_frac` | fraction of raw reseed distances at least as large as the mean SSA effect | `count(seed_noise_dist >= ssa_effect_dist_mean) / n_seed_noise_pairs` |
| `mannwhitney_p` | Mann-Whitney U p-value for SSA-effect distances vs seed-noise distances | two-sided Mann-Whitney U test over the two distance samples |

The Mann-Whitney U implementation ranks the combined distance samples with tie
correction and continuity correction. It is reported as a guideline because the
raw-vs-raw seed-noise pairs share partitions and are not fully independent.

## Use of Metrics

The metric groups serve different purposes:

| Metric Group                | Main Use                                         |
| --------------------------- | ------------------------------------------------ |
| graph scale                 | check extraction size and graph enrichment       |
| SSA graph impact            | measure how much SSA changes the graph           |
| partition change            | compare raw and SSA Leiden outputs               |
| structural quality          | inspect cohesion and separation inside the graph |
| granularity and balance     | detect oversized clusters or fragmentation       |
| DayTrader reference metrics | provide secondary sanity checks during calibration |
| seed robustness metrics     | compare SSA-induced partition movement with Leiden seed noise |
