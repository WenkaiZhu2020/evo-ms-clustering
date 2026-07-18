from evo_ms.analysis.random_graph_baseline import (
    REPETITIONS,
    baseline_rows,
    candidate_pairs,
    mapped_ratio,
    quantile,
    repetition_seed,
    sample_edges,
)
from pathlib import Path


def test_random_pair_universe_and_sampling_contract():
    assert candidate_pairs(["c", "a", "b"]) == [("a", "b"), ("a", "c"), ("b", "c")]
    assert len(candidate_pairs(["a", "b", "c", "d"])) == 6
    edges = sample_edges(["a", "b", "c", "d"], 3, "jpetstore", 0)
    assert len(edges) == len(set(edges)) == 3
    assert all(left < right for left, right in edges)
    assert edges == sample_edges(["a", "b", "c", "d"], 3, "jpetstore", 0)
    assert edges != sample_edges(["a", "b", "c", "d"], 3, "jpetstore", 1)
    assert repetition_seed("xerces", 999) == 62999


def test_random_mapping_denominators_and_missing_reference_are_null():
    edges = [("a", "b"), ("a", "c"), ("b", "c")]
    value, numerator, denominator = mapped_ratio(edges, {"a": "x", "b": "x"})
    assert value == 1.0 and numerator == 1 and denominator == 1
    assert mapped_ratio(edges, {}) == (None, 0, 0)


def test_random_quantile_and_full_repetition_determinism():
    assert quantile([0.1, 0.2, 0.3, 0.4], 0.5) == 0.3
    kwargs = {
        "class_ids": ["a", "b", "c", "d", "e"],
        "edge_count": 3,
        "subject": "daytrader",
        "raw_edges": {("a", "b")},
        "reference_labels": {"a": "x", "b": "x", "c": "y"},
        "leiden_labels": {"a": "1", "b": "1", "c": "2", "d": "2", "e": "3"},
    }
    first = baseline_rows(**kwargs)
    second = baseline_rows(**kwargs)
    assert len(first) == len(second) == REPETITIONS == 1000
    assert first == second
    assert first[0]["random_seed"] == 52000
    assert first[-1]["random_seed"] == 52999


def test_random_baseline_does_not_use_stage2_random_fill():
    source = Path(__import__("evo_ms.analysis.random_graph_baseline", fromlist=["__file__"]).__file__).read_text(encoding="utf-8")
    assert "random_fill" not in source
    assert "default_rng" in source
