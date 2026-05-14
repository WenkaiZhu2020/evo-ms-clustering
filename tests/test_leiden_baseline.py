"""Tests for the Stage 1 Leiden baseline placeholder."""

from pathlib import Path
import sys

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.clustering.leiden_baseline import run_leiden_baseline


def test_run_leiden_baseline_returns_component_partition() -> None:
    graph = nx.Graph()
    graph.add_edges_from([("A", "B"), ("C", "D")])
    partition = run_leiden_baseline(graph)
    assert partition["A"] == partition["B"]
    assert partition["C"] == partition["D"]
    assert partition["A"] != partition["C"]
