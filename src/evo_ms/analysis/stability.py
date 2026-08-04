"""Pure partition and neighbour stability diagnostics."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np


def neighbour_retention(
    baseline: Mapping[str, Iterable[str]],
    observed: Mapping[str, Iterable[str]],
) -> dict[str, int]:
    """Count baseline neighbours retained for each class."""
    return {
        class_id: len(set(baseline.get(class_id, ())) & set(observed.get(class_id, ())))
        for class_id in sorted(set(baseline) | set(observed))
    }


def neighbour_retention_ratio(
    baseline: Mapping[str, Iterable[str]],
    observed: Mapping[str, Iterable[str]],
) -> dict[str, float]:
    """Return retained-neighbour fractions with zero-degree handling."""
    values: dict[str, float] = {}
    for class_id in sorted(set(baseline) | set(observed)):
        expected = set(baseline.get(class_id, ()))
        retained = expected & set(observed.get(class_id, ()))
        values[class_id] = 1.0 if not expected else float(len(retained) / len(expected))
    return values


def summarize_retention(
    ratios: Mapping[str, float],
) -> dict[str, Any]:
    values = np.asarray([float(ratios[key]) for key in sorted(ratios)], dtype=float)
    return {
        "class_count": int(len(values)),
        "mean": float(np.mean(values)) if len(values) else None,
        "median": float(np.median(values)) if len(values) else None,
        "zero_retention_count": int(np.sum(values == 0.0)) if len(values) else 0,
        "all_retained_count": int(np.sum(values == 1.0)) if len(values) else 0,
    }


def partition_change_fraction(
    baseline: Mapping[str, Iterable[str]],
    observed: Mapping[str, Iterable[str]],
) -> float:
    """Return the fraction of classes whose same-cluster neighbours changed."""
    class_ids = sorted(set(baseline) | set(observed))
    if not class_ids:
        return 0.0
    changed = sum(
        set(baseline.get(class_id, ())) != set(observed.get(class_id, ()))
        for class_id in class_ids
    )
    return float(changed / len(class_ids))
