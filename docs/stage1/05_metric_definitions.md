# Metric Definitions

This repository currently uses Stage 1 graph and clustering metrics only. The metrics describe extraction scale, graph impact, Leiden partition change, and sensitivity behaviour. They do not prove final microservice correctness.

## Scale and Feasibility Metrics

These metrics check whether the pipeline works across small, medium, and large subjects.

- `class_count`: number of extracted application classes.
- `raw_edge_count`: number of unique undirected class-pair edges in `G_raw` after aggregation.
- `g_ssa_edge_count`: number of unique undirected class-pair edges in `G_ssa` after aggregation.
- `ssa_flow_evidence_count`: number of raw SSA flow evidence rows, when recorded.

## SSA Graph Impact Metrics

These metrics check whether SSA adds graph evidence beyond raw type and call dependencies.

- `new_ssa_edge_count`: unique undirected class-pair edges present in `G_ssa` but not in `G_raw`.
- `new_ssa_edge_ratio`: `new_ssa_edge_count / g_ssa_edge_count`.
- `ssa_weight_share`: total SSA flow contribution divided by total `g_ssa_weight`.
- `cross_raw_cluster_ssa_edge_ratio`: share of SSA edges that connect classes in different raw Leiden clusters, when available.

## Partition Change Metrics

These metrics check whether SSA changes the actual Leiden clustering result.

- `raw_cluster_count`: number of Leiden clusters on `G_raw`.
- `ssa_cluster_count`: number of Leiden clusters on `G_ssa`.
- `cluster_count_delta`: `ssa_cluster_count - raw_cluster_count`.
- `ARI raw-vs-SSA`: adjusted Rand index between raw and SSA partitions.
- `NMI raw-vs-SSA`: normalized mutual information between raw and SSA partitions.
- `changed_partition_ratio`: share of classes whose same-cluster membership set changes, when available.

## Internal Structural Quality Metrics

These metrics describe whether clusters are compact and separated under the graph weights. They are internal structural metrics, not ground-truth correctness metrics.

- `weighted_modularity`: weighted Leiden partition score using `raw_weight` for `G_raw` and `g_ssa_weight` for `G_ssa`.
- `internal_edge_weight_ratio`: total intra-cluster edge weight divided by total edge weight.
- `raw_internal_edge_weight_ratio`: internal edge weight ratio for `G_raw`.
- `ssa_internal_edge_weight_ratio`: internal edge weight ratio for `G_ssa`.
- Cross-cluster edge or weight ratios, when available, describe how much weighted evidence crosses cluster boundaries.

## Granularity and Balance Metrics

These metrics detect over-fragmentation, oversized clusters, and possible hub aggregation.

- `cluster_count`: number of clusters in a run.
- `cluster_size_distribution`: grouped distribution of cluster sizes.
- `max_cluster_ratio`: largest cluster size divided by total class count.
- `singleton_ratio`: singleton cluster count divided by total class count.

## Reference-Based Metrics for DayTrader

DayTrader has a reference-service mapping, so it is used as the main calibration case.

- `mojofm_vs_reference`: MoJoFM score against the reference mapping.
- `pairwise_precision`: pairwise same-service precision against the reference.
- `pairwise_recall`: pairwise same-service recall against the reference.
- `pairwise_f1`: pairwise F1 against the reference.
- `ari_vs_reference`: ARI against the reference partition.
- `nmi_vs_reference`: NMI against the reference partition.
- `reference_coverage_ratio`: share of extracted classes covered by the reference mapping.

Reference metrics are computed only on the mapped class subset.

## Sensitivity Metrics

Sensitivity metrics check whether conclusions are stable under parameter changes.

- Resolution sweep: varies Leiden resolution to test cluster granularity.
- Lambda / SSA-weight sweep: varies SSA contribution in `g_ssa_weight(lambda)`.
- The sweep outputs record cluster count, modularity, internal edge weight ratio, balance metrics where available, and raw-vs-SSA or reference comparison metrics.

These sweeps are not used to claim that SSA is always better than raw structure. They help define safer fixed settings and stronger baselines for later Stage 2 and Stage 3 experiments.
