from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.graph.raw_graph_builder import build_raw_edges, build_raw_graph
from evo_ms.graph.ssa_graph_builder import build_g_ssa_graph, build_ssa_edges
from evo_ms.evidence.ssa_flow_evidence import validate_ssa_flow_type


def test_build_raw_graph_adds_undirected_edges() -> None:
    graph = build_raw_graph([("A", "B")])
    assert graph.has_edge("A", "B")
    assert not graph.is_directed()


def test_build_raw_edges_adds_simple_type_edge() -> None:
    raw_edges = build_raw_edges(
        class_nodes_frame("A", "B"),
        structural_frame(("A", "B", "type", 1.0)),
    )

    assert raw_edges.to_dict("records") == [
        {
            "source": "A",
            "target": "B",
            "type_weight": 1.0,
            "call_weight": 0.0,
            "raw_weight": 1.0,
        }
    ]


def test_build_raw_edges_adds_simple_call_edge() -> None:
    raw_edges = build_raw_edges(
        class_nodes_frame("A", "B"),
        structural_frame(("A", "B", "call", 2.0)),
    )

    assert raw_edges.loc[0, "type_weight"] == 0.0
    assert raw_edges.loc[0, "call_weight"] == 2.0
    assert raw_edges.loc[0, "raw_weight"] == 2.0


def test_build_raw_edges_combines_type_and_call_edges_between_same_classes() -> None:
    raw_edges = build_raw_edges(
        class_nodes_frame("A", "B"),
        structural_frame(
            ("A", "B", "type", 1.0),
            ("A", "B", "type", 2.0),
            ("A", "B", "call", 2.0),
        ),
    )

    assert raw_edges.loc[0, "type_weight"] == 3.0
    assert raw_edges.loc[0, "call_weight"] == 2.0
    assert raw_edges.loc[0, "raw_weight"] == 5.0


def test_build_raw_edges_combines_reverse_direction_as_one_undirected_pair() -> None:
    raw_edges = build_raw_edges(
        class_nodes_frame("A", "B"),
        structural_frame(
            ("B", "A", "type", 1.0),
            ("A", "B", "call", 2.0),
        ),
    )

    assert raw_edges.to_dict("records") == [
        {
            "source": "A",
            "target": "B",
            "type_weight": 1.0,
            "call_weight": 2.0,
            "raw_weight": 3.0,
        }
    ]


def test_build_raw_edges_rejects_invalid_node_reference() -> None:
    with pytest.raises(ValueError, match="not present in class_nodes.csv"):
        build_raw_edges(
            class_nodes_frame("A"),
            structural_frame(("A", "B", "type", 1.0)),
        )


def test_build_raw_edges_removes_self_loops_with_warning() -> None:
    with pytest.warns(RuntimeWarning, match="removed 1 self-loop"):
        raw_edges = build_raw_edges(
            class_nodes_frame("A", "B"),
            structural_frame(("A", "A", "type", 1.0), ("A", "B", "call", 2.0)),
        )

    assert raw_edges[["source", "target"]].to_dict("records") == [
        {"source": "A", "target": "B"}
    ]


def test_build_raw_edges_row_count_matches_unique_undirected_pairs() -> None:
    with pytest.warns(RuntimeWarning, match="removed 1 self-loop"):
        raw_edges = build_raw_edges(
            class_nodes_frame("A", "B", "C"),
            structural_frame(
                ("B", "A", "type", 1.0),
                ("A", "B", "call", 2.0),
                ("C", "A", "type", 1.0),
                ("C", "C", "call", 4.0),
            ),
        )

    assert len(raw_edges) == 2
    assert raw_edges["source"].ne(raw_edges["target"]).all()
    assert len(_undirected_pairs(raw_edges)) == len(raw_edges)
    assert raw_edges[["source", "target"]].to_dict("records") == [
        {"source": "A", "target": "B"},
        {"source": "A", "target": "C"},
    ]


def test_build_raw_graph_uses_weighted_raw_edges() -> None:
    graph = build_raw_graph(
        class_nodes_frame("A", "B"),
        structural_frame(("A", "B", "type", 1.0), ("A", "B", "call", 2.0)),
    )

    assert graph.has_node("A")
    assert graph.has_edge("A", "B")
    assert not graph.is_directed()
    assert graph["A"]["B"]["type_weight"] == 1.0
    assert graph["A"]["B"]["call_weight"] == 2.0
    assert graph["A"]["B"]["raw_weight"] == 3.0


