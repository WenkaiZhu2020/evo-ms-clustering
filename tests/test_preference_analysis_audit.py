"""Focused regression tests for the preference-analysis audit boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.preference_analysis import analyze_preference_response as analysis  # noqa: E402
from scripts.preference_analysis import audit_preference_analysis as audit  # noqa: E402


def _context() -> dict:
    class_nodes = pd.DataFrame({"class_id": ["a.A", "b.B", "c.C"], "class_name": ["A", "B", "C"]})
    raw_edges = pd.DataFrame({"source": ["a.A", "b.B", "b.B"], "target": ["b.B", "c.C", "c.C"], "raw_weight": [1.0, 2.0, 1.0]})
    semantic_edges = pd.DataFrame({"class_id_a": ["a.A", "b.B"], "class_id_b": ["b.B", "c.C"], "weight": [1.0, 2.0]})
    context = {"class_nodes": class_nodes, "raw_edges": raw_edges, "semantic_edges": semantic_edges, "semantic_graph_metadata": {"total_edge_weight": 3.0}}
    analysis.prepare_fast_context(context)
    return context


def test_slow_reference_matches_vectorized_structural_metrics() -> None:
    context = _context()
    partition = analysis.vector_partition(context["class_nodes"], [0, 0, 1])
    production = analysis.metric_row(context, partition)
    reference = analysis.reference_metric_row(context, partition)
    for field in ("weighted_modularity", "coupling", "cohesion", "imbalance", "cluster_count", "singleton_ratio"):
        assert np.isclose(production[field], reference[field], rtol=0.0, atol=2e-12)


def test_slow_reference_matches_vectorized_semantic_metric() -> None:
    context = _context()
    partition = analysis.vector_partition(context["class_nodes"], [0, 0, 1])
    assert np.isclose(analysis.semantic_value(context, partition), analysis.reference_semantic_value(context, partition), rtol=0.0, atol=2e-12)


def test_reference_selector_has_same_deterministic_tie_break() -> None:
    frame = pd.DataFrame([
        {"solution_id": "z", "imbalance": 0.1, "weighted_modularity": 0.8, "q_loss": 0.01, "projected_membership": True, "f_semantic": 0.3},
        {"solution_id": "a", "imbalance": 0.1, "weighted_modularity": 0.8, "q_loss": 0.01, "projected_membership": True, "f_semantic": 0.3},
    ])
    assert analysis.select_candidate(frame, "balance", 0.02).solution_id == audit.reference_select(frame, "balance", 0.02).solution_id == "a"


def test_atomic_write_replaces_complete_file(tmp_path: Path) -> None:
    path = tmp_path / "report.csv"
    analysis._atomic_write(path, b"first\n")
    analysis._atomic_write(path, b"second\n")
    assert path.read_bytes() == b"second\n"


def test_analysis_lock_rejects_concurrent_run(tmp_path: Path) -> None:
    path = tmp_path / "analysis.lock"
    with analysis.AnalysisLock(path):
        with pytest.raises(RuntimeError):
            with analysis.AnalysisLock(path):
                pass
    assert not path.exists()


def test_timeline_status_is_explicitly_post_hoc() -> None:
    _, text = audit.timeline_audit()
    assert text == "post-hoc exploratory"
    # The function writes only to the isolated audit root; this test removes
    # no accepted source report.
