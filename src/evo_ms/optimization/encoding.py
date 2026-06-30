"""Stage 2 individual encoding: an integer label vector over classes.

Design scaffold: an individual is a length-N integer array where `labels[i]`
is the cluster id for the i-th class in `class_nodes` order. The number of
clusters is variable. This encoding maps cleanly to the existing Stage 1
`cluster_by_class: dict[str, int]` format and the
`DataFrame[class_id, class_name, cluster_id]` partition schema.

All operators canonicalize labels to first-seen order so equivalent partitions
share a stable representation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def to_cluster_by_class(
    labels: np.ndarray,
    class_nodes: pd.DataFrame | list[str] | pd.Series,
) -> dict[str, int]:
    """Convert a label vector to `{class_id: cluster_id}` for Stage 1 metrics.

    `class_nodes` may be the Stage 1 class-node DataFrame or a class-id
    sequence. The output order follows the provided row or sequence order.
    """
    canonical = canonical_relabel(labels)
    class_ids = _class_ids(class_nodes)
    if len(canonical) != len(class_ids):
        raise ValueError(
            f"labels length {len(canonical)} does not match class count {len(class_ids)}"
        )
    return {
        str(class_id): int(cluster_id)
        for class_id, cluster_id in zip(class_ids, canonical, strict=True)
    }


def to_clusters_frame(labels: np.ndarray, class_nodes: pd.DataFrame) -> pd.DataFrame:
    """Convert a label vector to the Stage 1 partition DataFrame schema.
    """
    _validate_class_nodes(class_nodes)
    canonical = canonical_relabel(labels)
    if len(canonical) != len(class_nodes):
        raise ValueError(
            f"labels length {len(canonical)} does not match class count {len(class_nodes)}"
        )
    return pd.DataFrame(
        {
            "class_id": class_nodes["class_id"].astype(str).tolist(),
            "class_name": class_nodes["class_name"].astype(str).tolist(),
            "cluster_id": canonical.astype(int).tolist(),
        }
    )


def canonical_relabel(labels: np.ndarray) -> np.ndarray:
    """Canonicalize labels to remove label symmetry after genetic operators.

    Labels are remapped to `0..k-1` in first-seen order. For example,
    `[4, 4, 9, 4, 2]` becomes `[0, 0, 1, 0, 2]`.
    """
    array = np.asarray(labels, dtype=int).reshape(-1)
    mapping: dict[int, int] = {}
    relabeled = np.empty(len(array), dtype=int)
    for index, label in enumerate(array.tolist()):
        if label not in mapping:
            mapping[label] = len(mapping)
        relabeled[index] = mapping[label]
    return relabeled


def random_individual(n_classes: int, rng: np.random.Generator, max_clusters: int | None = None) -> np.ndarray:
    """Create one random initial individual as a label vector.

    The number of clusters is sampled between 2 and `max_clusters`, bounded by
    `n_classes`. The result is canonicalized before it is returned.
    """
    if n_classes <= 0:
        raise ValueError("n_classes must be positive")
    if n_classes == 1:
        return np.asarray([0], dtype=int)

    if max_clusters is None:
        max_clusters = max(2, int(np.ceil(np.sqrt(n_classes) * 2.0)))
    max_clusters = max(2, min(int(max_clusters), n_classes))
    cluster_count = int(rng.integers(2, max_clusters + 1))
    labels = rng.integers(0, cluster_count, size=n_classes, dtype=int)
    return canonical_relabel(labels)


def _class_ids(class_nodes: pd.DataFrame | list[str] | pd.Series) -> list[str]:
    if isinstance(class_nodes, pd.DataFrame):
        _validate_class_nodes(class_nodes)
        return class_nodes["class_id"].astype(str).tolist()
    if isinstance(class_nodes, pd.Series):
        return class_nodes.astype(str).tolist()
    return [str(class_id) for class_id in class_nodes]


def _validate_class_nodes(class_nodes: pd.DataFrame) -> None:
    missing = [
        column
        for column in ["class_id", "class_name"]
        if column not in class_nodes.columns
    ]
    if missing:
        raise ValueError(f"class_nodes is missing required columns: {', '.join(missing)}")
    if class_nodes["class_id"].astype(str).duplicated().any():
        raise ValueError("class_nodes contains duplicate class_id values")
