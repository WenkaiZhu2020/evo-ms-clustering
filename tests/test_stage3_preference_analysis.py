from __future__ import annotations

import pandas as pd

from scripts.preference_analysis import final_preference as preference


def test_final_preference_boundary_accepts_only_stage2_and_final_stage3() -> None:
    preference.validate_stage_labels(["stage2", "stage3"])
    try:
        preference.validate_stage_labels(["stage3a"])
    except ValueError as exc:
        assert "obsolete stages" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("obsolete stage was accepted")


def test_final_preference_selection_is_deterministic() -> None:
    frame = pd.DataFrame([
        {"solution_id": "z", "imbalance": 0.1, "weighted_modularity": 0.8, "q_loss": 0.01},
        {"solution_id": "a", "imbalance": 0.1, "weighted_modularity": 0.8, "q_loss": 0.01},
    ])
    assert preference.select_candidate(frame, "balance", 0.02)["solution_id"] == "a"

