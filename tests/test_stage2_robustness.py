"""Stage 2 robustness runner contracts."""

from __future__ import annotations

import importlib.util
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.extraction.dependency_extractor import load_raw_extracted_subject
from evo_ms.optimization.objectives import evaluate_structural_objectives

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "experiments" / "02_stage2_nsga_structure_only" / "run.py"
ROBUSTNESS_PATH = ROOT / "experiments" / "02_stage2_nsga_structure_only" / "run_robustness.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


stage2_run = _load_module(RUNNER_PATH, "stage2_run_for_tests")
stage2_robustness = _load_module(ROBUSTNESS_PATH, "stage2_robustness_for_tests")


def test_raw_only_loader_does_not_require_ssa_csv(tmp_path: Path) -> None:
    pd.DataFrame(
        [
            {
                "class_id": "A",
                "class_name": "A",
                "package": "p",
                "class_file_path": "A.class",
            },
            {
                "class_id": "B",
                "class_name": "B",
                "package": "p",
                "class_file_path": "B.class",
            },
        ]
    ).to_csv(tmp_path / "class_nodes.csv", index=False)
    pd.DataFrame(
        [
            {
                "source": "A",
                "target": "B",
                "dependency_type": "call",
                "weight": 2.0,
                "evidence_kind": "method_call",
                "evidence_location": "A.m",
            }
        ]
    ).to_csv(tmp_path / "structural_dependencies.csv", index=False)

    extracted = load_raw_extracted_subject(tmp_path)

    assert set(extracted) == {"class_nodes", "structural_dependencies"}
    assert len(extracted["class_nodes"]) == 2
    assert len(extracted["structural_dependencies"]) == 1


def test_adjacency_iteration_order_is_stable() -> None:
    edges = pd.DataFrame(
        [
            {"source": "C", "target": "A", "raw_weight": 1.0},
            {"source": "B", "target": "A", "raw_weight": 1.0},
            {"source": "D", "target": "A", "raw_weight": 1.0},
        ]
    )

    adjacency = stage2_run._adjacency_by_class(edges)

    assert adjacency["A"] == ("B", "C", "D")
    assert all(isinstance(neighbors, tuple) for neighbors in adjacency.values())


def test_perturbed_initialization_is_repeatable_for_same_seed() -> None:
    class_nodes = pd.DataFrame(
        {
            "class_id": ["A", "B", "C", "D", "E", "F"],
            "class_name": ["A", "B", "C", "D", "E", "F"],
        }
    )
    raw_edges = pd.DataFrame(
        [
            {"source": "A", "target": "C", "raw_weight": 1.0},
            {"source": "A", "target": "B", "raw_weight": 1.0},
            {"source": "A", "target": "D", "raw_weight": 1.0},
            {"source": "E", "target": "F", "raw_weight": 1.0},
        ]
    )
    raw_leiden = pd.DataFrame(
        {
            "class_id": ["A", "B", "C", "D", "E", "F"],
            "class_name": ["A", "B", "C", "D", "E", "F"],
            "cluster_id": [0, 0, 1, 1, 2, 2],
        }
    )
    config = {
        "enabled": True,
        "include_raw_leiden": True,
        "perturbations": {"enabled": True, "fractions": [0.2], "per_fraction": 3},
        "graph_groupings": {"enabled": True, "target_offsets_from_raw_leiden": [0]},
    }

    first = stage2_run._seed_initialization_records(
        class_nodes,
        raw_edges,
        raw_leiden,
        seed=7,
        config=config,
    )
    second = stage2_run._seed_initialization_records(
        class_nodes,
        raw_edges,
        raw_leiden,
        seed=7,
        config=config,
    )

    assert [(r["name"], r["category"]) for r in first] == [
        (r["name"], r["category"]) for r in second
    ]
    for left, right in zip(first, second, strict=True):
        np.testing.assert_array_equal(left["labels"], right["labels"])


