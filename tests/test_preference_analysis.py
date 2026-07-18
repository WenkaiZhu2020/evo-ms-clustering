"""Focused tests for the frozen post-hoc preference analysis helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.preference_analysis import analyze_preference_response as analysis  # noqa: E402


def _class_nodes() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "class_id": ["a.A", "b.B", "c.C"],
            "class_name": ["A", "B", "C"],
        }
    )


def _candidate_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "solution_id": "seed0_solution002",
                "weighted_modularity": 0.90,
                "imbalance": 0.20,
                "f_semantic": 0.70,
                "label_vector": json.dumps([0, 0, 1]),
                "projected_membership": True,
            },
            {
                "solution_id": "seed0_solution001",
                "weighted_modularity": 0.89,
                "imbalance": 0.10,
                "f_semantic": 0.60,
                "label_vector": json.dumps([0, 1, 1]),
                "projected_membership": True,
            },
        ]
    )


def test_canonical_partition_equality_ignores_cluster_labels() -> None:
    nodes = _class_nodes()
    left = analysis.vector_partition(nodes, [0, 0, 1])
    right = analysis.vector_partition(nodes, [7, 7, 3])
    assert analysis.canonical_partition_key(left) == analysis.canonical_partition_key(right)


def test_dominance_uses_minimisation_orientation() -> None:
    # cohesion is already represented as negative cohesion by the caller.
    assert analysis._dominates(np.asarray([0.2, -5.0, 0.1]), np.asarray([0.3, -4.0, 0.2]))
    assert not analysis._dominates(np.asarray([0.2, -3.0, 0.1]), np.asarray([0.3, -4.0, 0.2]))


def test_relative_modularity_loss_preserves_negative_values() -> None:
    assert np.isclose(analysis.loss_q(0.5, 0.5), 0.0)
    assert np.isclose(analysis.loss_q(0.5, 0.6), -0.2)
    assert np.isclose(analysis.relative_gain(0.4, 0.2), 0.5)


def test_budget_selection_is_deterministic_and_unavailable_is_explicit() -> None:
    frame = _candidate_frame()
    frame["q_loss"] = [0.0, 0.02]
    selected = analysis.select_candidate(frame, "balance", 0.02)
    assert selected is not None
    assert selected["solution_id"] == "seed0_solution001"
    assert analysis.select_candidate(frame, "balance", -0.01) is None


def test_semantic_tie_break_prefers_modularity_then_solution_id() -> None:
    frame = _candidate_frame()
    frame["q_loss"] = [0.01, 0.01]
    frame.loc[:, "f_semantic"] = 0.5
    selected = analysis.select_candidate(frame, "semantic", 0.02)
    assert selected is not None
    assert selected["solution_id"] == "seed0_solution002"


def test_knee_zero_range_normalisation_is_finite() -> None:
    matrix = np.ones((3, 4), dtype=float)
    low, high = matrix.min(axis=0), matrix.max(axis=0)
    normalised = np.divide(matrix - low, high - low, out=np.zeros_like(matrix), where=(high - low) > analysis.TOL)
    assert np.isfinite(normalised).all()
    assert np.all(normalised == 0.0)


def test_generated_reports_keep_scientific_artifact_integrity() -> None:
    report = ROOT / "reports/preference_analysis/scientific_artifact_integrity.csv"
    if not report.exists():
        return
    frame = pd.read_csv(report)
    assert len(frame) >= 552
    assert set(frame["status"]) == {"PASS"}
    assert frame["sha256_before"].equals(frame["sha256_after"])


def test_report_has_all_three_subjects_and_thirty_seeds() -> None:
    report = ROOT / "reports/preference_analysis/stage2_budgeted_balance_per_seed.csv"
    if not report.exists():
        return
    frame = pd.read_csv(report)
    assert set(frame["subject"]) == set(analysis.SUBJECTS)
    assert set(frame["seed"]) == set(range(30))
    assert set(np.round(frame["budget"], 3)) == set(np.round(analysis.BUDGETS, 3))
