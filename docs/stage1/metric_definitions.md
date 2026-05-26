# Metric Definitions

This branch uses Stage 1 graph and clustering metrics only.

Graph-level diagnostics describe the input graph before clustering. They are useful for comparing `G_raw` and `G_ssa`, but they do not prove decomposition quality.

- Node count: number of classes represented as graph nodes.
- Edge count: number of dependency edges between classes.
- Graph density: ratio of observed edges to possible edges.
- Average degree: mean number of incident edges per node.

Partition-level metrics describe Leiden output clusters.

- Number of clusters: number of communities produced by Leiden.
- Modularity: weighted partition score using `raw_weight` for `raw` and `g_ssa_weight` for `ssa`.
- Cluster size distribution: minimum, maximum, average, and grouped cluster sizes where available.
- Max cluster ratio: largest cluster size divided by total class count.
- Singleton ratio: singleton cluster count divided by total class count.
- Internal/external edge ratio: ratio of weighted edges inside clusters to weighted edges crossing cluster boundaries.
- Internal edge weight ratio: weighted internal edges divided by total edge weight.

Raw-vs-SSA comparison metrics describe how `G_ssa` changes the graph and partition.

- New SSA edge count: unique undirected class-pair edges present in `G_ssa` but not in `G_raw`.
- New SSA edge ratio: `new_ssa_edge_count / g_ssa_edge_count`.
- SSA weight share: total SSA flow contribution divided by total `g_ssa_weight`.
- Cross raw-cluster SSA edge ratio: share of `G_ssa` edges that cross the raw Leiden clusters.
- ARI raw-vs-SSA: adjusted Rand index between raw and SSA partitions.
- NMI raw-vs-SSA: normalized mutual information between raw and SSA partitions.

Reference-based metrics are currently used for DayTrader calibration when a reference mapping is available.

- MoJoFM: reference-based decomposition similarity.
- Pairwise precision, recall, and F1: pairwise same-service agreement against the reference mapping.
- Reference coverage ratio: share of extracted classes covered by the reference mapping.
