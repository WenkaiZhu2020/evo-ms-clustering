"""Tests for the final-only preference-analysis boundary."""

from __future__ import annotations

import inspect

from scripts.preference_analysis import analyze_preference_response as analysis


def test_preference_stage_labels_are_final_only() -> None:
    analysis.validate_stage_labels(["stage2", "stage3"])
    try:
        analysis.validate_stage_labels(["stage3a"])
    except ValueError as exc:
        assert "obsolete stages" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("obsolete preference stage was accepted")


def test_preference_entry_point_is_read_only_and_final_only() -> None:
    source = inspect.getsource(analysis)
    assert "stage3a" not in source.lower()
    assert "generate_embeddings" not in source
    assert "run_optimizer" not in source


def test_final_preference_selection_helper_is_deterministic() -> None:
    import pandas as pd

    frame = pd.DataFrame([
        {"solution_id": "z", "imbalance": 0.1, "weighted_modularity": 0.8, "q_loss": 0.01},
        {"solution_id": "a", "imbalance": 0.1, "weighted_modularity": 0.8, "q_loss": 0.01},
    ])
    assert analysis.select_candidate(frame, "balance", 0.02)["solution_id"] == "a"
