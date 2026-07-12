"""Stage 2 structural objectives and anti-degeneration constraints.

Design decisions:
- Stage 2 optimizes exactly three structural objectives:
  minimize inter-cluster coupling, maximize density-based intra-cluster
  cohesion, and minimize cluster-size imbalance.
- Objective evaluation must stay O(E) and reuse the Stage 1 edge-weight
  split primitive instead of `_weighted_modularity`, which is too expensive
  for the inner optimization loop.
- Modularity, MoJoFM, Pairwise F1, and Hypervolume are post-hoc evaluation
  metrics only. They must not enter the NSGA-II fitness function.
- Anti-degeneration checks reuse Stage 1 admissibility thresholds as
  constraints or repair logic, not as additional objectives.

The objective loop is intentionally O(E). Weighted modularity is reserved for
post-hoc evaluation and is not used here.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Reuse the Stage 1 O(E) edge split primitive without changing Stage 1 behavior.
from evo_ms.evaluation.partition_metrics import _edge_weight_split

# Anti-degeneration thresholds from Stage 1 admissibility.
MAX_CLUSTER_RATIO = 0.4
SINGLETON_RATIO = 0.15
MIN_CLUSTER_COUNT = 2


@dataclass(frozen=True)
class ObjectiveSpec:
    """Metadata for one optimization objective."""

    name: str
    direction: str  # "maximize" | "minimize"


# Stage 2 optimizes exactly these three structural objectives.
STRUCTURAL_OBJECTIVES: list[ObjectiveSpec] = [
    ObjectiveSpec("coupling", "minimize"),
    ObjectiveSpec("cohesion", "maximize"),
    ObjectiveSpec("imbalance", "minimize"),
]


def evaluate_structural_objectives(
    edges: pd.DataFrame,
    cluster_by_class: dict[str, int],
    weight_column: str,
) -> tuple[float, float, float]:
    """Return `(coupling, cohesion, imbalance)` for one partition.

    Objective definitions:
    1. Coupling is `W_external / W_total` and is minimized.
    2. Cohesion is density-based and is maximized: for each cluster `c`,
       use `2 * W_internal(c) / (|c| * (|c| - 1))`, then average over
       clusters. Singleton clusters have cohesion `0.0` to avoid division by
       zero and to avoid rewarding degenerate one-class clusters.
    3. Imbalance is `std(cluster_sizes) / mean(cluster_sizes)` and is
       minimized.
    """
    _validate_edges(edges, weight_column)
    class_ids = {str(class_id) for class_id in cluster_by_class}
    if not class_ids:
        return 0.0, 0.0, 0.0

    normalized_clusters = {
        str(class_id): int(cluster_id)
        for class_id, cluster_id in cluster_by_class.items()
    }
    cluster_sizes = Counter(normalized_clusters.values())

    internal_weight, external_weight = _edge_weight_split(
        edges,
        normalized_clusters,
        weight_column,
    )
    total_weight = internal_weight + external_weight
    coupling = 0.0 if total_weight == 0 else float(external_weight / total_weight)

    internal_by_cluster = _internal_weight_by_cluster(
        edges,
        normalized_clusters,
        weight_column,
    )
    cohesion_values = []
    for cluster_id, size in cluster_sizes.items():
        if size <= 1:
            cohesion_values.append(0.0)
            continue
        cluster_internal = internal_by_cluster.get(cluster_id, 0.0)
        cohesion_values.append(float(2.0 * cluster_internal / (size * (size - 1))))
    cohesion = float(np.mean(cohesion_values)) if cohesion_values else 0.0

    sizes = np.asarray(list(cluster_sizes.values()), dtype=float)
    mean_size = float(np.mean(sizes)) if len(sizes) else 0.0
    imbalance = 0.0 if mean_size == 0.0 else float(np.std(sizes) / mean_size)
    return coupling, cohesion, imbalance


def admissibility_violation(labels: np.ndarray, class_count: int) -> np.ndarray:
    """Return pymoo-compatible violations for hard anti-degeneration constraints.

    The returned vector uses pymoo's convention: each value must be `<= 0.0` for
    feasibility. The entries are max-cluster ratio, singleton ratio, and minimum
    cluster count, in that order.
    """
    labels = np.asarray(labels, dtype=int).reshape(-1)
    if class_count <= 0 or len(labels) == 0:
        return np.asarray([0.0, 0.0, float(MIN_CLUSTER_COUNT)], dtype=float)

    counts = np.asarray(list(Counter(labels.tolist()).values()), dtype=float)
    cluster_count = int(len(counts))
    max_cluster_ratio = float(counts.max() / class_count) if len(counts) else 0.0
    singleton_ratio = float(np.sum(counts == 1.0) / class_count) if len(counts) else 0.0
    return np.asarray(
        [
            max_cluster_ratio - MAX_CLUSTER_RATIO,
            singleton_ratio - SINGLETON_RATIO,
            float(MIN_CLUSTER_COUNT - cluster_count),
        ],
        dtype=float,
    )


def _internal_weight_by_cluster(
    edges: pd.DataFrame,
    cluster_by_class: dict[str, int],
    weight_column: str,
) -> dict[int, float]:
    internal_by_cluster: dict[int, float] = {}
    for row in edges.to_dict("records"):
        source_cluster = cluster_by_class.get(str(row["source"]))
        target_cluster = cluster_by_class.get(str(row["target"]))
        if source_cluster is None or target_cluster is None:
            continue
        if source_cluster != target_cluster:
            continue
        internal_by_cluster[source_cluster] = (
            internal_by_cluster.get(source_cluster, 0.0) + float(row[weight_column])
        )
    return internal_by_cluster


def _validate_edges(edges: pd.DataFrame, weight_column: str) -> None:
    required = ["source", "target", weight_column]
    missing = [column for column in required if column not in edges.columns]
    if missing:
        raise ValueError(f"edges is missing required columns: {', '.join(missing)}")
    weights = pd.to_numeric(edges[weight_column], errors="coerce")
    if weights.isna().any():
        raise ValueError(f"edges contains non-numeric {weight_column} values")
    if (weights < 0).any():
        raise ValueError(f"edges contains negative {weight_column} values")
