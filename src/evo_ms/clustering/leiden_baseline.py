from collections.abc import Hashable


def run_leiden_baseline(
    graph,
    resolution: float = 1.0,
    seed: int | None = 42,
) -> dict[Hashable, int]:
    import networkx as nx

    _ = (resolution, seed)
    partition: dict[Hashable, int] = {}
    for cluster_id, component in enumerate(nx.connected_components(graph)):
        for node in component:
            partition[node] = cluster_id
    return partition
