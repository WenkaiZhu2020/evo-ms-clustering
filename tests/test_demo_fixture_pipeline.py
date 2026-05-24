from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.clustering.leiden_baseline import run_leiden_baseline
from evo_ms.evaluation.partition_metrics import calculate_partition_metrics
from evo_ms.extraction.dependency_extractor import load_extracted_subject
from evo_ms.graph.raw_graph_builder import build_raw_edges, build_raw_graph
from evo_ms.graph.ssa_graph_builder import build_g_ssa_graph, build_ssa_edges


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "demo_subject"


def test_demo_fixture_builds_raw_and_ssa_graphs() -> None:
    extracted = load_extracted_subject(FIXTURE_DIR)
    class_nodes = extracted["class_nodes"]
    structural_dependencies = extracted["structural_dependencies"]
    ssa_flow_edges = extracted["ssa_flow_edges"]

    raw_edges = build_raw_edges(class_nodes, structural_dependencies)
    ssa_edges = build_ssa_edges(class_nodes, raw_edges, ssa_flow_edges)
    raw_graph = build_raw_graph(class_nodes, structural_dependencies)
    ssa_graph = build_g_ssa_graph(class_nodes, raw_edges, ssa_flow_edges)

    assert len(class_nodes) == 6
    assert set(class_nodes["class_id"]) == {"A", "B", "C", "D", "E", "F"}
    assert raw_edges["raw_weight"].sum() == 7.0
    assert ssa_edges["g_ssa_weight"].sum() == 13.0
    assert raw_graph.has_node("F")
    assert ssa_graph.has_node("F")
    assert raw_graph.number_of_nodes() == 6
    assert raw_graph.number_of_edges() == 5
    assert ssa_graph.number_of_nodes() == 6
    assert ssa_graph.number_of_edges() == 7


def test_demo_fixture_runs_leiden_and_partition_metrics(tmp_path: Path) -> None:
    pytest.importorskip("igraph")
    pytest.importorskip("leidenalg")

    extracted = load_extracted_subject(FIXTURE_DIR)
    class_nodes = extracted["class_nodes"]
    raw_edges = build_raw_edges(class_nodes, extracted["structural_dependencies"])
    ssa_edges = build_ssa_edges(class_nodes, raw_edges, extracted["ssa_flow_edges"])

    clusters = run_leiden_baseline(
        class_nodes,
        ssa_edges,
        graph_type="ssa",
        resolution=1.0,
        seed=42,
    )
    metrics = calculate_partition_metrics(
        class_nodes,
        ssa_edges,
        clusters,
        subject="demo_subject",
        algorithm="leiden",
        graph_type="ssa",
    )

    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    clusters.to_csv(output_dir / "clusters.csv", index=False)
    metrics.to_csv(output_dir / "metrics.csv", index=False)

    assert set(clusters["class_id"]) == {"A", "B", "C", "D", "E", "F"}
    assert metrics.loc[0, "subject"] == "demo_subject"
    assert metrics.loc[0, "graph_type"] == "ssa"
    assert metrics.loc[0, "cluster_count"] >= 1
    assert (output_dir / "clusters.csv").exists()
    assert (output_dir / "metrics.csv").exists()
