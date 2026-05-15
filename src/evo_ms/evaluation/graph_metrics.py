"""Compute basic graph-level metrics for G_raw and G_ssa comparison."""


def graph_size_metrics(graph) -> dict[str, int]:
    """Return node and edge counts for a graph."""
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
    }
