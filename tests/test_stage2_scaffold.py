"""Stage 2 smoke tests for structure, wiring, and executable contracts."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.optimization import STRUCTURAL_OBJECTIVES
from evo_ms.optimization import objectives as obj
from evo_ms.optimization import encoding, problem
from evo_ms.utils.config_loader import load_yaml

ROOT = Path(__file__).resolve().parents[1]


def test_three_structural_objectives_only() -> None:
    names = [(o.name, o.direction) for o in STRUCTURAL_OBJECTIVES]
    assert names == [
        ("coupling", "minimize"),
        ("cohesion", "maximize"),
        ("imbalance", "minimize"),
    ]


def test_admissibility_thresholds_match_stage2_design() -> None:
    assert obj.MIN_CLUSTER_COUNT == 2
    assert problem.DEFAULT_MAX_CLUSTER_RATIO == 0.4


def test_config_declares_three_objectives_and_constraints() -> None:
    config = load_yaml(ROOT / "configs" / "experiments" / "02_stage2_nsga_structure_only.yml")
    assert [o["name"] for o in config["objectives"]] == ["coupling", "cohesion", "imbalance"]
    assert config["constraints"]["max_cluster_ratio"] == 0.4
    assert "singleton_ratio" not in config["constraints"]
    assert config["constraints"]["min_cluster_count"] == 2
    assert config["input_graph"]["name"] == "G_raw"
    assert config["input_graph"]["weight_column"] == "raw_weight"
    assert "graph_type" not in config
    assert "ssa_lambda" not in config
    assert config["baseline_leiden_profiles"] == ["raw_reference_leiden"]
    assert config["initialization"]["enabled"] is True
    assert config["initialization"]["strategy"] == "structure_aware_seeded"
    assert config["initialization"]["basis"] == "raw_reference_leiden_and_raw_graph"
    assert config["initialization"]["include_raw_leiden"] is True


def test_objectives_use_three_objective_contract() -> None:
    edges = pd.DataFrame(
        [
            {"source": "A", "target": "B", "raw_weight": 2.0},
            {"source": "C", "target": "D", "raw_weight": 3.0},
            {"source": "B", "target": "C", "raw_weight": 5.0},
        ]
    )
    cluster_by_class = {"A": 0, "B": 0, "C": 1, "D": 1}

    coupling, cohesion, imbalance = obj.evaluate_structural_objectives(
        edges,
        cluster_by_class,
        "raw_weight",
    )

    assert coupling == pytest.approx(0.5)
    assert cohesion == pytest.approx(2.5)
    assert imbalance == pytest.approx(0.0)


def test_singleton_cohesion_is_zero_and_constraints_are_vectorized() -> None:
    edges = pd.DataFrame(
        [
            {"source": "A", "target": "B", "raw_weight": 2.0},
            {"source": "B", "target": "C", "raw_weight": 1.0},
        ]
    )
    coupling, cohesion, imbalance = obj.evaluate_structural_objectives(
        edges,
        {"A": 0, "B": 0, "C": 1},
        "raw_weight",
    )
    assert coupling == pytest.approx(1.0 / 3.0)
    assert cohesion == pytest.approx(1.0)
    assert imbalance == pytest.approx(np.std([2, 1]) / np.mean([2, 1]))

    violations = obj.admissibility_violation(
        np.asarray([0, 0, 0, 0, 1, 1, 2, 2, 3, 4]),
        class_count=10,
        max_cluster_ratio=0.4,
    )
    np.testing.assert_allclose(violations, [0.0, -3.0])


def test_encoding_contracts() -> None:
    class_nodes = pd.DataFrame(
        {
            "class_id": ["A", "B", "C"],
            "class_name": ["Alpha", "Beta", "Gamma"],
        }
    )
    labels = np.asarray([7, 7, 3])

    np.testing.assert_array_equal(encoding.canonical_relabel(labels), [0, 0, 1])
    assert encoding.to_cluster_by_class(labels, class_nodes) == {"A": 0, "B": 0, "C": 1}
    clusters = encoding.to_clusters_frame(labels, class_nodes)
    assert list(clusters.columns) == ["class_id", "class_name", "cluster_id"]
    assert clusters.to_dict("records") == [
        {"class_id": "A", "class_name": "Alpha", "cluster_id": 0},
        {"class_id": "B", "class_name": "Beta", "cluster_id": 0},
        {"class_id": "C", "class_name": "Gamma", "cluster_id": 1},
    ]


def test_pymoo_problem_contract() -> None:
    pytest.importorskip("pymoo")
    class_nodes = pd.DataFrame(
        {
            "class_id": ["A", "B", "C", "D"],
            "class_name": ["Alpha", "Beta", "Gamma", "Delta"],
        }
    )
    edges = pd.DataFrame(
        [
            {"source": "A", "target": "B", "raw_weight": 2.0},
            {"source": "C", "target": "D", "raw_weight": 3.0},
            {"source": "B", "target": "C", "raw_weight": 5.0},
        ]
    )
    structural_problem = problem.build_structural_problem(
        class_nodes,
        edges,
        "raw_weight",
    )
    f, g = structural_problem.evaluate(
        np.asarray([0, 0, 1, 1]),
        return_values_of=["F", "G"],
    )
    repaired = problem.repair_labels(np.asarray([0, 0, 1, 1]), len(class_nodes))
    coupling, cohesion, imbalance = obj.evaluate_structural_objectives(
        edges,
        encoding.to_cluster_by_class(repaired, class_nodes),
        "raw_weight",
    )
    np.testing.assert_allclose(f, [coupling, -cohesion, imbalance])
    assert g.shape == (2,)
    assert np.all(g <= 0.0)


def test_max_cluster_ratio_is_shared_by_constraint_and_repair() -> None:
    labels = np.zeros(10, dtype=int)

    repaired = problem.repair_labels(labels, class_count=10, max_cluster_ratio=0.5)
    violations = obj.admissibility_violation(
        repaired,
        class_count=10,
        max_cluster_ratio=0.5,
    )

    assert max(np.bincount(repaired)) == 5
    assert violations[0] <= 0.0
    assert obj.admissibility_violation(
        repaired,
        class_count=10,
        max_cluster_ratio=0.4,
    )[0] > 0.0


@pytest.mark.parametrize("value", [0.0, -0.1, 1.0, 1.1])
def test_invalid_max_cluster_ratio_is_rejected(value: float) -> None:
    with pytest.raises(ValueError, match="max_cluster_ratio"):
        problem.validate_max_cluster_ratio(value)


def test_seeded_sampling_places_seed_individual_first() -> None:
    pytest.importorskip("pymoo")

    class DummyProblem:
        n_var = 6

    sampling = problem.LabelVectorSampling(
        seed_labels=[np.asarray([9, 9, 3, 3, 5, 5])],
    ).operator
    rows = sampling._do(DummyProblem(), 3, random_state=7)

    assert rows.shape == (3, 6)
    np.testing.assert_array_equal(rows[0], [0, 0, 1, 1, 2, 2])


def test_runner_and_design_docs_exist() -> None:
    assert (ROOT / "experiments" / "02_stage2_nsga_structure_only" / "run.py").exists()
    base = ROOT / "docs" / "stage2"
    for doc in ["workflow.md", "objectives_and_metrics.md", "experiment_design.md", "encoding_and_operators.md"]:
        assert (base / doc).exists()


def test_stage2_runner_is_raw_only() -> None:
    runner = (ROOT / "experiments" / "02_stage2_nsga_structure_only" / "run.py").read_text(
        encoding="utf-8",
    )
    for obsolete in [
        "build_ssa_edges",
        "run_rq3_comparison",
        "run_lambda_sensitivity",
        "--graph-type",
        "--ssa-lambda",
    ]:
        assert obsolete not in runner


def test_pymoo_dependency_importable_or_skipped() -> None:
    pytest.importorskip("pymoo")


def test_stage2_boundary_is_independent_of_final_stage3() -> None:
    runner = (ROOT / "experiments" / "02_stage2_nsga_structure_only" / "run.py").read_text(encoding="utf-8")
    config = (ROOT / "configs" / "experiments" / "02_stage2_nsga_structure_only.yml").read_text(encoding="utf-8")
    assert "stage3" not in runner.lower()
    assert "stage3" not in config.lower()
    # Final Stage 3 documentation is an allowed downstream namespace.  This
    # test protects the actual Stage 2 dependency boundary instead of
    # rejecting a documentation directory by name.
    assert (ROOT / "docs" / "stage3").is_dir()


def test_stage1_frozen_paths_intact() -> None:
    assert (ROOT / "experiments" / "01_stage1_leiden_baseline").is_dir()
    assert (ROOT / "results" / "daytrader" / "01_stage1_leiden_baseline").is_dir()
