"""Tests for early edge weight calculation helpers."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.graph.weight_calculator import calculate_edge_weight, normalize_weight


def test_calculate_edge_weight_uses_default_weights() -> None:
    assert calculate_edge_weight(["dependency", "inheritance"]) == 2.5


def test_normalize_weight_rejects_non_positive_maximum() -> None:
    try:
        normalize_weight(1.0, 0.0)
    except ValueError:
        return
    raise AssertionError("normalize_weight should reject a non-positive maximum")
