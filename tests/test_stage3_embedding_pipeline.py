import csv
import hashlib
from pathlib import Path

import numpy as np
import pytest
import yaml

from scripts.stage3.generate_embeddings import (
    INPUT_PATHS,
    SUBJECTS,
    encode_texts,
    nearest_neighbors,
    read_subject,
    vector_hash,
    validate_vectors,
)
from scripts.stage3.similarity import true_cosine_similarity


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_INPUT_HASHES = {
    "jpetstore": "1ecdb9083a37668fd07388454095a317268c8b736e6fd45957ab16bf87f6ad23",
    "daytrader": "ab09380f87119e4fe4621efbbdd8fdfd8cfc92cd383ed812169e2427a35eae44",
    "xerces": "f81d0f9bda5aa0fcdf3a35c75876cc73c8b419eccfb8c9e00634ec13fad4d60a",
}
EXPECTED_EMBEDDINGS_NPY_HASHES = {
    "jpetstore": "1ae21e10d3978a658dfdf57423c7cdb157cc46767145c14e605d0bba7c9014d8",
    "daytrader": "8aa45b898a870c7a226cdb9f2d6296a5919dca148126869140917e8874f14d29",
    "xerces": "72a4049f856edcdf4415df39c98d5ebad0c9e0593e39f7f40596aa2c37f4a23f",
}


def test_input_rows_are_lexicographically_ordered_and_unchanged() -> None:
    for subject in SUBJECTS:
        rows = read_subject(subject)
        assert [row["class_id"] for row in rows] == sorted(row["class_id"] for row in rows)
        assert all(hashlib.sha256(row["semantic_text"].encode()).hexdigest() == row["input_hash"] for row in rows)


def test_semantic_text_is_passed_unchanged_and_formal_encode_arguments_are_safe() -> None:
    rows = read_subject("jpetstore")[:2]
    expected_texts = [row["semantic_text"] for row in rows]

    class FakeModel:
        def __init__(self) -> None:
            self.inputs = None
            self.kwargs = None

        def encode(self, inputs, **kwargs):
            self.inputs = inputs
            self.kwargs = kwargs
            return np.ones((len(inputs), 3584), dtype=np.float16)

    model = FakeModel()
    result = encode_texts(model, expected_texts, 2)
    assert model.inputs == expected_texts
    assert model.kwargs["prompt_name"] is None
    assert model.kwargs["prompt"] is None
    assert model.kwargs["normalize_embeddings"] is False
    assert model.kwargs["convert_to_tensor"] is False
    assert result.dtype == np.dtype("<f4")
    assert result.shape == (2, 3584)


