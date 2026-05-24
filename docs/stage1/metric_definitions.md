# Metric Definitions

This branch uses early-stage graph and clustering metrics only.

Graph-level diagnostics describe the input graph before clustering. They are useful for comparing `G_raw` and `G_ssa`, but they do not prove decomposition quality.

- Node count: number of classes represented as graph nodes.
- Edge count: number of dependency edges between classes.
- Graph density: ratio of observed edges to possible edges.
- Average degree: mean number of incident edges per node.

Partition-level metrics describe Leiden output clusters.

- Number of clusters: number of communities produced by Leiden.
- Modularity: weighted partition score using `raw_weight` for `raw` and `g_ssa_weight` for `ssa`.
- Cluster size distribution: minimum, maximum, and average cluster sizes.
- Internal/external edge ratio: ratio of weighted edges inside clusters to weighted edges crossing cluster boundaries.
