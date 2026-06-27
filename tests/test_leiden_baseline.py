from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.clustering.cluster_summary import summarize_clusters
from evo_ms.clustering.leiden_baseline import run_leiden_baseline


def test_run_leiden_baseline_returns_cluster_assignments() -> None:
    require_leiden()

    clusters = run_leiden_baseline(
        class_nodes_frame("A", "B", "C", "D"),
        edge_frame(("A", "B", 2.0), ("C", "D", 2.0), weight_column="g_ssa_weight"),
        graph_type="ssa",
        seed=7,
    )

    assert list(clusters.columns) == ["class_id", "class_name", "cluster_id"]
    assert clusters["class_id"].tolist() == ["A", "B", "C", "D"]
    assert clusters["cluster_id"].notna().all()


def test_run_leiden_baseline_preserves_isolated_nodes() -> None:
    require_leiden()

    clusters = run_leiden_baseline(
        class_nodes_frame("A", "B", "C"),
        edge_frame(("A", "B", 1.0), weight_column="g_ssa_weight"),
        graph_type="ssa",
    )

    assert set(clusters["class_id"]) == {"A", "B", "C"}


def test_run_leiden_baseline_uses_raw_weight_for_raw_graph() -> None:
    require_leiden()

    clusters = run_leiden_baseline(
        class_nodes_frame("A", "B"),
        edge_frame(("A", "B", 1.0), weight_column="raw_weight"),
        graph_type="raw",
    )

    assert clusters["class_id"].tolist() == ["A", "B"]


def test_run_leiden_baseline_uses_g_ssa_weight_for_ssa_graph() -> None:
    require_leiden()

    clusters = run_leiden_baseline(
        class_nodes_frame("A", "B"),
        edge_frame(("A", "B", 3.0), weight_column="g_ssa_weight"),
        graph_type="ssa",
    )

    assert clusters["class_id"].tolist() == ["A", "B"]


def test_run_leiden_baseline_accepts_n_iterations_override() -> None:
    require_leiden()

    clusters = run_leiden_baseline(
        class_nodes_frame("A", "B", "C", "D"),
        edge_frame(("A", "B", 2.0), ("C", "D", 2.0), weight_column="g_ssa_weight"),
        graph_type="ssa",
        seed=7,
        n_iterations=-1,
    )

    assert clusters["class_id"].tolist() == ["A", "B", "C", "D"]
    assert clusters["cluster_id"].notna().all()


def test_run_leiden_baseline_rejects_invalid_graph_type() -> None:
    with pytest.raises(ValueError, match="graph_type must be 'raw' or 'ssa'"):
        run_leiden_baseline(
            class_nodes_frame("A", "B"),
            edge_frame(("A", "B", 1.0), weight_column="raw_weight"),
            graph_type="G_raw",
        )


def test_run_leiden_baseline_rejects_missing_weight_column() -> None:
    with pytest.raises(ValueError, match="g_ssa_weight"):
        run_leiden_baseline(
            class_nodes_frame("A", "B"),
            edge_frame(("A", "B", 1.0), weight_column="raw_weight"),
            graph_type="ssa",
        )


def test_summarize_clusters_returns_cluster_sizes_and_class_names() -> None:
    summary = summarize_clusters(
        pd.DataFrame(
            {
                "class_id": ["A", "B", "C"],
                "class_name": ["pkg.Beta", "pkg.Alpha", "pkg.Gamma"],
                "cluster_id": [1, 1, 2],
            }
        )
    )

    assert summary.to_dict("records") == [
        {"cluster_id": 1, "cluster_size": 2, "class_names": "pkg.Alpha;pkg.Beta"},
        {"cluster_id": 2, "cluster_size": 1, "class_names": "pkg.Gamma"},
    ]


def require_leiden() -> None:
    pytest.importorskip("igraph")
    pytest.importorskip("leidenalg")


def class_nodes_frame(*class_ids: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "class_id": list(class_ids),
            "class_name": [f"pkg.{class_id}" for class_id in class_ids],
        }
    )


def edge_frame(*rows: tuple[str, str, float], weight_column: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source": [row[0] for row in rows],
            "target": [row[1] for row in rows],
            weight_column: [row[2] for row in rows],
        }
    )