def test_build_ssa_edges_adds_return_value_flow() -> None:
    ssa_edges = build_ssa_edges(
        class_nodes_frame("A", "B"),
        empty_raw_edges_frame(),
        ssa_flow_frame(("A", "B", "return_value_flow", 3.0)),
    )

    assert ssa_edges.to_dict("records") == [
        {
            "source": "A",
            "target": "B",
            "type_weight": 0.0,
            "call_weight": 0.0,
            "return_flow_weight": 3.0,
            "argument_flow_weight": 0.0,
            "ssa_flow_weight": 3.0,
            "g_ssa_weight": 3.0,
        }
    ]


def test_build_ssa_edges_adds_argument_passing_flow() -> None:
    ssa_edges = build_ssa_edges(
        class_nodes_frame("A", "B"),
        empty_raw_edges_frame(),
        ssa_flow_frame(("A", "B", "argument_passing_flow", 3.0)),
    )

    assert ssa_edges.loc[0, "return_flow_weight"] == 0.0
    assert ssa_edges.loc[0, "argument_flow_weight"] == 3.0
    assert ssa_edges.loc[0, "ssa_flow_weight"] == 3.0
    assert ssa_edges.loc[0, "g_ssa_weight"] == 3.0


def test_build_ssa_edges_combines_raw_and_ssa_flow_edges() -> None:
    raw_edges = build_raw_edges(
        class_nodes_frame("A", "B"),
        structural_frame(("A", "B", "type", 1.0), ("A", "B", "call", 2.0)),
    )

    ssa_edges = build_ssa_edges(
        class_nodes_frame("A", "B"),
        raw_edges,
        ssa_flow_frame(
            ("A", "B", "return_value_flow", 3.0),
            ("A", "B", "argument_passing_flow", 3.0),
        ),
    )

    assert ssa_edges.loc[0, "type_weight"] == 1.0
    assert ssa_edges.loc[0, "call_weight"] == 2.0
    assert ssa_edges.loc[0, "ssa_flow_weight"] == 6.0
    assert ssa_edges.loc[0, "g_ssa_weight"] == 9.0


def test_build_ssa_edges_combines_reverse_direction_as_one_undirected_pair() -> None:
    ssa_edges = build_ssa_edges(
        class_nodes_frame("A", "B"),
        build_raw_edges(
            class_nodes_frame("A", "B"),
            structural_frame(("B", "A", "type", 1.0)),
        ),
        ssa_flow_frame(
            ("A", "B", "return_value_flow", 3.0),
            ("B", "A", "argument_passing_flow", 3.0),
        ),
    )

    assert ssa_edges.to_dict("records") == [
        {
            "source": "A",
            "target": "B",
            "type_weight": 1.0,
            "call_weight": 0.0,
            "return_flow_weight": 3.0,
            "argument_flow_weight": 3.0,
            "ssa_flow_weight": 6.0,
            "g_ssa_weight": 7.0,
        }
    ]


def test_build_ssa_edges_drops_self_loops_and_keeps_unique_undirected_pairs() -> None:
    class_nodes = class_nodes_frame("A", "B", "C", "D")
    raw_edges = build_raw_edges(
        class_nodes,
        structural_frame(
            ("B", "A", "type", 1.0),
            ("A", "B", "call", 2.0),
        ),
    )

    ssa_edges = build_ssa_edges(
        class_nodes,
        raw_edges,
        ssa_flow_frame(
            ("A", "B", "argument_passing_flow", 3.0),
            ("C", "D", "return_value_flow", 3.0),
            ("D", "C", "return_value_flow", 3.0),
            ("B", "B", "argument_passing_flow", 3.0),
        ),
    )

    assert len(ssa_edges) == 2
    assert ssa_edges["source"].ne(ssa_edges["target"]).all()
    assert len(_undirected_pairs(ssa_edges)) == len(ssa_edges)

    by_pair = {
        (row["source"], row["target"]): row
        for row in ssa_edges.to_dict("records")
    }
    assert by_pair[("A", "B")]["type_weight"] == 1.0
    assert by_pair[("A", "B")]["call_weight"] == 2.0
    assert by_pair[("A", "B")]["argument_flow_weight"] == 3.0
    assert by_pair[("A", "B")]["g_ssa_weight"] == 6.0
    assert by_pair[("C", "D")]["type_weight"] == 0.0
    assert by_pair[("C", "D")]["call_weight"] == 0.0
    assert by_pair[("C", "D")]["return_flow_weight"] == 6.0
    assert by_pair[("C", "D")]["g_ssa_weight"] == 6.0


