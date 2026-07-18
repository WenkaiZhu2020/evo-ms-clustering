"""Reusable true-cosine and deterministic top-k graph construction."""

from __future__ import annotations

import numpy as np


def true_cosine_similarity(vectors: np.ndarray) -> np.ndarray:
    """Calculate true cosine similarity without modifying saved vectors."""
    values = np.asarray(vectors, dtype=np.float64)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("cosine input must be a finite 2-D matrix")
    norms = np.linalg.norm(values, axis=1)
    if np.any(norms == 0.0):
        raise ValueError("cosine input contains a zero-norm vector")
    normalized = values / norms[:, None]
    return np.clip(normalized @ normalized.T, -1.0, 1.0)


def canonical_weight(weight: float) -> str:
    value = float(weight)
    return "0" if value == 0.0 else format(value, ".17g")


def select_directed_top_k(class_ids: list[str], similarity: np.ndarray, k: int = 3) -> list[dict[str, object]]:
    if similarity.shape != (len(class_ids), len(class_ids)):
        raise ValueError("similarity matrix shape does not match class IDs")
    if len(class_ids) <= k:
        raise ValueError("top-k graph requires more nodes than k")
    rows: list[dict[str, object]] = []
    for source_index, source_id in enumerate(class_ids):
        candidates = sorted(
            ((float(similarity[source_index, target_index]), class_ids[target_index])
             for target_index in range(len(class_ids)) if target_index != source_index),
            key=lambda item: (-item[0], item[1]),
        )
        rows.extend(
            {"source_class_id": source_id, "rank": rank, "target_class_id": target, "weight": weight}
            for rank, (weight, target) in enumerate(candidates[:k], start=1)
        )
    return rows


def symmetrise_or(class_ids: list[str], directed_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    known = set(class_ids)
    selected = {(str(row["source_class_id"]), str(row["target_class_id"])) for row in directed_rows}
    weights = {(str(row["source_class_id"]), str(row["target_class_id"])): float(row["weight"]) for row in directed_rows}
    pairs = {tuple(sorted((source, target))) for source, target in selected}
    output = []
    for left, right in sorted(pairs):
        if left not in known or right not in known:
            raise ValueError("semantic edge endpoint is outside class scope")
        first = weights.get((left, right), weights.get((right, left)))
        second = weights.get((right, left), weights.get((left, right)))
        if first is None or second is None or not np.isclose(first, second, atol=1e-12):
            raise ValueError("OR symmetrisation received inconsistent edge weights")
        selected_by = "both" if (left, right) in selected and (right, left) in selected else ("a" if (left, right) in selected else "b")
        output.append({"class_id_a": left, "class_id_b": right, "weight": float(first), "selected_by": selected_by})
    return output


def build_graph_from_embeddings(class_ids: list[str], embeddings: np.ndarray, k: int = 3) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    matrix = true_cosine_similarity(embeddings)
    if not np.allclose(matrix, matrix.T, atol=1e-12) or not np.allclose(np.diag(matrix), 1.0, atol=1e-12):
        raise ValueError("true-cosine matrix symmetry/diagonal check failed")
    directed = select_directed_top_k(class_ids, matrix, k)
    return directed, symmetrise_or(class_ids, directed)
