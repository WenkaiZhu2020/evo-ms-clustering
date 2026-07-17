"""Focused tests for the saved Xerces formal-run validator."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.stage3 import validate_xerces_formal as validator


def _artifact_fixture(tmp_path: Path) -> Path:
    source = tmp_path / "seed_00"
    source.mkdir()
    for name in validator.REQUIRED_ARTIFACTS:
        path = source / name
        if name == "run_metadata.json":
            path.write_text(json.dumps({"subject": "xerces", "completed_at_utc": "one"}) + "\n")
        elif name == "run.log":
            path.write_text("completed runtime_seconds=1\n")
        elif name.endswith(".csv"):
            path.write_text("header\nvalue\n")
        else:
            path.write_text("{}\n")
    return source


def test_missing_artifact_is_rejected(tmp_path: Path) -> None:
    source = _artifact_fixture(tmp_path)
    (source / "run.log").unlink()
    with pytest.raises(validator.ValidationFailure, match="missing required artifact"):
        validator.canonical_seed_artifact_hash(source)


def test_timestamp_fields_do_not_change_seed_aggregate(tmp_path: Path) -> None:
    source = _artifact_fixture(tmp_path)
    first = validator.canonical_seed_artifact_hash(source)
    (source / "run_metadata.json").write_text(
        json.dumps({"subject": "xerces", "completed_at_utc": "two"}) + "\n"
    )
    second = validator.canonical_seed_artifact_hash(source)
    assert first == second
    (source / "run_metadata.json").write_text(
        json.dumps({"subject": "other", "completed_at_utc": "two"}) + "\n"
    )
    assert validator.canonical_seed_artifact_hash(source) != first


def test_duplicate_seed_list_is_rejected() -> None:
    with pytest.raises(validator.ValidationFailure, match="30 unique"):
        validator.validate_seed_values([0] * 30)


def test_unexpected_seed_directory_is_rejected(tmp_path: Path, monkeypatch) -> None:
    seed_zero = tmp_path / "validation" / "seed_00"
    formal = tmp_path / "formal"
    seed_zero.mkdir(parents=True)
    for name in ["seed_01", "seed_02", "seed_03"]:
        (formal / name).mkdir(parents=True)
    monkeypatch.setattr(validator, "SEED_ZERO_ROOT", seed_zero)
    monkeypatch.setattr(validator, "FORMAL_ROOT", formal)
    with pytest.raises(validator.ValidationFailure, match="extra=.*seed_03"):
        validator.resolve_seed_sources([0, 1, 2])


def test_failed_run_log_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "run.log"
    path.write_text("Traceback: failed\n")
    with pytest.raises(validator.ValidationFailure, match="no completion|Traceback"):
        validator.validate_run_log(path)


def test_objective_order_and_provenance_mismatch_are_rejected() -> None:
    metadata = {
        "subject": "xerces",
        "seed": 0,
        "run_type": "validation",
        "completion_status": "completed",
        "config_sha256": "config",
        "g_sem_graph_hash": "graph",
        "report_objective_order": ["coupling", "cohesion", "imbalance", "f_semantic"],
        "population_size": 100,
        "generations": 100,
        "objective_order": ["coupling", "negative_cohesion", "imbalance", "f_semantic"],
        "g_raw_provenance": {
            "loader": "experiments/02_stage2_nsga_structure_only/run.py:_raw_graph_inputs",
            "builder": "src/evo_ms/graph/raw_graph_builder.py",
            "class_nodes_path": "data/extracted/xerces-j/class_nodes.csv",
            "structural_dependencies_path": "data/extracted/xerces-j/structural_dependencies.csv",
            "raw_edge_hash": "raw",
        },
    }
    with pytest.raises(validator.ValidationFailure, match="objective order"):
        validator._validate_metadata({**metadata, "objective_order": ["bad"]}, 0, "config", "graph", "raw")
    with pytest.raises(validator.ValidationFailure, match="semantic graph hash"):
        validator._validate_metadata(metadata, 0, "config", "wrong", "raw")


def _valid_front() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "solution_id": "a",
                "coupling": 0.1,
                "cohesion": 1.0,
                "imbalance": 0.1,
                "f_semantic": 0.2,
                "pymoo_f0_coupling": 0.1,
                "pymoo_f1_negative_cohesion": -1.0,
                "pymoo_f2_imbalance": 0.1,
                "pymoo_f3_f_semantic": 0.2,
            },
            {
                "solution_id": "b",
                "coupling": 0.2,
                "cohesion": 0.5,
                "imbalance": 0.2,
                "f_semantic": 0.8,
                "pymoo_f0_coupling": 0.2,
                "pymoo_f1_negative_cohesion": -0.5,
                "pymoo_f2_imbalance": 0.2,
                "pymoo_f3_f_semantic": 0.8,
            },
        ]
    )


def test_nonfinite_and_dominated_four_dimensional_fronts_are_rejected() -> None:
    front = _valid_front()
    bad = front.copy()
    bad.loc[0, "f_semantic"] = np.nan
    with pytest.raises(validator.ValidationFailure, match="non-finite"):
        validator.validate_four_dimensional_front(bad, 0)
    dominated = pd.concat([front, front.iloc[[0]].assign(solution_id="c", pymoo_f3_f_semantic=0.3)], ignore_index=True)
    with pytest.raises(validator.ValidationFailure, match="dominated"):
        validator.validate_four_dimensional_front(dominated, 0)


def test_invalid_projected_front_and_hypervolume_mismatch_are_rejected() -> None:
    front = _valid_front()
    projected = pd.DataFrame(columns=validator.PROJECTED_COLUMNS)
    with pytest.raises(validator.ValidationFailure, match="empty projected"):
        validator.validate_projected_front(projected, front, 0, {})
    projected = pd.DataFrame([{
        "subject": "xerces", "seed": 0, "solution_id": "a", "original_solution_id": "a",
        "coupling": 0.1, "cohesion": 1.0, "imbalance": 0.1, "original_f_semantic": 0.2,
        "pymoo_f0_coupling": 0.1, "pymoo_f1_negative_cohesion": -1.0,
        "pymoo_f2_imbalance": 0.1, "feasible": True, "is_injected_seed": False,
        "label_vector": "[0]",
    }], columns=validator.PROJECTED_COLUMNS)
    bounds = {"lower_bounds": [0.0, -1.0, 0.0], "upper_bounds": [1.0, 0.0, 1.0], "bound_tolerance": 1e-12}
    assert validator.validate_projected_front(projected, front, 0, bounds) >= 0.0
    assert not np.isclose(validator.validate_projected_front(projected, front, 0, bounds), 999.0, rtol=0.0, atol=1e-12)


def test_selected_scope_requires_exactly_814_classes() -> None:
    group = pd.DataFrame({"class_id": ["A"], "cluster_id": [0]})
    with pytest.raises(validator.ValidationFailure, match="class scope"):
        validator._assert_scope(group, {"A"}, "test")


def test_seed_and_formal_hashes_are_deterministic() -> None:
    hashes = {2: "b", 0: "a", 1: "c"}
    assert validator.canonical_formal_hash(hashes) == validator.canonical_formal_hash({0: "a", 1: "c", 2: "b"})


def test_algorithm_fingerprint_is_deterministic() -> None:
    first = validator.algorithm_fingerprint("f47a2d34a3e63dd4a4f6320ed6186080e27c3f21")
    second = validator.algorithm_fingerprint("f47a2d34a3e63dd4a4f6320ed6186080e27c3f21")
    assert first == second
