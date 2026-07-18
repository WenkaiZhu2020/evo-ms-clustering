"""Focused checks for the isolated Stage 3B seed-0 optimizer boundary."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/stage3_method_body/run_seed00_optimizer.py"
SPEC = importlib.util.spec_from_file_location("stage3b_seed00_optimizer_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_seed_zero_is_the_only_allowed_validation_seed() -> None:
    MODULE.validate_seed(0)
    with pytest.raises(ValueError, match="restricted to validation seed 0"):
        MODULE.validate_seed(1)


def test_stage3b_output_path_isolated_from_stage3a_and_formal_namespaces() -> None:
    expected = MODULE.output_dir("jpetstore")
    assert str(expected).endswith("results/jpetstore/05_stage3_declaration_method_body/validation/seed_00")
    with pytest.raises(Exception):
        MODULE.output_dir("jpetstore", ROOT / "results/jpetstore/04_stage3_semantic")
    with pytest.raises(ValueError, match="Stage 3B output crosses obsolete namespace"):
        MODULE.output_dir("jpetstore", Path("/tmp/results/jpetstore/04_stage3_semantic"))


def test_stage3b_config_identity_and_frozen_base_contract() -> None:
    config = MODULE._load_stage3b_config()
    assert config["experiment_name"] == "stage3_declaration_method_body"
    assert config["representation_id"] == "declaration_method_body_v1"
    assert "base_experiment_config" not in config
    assert config["input"]["semantic_text_root"] == "data/semantic_text/declaration_method_body"


@pytest.mark.parametrize("subject", MODULE.SUBJECTS)
def test_stage3b_context_has_frozen_graph_and_embedding_provenance(subject: str) -> None:
    context = MODULE.load_context(subject)
    assert len(context["class_nodes"]) == MODULE.EXPECTED_COUNTS[subject]
    assert context["semantic_graph_hash"] == MODULE.EXPECTED_GRAPH_HASHES[subject]
    assert context["semantic_graph_metadata"]["representation_id"] == MODULE.REPRESENTATION_ID
    assert context["graph_provenance"]["embedding_source"]["embedding_aggregate_sha256"] == MODULE.EXPECTED_EMBEDDING_HASHES[subject]


@pytest.mark.parametrize("subject", MODULE.SUBJECTS)
def test_structural_objective_seam_is_bitwise_invariant(subject: str) -> None:
    context = MODULE.load_context(subject)
    result = MODULE.structural_invariance_checks(context)
    assert result["pass"] is True
    assert all(row["pass"] for row in result["checks"].values())


def test_stage3b_four_objective_evaluation_is_finite_and_semantic_is_bounded() -> None:
    context = MODULE.load_context("jpetstore")
    labels = MODULE.encoding.canonical_relabel(np.arange(len(context["class_nodes"])) % 2)
    mapping = MODULE.encoding.to_cluster_by_class(labels, context["class_nodes"])
    values = MODULE.runtime.evaluate_four_objective_values(
        context["raw_edges"],
        context["semantic_edges"],
        mapping,
        "raw_weight",
        context["semantic_graph_metadata"]["total_edge_weight"],
    )
    assert np.isfinite(np.asarray(values, dtype=float)).all()
    assert 0.0 <= values[3] <= 1.0


@pytest.mark.parametrize("subject", MODULE.SUBJECTS)
def test_saved_seed_zero_front_hypervolume_and_selector_are_valid(subject: str) -> None:
    from scripts.stage3_method_body import validate_seed00_optimizer as validator

    context = MODULE.load_context(subject)
    _, front, projected, labels, selected = validator.load_output(subject)
    assert validator.front_validation(context, subject, front, projected, labels, selected)["pass"] is True
    assert validator.hv_validation(subject, context, projected)["pass"] is True
    assert validator.selector_validation(subject, context, projected, selected)["pass"] is True