def test_select_solution_tie_breaks_by_canonical_label_vector_independent_of_order() -> None:
    posthoc_rows = [
        {"solution_id": "b", "weighted_modularity": 0.5, "cluster_count": 2, "max_cluster_ratio": 0.5, "singleton_ratio": 0.0},
        {"solution_id": "a", "weighted_modularity": 0.5, "cluster_count": 2, "max_cluster_ratio": 0.5, "singleton_ratio": 0.0},
    ]
    rows = [
        {
            "solution_id": "b",
            "feasible": True,
            "is_injected_seed": False,
            "coupling": 0.2,
            "cohesion": 1.0,
            "imbalance": 0.0,
            "label_vector": "[1, 0, 1]",
        },
        {
            "solution_id": "a",
            "feasible": True,
            "is_injected_seed": False,
            "coupling": 0.2,
            "cohesion": 1.0,
            "imbalance": 0.0,
            "label_vector": "[0, 0, 1]",
        },
    ]

    selected_forward = stage2_run._select_solution(posthoc_rows, rows)
    selected_reverse = stage2_run._select_solution(list(reversed(posthoc_rows)), list(reversed(rows)))

    assert selected_forward["solution_id"] == "a"
    assert selected_reverse["solution_id"] == "a"


def test_normalize_checked_rejects_out_of_bounds() -> None:
    bounds = {
        "objective_order": ["coupling", "negative_cohesion", "imbalance"],
        "lower_bounds": [0.0, -2.0, 0.0],
        "upper_bounds": [1.0, 0.0, 1.0],
        "calibration_seeds": [1000],
    }

    normalized = stage2_robustness._normalize_checked(
        np.asarray([[0.5, -1.0, 0.25]]),
        bounds,
    )
    np.testing.assert_allclose(normalized, [[0.5, 0.5, 0.25]])

    with pytest.raises(ValueError, match="calibration-bound violation"):
        stage2_robustness._normalize_checked(np.asarray([[1.2, -1.0, 0.25]]), bounds)


def test_normalize_checked_accepts_boundary_and_tolerance() -> None:
    bounds = {
        "objective_order": ["coupling", "negative_cohesion", "imbalance"],
        "lower_bounds": [0.0, -2.0, 0.0],
        "upper_bounds": [1.0, 0.0, 1.0],
        "bound_tolerance": 1e-12,
    }

    normalized = stage2_robustness._normalize_checked(
        np.asarray([[1.0 + 5e-13, -2.0 - 5e-13, 1.0]]),
        bounds,
    )
    np.testing.assert_allclose(normalized, [[1.0 + 5e-13, -2.5e-13, 1.0]], atol=1e-16)

    with pytest.raises(ValueError, match="calibration-bound violation"):
        stage2_robustness._normalize_checked(np.asarray([[1.0 + 2e-12, -1.0, 0.0]]), bounds)


def test_theoretical_coupling_and_cohesion_bounds_cover_objective() -> None:
    edges = pd.DataFrame(
        [
            {"source": "A", "target": "B", "raw_weight": 3.0},
            {"source": "B", "target": "C", "raw_weight": 7.0},
            {"source": "A", "target": "C", "raw_weight": 5.0},
        ]
    )
    stage2_robustness._validate_nonnegative_raw_weights(edges)
    max_weight = stage2_robustness._max_raw_edge_weight(edges)
    assert max_weight == 7.0

    coupling, cohesion, imbalance = evaluate_structural_objectives(
        edges,
        {"A": 0, "B": 0, "C": 0},
        "raw_weight",
    )

    assert 0.0 <= coupling <= 1.0
    assert 0.0 <= cohesion <= max_weight
    assert imbalance == 0.0


def _brute_force_compositions(total: int, parts: int):
    if parts == 1:
        yield (total,)
        return
    for value in range(1, total - parts + 2):
        for rest in _brute_force_compositions(total - value, parts - 1):
            yield (value, *rest)


def _brute_force_imbalance_bound(n: int) -> float:
    max_cluster_size = int(np.floor(n * 0.4))
    max_singletons = int(np.floor(n * 0.15))
    best = 0.0
    for k in range(2, n + 1):
        for sizes in _brute_force_compositions(n, k):
            if max(sizes) > max_cluster_size:
                continue
            if sum(size == 1 for size in sizes) > max_singletons:
                continue
            values = np.asarray(sizes, dtype=float)
            best = max(best, float(np.std(values) / np.mean(values)))
    return best


