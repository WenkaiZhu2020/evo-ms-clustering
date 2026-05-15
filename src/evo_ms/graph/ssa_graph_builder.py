"""Build G_ssa class graphs from structural and scoped SSA flow evidence."""

from collections.abc import Iterable

from evo_ms.evidence.flow_evidence import ALLOWED_SSA_FLOW_TYPES
from evo_ms.graph.weight_calculator import calculate_edge_weight


EvidenceEdge = tuple[str, str, str]


def build_ssa_graph(evidence_edges: Iterable[EvidenceEdge]):
    """Create an undirected G_ssa graph from typed evidence edges."""
    import networkx as nx

    graph = nx.Graph()
    for source, target, evidence_type in evidence_edges:
        weight = calculate_edge_weight([evidence_type])
        raw_weight = 0.0 if evidence_type in ALLOWED_SSA_FLOW_TYPES else weight
        ssa_flow_weight = weight if evidence_type in ALLOWED_SSA_FLOW_TYPES else 0.0
        if graph.has_edge(source, target):
            graph[source][target]["raw_weight"] += raw_weight
            graph[source][target]["ssa_flow_weight"] += ssa_flow_weight
            graph[source][target]["G_ssa_weight"] += weight
            graph[source][target]["evidence"].append(evidence_type)
        else:
            graph.add_edge(
                source,
                target,
                raw_weight=raw_weight,
                ssa_flow_weight=ssa_flow_weight,
                G_ssa_weight=weight,
                evidence=[evidence_type],
            )
    return graph
