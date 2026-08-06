import importlib.util
import hashlib
import re
import sys
from pathlib import Path

import pytest


EXPORTER_PATH = Path(__file__).resolve().parents[1] / "scripts/visualization/export_partition_dot.py"
SPEC = importlib.util.spec_from_file_location("export_partition_dot", EXPORTER_PATH)
assert SPEC and SPEC.loader
exporter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = exporter
SPEC.loader.exec_module(exporter)


def write_csv(path: Path, header: str, rows: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return path


def inputs(tmp_path: Path, *, nodes=None, edges=None, partition=None):
    nodes = nodes or [
        "a,org.example.alpha.First,org.example.alpha,/First.class",
        "b,org.example.beta.Second,org.example.beta,/Second.class",
        "c,org.example.gamma.Third,org.example.gamma,/Third.class",
    ]
    edges = edges if edges is not None else [
        "org.example.alpha.First,org.example.beta.Second,1,0,1",
        "org.example.beta.Second,org.example.gamma.Third,0,2,4",
    ]
    partition = partition or [
        "a,org.example.alpha.First,2",
        "b,org.example.beta.Second,1",
        "c,org.example.gamma.Third,2",
    ]
    return (
        write_csv(tmp_path / "nodes.csv", "class_id,class_name,package,class_file_path", nodes),
        write_csv(tmp_path / "edges.csv", "source,target,type_weight,call_weight,raw_weight", edges),
        write_csv(tmp_path / "partition.csv", "class_id,class_name,cluster_id", partition),
    )


def export(tmp_path: Path, **kwargs) -> str:
    nodes, edges, partition = inputs(tmp_path, **kwargs)
    output = tmp_path / "graph.dot"
    exporter.export_dot(nodes, edges, partition, output, "simple_class", "Test")
    return output.read_text(encoding="utf-8")


def test_generates_dot_with_nodes_edges_and_isolated_node(tmp_path: Path):
    dot = export(tmp_path, edges=["org.example.alpha.First,org.example.beta.Second,1,0,1"])
    assert dot.startswith('graph "Test" {')
    assert dot.count(" [label=") == 3
    assert dot.count(" -- ") == 1
    assert 'label="Third"' in dot


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("simple_class", 'label="First"'),
        ("short_package_class", 'label="alpha.First"'),
        ("fully_qualified", 'label="org.example.alpha.First"'),
    ],
)
def test_label_modes(tmp_path: Path, mode: str, expected: str):
    nodes, edges, partition = inputs(tmp_path)
    output = tmp_path / f"{mode}.dot"
    exporter.export_dot(nodes, edges, partition, output, mode, "Test")
    assert expected in output.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("nodes", "edges", "partition", "message"),
    [
        (
            ["a,x.alpha.Same,x.alpha,/a", "b,y.beta.Same,y.beta,/b"],
            [],
            ["a,x.alpha.Same,1", "b,y.beta.Same,1"],
            "duplicate display labels",
        ),
        (None, None, ["a,org.example.alpha.First,1", "b,org.example.beta.Second,1"], "missing nodes"),
        (None, None, ["a,org.example.alpha.First,1", "b,org.example.beta.Second,1", "c,org.example.gamma.Third,2", "x,extra.Class,2"], "unknown nodes"),
        (None, ["org.example.alpha.First,org.example.beta.Second,1,0,1", "org.example.alpha.First,org.example.beta.Second,1,0,2"], None, "duplicate undirected edge"),
        (None, ["org.example.alpha.First,org.example.beta.Second,1,0,1", "org.example.beta.Second,org.example.alpha.First,1,0,2"], None, "duplicate undirected edge"),
        (None, ["org.example.alpha.First,org.example.alpha.First,1,0,1"], None, "self-loop"),
        (None, ["org.example.alpha.First,unknown.Class,1,0,1"], None, "not present in nodes CSV"),
        (None, ["org.example.alpha.First,org.example.beta.Second,1,0,-1"], None, "non-negative finite"),
        (None, None, ["a,org.example.alpha.First,1", "a,org.example.alpha.First,2", "b,org.example.beta.Second,1", "c,org.example.gamma.Third,2"], "duplicate class assignments"),
    ],
)
def test_rejects_invalid_inputs(tmp_path: Path, nodes, edges, partition, message: str):
    with pytest.raises(ValueError, match=message):
        export(tmp_path, nodes=nodes, edges=edges, partition=partition)
    assert not (tmp_path / "graph.dot").exists()


