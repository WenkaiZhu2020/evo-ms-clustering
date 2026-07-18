"""Reusable partition operations shared by Stage 2 and Stage 3."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from evo_ms.evaluation.partition_metrics import _edge_weight_split, _weighted_modularity, cluster_size_distribution
from evo_ms.evaluation.reference_metrics import calculate_reference_metrics


def safe_internal_external_ratio(internal_weight: float, external_weight: float) -> float:
    if external_weight == 0:
        return float(internal_weight) if internal_weight > 0 else 0.0
    return float(internal_weight / external_weight)


def partition_metrics_row(
    subject: str,
    seed: int,
    solution_id: str,
    class_nodes: pd.DataFrame,
    clusters: pd.DataFrame,
    raw_edges: pd.DataFrame,
    cluster_by_class: Mapping[str, int],
    reference_mapping: pd.DataFrame | None = None,
    weight_column: str = "raw_weight",
) -> dict[str, object]:
    sizes = clusters.groupby("cluster_id").size()
    class_count = int(len(class_nodes))
    singleton_count = int((sizes == 1).sum()) if not sizes.empty else 0
    internal_weight, external_weight = _edge_weight_split(
        raw_edges,
        dict(cluster_by_class),
        weight_column,
    )
    total_weight = internal_weight + external_weight
    row: dict[str, object] = {
        "subject": subject,
        "seed": int(seed),
        "solution_id": solution_id,
        "weighted_modularity": _weighted_modularity(
            raw_edges,
            dict(cluster_by_class),
            weight_column,
        ),
        "internal_edge_weight_ratio": 0.0 if total_weight == 0 else float(internal_weight / total_weight),
        "internal_external_edge_ratio": safe_internal_external_ratio(internal_weight, external_weight),
        "cluster_count": int(sizes.size),
        "average_cluster_size": float(sizes.mean()) if not sizes.empty else 0.0,
        "max_cluster_size": int(sizes.max()) if not sizes.empty else 0,
        "min_cluster_size": int(sizes.min()) if not sizes.empty else 0,
        "max_cluster_ratio": (
            0.0 if class_count == 0 or sizes.empty else float(sizes.max() / class_count)
        ),
        "singleton_ratio": 0.0 if class_count == 0 else float(singleton_count / class_count),
        "cluster_size_cv": (
            0.0
            if sizes.empty or float(sizes.mean()) == 0.0
            else float(sizes.std(ddof=0) / sizes.mean())
        ),
        "cluster_size_distribution": cluster_size_distribution(clusters),
    }
    if reference_mapping is not None:
        row.update(calculate_reference_metrics(class_nodes, clusters, reference_mapping))
    return row


def align_clusters(class_nodes: pd.DataFrame, clusters: pd.DataFrame) -> pd.DataFrame:
    cluster_map = dict(zip(clusters["class_id"].astype(str), clusters["cluster_id"], strict=True))
    return pd.DataFrame(
        {
            "class_id": class_nodes["class_id"].astype(str),
            "class_name": class_nodes["class_name"].astype(str),
            "cluster_id": [
                int(cluster_map[str(class_id)])
                for class_id in class_nodes["class_id"].astype(str).tolist()
            ],
        }
    )


def same_cluster_neighbors(clusters: pd.DataFrame) -> dict[str, set[str]]:
    neighbors: dict[str, set[str]] = {}
    for _, group in clusters.groupby("cluster_id"):
        class_ids = set(group["class_id"].astype(str))
        for class_id in class_ids:
            neighbors[class_id] = class_ids - {class_id}
    return neighbors


def changed_partition_ratio(
    class_nodes: pd.DataFrame,
    left_clusters: pd.DataFrame,
    right_clusters: pd.DataFrame,
) -> tuple[int, float]:
    left_neighbors = same_cluster_neighbors(left_clusters)
    right_neighbors = same_cluster_neighbors(right_clusters)
    class_ids = class_nodes["class_id"].astype(str).tolist()
    changed = sum(
        1
        for class_id in class_ids
        if left_neighbors.get(class_id, set()) != right_neighbors.get(class_id, set())
    )
    return changed, 0.0 if not class_ids else changed / len(class_ids)
