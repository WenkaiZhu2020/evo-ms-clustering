"""Tests for the self-contained final Stage 3 provenance boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evo_ms.semantic.embeddings import load_saved_embeddings, vector_hash
from evo_ms.semantic.graph import build_graph_from_embeddings, true_cosine_similarity
from evo_ms.semantic.input_contract import REPRESENTATION_ID, aggregate_input_hash, validate_identity


SUBJECTS = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
INPUT_HASHES = {
    "jpetstore": "2d9007f75a14f4a4ed6152563241b898837b6c12b66a98a2464b4cc3f969a921",
    "daytrader": "da53d434b820e3c25bc69df63ced807cd0113d412fa36acc9694d1a97631d655",
    "xerces": "65488944220cc3a503994d6f2289e0f7bdc06c619351a2e8243bca243538c8a3",
}
EMBEDDING_HASHES = {
    "jpetstore": "e7615e77d4f3258df46e499fd94c2dbb59bee03c0d2f6c3bb822c3aff4577139",
    "daytrader": "db7ef8d78036796c5c5c79cc95f54eb1b9b9974de5e6f035d1929391b415f66c",
    "xerces": "36bdeca0e1ef32f36631c30ebbf86a1875621490e92f9b4a7fd0860755676236",
}
GRAPH_HASHES = {
    "jpetstore": "2dcf34b9e931cfdb0eec205f7da5bd0f24f6956be98d838369e12573026a9214",
    "daytrader": "c7761509fe91acb398ee5bc3a0c71e3a368a34aae316b04c5907d34bced1714d",
    "xerces": "7d5d45f6e7cc46cdb57c57688bc89b5e90e0ecea7390833a7acb2e8887d935a5",
}


def _rows(subject: str) -> list[dict[str, str]]:
    path = ROOT / "data/semantic_text/declaration_method_body" / subject / "class_semantic_inputs.csv"
    import csv

    with path.open(encoding="utf-8", newline="") as handle:
        return sorted(csv.DictReader(handle), key=lambda row: row["class_id"])


def test_final_config_and_manifest_have_one_runtime_identity() -> None:
    config = yaml.safe_load((ROOT / "configs/experiments/05_stage3_declaration_method_body.yml").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "results/cross_subject/05_stage3_declaration_method_body/provenance/formal_experiment_manifest.json").read_text(encoding="utf-8"))
    assert config["experiment_name"] == "stage3_declaration_method_body"
    assert config["representation_id"] == REPRESENTATION_ID
    assert "base_experiment_config" not in config
    assert manifest["experiment_name"] == "stage3_declaration_method_body"
    assert manifest["representation_id"] == REPRESENTATION_ID
    assert manifest["semantic_graphs_regenerated"] is False
    assert manifest["task"] == "Stage 3B formal robustness experiment"


def test_final_reporting_manifest_uses_active_six_row_contract() -> None:
    manifest = json.loads(
        (
            ROOT
            / "results/cross_subject/05_stage3_declaration_method_body/provenance/formal_experiment_manifest.json"
        ).read_text(encoding="utf-8")
    )
    contract = manifest["reporting_correction"]
    assert contract["primary_family_row_count"] == 6
    assert contract["primary_metrics"] == [
        "projected_hypervolume",
        "selected_f_semantic",
    ]
    assert contract["correction"] == "Holm across exactly six confirmatory rows"
    assert contract["family_wise_alpha"] == 0.05
    assert contract["stage2_profile_source"].endswith(
        "modularity_band/canonical_operating_solution_per_seed.csv"
    )
    assert contract["experiment_rerun"] is False


def test_saved_formal_runs_validate_against_their_generation_config_snapshot() -> None:
    run = ROOT / "results/jpetstore/05_stage3_declaration_method_body/formal/seed_01"
    metadata = json.loads((run / "run_metadata.json").read_text(encoding="utf-8"))
    snapshot_hash = hashlib.sha256((run / "config_snapshot.yml").read_bytes()).hexdigest()
    current_hash = hashlib.sha256(
        (ROOT / "configs/experiments/05_stage3_declaration_method_body.yml").read_bytes()
    ).hexdigest()
    assert metadata["config_hash"] == metadata["config_sha256"] == snapshot_hash
    assert snapshot_hash != current_hash


def test_final_inputs_have_frozen_scope_and_aggregate_hashes() -> None:
    for subject, count in SUBJECTS.items():
        rows = _rows(subject)
        assert len(rows) == count
        assert len({row["class_id"] for row in rows}) == count
        assert aggregate_input_hash(rows) == INPUT_HASHES[subject]
        assert all(row["representation_id"] == REPRESENTATION_ID for row in rows)


@pytest.mark.parametrize("subject,count", SUBJECTS.items())
def test_saved_embeddings_are_final_and_hash_stable(subject: str, count: int) -> None:
    directory = ROOT / "data/embeddings/declaration_method_body" / subject
    vectors = load_saved_embeddings(directory / "embeddings.npy", rows=count, dimension=3584)
    rows = _rows(subject)
    with (directory / "embedding_hashes.csv").open(encoding="utf-8", newline="") as handle:
        import csv
        embedding_rows = list(csv.DictReader(handle))
    assert [row["embedding_sha256"] for row in embedding_rows] == [vector_hash(vector) for vector in vectors]
    aggregate = hashlib.sha256("".join(f"{r['class_id']}\t{r['embedding_sha256']}\n" for r in embedding_rows).encode()).hexdigest()
    assert aggregate == EMBEDDING_HASHES[subject]
    assert len(rows) == len(embedding_rows)


def test_shared_graph_helper_rejects_zero_norm_and_bounds_cosine() -> None:
    vectors = np.asarray([[3.0, 4.0], [6.0, 8.0]], dtype=np.float32)
    matrix = true_cosine_similarity(vectors)
    assert matrix[0, 1] == pytest.approx(1.0)
    assert np.all(matrix <= 1.0) and np.all(matrix >= -1.0)
    with pytest.raises(ValueError, match="zero-norm"):
        true_cosine_similarity(np.asarray([[0.0, 0.0], [1.0, 0.0]], dtype=np.float32))


def test_graph_helper_is_deterministic_and_excludes_self() -> None:
    ids = ["z", "b", "a", "c"]
    directed, edges = build_graph_from_embeddings(ids, np.ones((4, 3), dtype=np.float32), k=3)
    assert len(directed) == 12
    assert all(row["source_class_id"] != row["target_class_id"] for row in directed)
    assert [row["target_class_id"] for row in directed if row["source_class_id"] == "z"] == ["a", "b", "c"]
    assert len(edges) == len({(row["class_id_a"], row["class_id_b"]) for row in edges})


def test_final_runtime_sources_have_no_legacy_stage3a_reads() -> None:
    paths = [
        ROOT / "experiments/05_stage3_declaration_method_body/run.py",
        ROOT / "experiments/05_stage3_declaration_method_body/prepare_semantic.py",
        ROOT / "experiments/05_stage3_declaration_method_body/run_robustness.py",
        ROOT / "experiments/05_stage3_declaration_method_body/analyze.py",
    ]
    forbidden = ("experiments/04_stage3_semantic", "data/semantic_inputs", "reports/stage3/formal_run_manifest")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), path


def test_provenance_validator_rejects_other_representation() -> None:
    with pytest.raises(ValueError, match="final Stage 3 representation"):
        validate_identity({"representation_id": "stage3a_class_declaration"})


def test_canonical_report_subtrees_are_final_only() -> None:
    report_root = ROOT / "results/cross_subject/05_stage3_declaration_method_body"
    for subtree in ("stage2_vs_stage3", "quality", "validation"):
        for path in (report_root / subtree).rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace").lower()
                assert "stage3a" not in text, path
                assert "stage3b" not in text, path
