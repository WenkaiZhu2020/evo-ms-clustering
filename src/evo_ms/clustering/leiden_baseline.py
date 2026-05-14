"""Run the Stage 1 Leiden community detection baseline on enriched graphs."""

from collections.abc import Hashable



def run_leiden_baseline(
    graph,
    resolution: float = 1.0,
    seed: int | None = 42,
) -> dict[Hashable, int]:
    """Return a node-to-cluster mapping for the Leiden baseline.

    This placeholder preserves the public API while the full Leiden integration is staged.
    """
    import networkx as nx

    # TODO: Convert NetworkX graphs to igraph and call leidenalg.find_partition.
    _ = (resolution, seed)
    partition: dict[Hashable, int] = {}
    for cluster_id, component in enumerate(nx.connected_components(graph)):
        for node in component:
            partition[node] = cluster_id
    return partition
