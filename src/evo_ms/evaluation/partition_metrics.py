from collections import Counter
from collections.abc import Hashable

import pandas as pd


WEIGHT_COLUMNS = {
    "raw": "raw_weight",
    "ssa": "g_ssa_weight",
}


def calculate_partition_metrics(
    class_nodes: pd.DataFrame,
    edges: pd.DataFrame,
    clusters: pd.DataFrame,
    subject: str,
    algorithm: str,
    graph_type: str,
) -> pd.DataFrame:
    weight_column = _weight_column(graph_type)
    _validate_class_nodes(class_nodes)
    _validate_clusters(clusters)
    _validate_edges(edges, weight_column)

    cluster_by_class = dict(
        zip(clusters["class_id"].astype(str), clusters["cluster_id"], strict=True)
    )
    cluster_sizes = clusters.groupby("cluster_id").size()
    internal_weight, external_weight = _edge_weight_split(edges, cluster_by_class, weight_column)

    return pd.DataFrame(
        [
            {
                "subject": subject,
                "algorithm": algorithm,
                "graph_type": graph_type,
                "cluster_count": int(cluster_sizes.size),
                "modularity": _weighted_modularity(edges, cluster_by_class, weight_column),
                "average_cluster_size": float(cluster_sizes.mean()) if not cluster_sizes.empty else 0.0,
                "max_cluster_size": int(cluster_sizes.max()) if not cluster_sizes.empty else 0,
                "min_cluster_size": int(cluster_sizes.min()) if not cluster_sizes.empty else 0,
                "internal_external_edge_ratio": _safe_internal_external_ratio(
                    internal_weight,
                    external_weight,
                ),
            }
        ]
    )


def partition_size_metrics(partition: dict[Hashable, int]) -> dict[str, float]:
    sizes = Counter(partition.values())
    if not sizes:
        return {"clusters": 0, "average_cluster_size": 0.0}
    return {
        "clusters": len(sizes),
        "average_cluster_size": len(partition) / len(sizes),
    }


def _weight_column(graph_type: str) -> str:
    try:
        return WEIGHT_COLUMNS[graph_type]
    except KeyError as exc:
        raise ValueError("graph_type must be 'raw' or 'ssa'") from exc


def _validate_class_nodes(class_nodes: pd.DataFrame) -> None:
    missing = [column for column in ["class_id"] if column not in class_nodes.columns]
    if missing:
        raise ValueError(f"class_nodes is missing required columns: {', '.join(missing)}")


def _validate_clusters(clusters: pd.DataFrame) -> None:
    missing = [column for column in ["class_id", "cluster_id"] if column not in clusters.columns]
    if missing:
        raise ValueError(f"clusters is missing required columns: {', '.join(missing)}")
    if clusters["class_id"].astype(str).duplicated().any():
        raise ValueError("clusters contains duplicate class_id values")


def _validate_edges(edges: pd.DataFrame, weight_column: str) -> None:
    missing = [column for column in ["source", "target", weight_column] if column not in edges.columns]
    if missing:
        raise ValueError(f"edges is missing required columns: {', '.join(missing)}")
    weights = pd.to_numeric(edges[weight_column], errors="coerce")
    if weights.isna().any():
        raise ValueError(f"edges contains non-numeric {weight_column} values")
    if (weights < 0).any():
        raise ValueError(f"edges contains negative {weight_column} values")


def _edge_weight_split(
    edges: pd.DataFrame,
    cluster_by_class: dict[str, int],
    weight_column: str,
) -> tuple[float, float]:
    internal_weight = 0.0
    external_weight = 0.0
    for row in edges.to_dict("records"):
        source_cluster = cluster_by_class.get(str(row["source"]))
        target_cluster = cluster_by_class.get(str(row["target"]))
        if source_cluster is None or target_cluster is None:
            continue
        weight = float(row[weight_column])
        if source_cluster == target_cluster:
            internal_weight += weight
        else:
            external_weight += weight
    return internal_weight, external_weight


def _safe_internal_external_ratio(internal_weight: float, external_weight: float) -> float:
    if external_weight == 0:
        return float(internal_weight) if internal_weight > 0 else 0.0
    return float(internal_weight / external_weight)


def _weighted_modularity(
    edges: pd.DataFrame,
    cluster_by_class: dict[str, int],
    weight_column: str,
) -> float:
    if edges.empty:
        return 0.0

    adjacency: dict[str, dict[str, float]] = {}
    total_weight = 0.0
    for row in edges.to_dict("records"):
        source = str(row["source"])
        target = str(row["target"])
        if source not in cluster_by_class or target not in cluster_by_class:
            continue
        weight = float(row[weight_column])
        if weight == 0:
            continue
        _add_adjacency_weight(adjacency, source, target, weight)
        _add_adjacency_weight(adjacency, target, source, weight)
        total_weight += weight

    if total_weight == 0:
        return 0.0

    degree = {node: sum(neighbors.values()) for node, neighbors in adjacency.items()}
    modularity = 0.0
    doubled_weight = 2.0 * total_weight
    for source, source_degree in degree.items():
        for target, target_degree in degree.items():
            if cluster_by_class[source] != cluster_by_class[target]:
                continue
            edge_weight = adjacency.get(source, {}).get(target, 0.0)
            modularity += edge_weight - (source_degree * target_degree / doubled_weight)

    return float(modularity / doubled_weight)


def _add_adjacency_weight(
    adjacency: dict[str, dict[str, float]],
    source: str,
    target: str,
    weight: float,
) -> None:
    neighbors = adjacency.setdefault(source, {})
    neighbors[target] = neighbors.get(target, 0.0) + weight