def test_cluster_colors_are_deterministic(tmp_path: Path):
    first = export(tmp_path / "one")
    second = export(tmp_path / "two")
    assert re.findall(r'fillcolor="(#[0-9A-F]+)"', first) == re.findall(r'fillcolor="(#[0-9A-F]+)"', second)


def test_edge_widths_are_in_range_and_constant_weights_use_medium_width(tmp_path: Path):
    dot = export(tmp_path)
    widths = [float(value) for value in re.findall(r"penwidth=([0-9.]+)", dot)]
    assert widths and all(1.0 <= width <= 4.0 for width in widths)
    constant = export(tmp_path / "constant", edges=["org.example.alpha.First,org.example.beta.Second,1,0,2", "org.example.beta.Second,org.example.gamma.Third,1,0,2"])
    assert re.findall(r"penwidth=([0-9.]+)", constant) == ["2.5", "2.5"]


def test_same_input_produces_byte_identical_dot(tmp_path: Path):
    first = export(tmp_path / "one")
    second = export(tmp_path / "two")
    assert first == second


def canonical_partition_inputs(tmp_path: Path, partition: list[str]):
    return inputs(
        tmp_path,
        nodes=[
            "a,example.A,example,/A.class",
            "b,example.B,example,/B.class",
            "c,example.C,example,/C.class",
            "d,example.D,example,/D.class",
        ],
        edges=[
            "example.A,example.B,1,0,1",
            "example.B,example.C,1,0,2",
            "example.C,example.D,1,0,3",
        ],
        partition=partition,
    )


def render_partition(tmp_path: Path, partition: list[str]) -> str:
    nodes, edges, partition_path = canonical_partition_inputs(tmp_path, partition)
    output = tmp_path / "graph.dot"
    exporter.export_dot(nodes, edges, partition_path, output, "simple_class", "Canonical")
    return output.read_text(encoding="utf-8")


def test_equivalent_partition_permutation_is_byte_identical(tmp_path: Path):
    partition_a = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,3"]
    partition_b = ["a,example.A,8", "b,example.B,8", "c,example.C,4", "d,example.D,1"]
    first = render_partition(tmp_path / "a", partition_a)
    second = render_partition(tmp_path / "b", partition_b)
    assert first == second
    assert hashlib.sha256(first.encode()).digest() == hashlib.sha256(second.encode()).digest()
    assert re.findall(r'fillcolor="(#[0-9A-F]+)"', first) == re.findall(r'fillcolor="(#[0-9A-F]+)"', second)
    assert re.findall(r'tooltip="[^"]+ \| cluster (C[0-9]+)"', first) == re.findall(r'tooltip="[^"]+ \| cluster (C[0-9]+)"', second)


def test_partition_row_order_does_not_change_dot(tmp_path: Path):
    ordered = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,3"]
    reordered = ["d,example.D,3", "b,example.B,1", "a,example.A,1", "c,example.C,2"]
    assert render_partition(tmp_path / "ordered", ordered) == render_partition(tmp_path / "reordered", reordered)


def test_node_and_edge_row_order_do_not_change_dot(tmp_path: Path):
    nodes = [
        "a,example.A,example,/A.class",
        "b,example.B,example,/B.class",
        "c,example.C,example,/C.class",
        "d,example.D,example,/D.class",
    ]
    edges = [
        "example.A,example.B,1,0,1",
        "example.B,example.C,1,0,2",
        "example.C,example.D,1,0,3",
    ]
    partition = [
        "a,example.A,1",
        "b,example.B,1",
        "c,example.C,2",
        "d,example.D,3",
    ]
    first = export(tmp_path / "ordered", nodes=nodes, edges=edges, partition=partition)
    second = export(
        tmp_path / "reordered",
        nodes=list(reversed(nodes)),
        edges=[
            "example.D,example.C,1,0,3",
            "example.C,example.B,1,0,2",
            "example.B,example.A,1,0,1",
        ],
        partition=partition,
    )
    assert first == second


def test_non_equivalent_partition_is_different_but_deterministic(tmp_path: Path):
    original = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,3"]
    changed = ["a,example.A,1", "b,example.B,2", "c,example.C,2", "d,example.D,3"]
    original_dot = render_partition(tmp_path / "original", original)
    changed_first = render_partition(tmp_path / "changed-one", changed)
    changed_second = render_partition(tmp_path / "changed-two", changed)
    assert original_dot != changed_first
    assert changed_first == changed_second


