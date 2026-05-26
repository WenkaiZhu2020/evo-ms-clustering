from __future__ import annotations

import math
from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd


REFERENCE_COLUMNS = ["class_name", "reference_service"]


def load_reference_mapping(path: str | Path) -> pd.DataFrame:
    mapping = pd.read_csv(path)
    missing = [column for column in REFERENCE_COLUMNS if column not in mapping.columns]
    if missing:
        raise ValueError(f"reference mapping is missing required columns: {', '.join(missing)}")
    mapping = mapping.loc[:, REFERENCE_COLUMNS].copy()
    mapping["class_name"] = mapping["class_name"].astype("string")
    mapping["reference_service"] = mapping["reference_service"].astype("string")
    if mapping["class_name"].isna().any() or (mapping["class_name"].str.strip() == "").any():
        raise ValueError("reference mapping contains empty class_name values")
    if mapping["reference_service"].isna().any() or (
        mapping["reference_service"].str.strip() == ""
    ).any():
        raise ValueError("reference mapping contains empty reference_service values")
    if mapping["class_name"].astype(str).duplicated().any():
        raise ValueError("reference mapping contains duplicate class_name values")
    return mapping


def reference_mapping_diagnostics(
    class_nodes: pd.DataFrame,
    reference_mapping: pd.DataFrame,
) -> dict[str, pd.DataFrame | float]:
    _validate_class_nodes(class_nodes)
    mapping = _validate_reference_mapping(reference_mapping)
    extracted_names = set(class_nodes["class_name"].dropna().astype(str))
    reference_names = set(mapping["class_name"].dropna().astype(str))
    mapped_names = extracted_names & reference_names
    return {
        "reference_coverage_ratio": 0.0
        if not extracted_names
        else float(len(mapped_names) / len(extracted_names)),
        "unmapped_extracted_classes": pd.DataFrame(
            {"class_name": sorted(extracted_names - reference_names)},
        ),
        "reference_classes_not_found": pd.DataFrame(
            {"class_name": sorted(reference_names - extracted_names)},
        ),
    }


def calculate_reference_metrics(
    class_nodes: pd.DataFrame,
    clusters: pd.DataFrame,
    reference_mapping: pd.DataFrame,
) -> dict[str, float]:
    _validate_class_nodes(class_nodes)
    _validate_clusters(clusters)
    mapping = _validate_reference_mapping(reference_mapping)

    extracted_names = set(class_nodes["class_name"].dropna().astype(str))
    merged = (
        clusters.loc[:, ["class_name", "cluster_id"]]
        .copy()
        .assign(class_name=lambda frame: frame["class_name"].astype(str))
        .merge(mapping.astype(str), on="class_name", how="inner")
    )
    merged = merged.loc[merged["class_name"].isin(extracted_names)].copy()
    coverage = 0.0 if not extracted_names else float(len(merged) / len(extracted_names))
    if merged.empty:
        return _empty_metrics(coverage)

    class_names = merged["class_name"].astype(str).tolist()
    candidate = dict(zip(class_names, merged["cluster_id"].astype(str), strict=True))
    reference = dict(zip(class_names, merged["reference_service"].astype(str), strict=True))
    precision, recall, f1 = _pairwise_metrics(candidate, reference, class_names)
    return {
        "mojofm_vs_reference": _mojofm(candidate, reference, class_names),
        "pairwise_f1": f1,
        "reference_coverage_ratio": coverage,
        "ari_vs_reference": _adjusted_rand_index(candidate, reference, class_names),
        "nmi_vs_reference": _normalized_mutual_information(candidate, reference, class_names),
        "pairwise_precision": precision,
        "pairwise_recall": recall,
    }


def _empty_metrics(coverage: float) -> dict[str, float]:
    return {
        "mojofm_vs_reference": 0.0,
        "pairwise_f1": 0.0,
        "reference_coverage_ratio": coverage,
        "ari_vs_reference": 0.0,
        "nmi_vs_reference": 0.0,
        "pairwise_precision": 0.0,
        "pairwise_recall": 0.0,
    }


def _validate_class_nodes(class_nodes: pd.DataFrame) -> None:
    missing = [column for column in ["class_name"] if column not in class_nodes.columns]
    if missing:
        raise ValueError(f"class_nodes is missing required columns: {', '.join(missing)}")


def _validate_clusters(clusters: pd.DataFrame) -> None:
    missing = [
        column
        for column in ["class_name", "cluster_id"]
        if column not in clusters.columns
    ]
    if missing:
        raise ValueError(f"clusters is missing required columns: {', '.join(missing)}")