def test_build_ssa_edges_applies_lambda_to_ssa_contribution_only() -> None:
    raw_edges = build_raw_edges(
        class_nodes_frame("A", "B"),
        structural_frame(("A", "B", "type", 1.0), ("A", "B", "call", 2.0)),
    )

    ssa_edges = build_ssa_edges(
        class_nodes_frame("A", "B"),
        raw_edges,
        ssa_flow_frame(("A", "B", "return_value_flow", 3.0)),
        ssa_lambda=2.0,
    )

    assert ssa_edges.loc[0, "type_weight"] == 1.0
    assert ssa_edges.loc[0, "call_weight"] == 2.0
    assert ssa_edges.loc[0, "ssa_flow_weight"] == 6.0
    assert ssa_edges.loc[0, "g_ssa_weight"] == 9.0


def test_build_ssa_edges_lambda_zero_drops_flow_only_edges() -> None:
    ssa_edges = build_ssa_edges(
        class_nodes_frame("A", "B"),
        empty_raw_edges_frame(),
        ssa_flow_frame(("A", "B", "return_value_flow", 3.0)),
        ssa_lambda=0.0,
    )

    assert ssa_edges.empty


def test_build_ssa_edges_includes_ssa_flow_only_edge() -> None:
    ssa_edges = build_ssa_edges(
        class_nodes_frame("A", "B", "C"),
        build_raw_edges(class_nodes_frame("A", "B", "C"), structural_frame(("A", "B", "type", 1.0))),
        ssa_flow_frame(("B", "C", "return_value_flow", 3.0)),
    )

    flow_only = ssa_edges.loc[(ssa_edges["source"] == "B") & (ssa_edges["target"] == "C")].iloc[0]
    assert flow_only["type_weight"] == 0.0
    assert flow_only["call_weight"] == 0.0
    assert flow_only["return_flow_weight"] == 3.0
    assert flow_only["g_ssa_weight"] == 3.0


def test_build_ssa_edges_rejects_invalid_flow_type() -> None:
    with pytest.raises(ValueError, match="unsupported flow_type values"):
        build_ssa_edges(
            class_nodes_frame("A", "B"),
            empty_raw_edges_frame(),
            ssa_flow_frame(("A", "B", "data_flow", 3.0)),
        )


def test_build_ssa_edges_rejects_shared_domain_object() -> None:
    with pytest.raises(ValueError, match="shared_domain_object"):
        build_ssa_edges(
            class_nodes_frame("A", "B"),
            empty_raw_edges_frame(),
            ssa_flow_frame(("A", "B", "shared_domain_object", 1.0)),
        )


def test_build_g_ssa_graph_uses_weighted_ssa_edges() -> None:
    graph = build_g_ssa_graph(
        class_nodes_frame("A", "B"),
        build_raw_edges(class_nodes_frame("A", "B"), structural_frame(("A", "B", "call", 2.0))),
        ssa_flow_frame(("A", "B", "return_value_flow", 3.0)),
    )

    assert graph.has_edge("A", "B")
    assert not graph.is_directed()
    assert graph["A"]["B"]["call_weight"] == 2.0
    assert graph["A"]["B"]["return_flow_weight"] == 3.0
    assert graph["A"]["B"]["g_ssa_weight"] == 5.0


def test_validate_ssa_flow_type_rejects_removed_flow_types() -> None:
    for flow_type in ("shared_domain_object", "parameter_passing_flow"):
        try:
            validate_ssa_flow_type(flow_type)
        except ValueError:
            continue
        raise AssertionError(f"{flow_type} should not be accepted")


def class_nodes_frame(*class_ids: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "class_id": class_id,
                "class_name": f"com.example.{class_id}",
                "package": "com.example",
                "class_file_path": f"target/classes/com/example/{class_id}.class",
            }
            for class_id in class_ids
        ]
    )


def structural_frame(*rows: tuple[str, str, str, float]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "source": source,
                "target": target,
                "dependency_type": dependency_type,
                "weight": weight,
                "evidence_kind": "method_call" if dependency_type == "call" else "field_type_reference",
                "evidence_location": f"{source}.evidence",
            }
            for source, target, dependency_type, weight in rows
        ]
    )


def empty_raw_edges_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["source", "target", "type_weight", "call_weight", "raw_weight"])


def ssa_flow_frame(*rows: tuple[str, str, str, float]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "source": source,
                "target": target,
                "flow_type": flow_type,
                "weight": weight,
                "evidence_method": f"{source}.method",
                "evidence_statement": f"{source} statement",
            }
            for source, target, flow_type, weight in rows
        ]
    )


def _undirected_pairs(edges: pd.DataFrame) -> set[tuple[str, str]]:
    return {
        tuple(sorted((str(row["source"]), str(row["target"]))))
        for row in edges.to_dict("records")
    }
