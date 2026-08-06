from __future__ import annotations

from pathlib import Path

import pytest

from evo_ms.visualization.dot import (
    content_sha256,
    dot_quote,
    format_number,
    render_undirected_graph,
    stable_attributes,
    write_dot,
)


def test_dot_escaping() -> None:
    assert dot_quote('A "quoted" \\ path\nnext') == '"A \\"quoted\\" \\\\ path\\nnext"'


def test_attribute_order_is_stable() -> None:
    assert stable_attributes({"z": "last", "a": 2, "enabled": True}) == '[a=2, enabled=true, z="last"]'


def test_numeric_formatting_is_stable() -> None:
    assert format_number(2) == "2"
    assert format_number(-0.0) == "0"
    assert format_number(1.23456789012345) == "1.23456789012"
    with pytest.raises(ValueError, match="finite"):
        format_number(float("inf"))


def test_node_edge_and_endpoint_order_are_deterministic() -> None:
    nodes_one = {"b": {"label": "B"}, "a": {"label": "A"}, "c": {"label": "C"}}
    nodes_two = {"c": {"label": "C"}, "a": {"label": "A"}, "b": {"label": "B"}}
    first = render_undirected_graph(
        "G",
        nodes_one,
        [("c", "b", {"style": "dashed"}), ("b", "a", {"style": "solid"})],
    )
    second = render_undirected_graph(
        "G",
        nodes_two,
        [("a", "b", {"style": "solid"}), ("b", "c", {"style": "dashed"})],
    )
    assert first == second
    assert first.index('"a" [') < first.index('"b" [') < first.index('"c" [')
    assert first.count(" -- ") == 2


def test_same_input_is_byte_identical_and_has_final_newline(tmp_path: Path) -> None:
    text = render_undirected_graph("G", {"a": {"label": "A"}}, [])
    first = write_dot(tmp_path / "one.dot", text)
    second = write_dot(tmp_path / "two.dot", text.rstrip("\n"))
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes().endswith(b"\n")
    assert content_sha256(text) == content_sha256(text.rstrip("\n"))


def test_output_does_not_leak_absolute_paths(tmp_path: Path) -> None:
    text = render_undirected_graph("G", {"a": {"label": "A"}}, [])
    output = write_dot(tmp_path / "nested" / "graph.dot", text)
    assert str(tmp_path) not in output.read_text(encoding="utf-8")
    assert "/Users/" not in output.read_text(encoding="utf-8")


def test_self_loops_and_duplicate_undirected_edges_are_rejected() -> None:
    nodes = {"a": {}, "b": {}}
    with pytest.raises(ValueError, match="self-loop"):
        render_undirected_graph("G", nodes, [("a", "a", {})])
    with pytest.raises(ValueError, match="duplicate undirected edge"):
        render_undirected_graph("G", nodes, [("a", "b", {}), ("b", "a", {})])