@pytest.mark.parametrize("class_count", [6, 7, 8, 9, 10, 11, 12])
def test_theoretical_imbalance_bound_matches_bruteforce(class_count: int) -> None:
    analytical = stage2_robustness.theoretical_imbalance_upper_bound(class_count)
    brute_force = _brute_force_imbalance_bound(class_count)

    assert analytical + 1e-12 >= brute_force
    assert np.isclose(analytical, brute_force, rtol=1e-12, atol=1e-12)


def test_theoretical_bounds_yaml_schema(tmp_path: Path) -> None:
    config_path = ROOT / "configs" / "experiments" / "02_stage2_nsga_structure_only.yml"
    bounds_path = tmp_path / "bounds.yml"

    stage2_robustness.generate_theoretical_bounds("jpetstore", bounds_path, config_path)

    data = yaml.safe_load(bounds_path.read_text())
    bounds = data["subjects"]["jpetstore"]
    assert bounds["bounds_source"] == "theoretical"
    assert bounds["calibration_status"] == "not_required"
    assert bounds["objective_order"] == stage2_robustness.OBJECTIVE_ORDER
    assert bounds["reference_point"] == [1.1, 1.1, 1.1]
    assert bounds["lower_bounds"][0] == 0.0
    assert bounds["upper_bounds"][0] == 1.0
    assert bounds["lower_bounds"][1] == -bounds["max_raw_edge_weight"]
    assert bounds["upper_bounds"][1] == 0.0
    assert bounds["lower_bounds"][2] == 0.0
    assert bounds["upper_bounds"][2] == bounds["imbalance_upper_bound"]
    assert bounds["imbalance_upper_bound"] > 0.0
    assert bounds["graph_input_sha256"]
    assert bounds["working_tree_fingerprint"]


def test_smoke_bounds_require_explicit_allowance(tmp_path: Path) -> None:
    config_path = ROOT / "configs" / "experiments" / "02_stage2_nsga_structure_only.yml"
    git_head = stage2_robustness.stage2._git_state(ROOT)["git_head"]
    bounds_path = tmp_path / "bounds.yml"
    bounds_doc = {
        "schema_version": 2,
        "objective_order": stage2_robustness.OBJECTIVE_ORDER,
        "reference_point": [1.1, 1.1, 1.1],
        "subjects": {
            "daytrader": {
                "calibration_status": "smoke",
                "generated_from_commit": git_head,
                "algorithm_config_sha256": stage2_robustness._file_sha256(config_path),
                "calibration_seed_count": 2,
                "calibration_seeds": [1000, 1001],
                "objective_order": stage2_robustness.OBJECTIVE_ORDER,
                "reference_point": [1.1, 1.1, 1.1],
                "lower_bounds": [0.0, -10.0, 0.0],
                "upper_bounds": [1.0, 0.0, 2.0],
            }
        },
    }
    bounds_path.write_text(yaml.safe_dump(bounds_doc), encoding="utf-8")

    with pytest.raises(ValueError, match="theoretical bounds"):
        stage2_robustness._load_subject_bounds(
            bounds_path,
            "daytrader",
            config_path=config_path,
            run_type="formal",
            allow_smoke_bounds=False,
        )

    bounds = stage2_robustness._load_subject_bounds(
        bounds_path,
        "daytrader",
        config_path=config_path,
        run_type="smoke",
        allow_smoke_bounds=True,
    )
    assert bounds["calibration_status"] == "smoke"


