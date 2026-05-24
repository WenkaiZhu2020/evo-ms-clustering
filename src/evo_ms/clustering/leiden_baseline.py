import pandas as pd


WEIGHT_COLUMNS = {
    "raw": "raw_weight",
    "ssa": "g_ssa_weight",
}


def run_leiden_baseline(
    class_nodes: pd.DataFrame,
    edges: pd.DataFrame,
    graph_type: str = "ssa",
    resolution: float = 1.0,
    seed: int | None = 42,
) -> pd.DataFrame:
    weight_column = _weight_column(graph_type)
    _validate_class_nodes(class_nodes)
    _validate_edges(edges, weight_column, class_nodes)

    try:
        import igraph as ig
        import leidenalg
    except ImportError as exc:
        raise RuntimeError("Leiden baseline requires igraph and leidenalg") from exc

    nodes = class_nodes.loc[:, ["class_id", "class_name"]].copy()
    nodes["class_id"] = nodes["class_id"].astype("string")
    node_ids = nodes["class_id"].astype(str).tolist()
    index_by_id = {class_id: index for index, class_id in enumerate(node_ids)}

    edge_pairs = [
        (index_by_id[str(row["source"])], index_by_id[str(row["target"])])
        for row in edges.to_dict("records")
    ]
    weights = pd.to_numeric(edges[weight_column], errors="coerce").astype(float).tolist()

    graph = ig.Graph(n=len(node_ids), edges=edge_pairs, directed=False)
    graph.vs["class_id"] = node_ids
    graph.es["weight"] = weights

    partition = leidenalg.find_partition(
        graph,
        leidenalg.RBConfigurationVertexPartition,
        weights="weight",
        resolution_parameter=resolution,
        seed=seed,
    )

    return pd.DataFrame(
        {
            "class_id": nodes["class_id"].astype(str),
            "class_name": nodes["class_name"],
            "cluster_id": partition.membership,
        }
    )


def _weight_column(graph_type: str) -> str:
    try:
        return WEIGHT_COLUMNS[graph_type]
    except KeyError as exc:
        raise ValueError("graph_type must be 'raw' or 'ssa'") from exc


def _validate_class_nodes(class_nodes: pd.DataFrame) -> None:
    missing = [column for column in ["class_id", "class_name"] if column not in class_nodes.columns]
    if missing:
        raise ValueError(f"class_nodes is missing required columns: {', '.join(missing)}")
    if class_nodes["class_id"].isna().any():
        raise ValueError("class_nodes contains missing class_id values")
    if class_nodes["class_id"].astype(str).duplicated().any():
        raise ValueError("class_nodes contains duplicate class_id values")


def _validate_edges(edges: pd.DataFrame, weight_column: str, class_nodes: pd.DataFrame) -> None:
    required = ["source", "target", weight_column]
    missing = [column for column in required if column not in edges.columns]
    if missing:
        raise ValueError(f"edges is missing required columns: {', '.join(missing)}")

    weights = pd.to_numeric(edges[weight_column], errors="coerce")
    if weights.isna().any():
        raise ValueError(f"edges contains non-numeric {weight_column} values")
    if (weights < 0).any():
        raise ValueError(f"edges contains negative {weight_column} values")

    class_ids = set(class_nodes["class_id"].dropna().astype(str))
    edge_ids = set(edges["source"].dropna().astype(str)) | set(edges["target"].dropna().astype(str))
    missing = sorted(edge_ids - class_ids)
    if missing:
        raise ValueError(f"edges contain source/target values not present in class_nodes: {', '.join(missing)}")