def test_saved_embeddings_have_expected_shape_dtype_and_row_alignment() -> None:
    for subject, (expected_count, _) in SUBJECTS.items():
        output = ROOT / "results" / subject / "04_stage3_semantic" / "embeddings"
        vectors = np.load(output / "embeddings.npy")
        assert vectors.shape == (expected_count, 3584)
        assert vectors.dtype == np.dtype("<f4")
        with (output / "class_ids.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert [int(row["row_index"]) for row in rows] == list(range(expected_count))
        assert [row["class_id"] for row in rows] == sorted(row["class_id"] for row in rows)


def test_vector_validation_properties_are_present_in_saved_outputs() -> None:
    for subject in SUBJECTS:
        vectors = np.load(ROOT / "results" / subject / "04_stage3_semantic" / "embeddings" / "embeddings.npy")
        assert not np.isnan(vectors).any()
        assert not np.isinf(vectors).any()
        assert not np.any(np.all(vectors == 0, axis=1))
        norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
        assert np.all((norms >= 0.999) & (norms <= 1.001))


def test_vector_validation_rejects_nan_inf_and_bad_norms() -> None:
    with pytest.raises(ValueError, match="nan=3584"):
        validate_vectors(np.full((1, 3584), np.nan, dtype="<f4"))
    with pytest.raises(ValueError, match="inf=3584"):
        validate_vectors(np.full((1, 3584), np.inf, dtype="<f4"))
    with pytest.raises(ValueError, match="norm outside"):
        validate_vectors(np.ones((1, 3584), dtype="<f4"))


def test_per_class_and_aggregate_embedding_hashes_are_stable() -> None:
    for subject in SUBJECTS:
        output = ROOT / "results" / subject / "04_stage3_semantic" / "embeddings"
        vectors = np.load(output / "embeddings.npy")
        with (output / "embedding_hashes.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert [row["embedding_sha256"] for row, vector in zip(rows, vectors)] == [vector_hash(vector) for vector in vectors]
        payload = "".join(f"{row['class_id']}\t{row['embedding_sha256']}\n" for row in rows).encode()
        aggregate = hashlib.sha256(payload).hexdigest()
        metadata = yaml.safe_load((output / "embedding_metadata.json").read_text(encoding="utf-8"))
        assert aggregate == metadata["aggregate_embedding_sha256"]
        assert hashlib.sha256((output / "embeddings.npy").read_bytes()).hexdigest() == EXPECTED_EMBEDDINGS_NPY_HASHES[subject]


def test_nearest_neighbors_exclude_self_and_break_ties_by_class_id() -> None:
    rows = [{"class_id": class_id} for class_id in ["q", "b", "a", "c", "d", "e"]]
    vectors = np.ones((len(rows), 3584), dtype="<f4")
    neighbors = nearest_neighbors(rows, vectors)
    query = [row for row in neighbors if row["class_id"] == "q"]
    assert [row["neighbor_rank"] for row in query] == [1, 2, 3, 4, 5]
    assert [row["neighbor_class_id"] for row in query] == ["a", "b", "c", "d", "e"]
    assert all(row["neighbor_class_id"] != row["class_id"] for row in neighbors)


def test_true_cosine_is_bounded_and_handles_non_unit_identical_vectors() -> None:
    vectors = np.asarray([[3.0, 4.0], [6.0, 8.0], [-3.0, -4.0]], dtype=np.float32)
    similarity = true_cosine_similarity(vectors)
    assert similarity[0, 1] == pytest.approx(1.0)
    assert similarity[0, 2] == pytest.approx(-1.0)
    assert np.all(similarity <= 1.0)
    assert np.all(similarity >= -1.0)


def test_true_cosine_rejects_zero_norm_input() -> None:
    with pytest.raises(ValueError, match="zero-norm"):
        true_cosine_similarity(np.asarray([[0.0, 0.0], [1.0, 0.0]], dtype=np.float32))


def test_manifest_preserves_inputs_and_leaves_graph_hashes_null() -> None:
    manifest = yaml.safe_load((ROOT / "reports/stage3/formal_run_manifest.json").read_text(encoding="utf-8"))
    for subject, expected_hash in EXPECTED_INPUT_HASHES.items():
        assert manifest["input_hashes"][subject]["aggregate_sha256"] == expected_hash
    assert manifest["semantic_graph_hashes"] == {"jpetstore": None, "daytrader": None, "xerces": None}
    assert set(manifest["embedding_hashes"]) == set(EXPECTED_INPUT_HASHES)


def test_frozen_config_disables_truncation_and_query_prompt() -> None:
    config = yaml.safe_load((ROOT / "configs/experiments/04_stage3_semantic.yml").read_text(encoding="utf-8"))
    assert config["embedding_runtime"]["formal_truncation"] is False
    assert config["embedding_runtime"]["query_prompt_used"] is False
    assert config["embedding_runtime"]["runtime_frozen"] is True


def test_input_count_mismatch_fails(monkeypatch, tmp_path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("subject,class_id,semantic_text,input_hash\nx,a,text,hash\n", encoding="utf-8")
    monkeypatch.setitem(INPUT_PATHS, "jpetstore", path)
    monkeypatch.setitem(SUBJECTS, "jpetstore", (24, EXPECTED_INPUT_HASHES["jpetstore"]))
    with pytest.raises(ValueError, match="expected 24 rows"):
        read_subject("jpetstore")