def aligned_dot(tmp_path: Path, target: list[str], reference: list[str] | None) -> str:
    nodes, edges, target_path = canonical_partition_inputs(tmp_path, target)
    reference_path = None
    if reference is not None:
        reference_path = write_csv(
            tmp_path / "reference.csv", "class_id,class_name,cluster_id", reference
        )
    output = tmp_path / "aligned.dot"
    exporter.export_dot(
        nodes, edges, target_path, output, "simple_class", "Aligned", reference_path
    )
    return output.read_text(encoding="utf-8")


def colors_by_label(dot: str) -> dict[str, str]:
    return dict(re.findall(r'label="([A-Z])".*?fillcolor="(#[0-9A-F]+)"', dot))


def test_equivalent_reference_partition_permutation_inherits_identical_colors(tmp_path: Path):
    reference = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,3"]
    target = ["a,example.A,8", "b,example.B,8", "c,example.C,4", "d,example.D,1"]
    reference_dot = aligned_dot(tmp_path / "reference", reference, None)
    target_dot = aligned_dot(tmp_path / "target", target, reference)
    assert colors_by_label(reference_dot) == colors_by_label(target_dot)
    assert "target cluster T1" in target_dot
    assert "aligned to reference C1" in target_dot


def test_target_merge_inherits_largest_overlap_reference_color(tmp_path: Path):
    reference = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,3"]
    target = ["a,example.A,9", "b,example.B,9", "c,example.C,9", "d,example.D,8"]
    reference_dot = aligned_dot(tmp_path / "reference", reference, None)
    target_dot = aligned_dot(tmp_path / "target", target, reference)
    reference_colors = colors_by_label(reference_dot)
    target_colors = colors_by_label(target_dot)
    assert target_colors["A"] == target_colors["B"] == target_colors["C"] == reference_colors["A"]


def test_unmatched_target_cluster_uses_extra_color(tmp_path: Path):
    reference = ["a,example.A,1", "b,example.B,1", "c,example.C,1", "d,example.D,1"]
    target = ["a,example.A,2", "b,example.B,2", "c,example.C,3", "d,example.D,3"]
    reference_dot = aligned_dot(tmp_path / "reference", reference, None)
    target_dot = aligned_dot(tmp_path / "target", target, reference)
    reference_colors = set(colors_by_label(reference_dot).values())
    target_colors = colors_by_label(target_dot)
    unmatched_colors = {target_colors["C"], target_colors["D"]}
    assert "| unmatched" in target_dot
    assert any(color not in reference_colors for color in unmatched_colors)


def test_tied_overlap_is_deterministic(tmp_path: Path):
    reference = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,2"]
    target = ["a,example.A,8", "b,example.B,4", "c,example.C,8", "d,example.D,4"]
    first = aligned_dot(tmp_path / "one", target, reference)
    second = aligned_dot(tmp_path / "two", target, reference)
    assert first == second


def test_tied_overlap_uses_same_mapping_for_colors_and_changed_classes():
    reference = {"example.A": "1", "example.B": "1", "example.C": "2", "example.D": "2"}
    target = {"example.A": "8", "example.B": "4", "example.C": "8", "example.D": "4"}
    matching = exporter.maximum_overlap_matching(target, reference)
    assert matching == {"8": "1", "4": "2"}
    assert exporter.changed_classes(target, reference) == {"example.B", "example.C"}


def test_reference_partition_scope_mismatch_is_rejected(tmp_path: Path):
    target = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,3"]
    with pytest.raises(ValueError, match="reference partition class scope"):
        aligned_dot(tmp_path, target, target[:-1])


def test_aligned_export_is_byte_identical_on_repeat(tmp_path: Path):
    reference = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,3"]
    target = ["a,example.A,8", "b,example.B,8", "c,example.C,4", "d,example.D,1"]
    assert aligned_dot(tmp_path / "one", target, reference) == aligned_dot(tmp_path / "two", target, reference)


def test_omitting_reference_preserves_canonical_mode(tmp_path: Path):
    partition = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,3"]
    assert aligned_dot(tmp_path / "one", partition, None) == aligned_dot(tmp_path / "two", partition, None)


