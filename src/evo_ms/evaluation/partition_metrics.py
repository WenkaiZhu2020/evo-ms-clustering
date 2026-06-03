import json
import math
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
    total_edge_weight = internal_weight + external_weight
    class_count = int(len(class_nodes))
    max_cluster_size = int(cluster_sizes.max()) if not cluster_sizes.empty else 0
    singleton_count = int((cluster_sizes == 1).sum()) if not cluster_sizes.empty else 0

    return pd.DataFrame(
        [
            {
                "subject": subject,
                "algorithm": algorithm,
                "graph_type": graph_type,
                "cluster_count": int(cluster_sizes.size),
                "modularity": _weighted_modularity(edges, cluster_by_class, weight_column),
                "average_cluster_size": float(cluster_sizes.mean()) if not cluster_sizes.empty else 0.0,
                "max_cluster_size": max_cluster_size,
                "min_cluster_size": int(cluster_sizes.min()) if not cluster_sizes.empty else 0,
                "max_cluster_ratio": _safe_ratio(max_cluster_size, class_count),
                "singleton_ratio": _safe_ratio(singleton_count, class_count),
                "internal_external_edge_ratio": _safe_internal_external_ratio(
                    internal_weight,
                    external_weight,
                ),
                "internal_edge_weight_ratio": _safe_ratio(internal_weight, total_edge_weight),
            }
        ]
    )


