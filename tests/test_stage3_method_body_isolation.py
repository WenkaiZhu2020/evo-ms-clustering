from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from scripts.stage3_method_body.isolation import (
    EXPERIMENT_ID,
    REPRESENTATION_ID,
    STAGE3B_CONFIG,
    Stage3BIsolationError,
    assert_declaration_source,
    assert_representation,
    assert_stage3b_write_path,
    declaration_source_path,
    stage3b_paths,
    validate_cache_metadata,
)


ROOT = Path(__file__).resolve().parents[1]


def test_stage3b_config_has_distinct_identity_and_roots() -> None:
    config = yaml.safe_load(STAGE3B_CONFIG.read_text(encoding="utf-8"))
    assert config["experiment_name"] == EXPERIMENT_ID
    assert config["representation_id"] == REPRESENTATION_ID
    assert config["outputs"]["report_root"] == "reports/stage3_method_body"
    assert config["outputs"]["embedding_root"] == "data/embeddings/declaration_method_body"
    assert config["outputs"]["semantic_graph_root"] == "data/semantic_graphs/declaration_method_body"
    assert all(
        "05_stage3_declaration_method_body" in value
        for value in config["outputs"]["result_roots"].values()
    )


def test_stage3a_and_stage3b_paths_are_distinct() -> None:
    paths = stage3b_paths("jpetstore")
    assert all("04_stage3_semantic" not in str(path) for path in paths.values())
    assert all("/reports/stage3/" not in str(path) for path in paths.values())
    assert "05_stage3_declaration_method_body" in str(paths["results"])
    assert_stage3b_write_path(paths["embeddings"], kind="embedding")
    assert_stage3b_write_path(paths["semantic_graph"], kind="graph")


def test_stage3b_write_rejects_stage3a_result_and_report_paths() -> None:
    with pytest.raises(Stage3BIsolationError, match="Stage 3A"):
        assert_stage3b_write_path(ROOT / "results/jpetstore/04_stage3_semantic/embeddings")
    with pytest.raises(Stage3BIsolationError, match="Stage 3A"):
        assert_stage3b_write_path(ROOT / "reports/stage3/new-report.md")


@pytest.mark.parametrize("artifact_kind", ["embedding", "graph", "seed"])
def test_stage3a_metadata_is_rejected_for_stage3b(artifact_kind: str) -> None:
    metadata = {
        "experiment_id": "04_stage3_semantic",
        "representation_id": "declaration_v1",
        "artifact_kind": artifact_kind,
    }
    with pytest.raises(Stage3BIsolationError, match="representation_id"):
        assert_representation(metadata)


def test_stage3b_cache_requires_identity_and_input_hash() -> None:
    metadata = {
        "experiment_id": EXPERIMENT_ID,
        "representation_id": REPRESENTATION_ID,
        "subject": "jpetstore",
        "input_hash": "body-input-hash",
        "model_identity": "nomic-pinned",
        "class_mapping_hash": "classes-hash",
    }
    validate_cache_metadata(
        metadata,
        subject="jpetstore",
        input_hash="body-input-hash",
        model_identity="nomic-pinned",
        class_mapping_hash="classes-hash",
    )
    with pytest.raises(Stage3BIsolationError, match="input hash"):
        validate_cache_metadata(metadata, subject="jpetstore", input_hash="stage3a-hash")
    with pytest.raises(Stage3BIsolationError, match="model identity"):
        validate_cache_metadata(
            metadata,
            subject="jpetstore",
            input_hash="body-input-hash",
            model_identity="different-model",
        )


def test_only_explicit_stage3a_declaration_source_is_allowed() -> None:
    expected = declaration_source_path("jpetstore")
    assert assert_declaration_source(expected, "jpetstore") == expected
    with pytest.raises(Stage3BIsolationError, match="explicit frozen declaration"):
        assert_declaration_source(
            ROOT / "results/jpetstore/04_stage3_semantic/embeddings/embeddings.npy",
            "jpetstore",
        )


def test_frozen_stage3a_config_was_not_changed() -> None:
    path = ROOT / "configs/experiments/04_stage3_semantic.yml"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == "eddbb3674dacabfac2925f4ef6887bb86c9030f629a231230d6a889e1c28cc27"
