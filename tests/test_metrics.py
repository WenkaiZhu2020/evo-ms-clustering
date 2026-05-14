"""Tests for early graph and partition metric helpers."""

from pathlib import Path
import sys

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.evaluation.graph_metrics import graph_size_metrics
from evo_ms.evaluation.partition_metrics import partition_size_metrics


def test_graph_size_metrics_counts_nodes_and_edges() -> None:
    graph = nx.Graph()
    graph.add_edge("A", "B")
    assert graph_size_metrics(graph) == {"nodes": 2, "edges": 1}


def test_partition_size_metrics_reports_average_size() -> None:
    metrics = partition_size_metrics({"A": 0, "B": 0, "C": 1})
    assert metrics == {"clusters": 2, "average_cluster_size": 1.5}
