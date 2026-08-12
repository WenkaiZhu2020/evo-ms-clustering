import importlib.util
import re
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts/visualization"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("export_cluster_graph_dot", SCRIPTS / "export_cluster_graph_dot.py")
assert spec and spec.loader
exporter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = exporter
spec.loader.exec_module(exporter)


NODE_HEADER = "class_id,class_name,package,class_file_path"
EDGE_HEADER = "source,target,type_weight,call_weight,raw_weight"
PARTITION_HEADER = "class_id,class_name,cluster_id"


def write_csv(path: Path, header: str, rows: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return path


def fixture(tmp_path: Path, partition: list[str], edges: list[str] | None = None, nodes=None):
    nodes = nodes or [
        "a,p.A,p,/A.class",
        "b,p.B,p,/B.class",
        "c,p.C,p,/C.class",
        "d,p.D,p,/D.class",
        "e,p.E,p,/E.class",
    ]
    edges = edges if edges is not None else [
        "p.A,p.B,1,2,3",
        "p.A,p.C,2,0,2",
        "p.B,p.C,0,1,1",
        "p.C,p.D,1,1,2",
    ]
    return (
        write_csv(tmp_path / "nodes.csv", NODE_HEADER, nodes),
        write_csv(tmp_path / "edges.csv", EDGE_HEADER, edges),
        write_csv(tmp_path / "partition.csv", PARTITION_HEADER, partition),
    )


def run_export(tmp_path: Path, partition: list[str], *, reference=None, edges=None, nodes=None):
    nodes_path, edges_path, partition_path = fixture(tmp_path, partition, edges, nodes)
    reference_path = None
    if reference is not None:
        reference_path = write_csv(tmp_path / "reference.csv", PARTITION_HEADER, reference)
    output = tmp_path / "graph.dot"
    node_summary = tmp_path / "cluster_nodes.csv"
    edge_summary = tmp_path / "cluster_edges.csv"
    summary = exporter.export_cluster_dot(
        nodes_path, edges_path, partition_path, output, "Test", reference_path,
        nodes_summary_output=node_summary, edges_summary_output=edge_summary,
    )
    return summary, output.read_text(encoding="utf-8"), node_summary.read_text(encoding="utf-8"), edge_summary.read_text(encoding="utf-8")


def test_aggregates_internal_and_cross_edges_and_keeps_isolate_cluster(tmp_path: Path):
    partition = [
        "a,p.A,1", "b,p.B,1", "c,p.C,2", "d,p.D,2", "e,p.E,3",
    ]
    summary, dot, node_csv, edge_csv = run_export(tmp_path, partition)
    assert summary["class_count"] == 5
    assert summary["raw_edge_count"] == 4
    assert summary["cluster_nodes"] == 3
    assert summary["aggregate_edges"] == 1
    assert summary["internal_class_edges"] == 2
    assert summary["cross_class_edges"] == 2
    assert summary["isolated_class_count"] == 1
    assert dot.count(" -- ") == 1
    assert 'label="C3\\n1 classes"' in dot
    assert "internal_edge_count" in node_csv
    assert "C1,1,2,1,3" in node_csv
    assert ",2," in edge_csv
    assert "C1,C2,2,2,1,3" in edge_csv


def test_canonical_order_and_partition_row_order_are_deterministic(tmp_path: Path):
    first = ["a,p.A,7", "b,p.B,7", "c,p.C,2", "d,p.D,2", "e,p.E,9"]
    permuted = ["e,p.E,4", "d,p.D,1", "c,p.C,1", "b,p.B,8", "a,p.A,8"]
    _, first_dot, *_ = run_export(tmp_path / "one", first)
    _, second_dot, *_ = run_export(tmp_path / "two", permuted)
    assert first_dot == second_dot


def test_reference_alignment_merge_and_unmatched_target_color(tmp_path: Path):
    reference = ["a,p.A,1", "b,p.B,1", "c,p.C,2", "d,p.D,2", "e,p.E,2"]
    target = ["a,p.A,7", "b,p.B,7", "c,p.C,8", "d,p.D,8", "e,p.E,9"]
    _, dot, node_csv, _ = run_export(tmp_path, target, reference=reference)
    assert "aligned to reference C" in dot
    assert "original_cluster_id" in node_csv
    assert "aligned_reference_cluster" in node_csv
    colors = re.findall(r'fillcolor="(#[0-9A-F]+)"', dot)
    assert len(colors) == 3 and len(set(colors)) == 3


def test_tie_matching_and_repeat_are_deterministic(tmp_path: Path):
    reference = ["a,p.A,1", "b,p.B,1", "c,p.C,2", "d,p.D,2", "e,p.E,3"]
    target = ["a,p.A,7", "b,p.B,8", "c,p.C,7", "d,p.D,8", "e,p.E,9"]
    first = run_export(tmp_path / "one", target, reference=reference)[1]
    second = run_export(tmp_path / "two", target, reference=reference)[1]
    assert first == second


def test_tie_matching_uses_shared_class_level_rule(tmp_path: Path):
    reference = ["a,p.A,1", "b,p.B,1", "c,p.C,2", "d,p.D,2", "e,p.E,3"]
    target = ["a,p.A,7", "b,p.B,8", "c,p.C,7", "d,p.D,8", "e,p.E,9"]
    _, dot, node_csv, _ = run_export(tmp_path, target, reference=reference)
    assert re.search(r"^T1,7,.*?,C1,", node_csv, flags=re.MULTILINE)
    assert re.search(r"^T2,8,.*?,C2,", node_csv, flags=re.MULTILINE)
    assert "aligned to reference C1" in dot
    assert "aligned to reference C2" in dot


@pytest.mark.parametrize(
    ("partition", "edges", "message"),
    [
        (["a,p.A,1", "b,p.B,1", "c,p.C,2", "d,p.D,2"], None, "class scope"),
        (["a,p.A,1", "a,p.A,2", "b,p.B,1", "c,p.C,2", "d,p.D,2", "e,p.E,3"], None, "duplicate class assignments"),
        (["a,p.A,1", "b,p.B,1", "c,p.C,2", "d,p.D,2", "e,p.E,3"], ["p.A,unknown.X,1,0,1"], "not present in nodes CSV"),
        (["a,p.A,1", "b,p.B,1", "c,p.C,2", "d,p.D,2", "e,p.E,3"], ["p.A,p.B,1,0,-1"], "non-negative"),
    ],
)
def test_invalid_inputs_are_rejected(tmp_path: Path, partition, edges, message):
    with pytest.raises(ValueError, match=message):
        run_export(tmp_path, partition, edges=edges)


def test_reference_scope_mismatch_is_rejected(tmp_path: Path):
    partition = ["a,p.A,1", "b,p.B,1", "c,p.C,2", "d,p.D,2", "e,p.E,3"]
    with pytest.raises(ValueError, match="reference partition class scope"):
        run_export(tmp_path, partition, reference=partition[:-1])


def test_node_size_and_edge_width_ranges(tmp_path: Path):
    partition = ["a,p.A,1", "b,p.B,1", "c,p.C,2", "d,p.D,3", "e,p.E,3"]
    _, dot, *_ = run_export(tmp_path, partition)
    widths = [float(value) for value in re.findall(r"(?<!pen)width=([0-9.]+)", dot)]
    pens = [float(value) for value in re.findall(r"penwidth=([0-9.]+)", dot)]
    assert widths and all(1.2 <= value <= 2.8 for value in widths)
    assert pens and all(0.8 <= value <= 5.0 for value in pens)


def test_palette_supports_at_least_40_unique_clusters():
    assert len(exporter._unique_palette()) >= 40
    assert len(set(exporter._unique_palette())) >= 40


def test_exporter_rejects_duplicate_undirected_edges(tmp_path: Path):
    partition = ["a,p.A,1", "b,p.B,1", "c,p.C,2", "d,p.D,2", "e,p.E,3"]
    duplicate = ["p.A,p.B,1,0,1", "p.B,p.A,1,0,1"]
    with pytest.raises(ValueError, match="duplicate undirected edge"):
        run_export(tmp_path, partition, edges=duplicate)


def test_exporter_rejects_self_loops(tmp_path: Path):
    partition = ["a,p.A,1", "b,p.B,1", "c,p.C,2", "d,p.D,2", "e,p.E,3"]
    with pytest.raises(ValueError, match="self-loop"):
        run_export(tmp_path, partition, edges=["p.A,p.A,1,0,1"])


def test_fixed_positions_are_imported_without_embedding_paths(tmp_path: Path):
    partition = ["a,p.A,1", "b,p.B,1", "c,p.C,2", "d,p.D,2", "e,p.E,3"]
    nodes_path, edges_path, partition_path = fixture(tmp_path, partition)
    positioned = tmp_path / "user-specific" / "positioned.dot"
    positioned.parent.mkdir()
    positioned.write_text(
        'graph G {\n  n0 [pos="10,20"];\n  n1 [pos="30,40"];\n  n2 [pos="50,60"];\n}\n',
        encoding="utf-8",
    )
    output = tmp_path / "fixed.dot"
    exporter.export_cluster_dot(
        nodes_path,
        edges_path,
        partition_path,
        output,
        "Fixed",
        reference_partition=partition_path,
        positions_from=positioned,
    )
    dot = output.read_text(encoding="utf-8")
    assert 'pos="10,20", pin=true' in dot
    assert 'pos="30,40", pin=true' in dot
    assert 'pos="50,60", pin=true' in dot
    assert str(tmp_path) not in dot
