from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evo_ms.semantic.graph import build_graph_from_embeddings, true_cosine_similarity


def test_true_cosine_normalizes_non_unit_vectors_and_rejects_zero_norm() -> None:
    matrix = true_cosine_similarity(np.asarray([[3.0, 4.0], [6.0, 8.0]], dtype=np.float32))
    assert matrix[0, 1] == pytest.approx(1.0)
    assert float(matrix.max()) <= 1.0
    with pytest.raises(ValueError, match="zero-norm"):
        true_cosine_similarity(np.asarray([[0.0, 0.0], [1.0, 0.0]], dtype=np.float32))


def test_final_top_three_graph_excludes_self_and_uses_class_id_ties() -> None:
    class_ids = ["z", "b", "a", "c"]
    directed, edges = build_graph_from_embeddings(class_ids, np.ones((4, 3), dtype=np.float32), k=3)
    assert len(directed) == 12
    assert all(row["source_class_id"] != row["target_class_id"] for row in directed)
    assert [row["target_class_id"] for row in directed if row["source_class_id"] == "z"] == ["a", "b", "c"]
    assert len(edges) == len({(row["class_id_a"], row["class_id_b"]) for row in edges})
