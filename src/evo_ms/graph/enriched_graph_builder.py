"""Build SSA-inspired enriched class graphs from structural and flow evidence."""

from collections.abc import Iterable

from evo_ms.graph.weight_calculator import calculate_edge_weight


EvidenceEdge = tuple[str, str, str]


def build_enriched_graph(evidence_edges: Iterable[EvidenceEdge]):
    """Create an undirected enriched class graph from typed evidence edges."""
    import networkx as nx

    graph = nx.Graph()
    for source, target, evidence_type in evidence_edges:
        weight = calculate_edge_weight([evidence_type])
        if graph.has_edge(source, target):
            graph[source][target]["weight"] += weight
            graph[source][target]["evidence"].append(evidence_type)
        else:
            graph.add_edge(source, target, weight=weight, evidence=[evidence_type])
    return graph
