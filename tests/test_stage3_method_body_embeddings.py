import numpy as np
import pytest

from scripts.stage3_method_body.generate_embeddings import (
    EXPECTED_COUNTS,
    OUTPUT_ROOT,
    verify_frozen_inputs,
)
from scripts.stage3_method_body.validate_embeddings import (
    group_indices,
    pairwise_cosine,
)


def test_frozen_stage3b_inputs_are_verified_before_generation() -> None:
    rows = verify_frozen_inputs()
    assert {subject: len(value) for subject, value in rows.items()} == EXPECTED_COUNTS
    for subject, subject_rows in rows.items():
        assert [row["class_id"] for row in subject_rows] == sorted(row["class_id"] for row in subject_rows)


def test_canonical_output_root_is_not_a_stage3a_cache_path(tmp_path) -> None:
    from scripts.stage3_method_body.generate_embeddings import assert_empty_output

    with pytest.raises(ValueError, match="canonical Stage 3B output"):
        assert_empty_output(tmp_path / "results" / "jpetstore" / "04_stage3_semantic" / "embeddings", canonical=True)
    assert OUTPUT_ROOT.name == "declaration_method_body"


def test_pairwise_cosine_normalizes_non_unit_vectors_and_rejects_invalid_vectors() -> None:
    result = pairwise_cosine(np.asarray([[3.0, 4.0]], dtype=np.float32), np.asarray([[6.0, 8.0]], dtype=np.float32))
    assert result[0] == pytest.approx(1.0)
    with pytest.raises(ValueError, match="zero-norm"):
        pairwise_cosine(np.asarray([[0.0, 0.0]]), np.asarray([[1.0, 0.0]]))
    with pytest.raises(ValueError, match="non-finite"):
        pairwise_cosine(np.asarray([[np.nan, 0.0]]), np.asarray([[1.0, 0.0]]))


def test_duplicate_grouping_is_deterministic() -> None:
    assert group_indices(["b", "a", "b", "c", "a"]) == [[0, 2], [1, 4]]