def calculate_stage1_smoke_metrics(
    class_nodes: pd.DataFrame,
    raw_edges: pd.DataFrame,
    ssa_edges: pd.DataFrame,
    raw_clusters: pd.DataFrame,
    ssa_clusters: pd.DataFrame,
    subject: str,
    algorithm: str = "leiden",
    ssa_flow_edges: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return one-row Stage 1 smoke-run metrics for raw-vs-SSA verification."""
    _validate_class_nodes(class_nodes)
    _validate_clusters(raw_clusters)
    _validate_clusters(ssa_clusters)
    _validate_edges(raw_edges, "raw_weight")
    _validate_edges(ssa_edges, "g_ssa_weight")

    class_ids = class_nodes["class_id"].dropna().astype(str).tolist()
    raw_partition = _cluster_by_class_for_nodes(raw_clusters, class_ids, "raw_clusters")
    ssa_partition = _cluster_by_class_for_nodes(ssa_clusters, class_ids, "ssa_clusters")

    raw_edge_keys = _undirected_edge_keys(raw_edges)
    ssa_edge_keys = _undirected_edge_keys(ssa_edges)
    raw_edge_count = int(len(raw_edge_keys))
    g_ssa_edge_count = int(len(ssa_edge_keys))
    new_ssa_edge_count = int(len(ssa_edge_keys - raw_edge_keys))

    total_ssa_flow_weight = _total_ssa_flow_weight(ssa_edges)
    total_g_ssa_weight = _sum_weight(ssa_edges, "g_ssa_weight")

    raw_sizes = _cluster_sizes(raw_clusters)
    ssa_sizes = _cluster_sizes(ssa_clusters)

    raw_cluster_count = int(len(raw_sizes))
    ssa_cluster_count = int(len(ssa_sizes))
    raw_max_cluster_ratio = _safe_ratio(max(raw_sizes, default=0), len(class_ids))
    ssa_max_cluster_ratio = _safe_ratio(max(ssa_sizes, default=0), len(class_ids))
    raw_singleton_ratio = _safe_ratio(sum(1 for size in raw_sizes if size == 1), len(class_ids))
    ssa_singleton_ratio = _safe_ratio(sum(1 for size in ssa_sizes if size == 1), len(class_ids))

    return pd.DataFrame(
        [
            {
                "subject": subject,
                "algorithm": algorithm,
                "class_count": int(len(class_ids)),
                "raw_edge_count": raw_edge_count,
                "g_ssa_edge_count": g_ssa_edge_count,
                "new_ssa_edge_count": new_ssa_edge_count,
                "new_ssa_edge_ratio": _safe_ratio(new_ssa_edge_count, g_ssa_edge_count),
                "ssa_flow_evidence_count": 0 if ssa_flow_edges is None else int(len(ssa_flow_edges)),
                "ssa_weight_share": _safe_ratio(total_ssa_flow_weight, total_g_ssa_weight),
                "cross_raw_cluster_ssa_edge_ratio": _cross_cluster_edge_ratio(
                    ssa_edges,
                    raw_partition,
                ),
                "raw_cluster_count": raw_cluster_count,
                "ssa_cluster_count": ssa_cluster_count,
                "cluster_count_delta": int(ssa_cluster_count - raw_cluster_count),
                "ari_raw_vs_ssa": _adjusted_rand_index(raw_partition, ssa_partition, class_ids),
                "nmi_raw_vs_ssa": _normalized_mutual_information(
                    raw_partition,
                    ssa_partition,
                    class_ids,
                ),
                "raw_max_cluster_ratio": raw_max_cluster_ratio,
                "ssa_max_cluster_ratio": ssa_max_cluster_ratio,
                "max_cluster_ratio": ssa_max_cluster_ratio,
                "raw_singleton_ratio": raw_singleton_ratio,
                "ssa_singleton_ratio": ssa_singleton_ratio,
                "singleton_ratio": ssa_singleton_ratio,
                "raw_cluster_size_distribution": _cluster_size_distribution(raw_sizes),
                "ssa_cluster_size_distribution": _cluster_size_distribution(ssa_sizes),
                "cluster_size_distribution": _cluster_size_distribution(ssa_sizes),
                "raw_weighted_modularity": _weighted_modularity(
                    raw_edges,
                    raw_partition,
                    "raw_weight",
                ),
                "ssa_weighted_modularity": _weighted_modularity(
                    ssa_edges,
                    ssa_partition,
                    "g_ssa_weight",
                ),
                "raw_internal_edge_weight_ratio": _internal_edge_weight_ratio(
                    raw_edges,
                    raw_partition,
                    "raw_weight",
                ),
                "ssa_internal_edge_weight_ratio": _internal_edge_weight_ratio(
                    ssa_edges,
                    ssa_partition,
                    "g_ssa_weight",
                ),
            }
        ]
    )


def calculate_ssa_impact_tables(
    raw_edges: pd.DataFrame,
    ssa_edges: pd.DataFrame,
    raw_clusters: pd.DataFrame,
    ssa_clusters: pd.DataFrame,
    ssa_flow_edges: pd.DataFrame | None = None,
    top_n: int = 20,
) -> dict[str, pd.DataFrame]:
    """Build human-readable tables explaining what SSA changed."""
    _validate_edges(raw_edges, "raw_weight")
    _validate_edges(ssa_edges, "g_ssa_weight")
    _validate_clusters(raw_clusters)
    _validate_clusters(ssa_clusters)

    pair_weights = _pair_weight_table(raw_edges, ssa_edges)
    flow_summary = _flow_type_summary_by_pair(ssa_flow_edges)
    impact = pair_weights.merge(flow_summary, on=["class_pair_key"], how="left")
    impact["flow_type_summary"] = impact["flow_type_summary"].fillna("")
    impact["weight_increase"] = impact["g_ssa_weight"] - impact["raw_weight"]

    new_edges = (
        impact.loc[impact["is_new_ssa_edge"]]
        .sort_values(
            ["g_ssa_weight", "ssa_flow_weight", "source", "target"],
            ascending=[False, False, True, True],
        )
        .head(top_n)
        .loc[
            :,
            [
                "source",
                "target",
                "raw_weight",
                "ssa_flow_weight",
                "g_ssa_weight",
                "flow_type_summary",
            ],
        ]
        .reset_index(drop=True)
    )

    increased_edges = (
        impact.loc[impact["weight_increase"] > 0]
        .sort_values(
            ["weight_increase", "g_ssa_weight", "source", "target"],
            ascending=[False, False, True, True],
        )
        .head(top_n)
        .loc[
            :,
            [
                "source",
                "target",
                "raw_weight",
                "g_ssa_weight",
                "ssa_flow_weight",
                "weight_increase",
                "flow_type_summary",
            ],
        ]
        .reset_index(drop=True)
    )

    return {
        "top_new_ssa_edges": new_edges,
        "top_weight_increased_edges": increased_edges,
        "top_moved_classes": _moved_classes(raw_clusters, ssa_clusters),
    }


def partition_size_metrics(partition: dict[Hashable, int]) -> dict[str, float]:
    sizes = Counter(partition.values())
    if not sizes:
        return {"clusters": 0, "average_cluster_size": 0.0}
    return {
        "clusters": len(sizes),
        "average_cluster_size": len(partition) / len(sizes),
    }


def cluster_size_distribution(clusters: pd.DataFrame) -> str:
    _validate_clusters(clusters)
    return _cluster_size_distribution(_cluster_sizes(clusters))


def partition_similarity(
    class_nodes: pd.DataFrame,
    left_clusters: pd.DataFrame,
    right_clusters: pd.DataFrame,
) -> tuple[float, float]:
    _validate_class_nodes(class_nodes)
    _validate_clusters(left_clusters)
    _validate_clusters(right_clusters)
    class_ids = class_nodes["class_id"].dropna().astype(str).tolist()
    left = _cluster_by_class_for_nodes(left_clusters, class_ids, "left_clusters")
    right = _cluster_by_class_for_nodes(right_clusters, class_ids, "right_clusters")
    return (
        _adjusted_rand_index(left, right, class_ids),
        _normalized_mutual_information(left, right, class_ids),
    )


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


def _safe_ratio(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0 else float(numerator / denominator)


def _cluster_by_class_for_nodes(
    clusters: pd.DataFrame,
    class_ids: list[str],
    name: str,
) -> dict[str, int]:
    cluster_by_class = dict(
        zip(clusters["class_id"].astype(str), clusters["cluster_id"], strict=True)
    )
    missing = sorted(class_id for class_id in class_ids if class_id not in cluster_by_class)
    if missing:
        raise ValueError(f"{name} is missing class_id values: {', '.join(missing)}")
    return {class_id: int(cluster_by_class[class_id]) for class_id in class_ids}


def _cluster_sizes(clusters: pd.DataFrame) -> list[int]:
    return sorted((int(size) for size in clusters.groupby("cluster_id").size()), reverse=True)


def _cluster_size_distribution(sizes: list[int]) -> str:
    distribution = Counter(sizes)
    return json.dumps(
        {str(size): int(count) for size, count in sorted(distribution.items())},
        sort_keys=True,
    )


def _pair_weight_table(raw_edges: pd.DataFrame, ssa_edges: pd.DataFrame) -> pd.DataFrame:
    raw_pairs = _aggregate_edge_pairs(raw_edges, ["raw_weight"])
    ssa_pairs = _aggregate_edge_pairs(ssa_edges, ["g_ssa_weight", "ssa_flow_weight"])
    combined = raw_pairs.merge(ssa_pairs, on=["class_pair_key", "source", "target"], how="outer")
    for column in ["raw_weight", "g_ssa_weight", "ssa_flow_weight"]:
        if column not in combined:
            combined[column] = 0.0
        combined[column] = combined[column].fillna(0.0)
    combined["is_new_ssa_edge"] = (combined["raw_weight"] == 0) & (combined["g_ssa_weight"] > 0)
    return combined


def _aggregate_edge_pairs(edges: pd.DataFrame, weight_columns: list[str]) -> pd.DataFrame:
    rows = []
    for row in edges.to_dict("records"):
        source, target = _undirected_pair(str(row["source"]), str(row["target"]))
        if source == target:
            continue
        record = {"class_pair_key": _class_pair_key(source, target), "source": source, "target": target}
        for column in weight_columns:
            record[column] = float(row[column]) if column in row and pd.notna(row[column]) else 0.0
        rows.append(record)

    columns = ["class_pair_key", "source", "target", *weight_columns]
    if not rows:
        return pd.DataFrame(columns=columns)
    return (
        pd.DataFrame(rows)
        .groupby(["class_pair_key", "source", "target"], as_index=False)[weight_columns]
        .sum()
        .loc[:, columns]
    )


def _flow_type_summary_by_pair(ssa_flow_edges: pd.DataFrame | None) -> pd.DataFrame:
    columns = ["class_pair_key", "flow_type_summary"]
    if ssa_flow_edges is None or ssa_flow_edges.empty:
        return pd.DataFrame(columns=columns)

    _validate_flow_edges_for_summary(ssa_flow_edges)
    summaries = []
    flows = ssa_flow_edges.loc[:, ["source", "target", "flow_type", "weight"]].copy()
    flows["weight"] = pd.to_numeric(flows["weight"], errors="coerce").fillna(0.0)
    for row in flows.to_dict("records"):
        source, target = _undirected_pair(str(row["source"]), str(row["target"]))
        summaries.append(
            {
                "class_pair_key": _class_pair_key(source, target),
                "flow_type": str(row["flow_type"]),
                "weight": float(row["weight"]),
            }
        )
    if not summaries:
        return pd.DataFrame(columns=columns)

    grouped = (
        pd.DataFrame(summaries)
        .groupby(["class_pair_key", "flow_type"], as_index=False)
        .agg(flow_count=("flow_type", "size"), flow_weight=("weight", "sum"))
    )
    rows = [
        {"class_pair_key": class_pair_key, "flow_type_summary": _format_flow_type_summary(group)}
        for class_pair_key, group in grouped.groupby("class_pair_key")
    ]
    return pd.DataFrame(rows, columns=columns)


def _validate_flow_edges_for_summary(ssa_flow_edges: pd.DataFrame) -> None:
    missing = [
        column
        for column in ["source", "target", "flow_type", "weight"]
        if column not in ssa_flow_edges.columns
    ]
    if missing:
        raise ValueError(f"ssa_flow_edges is missing required columns: {', '.join(missing)}")


def _format_flow_type_summary(group: pd.DataFrame) -> str:
    parts = []
    for row in group.sort_values("flow_type").to_dict("records"):
        parts.append(f"{row['flow_type']}:{int(row['flow_count'])} rows/{row['flow_weight']:.1f} weight")
    return "; ".join(parts)


def _moved_classes(raw_clusters: pd.DataFrame, ssa_clusters: pd.DataFrame) -> pd.DataFrame:
    raw = _cluster_neighbor_context(raw_clusters, "raw")
    ssa = _cluster_neighbor_context(ssa_clusters, "ssa")
    moved = raw.merge(ssa, on=["class_id", "class_name"], how="inner")
    moved["lost_same_cluster_neighbors"] = moved.apply(
        lambda row: _format_neighbor_delta(row["raw_neighbors"] - row["ssa_neighbors"]),
        axis=1,
    )
    moved["gained_same_cluster_neighbors"] = moved.apply(
        lambda row: _format_neighbor_delta(row["ssa_neighbors"] - row["raw_neighbors"]),
        axis=1,
    )
    moved["changed_neighbor_count"] = moved.apply(
        lambda row: len(row["raw_neighbors"] ^ row["ssa_neighbors"]),
        axis=1,
    )
    moved["membership_jaccard"] = moved.apply(
        lambda row: _jaccard(row["raw_neighbors"], row["ssa_neighbors"]),
        axis=1,
    )
    moved = moved.loc[moved["changed_neighbor_count"] > 0].copy()
    columns = [
        "class_id",
        "class_name",
        "raw_cluster_id",
        "ssa_cluster_id",
        "raw_cluster_size",
        "ssa_cluster_size",
        "lost_same_cluster_neighbors",
        "gained_same_cluster_neighbors",
        "membership_jaccard",
    ]
    if moved.empty:
        return pd.DataFrame(columns=columns)
    return (
        moved.sort_values(
            ["membership_jaccard", "changed_neighbor_count", "class_name"],
            ascending=[True, False, True],
        )
        .loc[:, columns]
        .reset_index(drop=True)
    )


def _cluster_neighbor_context(clusters: pd.DataFrame, prefix: str) -> pd.DataFrame:
    clusters = clusters.copy()
    if "class_name" not in clusters.columns:
        clusters["class_name"] = clusters["class_id"].astype(str)

    records = []
    for cluster_id, group in clusters.groupby("cluster_id"):
        class_by_id = {
            str(row["class_id"]): str(row["class_name"])
            for row in group.to_dict("records")
        }
        for row in group.to_dict("records"):
            class_id = str(row["class_id"])
            records.append(
                {
                    "class_id": class_id,
                    "class_name": str(row["class_name"]),
                    f"{prefix}_cluster_id": int(cluster_id),
                    f"{prefix}_cluster_size": int(len(group)),
                    f"{prefix}_neighbors": {
                        class_name
                        for neighbor_id, class_name in class_by_id.items()
                        if neighbor_id != class_id
                    },
                }
            )
    return pd.DataFrame(records)


def _format_neighbor_delta(neighbors: set[str]) -> str:
    return ";".join(sorted(neighbors))


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    if not union:
        return 1.0
    return float(len(left & right) / len(union))


def _undirected_pair(source: str, target: str) -> tuple[str, str]:
    return tuple(sorted((source, target)))


def _class_pair_key(source: str, target: str) -> str:
    return f"{source}||{target}"


def _undirected_edge_keys(edges: pd.DataFrame) -> set[tuple[str, str]]:
    return {
        _undirected_pair(str(row["source"]), str(row["target"]))
        for row in edges.loc[:, ["source", "target"]].to_dict("records")
        if str(row["source"]) != str(row["target"])
    }


def _sum_weight(edges: pd.DataFrame, weight_column: str) -> float:
    if weight_column not in edges.columns:
        return 0.0
    return float(pd.to_numeric(edges[weight_column], errors="coerce").fillna(0.0).sum())


def _total_ssa_flow_weight(ssa_edges: pd.DataFrame) -> float:
    if "ssa_flow_weight" in ssa_edges.columns:
        return _sum_weight(ssa_edges, "ssa_flow_weight")
    return _sum_weight(ssa_edges, "return_flow_weight") + _sum_weight(
        ssa_edges,
        "argument_flow_weight",
    )


def _cross_cluster_edge_ratio(edges: pd.DataFrame, cluster_by_class: dict[str, int]) -> float:
    edge_keys = _undirected_edge_keys(edges)
    if not edge_keys:
        return 0.0
    cross_cluster_count = 0
    for source, target in edge_keys:
        source_cluster = cluster_by_class.get(source)
        target_cluster = cluster_by_class.get(target)
        if source_cluster is None or target_cluster is None:
            continue
        if source_cluster != target_cluster:
            cross_cluster_count += 1
    return _safe_ratio(cross_cluster_count, len(edge_keys))


def _internal_edge_weight_ratio(
    edges: pd.DataFrame,
    cluster_by_class: dict[str, int],
    weight_column: str,
) -> float:
    internal_weight, external_weight = _edge_weight_split(edges, cluster_by_class, weight_column)
    return _safe_ratio(internal_weight, internal_weight + external_weight)


def _adjusted_rand_index(
    left_partition: dict[str, int],
    right_partition: dict[str, int],
    class_ids: list[str],
) -> float:
    n = len(class_ids)
    total_pairs = _choose_two(n)
    if total_pairs == 0:
        return 1.0

    contingency: Counter[tuple[int, int]] = Counter(
        (left_partition[class_id], right_partition[class_id]) for class_id in class_ids
    )
    left_counts: Counter[int] = Counter(left_partition[class_id] for class_id in class_ids)
    right_counts: Counter[int] = Counter(right_partition[class_id] for class_id in class_ids)

    index = sum(_choose_two(count) for count in contingency.values())
    left_pair_sum = sum(_choose_two(count) for count in left_counts.values())
    right_pair_sum = sum(_choose_two(count) for count in right_counts.values())
    expected_index = left_pair_sum * right_pair_sum / total_pairs
    max_index = (left_pair_sum + right_pair_sum) / 2.0
    denominator = max_index - expected_index
    if denominator == 0:
        return 1.0
    return float((index - expected_index) / denominator)


def _normalized_mutual_information(
    left_partition: dict[str, int],
    right_partition: dict[str, int],
    class_ids: list[str],
) -> float:
    n = len(class_ids)
    if n == 0:
        return 1.0

    contingency: Counter[tuple[int, int]] = Counter(
        (left_partition[class_id], right_partition[class_id]) for class_id in class_ids
    )
    left_counts: Counter[int] = Counter(left_partition[class_id] for class_id in class_ids)
    right_counts: Counter[int] = Counter(right_partition[class_id] for class_id in class_ids)

    mutual_information = 0.0
    for (left_cluster, right_cluster), count in contingency.items():
        mutual_information += (count / n) * math.log(
            (count * n) / (left_counts[left_cluster] * right_counts[right_cluster])
        )

    left_entropy = _entropy(left_counts.values(), n)
    right_entropy = _entropy(right_counts.values(), n)
    if left_entropy == 0 and right_entropy == 0:
        return 1.0
    denominator = math.sqrt(left_entropy * right_entropy)
    return 0.0 if denominator == 0 else float(mutual_information / denominator)


def _entropy(counts, total: int) -> float:
    return -sum((count / total) * math.log(count / total) for count in counts if count)


def _choose_two(value: int) -> float:
    return value * (value - 1) / 2.0


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
