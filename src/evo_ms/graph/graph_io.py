"""Read and write graph artifacts for experiments."""

from pathlib import Path



def write_graphml(graph, path: str | Path) -> None:
    """Write a graph to GraphML, creating parent directories as needed."""
    import networkx as nx

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, output_path)


def read_graphml(path: str | Path):
    """Read a graph from GraphML."""
    import networkx as nx

    return nx.read_graphml(path)
