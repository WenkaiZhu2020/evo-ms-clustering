from pathlib import Path


def write_graphml(graph, path: str | Path) -> None:
    import networkx as nx

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, output_path)


def read_graphml(path: str | Path):
    import networkx as nx

    return nx.read_graphml(path)


def write_raw_edges_csv(raw_edges, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_edges.to_csv(output_path, index=False)


def write_ssa_edges_csv(ssa_edges, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ssa_edges.to_csv(output_path, index=False)
