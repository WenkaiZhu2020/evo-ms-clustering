"""Reusable deterministic structure-aware initialization policies."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from evo_ms.optimization import encoding
from evo_ms.optimization.problem import DEFAULT_MAX_CLUSTER_RATIO, repair_labels


def initialization_rng_seed(seed: int) -> int:
    """Return the frozen initialization RNG seed for an optimizer seed."""
    return 10_000 + int(seed)


def adjacency_by_class(edges: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    """Return deterministic undirected adjacency keyed by class ID."""
    adjacency: dict[str, set[str]] = {}
    for row in edges.to_dict("records"):
        source = str(row["source"])
        target = str(row["target"])
        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set()).add(source)
    return {
        class_id: tuple(sorted(neighbors))
        for class_id, neighbors in sorted(adjacency.items())
    }


def strongest_edge_grouping_labels(
    class_count: int,
    raw_edges: pd.DataFrame,
    index_by_id: Mapping[str, int],
    target_count: int,
    max_cluster_ratio: float = DEFAULT_MAX_CLUSTER_RATIO,
) -> np.ndarray:
    """Build the deterministic strongest-edge grouping initialization."""
    parent = np.arange(class_count, dtype=int)
    sizes = np.ones(class_count, dtype=int)
    cluster_count = class_count
    max_size = max(1, int(np.floor(max_cluster_ratio * class_count)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return int(index)

    for row in raw_edges.sort_values(
        ["raw_weight", "source", "target"],
        ascending=[False, True, True],
    ).to_dict("records"):
        if cluster_count <= target_count:
            break
        left = index_by_id.get(str(row["source"]))
        right = index_by_id.get(str(row["target"]))
        if left is None or right is None:
            continue
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root or sizes[left_root] + sizes[right_root] > max_size:
            continue
        if sizes[left_root] < sizes[right_root]:
            left_root, right_root = right_root, left_root
        parent[right_root] = left_root
        sizes[left_root] += sizes[right_root]
        cluster_count -= 1
    return repair_labels(
        np.asarray([find(index) for index in range(class_count)], dtype=int),
        class_count,
        max_cluster_ratio,
    )


def _perturbed_leiden_records(
    raw_leiden_labels: np.ndarray,
    class_ids: list[str],
    raw_edges: pd.DataFrame,
    index_by_id: Mapping[str, int],
    rng: np.random.Generator,
    config: Mapping[str, object],
    max_cluster_ratio: float,
) -> list[dict[str, object]]:
    perturbation_config = config.get("perturbations", {})
    if not isinstance(perturbation_config, Mapping) or not bool(
        perturbation_config.get("enabled", True)
    ):
        return []
    fractions = [
        float(value)
        for value in perturbation_config.get("fractions", [0.005, 0.01, 0.02, 0.05])
    ]
    repetitions = int(perturbation_config.get("per_fraction", 5))
    adjacency = adjacency_by_class(raw_edges)
    records: list[dict[str, object]] = []
    for fraction in fractions:
        move_count = max(1, int(round(fraction * len(class_ids))))
        for repetition in range(repetitions):
            labels = raw_leiden_labels.copy()
            chosen = rng.choice(len(labels), size=move_count, replace=False)
            for index in chosen:
                neighbor_clusters = [
                    labels[index_by_id[neighbor]]
                    for neighbor in adjacency.get(class_ids[index], ())
                    if neighbor in index_by_id
                ]
                if neighbor_clusters:
                    labels[index] = int(rng.choice(neighbor_clusters))
                else:
                    labels[index] = int(rng.choice(labels))
            records.append(
                {
                    "name": f"raw_leiden_perturb_{fraction:g}_{repetition}",
                    "category": "raw_leiden_perturbation",
                    "labels": repair_labels(labels, len(class_ids), max_cluster_ratio),
                }
            )
    return records


def _graph_grouping_records(
    class_count: int,
    raw_edges: pd.DataFrame,
    index_by_id: Mapping[str, int],
    raw_leiden_cluster_count: int,
    config: Mapping[str, object],
    max_cluster_ratio: float,
) -> list[dict[str, object]]:
    grouping_config = config.get("graph_groupings", {})
    if not isinstance(grouping_config, Mapping) or not bool(grouping_config.get("enabled", True)):
        return []
    target_counts = {
        raw_leiden_cluster_count + int(offset)
        for offset in grouping_config.get("target_offsets_from_raw_leiden", [-10, 0, 10])
    }
    if bool(grouping_config.get("include_sqrt_target", True)):
        target_counts.add(int(np.ceil(np.sqrt(class_count) * 2.0)))
    target_counts = {
        max(2, min(int(target), class_count)) for target in target_counts
    }
    return [
        {
            "name": f"strongest_edge_grouping_k{target_count}",
            "category": "strongest_edge_grouping",
            "labels": strongest_edge_grouping_labels(
                class_count=class_count,
                raw_edges=raw_edges,
                index_by_id=index_by_id,
                target_count=target_count,
                max_cluster_ratio=max_cluster_ratio,
            ),
        }
        for target_count in sorted(target_counts)
    ]


def deduplicate_seed_records(
    records: Sequence[Mapping[str, object]],
    class_count: int,
    max_cluster_ratio: float = DEFAULT_MAX_CLUSTER_RATIO,
) -> list[dict[str, object]]:
    """Repair and retain the first record for each canonical partition."""
    unique: list[dict[str, object]] = []
    seen: set[tuple[int, ...]] = set()
    for record in records:
        labels = repair_labels(
            np.asarray(record["labels"], dtype=int),
            class_count,
            max_cluster_ratio,
        )
        key = canonical_label_key(labels)
        if key in seen:
            continue
        seen.add(key)
        unique.append({**record, "labels": labels})
    return unique


def canonical_label_key(labels: np.ndarray) -> tuple[int, ...]:
    """Return the canonical tuple used for partition identity."""
    canonical = encoding.canonical_relabel(labels)
    return tuple(int(value) for value in canonical.tolist())


def build_structure_aware_seed_records(
    class_nodes: pd.DataFrame,
    raw_edges: pd.DataFrame,
    raw_leiden_clusters: pd.DataFrame,
    seed: int,
    config: Mapping[str, object],
    max_cluster_ratio: float = DEFAULT_MAX_CLUSTER_RATIO,
) -> list[dict[str, object]]:
    """Build the frozen Stage 2 structure-aware seed records."""
    if not bool(config.get("enabled", True)):
        return []

    class_ids = class_nodes["class_id"].astype(str).tolist()
    index_by_id = {class_id: index for index, class_id in enumerate(class_ids)}
    raw_leiden_by_class = dict(
        zip(
            raw_leiden_clusters["class_id"].astype(str),
            raw_leiden_clusters["cluster_id"].astype(int),
            strict=True,
        )
    )
    raw_leiden_labels = encoding.canonical_relabel(
        np.asarray([raw_leiden_by_class[class_id] for class_id in class_ids], dtype=int)
    )
    rng = np.random.default_rng(initialization_rng_seed(seed))
    records: list[dict[str, object]] = []

    if bool(config.get("include_raw_leiden", True)):
        records.append(
            {
                "name": "raw_leiden",
                "category": "raw_leiden",
                "labels": repair_labels(raw_leiden_labels, len(class_ids), max_cluster_ratio),
            }
        )

    records.extend(
        _perturbed_leiden_records(
            raw_leiden_labels=raw_leiden_labels,
            class_ids=class_ids,
            raw_edges=raw_edges,
            index_by_id=index_by_id,
            rng=rng,
            config=config,
            max_cluster_ratio=max_cluster_ratio,
        )
    )
    records.extend(
        _graph_grouping_records(
            class_count=len(class_ids),
            raw_edges=raw_edges,
            index_by_id=index_by_id,
            raw_leiden_cluster_count=len(set(raw_leiden_labels.tolist())),
            config=config,
            max_cluster_ratio=max_cluster_ratio,
        )
    )
    return deduplicate_seed_records(records, len(class_ids), max_cluster_ratio)
