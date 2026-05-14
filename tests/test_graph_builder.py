"""Tests for raw and enriched graph builders."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.graph.enriched_graph_builder import build_enriched_graph
from evo_ms.graph.raw_graph_builder import build_raw_graph


def test_build_raw_graph_adds_directed_edges() -> None:
    graph = build_raw_graph([("A", "B")])
    assert graph.has_edge("A", "B")


def test_build_enriched_graph_accumulates_weight() -> None:
    graph = build_enriched_graph([("A", "B", "dependency"), ("A", "B", "flow")])
    assert graph["A"]["B"]["weight"] == 2.25
