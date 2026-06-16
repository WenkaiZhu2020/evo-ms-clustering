
# Metric Definitions

Stage 1 metrics describe graph scale, SSA impact, partition change, structural quality, and DayTrader calibration.

They are used to compare graph settings and Leiden outputs. They do not prove final microservice correctness.

## Graph Scale

| Metric | Meaning |
| --- | --- |
| `class_count` | number of extracted application classes |
| `raw_edge_count` | number of unique undirected edges in `G_raw` |
| `g_ssa_edge_count` | number of unique undirected edges in `G_ssa` |
| `ssa_flow_evidence_count` | number of raw SSA flow evidence rows |

## SSA Graph Impact

| Metric | Meaning |
| --- | --- |
| `new_ssa_edge_count` | `G_ssa` edges that do not exist in `G_raw` |
| `new_ssa_edge_ratio` | `new_ssa_edge_count / g_ssa_edge_count` |
| `ssa_weight_share` | SSA flow contribution divided by total `g_ssa_weight` |
| `cross_raw_cluster_ssa_edge_ratio` | SSA edges that cross raw Leiden clusters |

## Partition Change

| Metric | Meaning |
| --- | --- |
| `raw_cluster_count` | number of Leiden clusters on `G_raw` |
| `ssa_cluster_count` | number of Leiden clusters on `G_ssa` |
| `cluster_count_delta` | `ssa_cluster_count - raw_cluster_count` |
| `ari_raw_vs_ssa` | adjusted Rand index between raw and SSA partitions |
| `nmi_raw_vs_ssa` | normalized mutual information between raw and SSA partitions |
| `changed_partition_ratio` | share of classes whose same-cluster membership set changes |

## Structural Quality

| Metric | Meaning |
| --- | --- |
| `weighted_modularity` | weighted Leiden modularity on the corresponding graph representation |
| `internal_edge_weight_ratio` | internal edge weight divided by total edge weight |
| `internal_external_edge_ratio` | internal edge weight divided by external edge weight |

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

| Metric                      | Meaning                                           |
| --------------------------- | ------------------------------------------------- |
| `cluster_count`             | number of clusters                                |
| `cluster_size_distribution` | cluster sizes grouped by cluster                  |
| `max_cluster_ratio`         | largest cluster size divided by total class count |
| `singleton_ratio`           | singleton clusters divided by total class count   |

## DayTrader Reference Metrics

| Metric                     | Meaning                                               |
| -------------------------- | ----------------------------------------------------- |
| `mojofm_vs_reference`      | MoJoFM against the domain-informed proxy reference partition |
| `pairwise_precision`       | same-service precision                                |
| `pairwise_recall`          | same-service recall                                   |
| `pairwise_f1`              | same-service F1                                       |
| `ari_vs_reference`         | ARI against the domain-informed proxy reference partition |
| `nmi_vs_reference`         | NMI against the domain-informed proxy reference partition |
| `reference_coverage_ratio` | mapped extracted classes divided by extracted classes |

Reference metrics are calculated only on mapped classes.

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
