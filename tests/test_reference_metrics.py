from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.evaluation.reference_metrics import _mojo_distance
from evo_ms.evaluation.reference_metrics import _mojofm
from evo_ms.evaluation.reference_metrics import _maximum_mojo_distance
from evo_ms.evaluation.reference_metrics import calculate_reference_metrics
from evo_ms.evaluation.reference_metrics import reference_mapping_diagnostics


def test_reference_mapping_diagnostics_reports_coverage_and_missing_classes() -> None:
    diagnostics = reference_mapping_diagnostics(
        class_nodes_frame("A", "B", "C"),
        reference_mapping_frame(("A", "account"), ("B", "account"), ("Z", "order")),
    )

    assert diagnostics["reference_coverage_ratio"] == pytest.approx(2 / 3)
    assert diagnostics["unmapped_extracted_classes"]["class_name"].tolist() == ["C"]
    assert diagnostics["reference_classes_not_found"]["class_name"].tolist() == ["Z"]


def test_calculate_reference_metrics_uses_mapped_subset() -> None:
    metrics = calculate_reference_metrics(
        class_nodes_frame("A", "B", "C"),
        clusters_frame(("A", 0), ("B", 0), ("C", 1)),
        reference_mapping_frame(("A", "account"), ("B", "account")),
    )

    assert metrics["reference_coverage_ratio"] == pytest.approx(2 / 3)
    assert metrics["pairwise_precision"] == 1.0
    assert metrics["pairwise_recall"] == 1.0
    assert metrics["pairwise_f1"] == 1.0
    assert metrics["mojofm_vs_reference"] == 100.0
    assert metrics["ari_vs_reference"] == 1.0
    assert metrics["nmi_vs_reference"] == 1.0


def test_mojofm_identical_partitions() -> None:
    names = ["A", "B", "C", "D"]
    candidate = {"A": "0", "B": "0", "C": "1", "D": "1"}
    reference = {"A": "X", "B": "X", "C": "Y", "D": "Y"}

    assert _mojo_distance(candidate, reference, names) == 0
    assert _mojofm(candidate, reference, names) == 100.0


def test_mojofm_counts_joins_for_singleton_candidate_clusters() -> None:
    names = ["A", "B", "C"]
    candidate = {"A": "0", "B": "1", "C": "2"}
    reference = {"A": "X", "B": "X", "C": "X"}

    assert _mojo_distance(candidate, reference, names) == 2
    assert _mojofm(candidate, reference, names) == 0.0


def test_mojofm_counts_moves_for_singleton_reference_clusters() -> None:
    names = ["A", "B", "C"]
    candidate = {"A": "0", "B": "0", "C": "0"}
    reference = {"A": "X", "B": "Y", "C": "Z"}

    assert _mojo_distance(candidate, reference, names) == 2
    assert _mojofm(candidate, reference, names) == 0.0


def test_mojofm_mixed_partition_requires_move_and_join() -> None:
    names = ["A", "B", "C", "D"]
    candidate = {"A": "0", "B": "0", "C": "1", "D": "2"}
    reference = {"A": "X", "B": "Y", "C": "X", "D": "Y"}

    # One move preserves a reference pair, followed by one join.
    assert _mojo_distance(candidate, reference, names) == 2


def _canonical_partition(clusters: list[set[str]]) -> tuple[tuple[str, ...], ...]:
    return tuple(sorted(tuple(sorted(cluster)) for cluster in clusters if cluster))


def _partition_mapping(
    partition: tuple[tuple[str, ...], ...],
) -> dict[str, str]:
    return {
        class_name: str(cluster_id)
        for cluster_id, cluster in enumerate(partition)
        for class_name in cluster
    }


def _partition_neighbors(
    partition: tuple[tuple[str, ...], ...],
) -> set[tuple[tuple[str, ...], ...]]:
    clusters = [set(cluster) for cluster in partition]
    neighbors: set[tuple[tuple[str, ...], ...]] = set()

    for source_index, source in enumerate(clusters):
        for class_name in source:
            for target_index in range(len(clusters)):
                if target_index == source_index:
                    continue
                moved = [set(cluster) for cluster in clusters]
                moved[source_index].remove(class_name)
                moved[target_index].add(class_name)
                neighbors.add(_canonical_partition(moved))

            if len(source) > 1:
                moved = [set(cluster) for cluster in clusters]
                moved[source_index].remove(class_name)
                moved.append({class_name})
                neighbors.add(_canonical_partition(moved))

    for left in range(len(clusters)):
        for right in range(left + 1, len(clusters)):
            joined = [set(cluster) for cluster in clusters]
            joined[left].update(joined[right])
            del joined[right]
            neighbors.add(_canonical_partition(joined))

    return neighbors


def _brute_force_mojo_distance(
    candidate: tuple[tuple[str, ...], ...],
    reference: tuple[tuple[str, ...], ...],
) -> int:
    frontier = {candidate}
    visited = {candidate}
    distance = 0
    while frontier:
        if reference in frontier:
            return distance
        next_frontier: set[tuple[tuple[str, ...], ...]] = set()
        for partition in frontier:
            next_frontier.update(_partition_neighbors(partition) - visited)
        visited.update(next_frontier)
        frontier = next_frontier
        distance += 1
    raise AssertionError("Reference partition is unreachable")


def _set_partitions(items: tuple[str, ...]) -> list[tuple[tuple[str, ...], ...]]:
    if not items:
        return [()]

    first, *rest = items
    partitions: set[tuple[tuple[str, ...], ...]] = set()
    for partition in _set_partitions(tuple(rest)):
        clusters = [set(cluster) for cluster in partition]
        partitions.add(_canonical_partition(clusters + [{first}]))
        for index in range(len(clusters)):
            inserted = [set(cluster) for cluster in clusters]
            inserted[index].add(first)
            partitions.add(_canonical_partition(inserted))
    return sorted(partitions)


def test_mojo_distance_matches_brute_force_oracle_for_small_partitions() -> None:
    names = ("A", "B", "C", "D")
    partitions = _set_partitions(names)

    for candidate_partition in partitions:
        candidate = _partition_mapping(candidate_partition)
        for reference_partition in partitions:
            reference = _partition_mapping(reference_partition)
            expected = _brute_force_mojo_distance(
                candidate_partition,
                reference_partition,
            )
            assert _mojo_distance(candidate, reference, list(names)) == expected

    for reference_partition in partitions:
        reference = _partition_mapping(reference_partition)
        expected_maximum = max(
            _brute_force_mojo_distance(candidate_partition, reference_partition)
            for candidate_partition in partitions
        )
        assert (
            _maximum_mojo_distance(reference, list(names))
            == expected_maximum
        )


def class_nodes_frame(*class_names: str) -> pd.DataFrame:
    return pd.DataFrame({"class_name": list(class_names)})


def clusters_frame(*rows: tuple[str, int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "class_name": [row[0] for row in rows],
            "cluster_id": [row[1] for row in rows],
        }
    )


def reference_mapping_frame(*rows: tuple[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "class_name": [row[0] for row in rows],
            "reference_service": [row[1] for row in rows],
        }
    )