def _validate_reference_mapping(reference_mapping: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REFERENCE_COLUMNS if column not in reference_mapping.columns]
    if missing:
        raise ValueError(f"reference mapping is missing required columns: {', '.join(missing)}")
    mapping = reference_mapping.loc[:, REFERENCE_COLUMNS].copy()
    if mapping["class_name"].isna().any() or mapping["reference_service"].isna().any():
        raise ValueError("reference mapping contains missing values")
    if (mapping["reference_service"].astype(str).str.strip() == "").any():
        raise ValueError("reference mapping contains empty reference_service values")
    return mapping


def _pairwise_metrics(
    candidate: dict[str, str],
    reference: dict[str, str],
    class_names: list[str],
) -> tuple[float, float, float]:
    candidate_pairs = _same_cluster_pairs(candidate, class_names)
    reference_pairs = _same_cluster_pairs(reference, class_names)
    true_positive = len(candidate_pairs & reference_pairs)
    precision = 0.0 if not candidate_pairs else true_positive / len(candidate_pairs)
    recall = 0.0 if not reference_pairs else true_positive / len(reference_pairs)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return float(precision), float(recall), float(f1)


def _same_cluster_pairs(labels: dict[str, str], class_names: list[str]) -> set[tuple[str, str]]:
    return {
        (left, right)
        for left, right in combinations(sorted(class_names), 2)
        if labels[left] == labels[right]
    }


def _mojofm(
    candidate: dict[str, str],
    reference: dict[str, str],
    class_names: list[str],
) -> float:
    if not class_names:
        return 0.0
    candidate_clusters = _classes_by_label(candidate, class_names)
    reference_cluster_count = len(set(reference.values()))
    preserved = 0
    for members in candidate_clusters.values():
        overlaps = Counter(reference[class_name] for class_name in members)
        preserved += max(overlaps.values(), default=0)
    mojo_distance = len(class_names) - preserved
    max_distance = len(class_names) - reference_cluster_count
    if max_distance <= 0:
        return 100.0 if mojo_distance == 0 else 0.0
    return float(max(0.0, min(100.0, (1.0 - mojo_distance / max_distance) * 100.0)))


def _classes_by_label(labels: dict[str, str], class_names: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for class_name in class_names:
        grouped.setdefault(labels[class_name], []).append(class_name)
    return grouped


def _adjusted_rand_index(
    candidate: dict[str, str],
    reference: dict[str, str],
    class_names: list[str],
) -> float:
    n = len(class_names)
    total_pairs = _choose_two(n)
    if total_pairs == 0:
        return 1.0

    contingency: Counter[tuple[str, str]] = Counter(
        (candidate[class_name], reference[class_name]) for class_name in class_names
    )
    candidate_counts: Counter[str] = Counter(candidate[class_name] for class_name in class_names)
    reference_counts: Counter[str] = Counter(reference[class_name] for class_name in class_names)

    index = sum(_choose_two(count) for count in contingency.values())
    candidate_pair_sum = sum(_choose_two(count) for count in candidate_counts.values())
    reference_pair_sum = sum(_choose_two(count) for count in reference_counts.values())
    expected_index = candidate_pair_sum * reference_pair_sum / total_pairs
    max_index = (candidate_pair_sum + reference_pair_sum) / 2.0
    denominator = max_index - expected_index
    return 1.0 if denominator == 0 else float((index - expected_index) / denominator)


def _normalized_mutual_information(
    candidate: dict[str, str],
    reference: dict[str, str],
    class_names: list[str],
) -> float:
    n = len(class_names)
    if n == 0:
        return 1.0

    contingency: Counter[tuple[str, str]] = Counter(
        (candidate[class_name], reference[class_name]) for class_name in class_names
    )
    candidate_counts: Counter[str] = Counter(candidate[class_name] for class_name in class_names)
    reference_counts: Counter[str] = Counter(reference[class_name] for class_name in class_names)

    mutual_information = 0.0
    for (candidate_cluster, reference_cluster), count in contingency.items():
        mutual_information += (count / n) * math.log(
            (count * n) / (candidate_counts[candidate_cluster] * reference_counts[reference_cluster])
        )

    candidate_entropy = _entropy(candidate_counts.values(), n)
    reference_entropy = _entropy(reference_counts.values(), n)
    if candidate_entropy == 0 and reference_entropy == 0:
        return 1.0
    denominator = math.sqrt(candidate_entropy * reference_entropy)
    return 0.0 if denominator == 0 else float(mutual_information / denominator)


def _entropy(counts, total: int) -> float:
    return -sum((count / total) * math.log(count / total) for count in counts if count)


def _choose_two(value: int) -> float:
    return value * (value - 1) / 2.0
