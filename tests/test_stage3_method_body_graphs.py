from pathlib import Path
import inspect

import numpy as np
import pytest

from scripts.stage3_method_body.build_semantic_graphs import (
    EXPECTED_COUNTS,
    EXPECTED_DIMENSION,
    REPRESENTATION_ID,
    STAGE3B_GRAPH_ROOT,
    assert_empty_output,
    frozen_build_graph_from_embeddings,
    graph_config,
    load_stage3b_inputs,
    write_subject_artifacts,
)
from scripts.stage3_method_body.validate_semantic_graphs import (
    compare_reproducibility,
    validate_subject,
)


ROOT = Path(__file__).resolve().parents[1]
REPRO_ROOT = Path("/tmp/stage3b-graph-repro.graph")


def test_frozen_graph_contract_is_top3_true_cosine() -> None:
    graph, _ = graph_config()
    assert graph["k"] == 3
    assert graph["similarity"] == "true_cosine"
    assert graph["ranking"]["exact_tie_break"] == "class_id_lexicographic_ascending"
    assert graph["symmetrisation"] == "OR"
    assert graph["self_loops"] == "forbidden"


def test_stage3b_embedding_provenance_and_dimensions_are_frozen() -> None:
    for subject, count in EXPECTED_COUNTS.items():
        vectors, mapping, source = load_stage3b_inputs(subject)
        assert vectors.shape == (count, EXPECTED_DIMENSION)
        assert source["metadata"]["representation_id"] == REPRESENTATION_ID
        assert len(mapping) == count


def test_top3_excludes_self_and_uses_lexicographic_ties() -> None:
    from scripts.stage3_method_body.build_semantic_graphs import frozen_build_graph_from_embeddings

    class_ids = ["pkg.z", "pkg.b", "pkg.a", "pkg.c", "pkg.d"]
    directed, edges = frozen_build_graph_from_embeddings(class_ids, np.ones((5, 4), dtype=np.float32), 3)
    for class_id in class_ids:
        rows = [row for row in directed if row["source_class_id"] == class_id]
        assert [row["rank"] for row in rows] == [1, 2, 3]
        assert class_id not in [row["target_class_id"] for row in rows]
        assert [row["target_class_id"] for row in rows] == sorted(
            target for target in class_ids if target != class_id
        )[:3]
    assert all(row["class_id_a"] < row["class_id_b"] for row in edges)


def test_stage3b_graph_output_rejects_stage3a_result_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="canonical Stage 3B graph output"):
        assert_empty_output(tmp_path / "results" / "jpetstore" / "04_stage3_semantic" / "graph", canonical=True)
    assert STAGE3B_GRAPH_ROOT.name == "declaration_method_body"


def test_saved_stage3b_graphs_validate_with_no_isolates() -> None:
    for subject, count in EXPECTED_COUNTS.items():
        result = validate_subject(subject, STAGE3B_GRAPH_ROOT)
        assert result["node_count"] == count
        assert result["directed_count"] == count * 3
        assert result["isolated_count"] == 0
        assert result["self_loop_count"] == 0
        assert result["duplicate_edge_count"] == 0


def test_graph_reproducibility_is_byte_identical() -> None:
    rows = compare_reproducibility(STAGE3B_GRAPH_ROOT, REPRO_ROOT)
    assert all(row["passed"] == "true" for row in rows)


def test_graph_generation_adapter_is_independent_of_optimizer_and_result_paths(tmp_path: Path) -> None:
    """Graph construction remains graph-only after formal result creation."""
    import scripts.stage3_method_body.build_semantic_graphs as graph_builder

    source = inspect.getsource(graph_builder)
    assert "pymoo" not in source
    assert "run_seed00_optimizer" not in source

    vectors, mapping, embedding_source = load_stage3b_inputs("jpetstore")
    small_mapping = mapping[:4]
    class_ids = [row["class_id"] for row in small_mapping]
    directed, edges = frozen_build_graph_from_embeddings(class_ids, vectors[:4], 3)
    result = write_subject_artifacts(
        "jpetstore",
        small_mapping,
        directed,
        edges,
        embedding_source,
        "graph-test-config",
        "graph-test-source",
        tmp_path / "graph-only-output",
    )

    assert result["output_dir"] == tmp_path / "graph-only-output" / "jpetstore"
    assert (result["output_dir"] / "semantic_edges.csv").is_file()
    assert not (tmp_path / "results").exists()
    assert not (ROOT / "results" / "jpetstore" / "05_stage3_declaration_method_body" / "formal").exists()
    assert not (ROOT / "data" / "semantic_graphs" / "declaration_method_body" / "optimization").exists()