def test_reference_csv_row_order_does_not_change_aligned_dot(tmp_path: Path):
    target = ["a,example.A,8", "b,example.B,8", "c,example.C,4", "d,example.D,1"]
    reference = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,3"]
    reordered = [reference[3], reference[1], reference[0], reference[2]]
    assert aligned_dot(tmp_path / "one", target, reference) == aligned_dot(tmp_path / "two", target, reordered)


def highlighted_dot(tmp_path: Path, target: list[str], reference: list[str] | None) -> str:
    nodes, edges, target_path = canonical_partition_inputs(tmp_path, target)
    reference_path = None if reference is None else write_csv(
        tmp_path / "comparison.csv", "class_id,class_name,cluster_id", reference
    )
    output = tmp_path / "highlighted.dot"
    exporter.export_dot(
        nodes, edges, target_path, output, "simple_class", "Highlight",
        highlight_changes_from_path=reference_path,
    )
    return output.read_text(encoding="utf-8")


def test_highlight_detects_changed_nodes_but_not_label_permutations(tmp_path: Path):
    reference = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,3"]
    permutation = ["a,example.A,8", "b,example.B,8", "c,example.C,4", "d,example.D,1"]
    assert 'color="#C00000"' not in highlighted_dot(tmp_path / "permutation", permutation, reference)
    changed = ["a,example.A,8", "b,example.B,8", "c,example.C,8", "d,example.D,1"]
    dot = highlighted_dot(tmp_path / "changed", changed, reference)
    assert re.search(r'label="C".*color="#C00000", penwidth=3.0', dot) is not None
    assert re.search(r'label="A".*color="#C00000"', dot) is None
    assert 'changed from reference' in dot


def test_highlight_merge_marks_only_moved_member(tmp_path: Path):
    reference = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,3"]
    target = ["a,example.A,9", "b,example.B,9", "c,example.C,9", "d,example.D,8"]
    dot = highlighted_dot(tmp_path, target, reference)
    assert re.search(r'label="C".*color="#C00000", penwidth=3.0', dot)
    assert re.search(r'label="A".*color="#C00000"', dot) is None


def test_highlight_scope_mismatch_is_rejected(tmp_path: Path):
    target = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,3"]
    with pytest.raises(ValueError, match="highlight comparison partition class scope"):
        highlighted_dot(tmp_path, target, target[:-1])


def test_highlight_is_deterministic_and_omitting_it_is_compatible(tmp_path: Path):
    reference = ["a,example.A,1", "b,example.B,1", "c,example.C,2", "d,example.D,3"]
    target = ["a,example.A,8", "b,example.B,8", "c,example.C,8", "d,example.D,1"]
    assert highlighted_dot(tmp_path / "one", target, reference) == highlighted_dot(tmp_path / "two", target, reference)
    assert aligned_dot(tmp_path / "without-one", target, None) == aligned_dot(tmp_path / "without-two", target, None)


def test_positions_from_dot_reads_nodes_not_edge_splines(tmp_path: Path):
    positioned = tmp_path / "positioned.dot"
    positioned.write_text(
        'graph G {\n  n0 [pos="10,20"];\n  n1 [pos="30,40"];\n'
        '  n0 -- n1 [pos="1,2 3,4"];\n}\n',
        encoding="utf-8",
    )
    assert exporter.positions_from_dot(positioned, {"A", "B"}) == {"n0": "10,20", "n1": "30,40"}


def test_export_imports_positions_without_embedding_input_paths(tmp_path: Path):
    nodes, edges, partition = inputs(tmp_path)
    positioned = tmp_path / "user-specific" / "positioned.dot"
    positioned.parent.mkdir()
    positioned.write_text(
        'graph G {\n  n0 [pos="10,20"];\n  n1 [pos="30,40"];\n  n2 [pos="50,60"];\n}\n',
        encoding="utf-8",
    )
    output = tmp_path / "fixed.dot"
    exporter.export_dot(
        nodes,
        edges,
        partition,
        output,
        "simple_class",
        "Fixed",
        positions_from_path=positioned,
    )
    dot = output.read_text(encoding="utf-8")
    assert 'pos="10,20", pin=true' in dot
    assert 'pos="30,40", pin=true' in dot
    assert 'pos="50,60", pin=true' in dot
    assert str(tmp_path) not in dot
