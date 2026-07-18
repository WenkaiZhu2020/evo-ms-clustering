"""Shared deterministic representative-solution selection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json

import numpy as np

from evo_ms.optimization import encoding


def canonical_label_key(labels: np.ndarray) -> tuple[int, ...]:
    canonical = encoding.canonical_relabel(labels)
    return tuple(int(value) for value in canonical.tolist())


def label_tuple_from_row(row: Mapping[str, object]) -> tuple[int, ...]:
    value = row.get("label_vector", "[]")
    labels = json.loads(value) if isinstance(value, str) else value
    return canonical_label_key(np.asarray(labels, dtype=int))


def select_solution(
    posthoc_rows: Sequence[Mapping[str, object]],
    pareto_rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Apply the frozen Stage 2 representative-selection rule."""
    if not posthoc_rows:
        raise ValueError("cannot select a solution from an empty Pareto front")
    posthoc_by_id = {row["solution_id"]: row for row in posthoc_rows}
    candidates = [
        row for row in pareto_rows
        if bool(row["feasible"]) and row["solution_id"] in posthoc_by_id
    ]
    if not candidates:
        candidates = [row for row in pareto_rows if row["solution_id"] in posthoc_by_id]
    selected = min(
        candidates,
        key=lambda row: (
            -float(posthoc_by_id[row["solution_id"]]["weighted_modularity"]),
            bool(row["is_injected_seed"]),
            float(row["coupling"]),
            -float(row["cohesion"]),
            float(row["imbalance"]),
            label_tuple_from_row(row),
        ),
    )
    metrics = posthoc_by_id[selected["solution_id"]]
    return {
        **dict(selected),
        "selection_rule": "highest_weighted_modularity_among_feasible_pareto_solutions",
        "selected_weighted_modularity": float(metrics["weighted_modularity"]),
        "selected_cluster_count": int(metrics["cluster_count"]),
        "selected_max_cluster_ratio": float(metrics["max_cluster_ratio"]),
        "selected_singleton_ratio": float(metrics["singleton_ratio"]),
    }
