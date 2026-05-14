"""Build raw class dependency graphs from extracted dependency edges."""

from collections.abc import Iterable



def build_raw_graph(edges: Iterable[tuple[str, str]]):
    """Create a directed class dependency graph from source-target pairs."""
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_edges_from(edges)
    return graph
