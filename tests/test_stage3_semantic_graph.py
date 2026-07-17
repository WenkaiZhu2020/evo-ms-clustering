import hashlib
from pathlib import Path

import numpy as np
import pytest

from scripts.stage3 import build_semantic_graphs as builder


def test_true_cosine_helper_is_used_by_graph_builder(monkeypatch):
    called = False

    def fake(vectors):
        nonlocal called
        called = True
        return np.eye(len(vectors), dtype=float)

    monkeypatch.setattr(builder, "true_cosine_similarity", fake)
    directed, edges = builder.build_graph_from_embeddings(["a", "b", "c", "d"], np.ones((4, 2)), 3)
    assert called
    assert len(directed) == 12
    assert all(row["class_id_a"] < row["class_id_b"] for row in edges)


def test_tie_break_excludes_self_and_selects_exactly_three():
    class_ids = ["pkg.z", "pkg.b", "pkg.a", "pkg.c", "pkg.d"]
    vectors = np.ones((5, 4), dtype=np.float32)
    directed, _ = builder.build_graph_from_embeddings(class_ids, vectors, 3)
    for source in class_ids:
        rows = [row for row in directed if row["source_class_id"] == source]
        assert [row["rank"] for row in rows] == [1, 2, 3]
        assert source not in [row["target_class_id"] for row in rows]
        assert [row["target_class_id"] for row in rows] == sorted(
            target for target in class_ids if target != source
        )[:3]


def test_or_symmetrisation_selected_by_and_no_duplicates():
    rows = [
        {"source_class_id": "a", "rank": 1, "target_class_id": "b", "weight": 0.5},
        {"source_class_id": "c", "rank": 1, "target_class_id": "b", "weight": 0.4},
        {"source_class_id": "b", "rank": 1, "target_class_id": "a", "weight": 0.5},
    ]
    edges = builder.symmetrise_or(["a", "b", "c"], rows)
    assert edges == [
        {"class_id_a": "a", "class_id_b": "b", "weight": 0.5, "selected_by": "both"},
        {"class_id_a": "b", "class_id_b": "c", "weight": 0.4, "selected_by": "b"},
    ]


def test_negative_similarity_is_not_thresholded_and_zero_norm_rejected():
    with pytest.raises(ValueError, match="zero-norm"):
        builder.build_graph_from_embeddings(["a", "b", "c", "d"], np.vstack([np.zeros(2), np.eye(2), [1, 1]]), 3)
    class_ids = ["a", "b", "c", "d"]
    vectors = np.asarray([[1, 0], [-1, 0], [0, 1], [0, -1]], dtype=np.float32)
    directed, _ = builder.build_graph_from_embeddings(class_ids, vectors, 3)
    assert any(float(row["weight"]) < 0 for row in directed)


def test_canonical_weight_and_hash_payload_are_deterministic():
    assert builder.canonical_weight(-0.0) == "0"
    assert builder.canonical_weight(1.0) == "1"
    rows = [{"source_class_id": "a", "rank": 1, "target_class_id": "b", "weight": 0.5}]
    assert builder.canonical_directed_payload(rows) == b"a\t1\tb\t0.5\n"
    assert hashlib.sha256(builder.canonical_directed_payload(rows)).hexdigest() == hashlib.sha256(b"a\t1\tb\t0.5\n").hexdigest()


def test_saved_embedding_file_hashes_are_unchanged():
    expected = {
        "jpetstore": "1ae21e10d3978a658dfdf57423c7cdb157cc46767145c14e605d0bba7c9014d8",
        "daytrader": "8aa45b898a870c7a226cdb9f2d6296a5919dca148126869140917e8874f14d29",
        "xerces": "72a4049f856edcdf4415df39c98d5ebad0c9e0593e39f7f40596aa2c37f4a23f",
    }
    root = Path(__file__).resolve().parents[1]
    for subject, value in expected.items():
        path = root / "results" / subject / "04_stage3_semantic/embeddings/embeddings.npy"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == value


def test_graph_builder_has_no_diagnostic_or_random_fill_input_path():
    source = Path(builder.__file__).read_text(encoding="utf-8")
    assert "nearest_neighbors" not in source
    assert "random_fill" not in source
