# Metric Definitions

This branch uses early-stage graph and clustering metrics only. Graph-level metrics are diagnostic input-level measurements for comparing `G_raw` and `G_ssa`; they are not final decomposition-quality claims.

- Node count: number of classes represented as graph nodes.
- Edge count: number of dependency edges between classes.
- Graph density: ratio of observed edges to possible edges.
- Average degree: mean number of incident edges per node.
- Number of clusters: number of communities produced by Leiden.
- Modularity: quality score for the graph partition.
- Cluster size distribution: minimum, maximum, and average cluster sizes.
- Internal/external edge ratio: ratio of edges inside clusters to edges crossing cluster boundaries.
