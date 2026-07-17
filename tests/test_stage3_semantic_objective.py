from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from evo_ms.optimization.semantic_objective import (
    evaluate_semantic_objective,
    load_semantic_edges,
    semantic_total_weight,
    validate_semantic_edges,
)


def edges(rows):
    return pd.DataFrame(rows, columns=["class_id_a", "class_id_b", "weight"])


def labels(*values):
    return {class_id: cluster for class_id, cluster in values}


def test_all_weight_internal_is_zero():
    graph = edges([["A", "B", 2.0], ["B", "C", 3.0]])
    assert evaluate_semantic_objective(graph, labels(("A", 7), ("B", 7), ("C", 7))) == 0.0


def test_all_weight_external_is_one():
    graph = edges([["A", "B", 2.0], ["B", "C", 3.0]])
    assert evaluate_semantic_objective(graph, labels(("A", 1), ("B", 2), ("C", 3))) == 1.0


def test_half_internal_weight_is_half():
    graph = edges([["A", "B", 4.0], ["B", "C", 4.0]])
    assert evaluate_semantic_objective(graph, labels(("A", 1), ("B", 1), ("C", 2))) == pytest.approx(0.5)


def test_empty_function_level_graph_returns_one():
    graph = edges([])
    assert evaluate_semantic_objective(graph, {}) == 1.0


def test_cluster_label_renaming_and_noncontiguous_labels_are_invariant():
    graph = edges([["A", "B", 4.0], ["B", "C", 4.0]])
    left = evaluate_semantic_objective(graph, labels(("A", 0), ("B", 0), ("C", 1)))
    right = evaluate_semantic_objective(graph, labels(("A", 41), ("B", 41), ("C", 900)))
    assert left == right == pytest.approx(0.5)


def test_each_undirected_row_is_counted_once():
    graph = edges([["A", "B", 2.0], ["A", "C", 6.0]])
    assert semantic_total_weight(graph) == 8.0
    assert evaluate_semantic_objective(graph, labels(("A", 1), ("B", 1), ("C", 2))) == pytest.approx(0.75)


@pytest.mark.parametrize(
    "graph,pattern",
    [
        (edges([["A", "B", 0.0]]), "zero total"),
        (edges([["A", "B", np.nan]]), "NaN"),
        (edges([["A", "B", np.inf]]), "NaN"),
        (edges([["A", "B", -1.0]]), "negative"),
        (edges([["A", "A", 1.0]]), "self-loop"),
        (edges([["A", "B", 1.0], ["A", "B", 1.0]]), "duplicate"),
    ],
)
def test_invalid_formal_graphs_are_rejected(graph, pattern):
    with pytest.raises(ValueError, match=pattern):
        validate_semantic_edges(graph, expected_class_ids={"A", "B"})


def test_scope_mismatch_is_explicit():
    with pytest.raises(ValueError, match="scope mismatch"):
        validate_semantic_edges(edges([["A", "B", 1.0]]), expected_class_ids={"A", "B", "C"})
    with pytest.raises(ValueError, match="scope mismatch"):
        evaluate_semantic_objective(edges([["A", "B", 1.0]]), labels(("A", 0), ("B", 0), ("C", 1)))


def test_loader_reads_only_final_semantic_edges_schema(tmp_path: Path):
    path = tmp_path / "semantic_edges.csv"
    pd.DataFrame(
        [["A", "B", 2.0, "a"]],
        columns=["class_id_a", "class_id_b", "weight", "selected_by"],
    ).to_csv(path, index=False)
    loaded = load_semantic_edges(path, {"A", "B"})
    assert list(loaded.columns) == ["class_id_a", "class_id_b", "weight"]
    assert semantic_total_weight(loaded) == 2.0


def test_objective_function_does_not_open_unrelated_files(monkeypatch):
    graph = edges([["A", "B", 1.0]])
    assert evaluate_semantic_objective(graph, labels(("A", 0), ("B", 1))) == 1.0
