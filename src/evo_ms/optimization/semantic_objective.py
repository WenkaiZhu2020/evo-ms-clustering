"""Frozen Stage 3 semantic-cut objective over the final semantic graph."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd


SEMANTIC_COLUMNS = ["class_id_a", "class_id_b", "weight"]


def load_semantic_edges(
    path: str | Path,
    expected_class_ids: set[str] | frozenset[str] | None = None,
) -> pd.DataFrame:
    """Load and validate the final undirected semantic graph exactly once."""
    graph_path = Path(path)
    edges = pd.read_csv(graph_path, usecols=SEMANTIC_COLUMNS)
    validate_semantic_edges(edges, expected_class_ids=expected_class_ids)
    return edges.reset_index(drop=True)


def validate_semantic_edges(
    edges: pd.DataFrame,
    expected_class_ids: set[str] | frozenset[str] | None = None,
) -> None:
    missing = [column for column in SEMANTIC_COLUMNS if column not in edges.columns]
    if missing:
        raise ValueError(f"semantic_edges is missing required columns: {', '.join(missing)}")
    if edges.empty:
        return
    frame = edges.loc[:, SEMANTIC_COLUMNS].copy()
    frame["class_id_a"] = frame["class_id_a"].astype(str)
    frame["class_id_b"] = frame["class_id_b"].astype(str)
    weights = pd.to_numeric(frame["weight"], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(weights).all():
        raise ValueError("semantic_edges contains NaN or infinite weights")
    if np.any(weights < 0.0):
        raise ValueError("semantic_edges contains negative weights")
    if (frame["class_id_a"] == frame["class_id_b"]).any():
        raise ValueError("semantic_edges contains a self-loop")
    pairs = list(zip(frame["class_id_a"], frame["class_id_b"], strict=True))
    if len(set(pairs)) != len(pairs):
        raise ValueError("semantic_edges contains duplicate undirected edges")
    if any(left >= right for left, right in pairs):
        raise ValueError("semantic_edges endpoints are not canonically ordered")
    if expected_class_ids is not None:
        observed = {value for pair in pairs for value in pair}
        expected = {str(value) for value in expected_class_ids}
        if observed != expected:
            raise ValueError(
                "semantic graph class scope mismatch: "
                f"missing={sorted(expected - observed)}, extra={sorted(observed - expected)}"
            )
    if float(weights.sum()) <= 0.0:
        raise ValueError("formal semantic graph has zero total weight")


def semantic_total_weight(edges: pd.DataFrame) -> float:
    """Return W_all, counting each final undirected row once."""
    if edges.empty:
        return 0.0
    validate_semantic_edges(edges)
    total = float(pd.to_numeric(edges["weight"], errors="raise").sum())
    if total <= 0.0:
        raise ValueError("formal semantic graph has zero total weight")
    return total


def resolve_semantic_total_weight(
    edges: pd.DataFrame,
    graph_metadata: Mapping[str, object],
) -> float:
    """Resolve total weight from final edges, checking optional legacy metadata.

    Accepted final graph metadata does not serialize ``total_edge_weight``.
    Older runner code expected that convenience field.  The scientific source
    remains the saved edge table; when a metadata value is present it must agree
    exactly within floating-point tolerance.
    """
    calculated = semantic_total_weight(edges)
    recorded = graph_metadata.get("total_edge_weight")
    if recorded is not None and not np.isclose(
        float(recorded), calculated, rtol=0.0, atol=1e-12
    ):
        raise ValueError("semantic graph metadata total weight mismatch")
    return calculated


def evaluate_semantic_objective(
    edges: pd.DataFrame,
    cluster_by_class: Mapping[str, int],
    total_weight: float | None = None,
) -> float:
    """Return ``1 - W_in / W_all`` for one candidate partition.

    Empty edge collections have the defensive value 1.0. Formal runners must
    reject empty or zero-total graphs before constructing the optimization
    problem; this behavior is retained for function-level diagnostics.
    """
    if edges.empty:
        return 1.0
    validate_semantic_edges(edges)
    labels = {str(class_id): int(cluster_id) for class_id, cluster_id in cluster_by_class.items()}
    endpoints = {str(value) for value in edges["class_id_a"]} | {str(value) for value in edges["class_id_b"]}
    if endpoints != set(labels):
        raise ValueError(
            "candidate partition class scope mismatch: "
            f"missing={sorted(endpoints - set(labels))}, extra={sorted(set(labels) - endpoints)}"
        )
    weights = pd.to_numeric(edges["weight"], errors="raise").to_numpy(dtype=float)
    w_all = semantic_total_weight(edges) if total_weight is None else float(total_weight)
    if not np.isfinite(w_all) or w_all <= 0.0:
        raise ValueError("semantic total weight must be finite and greater than zero")
    left_labels = edges["class_id_a"].astype(str).map(labels).to_numpy(dtype=int)
    right_labels = edges["class_id_b"].astype(str).map(labels).to_numpy(dtype=int)
    w_in = float(weights[left_labels == right_labels].sum())
    value = float(1.0 - w_in / w_all)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"semantic objective outside [0,1]: {value}")
    return value
