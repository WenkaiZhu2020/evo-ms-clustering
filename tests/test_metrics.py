from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.evaluation.partition_metrics import calculate_partition_metrics, partition_size_metrics


def test_partition_size_metrics_reports_average_size() -> None:
    metrics = partition_size_metrics({"A": 0, "B": 0, "C": 1})
    assert metrics == {"clusters": 2, "average_cluster_size": 1.5}


def test_calculate_partition_metrics_reports_cluster_count() -> None:
    metrics = calculate_partition_metrics(
        class_nodes_frame("A", "B", "C"),
        ssa_edges_frame(("A", "B", 3.0)),
        clusters_frame(("A", 0), ("B", 0), ("C", 1)),
        subject="jpetstore",
        algorithm="leiden",
        graph_type="ssa",
    )

    assert metrics.loc[0, "cluster_count"] == 2
    assert metrics.loc[0, "subject"] == "jpetstore"
    assert metrics.loc[0, "algorithm"] == "leiden"
    assert metrics.loc[0, "graph_type"] == "ssa"


def test_calculate_partition_metrics_reports_cluster_size_statistics() -> None:
    metrics = calculate_partition_metrics(
        class_nodes_frame("A", "B", "C"),
        ssa_edges_frame(("A", "B", 3.0)),
        clusters_frame(("A", 0), ("B", 0), ("C", 1)),
        subject="jpetstore",
        algorithm="leiden",
        graph_type="ssa",
    )

    assert metrics.loc[0, "average_cluster_size"] == 1.5
    assert metrics.loc[0, "max_cluster_size"] == 2
    assert metrics.loc[0, "min_cluster_size"] == 1


def test_calculate_partition_metrics_reports_internal_external_edge_ratio() -> None:
    metrics = calculate_partition_metrics(
        class_nodes_frame("A", "B", "C"),
        ssa_edges_frame(("A", "B", 4.0), ("B", "C", 2.0)),
        clusters_frame(("A", 0), ("B", 0), ("C", 1)),
        subject="jpetstore",
        algorithm="leiden",
        graph_type="ssa",
    )

    assert metrics.loc[0, "internal_external_edge_ratio"] == 2.0


def test_calculate_partition_metrics_handles_zero_external_edges() -> None:
    metrics = calculate_partition_metrics(
        class_nodes_frame("A", "B"),
        ssa_edges_frame(("A", "B", 3.0)),
        clusters_frame(("A", 0), ("B", 0)),
        subject="jpetstore",
        algorithm="leiden",
        graph_type="ssa",
    )

    assert metrics.loc[0, "internal_external_edge_ratio"] == 3.0


def test_calculate_partition_metrics_handles_empty_edges() -> None:
    metrics = calculate_partition_metrics(
        class_nodes_frame("A", "B"),
        empty_edges_frame("g_ssa_weight"),
        clusters_frame(("A", 0), ("B", 1)),
        subject="jpetstore",
        algorithm="leiden",
        graph_type="ssa",
    )

    assert metrics.loc[0, "modularity"] == 0.0
    assert metrics.loc[0, "internal_external_edge_ratio"] == 0.0


def test_calculate_partition_metrics_returns_numeric_modularity() -> None:
    metrics = calculate_partition_metrics(
        class_nodes_frame("A", "B", "C"),
        ssa_edges_frame(("A", "B", 3.0), ("B", "C", 1.0)),
        clusters_frame(("A", 0), ("B", 0), ("C", 1)),
        subject="jpetstore",
        algorithm="leiden",
        graph_type="ssa",
    )

    assert isinstance(metrics.loc[0, "modularity"], float)


def test_calculate_partition_metrics_uses_raw_weight_for_raw_graph() -> None:
    edges = pd.DataFrame(
        {
            "source": ["A", "B"],
            "target": ["B", "C"],
            "raw_weight": [4.0, 2.0],
            "g_ssa_weight": [40.0, 20.0],
        }
    )

    metrics = calculate_partition_metrics(
        class_nodes_frame("A", "B", "C"),
        edges,
        clusters_frame(("A", 0), ("B", 0), ("C", 1)),
        subject="jpetstore",
        algorithm="leiden",
        graph_type="raw",
    )

    assert metrics.loc[0, "internal_external_edge_ratio"] == 2.0


def test_calculate_partition_metrics_uses_g_ssa_weight_for_ssa_graph() -> None:
    edges = pd.DataFrame(
        {
            "source": ["A", "B"],
            "target": ["B", "C"],
            "raw_weight": [4.0, 2.0],
            "g_ssa_weight": [8.0, 2.0],
        }
    )

    metrics = calculate_partition_metrics(
        class_nodes_frame("A", "B", "C"),
        edges,
        clusters_frame(("A", 0), ("B", 0), ("C", 1)),
        subject="jpetstore",
        algorithm="leiden",
        graph_type="ssa",
    )

    assert metrics.loc[0, "internal_external_edge_ratio"] == 4.0


def test_calculate_partition_metrics_rejects_invalid_graph_type() -> None:
    with pytest.raises(ValueError, match="graph_type must be 'raw' or 'ssa'"):
        calculate_partition_metrics(
            class_nodes_frame("A", "B"),
            ssa_edges_frame(("A", "B", 3.0)),
            clusters_frame(("A", 0), ("B", 0)),
            subject="jpetstore",
            algorithm="leiden",
            graph_type="G_ssa",
        )


def class_nodes_frame(*class_ids: str) -> pd.DataFrame:
    return pd.DataFrame({"class_id": list(class_ids)})


def clusters_frame(*rows: tuple[str, int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "class_id": [row[0] for row in rows],
            "cluster_id": [row[1] for row in rows],
        }
    )


def ssa_edges_frame(*rows: tuple[str, str, float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source": [row[0] for row in rows],
            "target": [row[1] for row in rows],
            "g_ssa_weight": [row[2] for row in rows],
        }
    )


def empty_edges_frame(weight_column: str) -> pd.DataFrame:
    return pd.DataFrame(columns=["source", "target", weight_column])
