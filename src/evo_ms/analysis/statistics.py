"""Pure deterministic summaries used by Stage 3 reports."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np


def deterministic_rows(
    rows: Iterable[Mapping[str, Any]],
    keys: Sequence[str] = ("subject", "seed"),
) -> list[Mapping[str, Any]]:
    """Return rows in a stable tuple-key order without mutating the input."""
    return sorted(
        rows,
        key=lambda row: tuple(str(row.get(key, "")) for key in keys),
    )


def paired_summary(
    rows: Iterable[Mapping[str, Any]],
    left_field: str,
    right_field: str,
) -> dict[str, float | int | None]:
    """Summarize paired finite differences as ``right - left``."""
    differences = [
        float(row[right_field]) - float(row[left_field])
        for row in rows
        if row.get(left_field) is not None and row.get(right_field) is not None
    ]
    values = np.asarray(differences, dtype=float)
    return {
        "count": int(len(values)),
        "mean_difference": float(np.mean(values)) if len(values) else None,
        "median_difference": float(np.median(values)) if len(values) else None,
        "minimum_difference": float(np.min(values)) if len(values) else None,
        "maximum_difference": float(np.max(values)) if len(values) else None,
    }


def conditional_summary(
    rows: Iterable[Mapping[str, Any]],
    group_field: str,
    value_field: str,
) -> list[dict[str, Any]]:
    """Return deterministic count/mean/median summaries by a grouping field."""
    grouped: dict[str, list[float]] = {}
    for row in rows:
        value = row.get(value_field)
        if value is None:
            continue
        grouped.setdefault(str(row.get(group_field, "")), []).append(float(value))
    output: list[dict[str, Any]] = []
    for group in sorted(grouped):
        values = np.asarray(grouped[group], dtype=float)
        output.append(
            {
                "group": group,
                "count": int(len(values)),
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
            }
        )
    return output


def spearman_summary(
    left: Sequence[float],
    right: Sequence[float],
) -> dict[str, Any]:
    """Calculate a reproducible Spearman diagnostic with explicit null reasons."""
    if len(left) != len(right):
        raise ValueError("Spearman inputs must have equal length")
    if len(left) < 2:
        return {"rho": None, "p_value": None, "undefined_reason": "fewer_than_two_values"}
    left_values = np.asarray(left, dtype=float)
    right_values = np.asarray(right, dtype=float)
    if not np.isfinite(left_values).all() or not np.isfinite(right_values).all():
        raise ValueError("Spearman inputs must be finite")
    if len(set(left_values.tolist())) <= 1 or len(set(right_values.tolist())) <= 1:
        return {"rho": None, "p_value": None, "undefined_reason": "constant_input"}
    from scipy.stats import spearmanr

    result = spearmanr(left_values, right_values)
    return {
        "rho": float(result.statistic),
        "p_value": float(result.pvalue),
        "undefined_reason": None,
    }
