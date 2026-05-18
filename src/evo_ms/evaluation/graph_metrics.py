def graph_size_metrics(graph) -> dict[str, int]:
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
    }
