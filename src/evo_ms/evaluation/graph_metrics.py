"""Compute basic graph-level metrics for raw and enriched graph comparison."""


def graph_size_metrics(graph) -> dict[str, int]:
    """Return node and edge counts for a graph."""
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
    }
