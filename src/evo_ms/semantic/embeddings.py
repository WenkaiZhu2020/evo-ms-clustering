"""Reusable saved-embedding validation and hashing helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np


def vector_hash(vector: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(vector, dtype="<f4").tobytes()).hexdigest()


def validate_embedding_matrix(vectors: np.ndarray, *, rows: int, dimension: int) -> None:
    values = np.asarray(vectors)
    if values.shape != (rows, dimension):
        raise ValueError(f"embedding shape mismatch: {values.shape} != {(rows, dimension)}")
    if values.dtype != np.dtype("float32") and values.dtype != np.dtype("<f4"):
        raise ValueError(f"embedding dtype mismatch: {values.dtype}")
    if not np.isfinite(values).all():
        raise ValueError("embedding matrix contains non-finite values")
    if np.any(np.all(values == 0, axis=1)):
        raise ValueError("embedding matrix contains a zero vector")


def load_saved_embeddings(path: str | Path, *, rows: int, dimension: int) -> np.ndarray:
    values = np.load(Path(path), allow_pickle=False)
    validate_embedding_matrix(values, rows=rows, dimension=dimension)
    return values