def test_formal_run_rejects_empirical_bounds(tmp_path: Path) -> None:
    config_path = ROOT / "configs" / "experiments" / "02_stage2_nsga_structure_only.yml"
    git_head = stage2_robustness.stage2._git_state(ROOT)["git_head"]
    bounds_path = tmp_path / "bounds.yml"
    bounds_doc = {
        "schema_version": 2,
        "objective_order": stage2_robustness.OBJECTIVE_ORDER,
        "reference_point": [1.1, 1.1, 1.1],
        "subjects": {
            "daytrader": {
                "bounds_source": "empirical",
                "calibration_status": "formal",
                "generated_from_commit": git_head,
                "algorithm_config_sha256": stage2_robustness._file_sha256(config_path),
                "objective_order": stage2_robustness.OBJECTIVE_ORDER,
                "reference_point": [1.1, 1.1, 1.1],
                "lower_bounds": [0.0, -10.0, 0.0],
                "upper_bounds": [1.0, 0.0, 2.0],
            }
        },
    }
    bounds_path.write_text(yaml.safe_dump(bounds_doc), encoding="utf-8")

    with pytest.raises(ValueError, match="theoretical bounds"):
        stage2_robustness._load_subject_bounds(
            bounds_path,
            "daytrader",
            config_path=config_path,
            run_type="formal",
            allow_smoke_bounds=False,
        )


def test_resume_rejects_old_empirical_bound_metadata(tmp_path: Path) -> None:
    manifest = {
        "subject": "daytrader",
        "run_type": "formal",
        "calibration_status": "not_required",
        "bounds_source": "theoretical",
        "bounds_derivation": {},
        "git_commit": "abc",
        "working_tree_dirty": True,
        "source_fingerprint": {"a.py": "123"},
        "working_tree_diff_sha256": "diff",
        "algorithm_config_sha256": "config",
        "bounds_config_sha256": "bounds",
        "class_count": 10,
        "max_raw_edge_weight": 1.0,
        "imbalance_upper_bound": 2.0,
        "imbalance_bound_method": "exact",
        "normalization_bounds": {"lower_bounds": [0.0, -1.0, 0.0], "upper_bounds": [1.0, 0.0, 2.0]},
        "reference_point": [1.1, 1.1, 1.1],
        "objective_order": stage2_robustness.OBJECTIVE_ORDER,
    }
    seed_dir = tmp_path / "seed_00"
    seed_dir.mkdir()
    for name in [
        "pareto_front.csv",
        "pareto_labels.csv.xz",
        "selected_solution.csv",
        "selected_partition.csv",
    ]:
        (seed_dir / name).write_text("", encoding="utf-8")
    (seed_dir / "run_metrics.json").write_text(
        json.dumps({"front_source": "recomputed_nondominated_front"}),
        encoding="utf-8",
    )
    old_metadata = stage2_robustness._seed_metadata(
        0,
        {**manifest, "calibration_status": "formal", "bounds_source": "empirical"},
        "recomputed_nondominated_front",
    )
    (seed_dir / "run_metadata.json").write_text(json.dumps(old_metadata), encoding="utf-8")

    assert not stage2_robustness._seed_output_is_valid(seed_dir, 0, manifest)


def test_subprocess_snapshot_comparison_logic() -> None:
    left = {
        "front_objective_vectors": np.asarray([[0.1, -1.0, 0.2]]),
        "front_partitions": [(0, 0, 1)],
        "normalized_objective_vectors": np.asarray([[0.1, 0.5, 0.2]]),
        "hypervolume": 0.5,
        "selected_solution": {"coupling": 0.1, "negative_cohesion": -1.0, "imbalance": 0.2},
        "selected_partition": (0, 0, 1),
        "leiden_diagnostics": {"selected_equals_leiden": False},
        "front_validation_diagnostics": {"front_validation_passed": True},
    }
    right = json.loads(json.dumps(left, default=lambda value: value.tolist()))
    right["front_objective_vectors"] = np.asarray(right["front_objective_vectors"])
    right["normalized_objective_vectors"] = np.asarray(right["normalized_objective_vectors"])
    right["front_partitions"] = [tuple(value) for value in right["front_partitions"]]
    right["selected_partition"] = tuple(right["selected_partition"])

    assert stage2_robustness.compare_run_snapshots(left, right) == []

    right["hypervolume"] = 0.6
    assert stage2_robustness.compare_run_snapshots(left, right) == ["hypervolume"]
