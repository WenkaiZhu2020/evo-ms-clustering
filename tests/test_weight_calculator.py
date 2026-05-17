"""Tests for early edge weight calculation helpers."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.graph.weight_calculator import (
    calculate_edge_weight,
    calculate_g_ssa_weight,
    calculate_raw_weight,
    calculate_ssa_flow_weight,
    calculate_stage1_edge_weights,
    normalize_weight,
)


def test_calculate_edge_weight_uses_default_weights() -> None:
    assert calculate_edge_weight(["type", "argument_passing_flow"]) == 4.0


def test_calculate_raw_weight_adds_type_and_call_weights() -> None:
    assert calculate_raw_weight(type_weight=1, call_weight=2) == 3.0


def test_calculate_ssa_flow_weight_adds_return_and_argument_weights() -> None:
    assert calculate_ssa_flow_weight(return_flow_weight=3, argument_flow_weight=6) == 9.0


def test_calculate_g_ssa_weight_adds_raw_and_ssa_flow_weights() -> None:
    assert (
        calculate_g_ssa_weight(
            type_weight=1,
            call_weight=2,
            return_flow_weight=3,
            argument_flow_weight=3,
        )
        == 9.0
    )


def test_calculate_stage1_edge_weights_treats_missing_values_as_zero() -> None:
    weights = calculate_stage1_edge_weights(
        {
            "type_weight": 1,
            "return_flow_weight": None,
            "argument_flow_weight": "",
        }
    )

    assert weights == {
        "raw_weight": 1.0,
        "ssa_flow_weight": 0.0,
        "g_ssa_weight": 1.0,
    }


def test_calculate_stage1_edge_weights_rejects_negative_weights() -> None:
    with pytest.raises(ValueError, match="call_weight must be non-negative"):
        calculate_stage1_edge_weights({"type_weight": 1, "call_weight": -2})


def test_calculate_stage1_edge_weights_does_not_require_shared_domain_weight() -> None:
    weights = calculate_stage1_edge_weights(
        {
            "type_weight": 1,
            "call_weight": 2,
            "return_flow_weight": 3,
            "argument_flow_weight": 3,
        }
    )

    assert "shared_domain_weight" not in weights
    assert weights["g_ssa_weight"] == 9.0


def test_normalize_weight_rejects_non_positive_maximum() -> None:
    with pytest.raises(ValueError, match="maximum must be positive"):
        normalize_weight(1.0, 0.0)
