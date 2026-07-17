"""Focused contracts for the Stage 3 four-objective integration."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from evo_ms.optimization.problem import build_structural_problem
from evo_ms.optimization.stage3_problem import (
    build_four_objective_problem,
    evaluate_four_objective_values,
)


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "experiments/04_stage3_semantic/run.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("stage3_runner_for_tests", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _synthetic_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    class_nodes = pd.DataFrame(
        {
            "class_id": ["A", "B", "C", "D"],
            "class_name": ["Alpha", "Beta", "Gamma", "Delta"],
        }
    )
    raw_edges = pd.DataFrame(
        [
            {"source": "A", "target": "B", "raw_weight": 2.0},
            {"source": "C", "target": "D", "raw_weight": 3.0},
            {"source": "B", "target": "C", "raw_weight": 5.0},
        ]
    )
    semantic_edges = pd.DataFrame(
        [
            {"class_id_a": "A", "class_id_b": "B", "weight": 2.0},
            {"class_id_a": "A", "class_id_b": "C", "weight": 1.0},
            {"class_id_a": "B", "class_id_b": "D", "weight": 1.0},
            {"class_id_a": "C", "class_id_b": "D", "weight": 2.0},
        ]
    )
    return class_nodes, raw_edges, semantic_edges


def test_stage3_problem_has_four_objectives_and_preserves_stage2_values() -> None:
    pytest.importorskip("pymoo")
    class_nodes, raw_edges, semantic_edges = _synthetic_inputs()
    stage2_problem = build_structural_problem(
        class_nodes, raw_edges, "raw_weight", max_cluster_ratio=0.5
    )
    stage3_problem = build_four_objective_problem(
        class_nodes, raw_edges, semantic_edges, "raw_weight", max_cluster_ratio=0.5
    )

    assert stage2_problem.n_obj == 3
    assert stage3_problem.n_obj == 4
    labels = np.asarray([0, 0, 1, 1])
    stage2_values = np.asarray(stage2_problem.evaluate(labels, return_values_of=["F"]), dtype=float)
    stage3_values = np.asarray(stage3_problem.evaluate(labels, return_values_of=["F"]), dtype=float)
    np.testing.assert_allclose(stage3_values[:3], stage2_values)
    assert stage3_values[3] == pytest.approx(1.0 / 3.0)


def test_stage3_direct_evaluation_matches_reported_objective_order() -> None:
    class_nodes, raw_edges, semantic_edges = _synthetic_inputs()
    mapping = {"A": 0, "B": 0, "C": 1, "D": 1}
    values = evaluate_four_objective_values(
        raw_edges, semantic_edges, mapping, "raw_weight", total_semantic_weight=6.0
    )
    assert len(values) == 4
    assert values[3] == pytest.approx(1.0 / 3.0)


@pytest.mark.parametrize(
    "semantic_edges, expected_message",
    [
        (pd.DataFrame(columns=["class_id_a", "class_id_b", "weight"]), "empty"),
        (pd.DataFrame([["A", "B", 0.0], ["C", "D", 0.0]], columns=["class_id_a", "class_id_b", "weight"]), "zero total"),
        (pd.DataFrame([["A", "B", 1.0]], columns=["class_id_a", "class_id_b", "weight"]), "scope mismatch"),
    ],
)
def test_stage3_problem_rejects_missing_or_invalid_formal_graph(
    semantic_edges: pd.DataFrame, expected_message: str
) -> None:
    class_nodes, raw_edges, _ = _synthetic_inputs()
    with pytest.raises(ValueError, match=expected_message):
        build_four_objective_problem(class_nodes, raw_edges, semantic_edges, "raw_weight")


def _pareto_row(solution_id: str, objective: tuple[float, float, float], f_semantic: float) -> dict:
    coupling, negative_cohesion, imbalance = objective
    return {
        "subject": "jpetstore",
        "seed": 0,
        "solution_id": solution_id,
        "coupling": coupling,
        "cohesion": -negative_cohesion,
        "imbalance": imbalance,
        "f_semantic": f_semantic,
        "pymoo_f0_coupling": coupling,
        "pymoo_f1_negative_cohesion": negative_cohesion,
        "pymoo_f2_imbalance": imbalance,
        "pymoo_f3_f_semantic": f_semantic,
        "feasible": True,
        "is_injected_seed": False,
        "label_vector": json.dumps([0, 0, 1, 1]),
    }


def test_projection_refilters_deduplicates_and_uses_only_stage2_selection_fields() -> None:
    runner = _load_runner()
    rows = [
        _pareto_row("seed0_solution000", (0.1, 0.8, 0.1), 0.2),
        _pareto_row("seed0_solution001", (0.1, 0.8, 0.1), 0.1),
        _pareto_row("seed0_solution002", (0.2, 0.7, 0.2), 0.3),
        _pareto_row("seed0_solution003", (0.3, 1.0, 0.3), 0.4),
    ]
    posthoc = [
        {"solution_id": solution_id, "weighted_modularity": modularity,
         "cluster_count": 2, "max_cluster_ratio": 0.5, "singleton_ratio": 0.0}
        for solution_id, modularity in [
            ("seed0_solution000", 0.2),
            ("seed0_solution001", 0.9),
            ("seed0_solution002", 0.8),
            ("seed0_solution003", 0.1),
        ]
    ]
    projected, selected = runner._project_front(rows, posthoc)
    assert [row["solution_id"] for row in projected] == [
        "seed0_solution000",
        "seed0_solution002",
    ]
    assert selected[0]["solution_id"] == "seed0_solution002"
    assert "f_semantic" not in selected[0]


def test_stage3_runner_does_not_load_model_or_fuse_graphs() -> None:
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "SentenceTransformer" not in source
    assert "generate_embeddings" not in source
    assert "union" not in source.lower()


def test_frozen_objective_contract_is_recorded_in_config_and_manifest() -> None:
    import yaml

    config = yaml.safe_load((ROOT / "configs/experiments/04_stage3_semantic.yml").read_text())
    manifest = json.loads((ROOT / "reports/stage3/formal_run_manifest.json").read_text())
    expected_report = ["coupling", "cohesion", "imbalance", "f_semantic"]
    expected_pymoo = ["coupling", "negative_cohesion", "imbalance", "f_semantic"]
    assert config["stage3_objective_order"]["report_columns"] == expected_report
    assert config["stage3_objective_order"]["pymoo_columns"] == expected_pymoo
    assert manifest["stage3_objective_order"]["report_columns"] == expected_report
    assert manifest["stage3_objective_order"]["pymoo_columns"] == expected_pymoo
    assert manifest["redundancy_diagnostic"]["diagnostic_only"] is True
