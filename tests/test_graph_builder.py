"""Tests for G_raw and G_ssa graph builders."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.graph.raw_graph_builder import build_raw_graph
from evo_ms.graph.ssa_graph_builder import build_ssa_graph
from evo_ms.evidence.flow_evidence import validate_ssa_flow_type


def test_build_raw_graph_adds_directed_edges() -> None:
    graph = build_raw_graph([("A", "B")])
    assert graph.has_edge("A", "B")


def test_build_ssa_graph_accumulates_raw_and_ssa_weights() -> None:
    graph = build_ssa_graph([("A", "B", "type"), ("A", "B", "return_value_flow")])
    assert graph["A"]["B"]["raw_weight"] == 1.0
    assert graph["A"]["B"]["ssa_flow_weight"] == 3.0
    assert graph["A"]["B"]["G_ssa_weight"] == 4.0


def test_validate_ssa_flow_type_rejects_removed_flow_types() -> None:
    for flow_type in ("shared_domain_object", "parameter_passing_flow"):
        try:
            validate_ssa_flow_type(flow_type)
        except ValueError:
            continue
        raise AssertionError(f"{flow_type} should not be accepted")
