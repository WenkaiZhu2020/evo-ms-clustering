"""Final-only preference-response analysis helpers.

The helpers in this module operate on saved Stage 2 and final Stage 3
candidate tables.  They do not load the historical Stage 3A namespace.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

FINAL_STAGE_LABELS = ("stage2", "stage3")
SUBJECTS = ("jpetstore", "daytrader", "xerces")
SEEDS = tuple(range(30))
STORAGE_SUBJECT = {"jpetstore": "jpetstore", "daytrader": "daytrader", "xerces": "xerces-j"}
CLASS_COUNTS = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
BUDGETS = (0.000, 0.005, 0.010, 0.025, 0.050, 0.100, 0.150, 0.200)
KEY_BUDGETS = (0.000, 0.010, 0.025, 0.050, 0.100)
TARGETS = (0.05, 0.10, 0.20, 0.30)
TOL = 1e-12
BOOTSTRAP_RESAMPLES = 10_000


def canonical_partition_key(partition: pd.DataFrame) -> tuple[int, ...]:
    ordered = partition.loc[:, ["class_id", "cluster_id"]].copy()
    ordered["class_id"] = ordered["class_id"].astype(str)
    ordered = ordered.sort_values("class_id", kind="stable")
    remap: dict[int, int] = {}
    result: list[int] = []
    for value in ordered["cluster_id"].tolist():
        key = int(value)
        if key not in remap:
            remap[key] = len(remap)
        result.append(remap[key])
    return tuple(result)


def vector_partition(class_nodes: pd.DataFrame, vector: str | list[int]) -> pd.DataFrame:
    values = json.loads(vector) if isinstance(vector, str) else vector
    if len(values) != len(class_nodes):
        raise ValueError(f"label vector length {len(values)} != class count {len(class_nodes)}")
    return pd.DataFrame({
        "class_id": class_nodes["class_id"].astype(str).tolist(),
        "class_name": class_nodes["class_name"].astype(str).tolist(),
        "cluster_id": [int(value) for value in values],
    })


def relative_gain(baseline: float, value: float) -> float:
    if abs(baseline) <= TOL:
        if abs(value - baseline) <= TOL:
            return 0.0
        return float("nan")
    return float((baseline - value) / abs(baseline))


def loss_q(q_leiden: float, q_value: float) -> float:
    if abs(q_leiden) <= TOL:
        raise ValueError("Q_L is zero; frozen relative modularity-loss definition is undefined")
    return float((q_leiden - q_value) / abs(q_leiden))


def _dominates(left: np.ndarray, right: np.ndarray) -> bool:
    return bool(np.all(left <= right + TOL) and np.any(left < right - TOL))


def select_candidate(frame: pd.DataFrame, rule: str, budget: float | None = None, projected_only: bool = False) -> pd.Series | None:
    eligible = frame
    if budget is not None:
        eligible = eligible.loc[eligible["q_loss"] <= float(budget) + TOL]
    if projected_only and "projected_membership" in eligible:
        eligible = eligible.loc[eligible["projected_membership"]]
    if eligible.empty:
        return None
    if rule in {"balance", "extreme_balance"}:
        order = ["imbalance", "weighted_modularity", "solution_id"]
        ascending = [True, False, True]
    elif rule in {"semantic", "extreme_semantic"}:
        order = ["f_semantic", "weighted_modularity", "solution_id"]
        ascending = [True, False, True]
    elif rule == "modularity":
        order = ["weighted_modularity", "imbalance", "solution_id"]
        ascending = [False, True, True]
    else:
        raise ValueError(rule)
    return eligible.sort_values(order, ascending=ascending, kind="stable").iloc[0]


def validate_stage_labels(labels: list[str]) -> None:
    unexpected = sorted(set(labels) - set(FINAL_STAGE_LABELS))
    if unexpected:
        raise ValueError(f"preference analysis contains obsolete stages: {unexpected}")
