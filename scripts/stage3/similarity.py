"""Shared similarity helpers for saved Stage 3 embedding diagnostics and graphs."""

from __future__ import annotations

import numpy as np


def true_cosine_similarity(vectors: np.ndarray) -> np.ndarray:
    """Return a clipped true-cosine similarity matrix without modifying inputs.

    Norms are computed in float64 and each vector is normalized only in the
    temporary working array. Zero-norm and non-finite vectors are rejected.
    The final clip removes only floating-point excursions outside [-1, 1].
    """

    values = np.asarray(vectors, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError(f"expected a 2-D vector matrix, got shape {values.shape}")
    if not np.isfinite(values).all():
        raise ValueError("cosine input contains NaN or infinite values")
    norms = np.linalg.norm(values, axis=1)
    if np.any(norms == 0.0):
        raise ValueError("cosine input contains a zero-norm vector")
    normalized = values / norms[:, None]
    return np.clip(normalized @ normalized.T, -1.0, 1.0)
