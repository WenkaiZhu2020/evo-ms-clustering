#!/usr/bin/env python3
"""Run preregistered diagnostics on the frozen semantic graphs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.evaluation.reference_metrics import load_reference_mapping  # noqa: E402
from evo_ms.extraction.dependency_extractor import load_raw_extracted_subject  # noqa: E402
from evo_ms.graph.raw_graph_builder import build_raw_edges  # noqa: E402

try:
    from .build_semantic_graphs import (  # noqa: E402
        SUBJECTS,
        canonical_weight,
        sha256_file,
        subject_embedding_dir,
        subject_graph_dir,
    )
    from .random_graph_baseline import baseline_rows, mapped_ratio, quantile  # noqa: E402
except ImportError:  # pragma: no cover - direct script execution
    from build_semantic_graphs import SUBJECTS, canonical_weight, sha256_file, subject_embedding_dir, subject_graph_dir
    from random_graph_baseline import baseline_rows, mapped_ratio, quantile


RESULT_SUBJECT = {"jpetstore": "jpetstore", "daytrader": "daytrader", "xerces": "xerces-j"}
INPUT_FILE = {
    "jpetstore": ROOT / "data/semantic_inputs/jpetstore_class_declarations.csv",
    "daytrader": ROOT / "data/semantic_inputs/daytrader_class_declarations.csv",
    "xerces": ROOT / "data/semantic_inputs/xerces-j_class_declarations.csv",
}
EXTRACTED_DIR = {
    subject: ROOT / "data/extracted" / RESULT_SUBJECT[subject] for subject in SUBJECTS
}
LEIDEN_FILE = {
    subject: ROOT / "results" / RESULT_SUBJECT[subject] / "01_stage1_leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv"
    for subject in SUBJECTS
}
REFERENCE_FILE = ROOT / "data/references/daytrader_reference_services.csv"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_semantic_rows(subject: str) -> list[dict[str, str]]:
    rows = read_csv(INPUT_FILE[subject])
    rows.sort(key=lambda row: row["class_id"])
    if len(rows) != SUBJECTS[subject]:
        raise ValueError(f"{subject}: semantic input scope mismatch")
    return rows


def canonical_edge(left: str, right: str) -> tuple[str, str]:
    if left == right:
        raise ValueError("self-loop cannot be canonicalized as a diagnostic edge")
    return tuple(sorted((str(left), str(right))))


def source_provenance(subject: str, formal_class_ids: set[str]) -> tuple[set[tuple[str, str]], dict[str, Any]]:
    extracted_dir = EXTRACTED_DIR[subject]
    extracted = load_raw_extracted_subject(extracted_dir)
    class_nodes = extracted["class_nodes"]
    raw_edges_frame = build_raw_edges(class_nodes, extracted["structural_dependencies"])
    raw_nodes = set(class_nodes["class_id"].astype(str))
    if raw_nodes != formal_class_ids:
        missing = sorted(formal_class_ids - raw_nodes)
        extra = sorted(raw_nodes - formal_class_ids)
        raise ValueError(f"{subject}: G_raw scope differs; missing={missing}; extra={extra}")
    raw_edges = {
        canonical_edge(str(row["source"]), str(row["target"]))
        for row in raw_edges_frame.to_dict("records")
        if str(row["source"]) != str(row["target"])
    }
    files = {
        "class_nodes": {
            "path": str((extracted_dir / "class_nodes.csv").relative_to(ROOT)),
            "sha256": sha256_file(extracted_dir / "class_nodes.csv"),
        },
        "structural_dependencies": {
            "path": str((extracted_dir / "structural_dependencies.csv").relative_to(ROOT)),
            "sha256": sha256_file(extracted_dir / "structural_dependencies.csv"),
        },
    }
    return raw_edges, {
        "source_files": files,
        "normalization": "evo_ms.graph.raw_graph_builder.build_raw_edges; undirected canonical endpoints; self-loops removed; duplicate pairs merged",
        "raw_structural_node_count": len(raw_nodes),
        "canonical_undirected_structural_edge_count": len(raw_edges),
    }


def load_labels(path: Path) -> dict[str, str]:
    rows = read_csv(path)
    return {row["class_id"]: row["cluster_id"] for row in rows}


def load_reference(subject: str) -> tuple[dict[str, str] | None, dict[str, Any]]:
    if subject != "daytrader":
        return None, {"path": None, "sha256": None, "mapping_available": False}
    mapping = load_reference_mapping(REFERENCE_FILE)
    return (
        {str(row["class_name"]): str(row["reference_service"]) for row in mapping.to_dict("records")},
        {"path": str(REFERENCE_FILE.relative_to(ROOT)), "sha256": sha256_file(REFERENCE_FILE), "mapping_available": True},
    )


def class_name_labels(subject: str) -> dict[str, str]:
    return {row["class_id"]: row["class_name"] for row in read_semantic_rows(subject)}


def extracted_class_name_labels(subject: str) -> dict[str, str]:
    return {
        row["class_id"]: row["class_name"]
        for row in read_csv(EXTRACTED_DIR[subject] / "class_nodes.csv")
    }


def package_name(class_id: str) -> str:
    return class_id.rsplit(".", 1)[0] if "." in class_id else ""


def load_graph_rows(subject: str, results_root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    graph_dir = subject_graph_dir(subject, results_root)
    directed = read_csv(graph_dir / "directed_top3.csv")
    edges = read_csv(graph_dir / "semantic_edges.csv")
    metadata = json.loads((graph_dir / "graph_metadata.json").read_text(encoding="utf-8"))
    return directed, edges, metadata


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def graph_structure(subject: str, directed: list[dict[str, str]], edges: list[dict[str, str]], metadata: dict[str, Any]) -> dict[str, Any]:
    class_ids = {row["source_class_id"] for row in directed}
    graph = nx.Graph()
    graph.add_nodes_from(class_ids)
    graph.add_edges_from((row["class_id_a"], row["class_id_b"]) for row in edges)
    degrees = [degree for _, degree in graph.degree()]
    weights = np.asarray([float(row["weight"]) for row in edges], dtype=float)
    components = sorted((len(component) for component in nx.connected_components(graph)), reverse=True)
    mutual = sum(row["selected_by"] == "both" for row in edges)
    incident = sum(degree > 0 for degree in degrees)
    return {
        "schema_version": 1,
        "subject": subject,
        "generated_at_utc": utc_now(),
        "node_count": len(class_ids),
        "edge_count": len(edges),
        "directed_selection_count": len(directed),
        "total_edge_weight": float(weights.sum()),
        "node_coverage": float(incident / len(class_ids)),
        "isolated_node_count": int(len(class_ids) - incident),
        "isolated_node_ratio": float((len(class_ids) - incident) / len(class_ids)),
        "degree_min": int(min(degrees)),
        "degree_mean": float(np.mean(degrees)),
        "degree_median": float(np.median(degrees)),
        "degree_max": int(max(degrees)),
        "largest_connected_component_node_count": int(components[0]),
        "largest_connected_component_ratio": float(components[0] / len(class_ids)),
        "connected_component_count": len(components),
        "edge_weight_min": float(weights.min()),
        "edge_weight_mean": float(weights.mean()),
        "edge_weight_median": float(np.median(weights)),
        "edge_weight_max": float(weights.max()),
        "negative_edge_count": int(np.sum(weights < 0)),
        "zero_edge_count": int(np.sum(weights == 0)),
        "mutual_selection_edge_count": int(mutual),
        "mutual_selection_edge_ratio": float(mutual / len(edges)),
        "source_graph_metadata": "graph_metadata.json",
    }


def novelty_alignment(
    subject: str,
    edges: list[dict[str, str]],
    raw_edges: set[tuple[str, str]],
    leiden_labels: dict[str, str],
    reference_name_labels: dict[str, str] | None,
    names: dict[str, str],
    reference_names: dict[str, str],
    source_info: dict[str, Any],
    leiden_path: Path,
    reference_info: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    semantic_pairs = {canonical_edge(row["class_id_a"], row["class_id_b"]) for row in edges}
    overlap = semantic_pairs & raw_edges
    novel = semantic_pairs - raw_edges
    same_package = sum(package_name(row["class_id_a"]) == package_name(row["class_id_b"]) for row in edges)
    leiden_edges = [(row["class_id_a"], row["class_id_b"]) for row in edges]
    leiden_value, leiden_num, leiden_den = mapped_ratio(leiden_edges, leiden_labels)
    reference_labels = None
    if reference_name_labels is not None:
        reference_labels = {
            class_id: reference_name_labels[reference_names[class_id]]
            for class_id in names
            if class_id in reference_names and reference_names[class_id] in reference_name_labels
        }
    reference_value, reference_num, reference_den = mapped_ratio(leiden_edges, reference_labels or {})
    result = {
        "schema_version": 1,
        "subject": subject,
        "generated_at_utc": utc_now(),
        "semantic_edge_count": len(semantic_pairs),
        "overlap_edge_count": len(overlap),
        "structural_overlap": float(len(overlap) / len(semantic_pairs)),
        "novel_edge_count": len(novel),
        "novel_edge_ratio": float(len(novel) / len(semantic_pairs)),
        "identity_check_sum": float(len(overlap) / len(semantic_pairs) + len(novel) / len(semantic_pairs)),
        "same_package_edge_count": int(same_package),
        "same_package_ratio": float(same_package / len(edges)),
        "cross_package_edge_count": int(len(edges) - same_package),
        "cross_package_ratio": float((len(edges) - same_package) / len(edges)),
        "fixed_leiden": {
            "mapping_node_count": len(leiden_labels),
            "mapping_coverage": float(len(set(leiden_labels) & set(names)) / len(names)),
            "eligible_edge_count": leiden_den,
            "ineligible_edge_count": len(edges) - leiden_den,
            "numerator": leiden_num,
            "denominator": leiden_den,
            "ratio": leiden_value,
            "cluster_count": len(set(leiden_labels.values())),
            "source_path": str(leiden_path.relative_to(ROOT)),
            "source_sha256": sha256_file(leiden_path),
        },
        "reference_service": {
            "mapping_available": reference_info["mapping_available"],
            "mapping_node_count": len(reference_labels or {}),
            "mapping_coverage": float(len(reference_labels or {}) / len(names)),
            "eligible_edge_count": reference_den,
            "ineligible_edge_count": len(edges) - reference_den,
            "numerator": reference_num,
            "denominator": reference_den,
            "ratio": reference_value,
            "source_path": reference_info["path"],
            "source_sha256": reference_info["sha256"],
        },
        "g_raw": source_info,
    }
    return result, {
        "raw_edges": raw_edges,
        "reference_labels": reference_labels or {},
        "leiden_labels": leiden_labels,
        "semantic_pairs": semantic_pairs,
    }


def duplicate_diagnostics(subject: str, directed: list[dict[str, str]], edges: list[dict[str, str]], names: dict[str, str]) -> dict[str, Any]:
    semantic_rows = read_semantic_rows(subject)
    input_hash_by_id = {row["class_id"]: row["input_hash"] for row in semantic_rows}
    text_by_hash: dict[str, list[str]] = defaultdict(list)
    for row in semantic_rows:
        text_by_hash[row["input_hash"]].append(row["class_id"])
    text_groups = [sorted(members) for members in text_by_hash.values() if len(members) > 1]
    embedding_rows = read_csv(subject_embedding_dir(subject) / "embedding_hashes.csv")
    vector_groups_by_hash: dict[str, list[str]] = defaultdict(list)
    for row in embedding_rows:
        vector_groups_by_hash[row["embedding_sha256"]].append(row["class_id"])
    vector_groups = [sorted(members) for members in vector_groups_by_hash.values() if len(members) > 1]
    duplicate_members = {class_id for group in text_groups for class_id in group}
    identical_text_directed = [
        row for row in directed if input_hash_by_id[row["source_class_id"]] == input_hash_by_id[row["target_class_id"]]
    ]
    exact_one_directed = [row for row in directed if float(row["weight"]) == 1.0]
    affected_nodes = {row["source_class_id"] for row in identical_text_directed}
    duplicate_edges = [
        row for row in edges if input_hash_by_id[row["class_id_a"]] == input_hash_by_id[row["class_id_b"]]
    ]
    involving_duplicate_group = [
        row for row in edges if row["class_id_a"] in duplicate_members or row["class_id_b"] in duplicate_members
    ]
    group_details = []
    for members in text_groups:
        member_set = set(members)
        group_edges = [row for row in edges if row["class_id_a"] in member_set and row["class_id_b"] in member_set]
        group_directed = [
            row for row in directed if row["source_class_id"] in member_set and row["target_class_id"] in member_set
        ]
        group_details.append(
            {
                "members": members,
                "group_size": len(members),
                "possible_intra_group_undirected_edge_count": len(members) * (len(members) - 1) // 2,
                "actual_final_intra_group_semantic_edges": len(group_edges),
                "directed_intra_group_selections": len(group_directed),
                "top_k_slots_occupied_by_intra_group_selections": len(group_directed),
            }
        )
    return {
        "schema_version": 1,
        "subject": subject,
        "generated_at_utc": utc_now(),
        "duplicate_text_group_count": len(text_groups),
        "duplicate_text_group_sizes": sorted(len(group) for group in text_groups),
        "duplicate_text_groups": group_details,
        "duplicate_text_class_count": len(duplicate_members),
        "duplicate_text_class_ratio": float(len(duplicate_members) / len(semantic_rows)),
        "identical_embedding_group_count": len(vector_groups),
        "identical_embedding_class_count": sum(len(group) for group in vector_groups),
        "identical_embedding_groups": [{"members": group, "group_size": len(group)} for group in vector_groups],
        "directed_identical_text_selection_count": len(identical_text_directed),
        "directed_exact_cosine_one_selection_count": len(exact_one_directed),
        "nodes_with_identical_text_top3_neighbour_count": len(affected_nodes),
        "nodes_with_identical_text_top3_neighbour_ratio": float(len(affected_nodes) / len(semantic_rows)),
        "identical_text_undirected_edge_count": len(duplicate_edges),
        "edges_involving_duplicate_text_group_class_count": len(involving_duplicate_group),
        "edges_involving_duplicate_text_group_class_ratio": float(len(involving_duplicate_group) / len(edges)),
        "policy": "representation-induced equivalence; no duplicate filtering, merging, down-weighting, or forced edges",
        "xerces_expected_duplicate_groups": 11 if subject == "xerces" else None,
    }


def write_random_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "subject", "repetition", "random_seed", "edge_count", "structural_overlap",
        "same_reference_service_ratio", "same_leiden_cluster_ratio",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            output = dict(row)
            for field in fields[4:]:
                if output[field] is not None:
                    output[field] = canonical_weight(float(output[field]))
            writer.writerow(output)


def random_summary(subject: str, edges: list[dict[str, str]], random_rows: list[dict[str, object]], raw_edges: set[tuple[str, str]], reference_labels: dict[str, str], leiden_labels: dict[str, str], runtime_seconds: float) -> dict[str, Any]:
    edge_pairs = [(row["class_id_a"], row["class_id_b"]) for row in edges]
    observed_structural = float(sum(canonical_edge(*pair) in raw_edges for pair in edge_pairs) / len(edge_pairs))
    observed_reference, _, _ = mapped_ratio(edge_pairs, reference_labels)
    observed_leiden, _, _ = mapped_ratio(edge_pairs, leiden_labels)
    metrics: dict[str, Any] = {}
    for key, observed in (
        ("structural_overlap", observed_structural),
        ("same_reference_service_ratio", observed_reference),
        ("same_leiden_cluster_ratio", observed_leiden),
    ):
        values = [float(row[key]) for row in random_rows if row[key] is not None]
        entry = {
            "observed": observed,
            "random_min": min(values) if values else None,
            "random_mean": float(np.mean(values)) if values else None,
            "random_p50": quantile(values, 0.50) if values else None,
            "random_p95": quantile(values, 0.95) if values else None,
            "random_max": max(values) if values else None,
            "valid_random_value_count": len(values),
            "percentile_implementation": "numpy.quantile",
            "percentile_method": "higher",
            "observed_strictly_greater_than_p95": bool(observed is not None and values and observed > quantile(values, 0.95)),
        }
        metrics[key] = entry
    return {
        "schema_version": 1,
        "subject": subject,
        "generated_at_utc": utc_now(),
        "baseline_code_path": "scripts/stage3/random_graph_baseline.py",
        "model": "uniform_simple_undirected_gnm",
        "repetitions": 1000,
        "subject_seed_base": {"jpetstore": 42000, "daytrader": 52000, "xerces": 62000}[subject],
        "repetition_seed_rule": "subject_seed_base + repetition_index, repetition_index=0..999",
        "sampling_rule": "uniformly select exactly m distinct unordered pairs without replacement from all i<j pairs",
        "degree_distribution_preserved": False,
        "quantile_method": "numpy.quantile(method='higher')",
        "edge_count": len(edges),
        "valid_random_values_by_metric": {key: value["valid_random_value_count"] for key, value in metrics.items()},
        "metrics": metrics,
        "runtime_seconds": runtime_seconds,
    }


def top_weight_edges(subject: str, edges: list[dict[str, str]], names: dict[str, str], raw_edges: set[tuple[str, str]], leiden_labels: dict[str, str], reference_labels: dict[str, str], input_hash_by_id: dict[str, str]) -> list[dict[str, object]]:
    ranked = sorted(edges, key=lambda row: (-float(row["weight"]), row["class_id_a"], row["class_id_b"]))[:10]
    output = []
    for rank, row in enumerate(ranked, start=1):
        left, right = row["class_id_a"], row["class_id_b"]
        ref = reference_labels.get(left) if left in reference_labels and right in reference_labels else None
        output.append(
            {
                "rank": rank,
                "class_id_a": left,
                "class_name_a": names[left],
                "class_id_b": right,
                "class_name_b": names[right],
                "weight": canonical_weight(float(row["weight"])),
                "selected_by": row["selected_by"],
                "overlaps_G_raw": str(canonical_edge(left, right) in raw_edges).lower(),
                "same_package": str(package_name(left) == package_name(right)).lower(),
                "same_Leiden_cluster": str(leiden_labels.get(left) == leiden_labels.get(right)).lower(),
                "same_reference_service": "" if ref is None else str(reference_labels[left] == reference_labels[right]).lower(),
                "duplicate_text_pair": str(input_hash_by_id[left] == input_hash_by_id[right]).lower(),
            }
        )
    return output


def run_subject(subject: str, results_root: Path, output_root: Path) -> dict[str, Any]:
    start = time.perf_counter()
    directed, edges, metadata = load_graph_rows(subject, results_root)
    names = class_name_labels(subject)
    reference_names = extracted_class_name_labels(subject)
    class_ids = set(names)
    raw_edges, source_info = source_provenance(subject, class_ids)
    leiden_path = LEIDEN_FILE[subject]
    leiden_labels = load_labels(leiden_path)
    if set(leiden_labels) != class_ids:
        raise ValueError(f"{subject}: fixed Leiden scope differs from formal scope")
    reference_name_labels, reference_info = load_reference(subject)
    novelty, context = novelty_alignment(subject, edges, raw_edges, leiden_labels, reference_name_labels, names, reference_names, source_info, leiden_path, reference_info)
    random_rows = baseline_rows(
        class_ids,
        len(edges),
        subject,
        raw_edges,
        context["reference_labels"],
        leiden_labels,
    )
    representation = duplicate_diagnostics(subject, directed, edges, names)
    input_hash_by_id = {row["class_id"]: row["input_hash"] for row in read_semantic_rows(subject)}
    top_edges = top_weight_edges(subject, edges, names, raw_edges, leiden_labels, context["reference_labels"], input_hash_by_id)
    summary = random_summary(subject, edges, random_rows, raw_edges, context["reference_labels"], leiden_labels, time.perf_counter() - start)
    output_dir = output_root / subject / "04_stage3_semantic" / "diagnostics"
    write_json(output_dir / "graph_structure.json", graph_structure(subject, directed, edges, metadata))
    write_json(output_dir / "novelty_alignment.json", novelty)
    write_random_csv(output_dir / "random_baseline_metrics.csv", random_rows)
    write_json(output_dir / "random_baseline_summary.json", summary)
    write_json(output_dir / "representation_ties.json", representation)
    fields = list(top_edges[0]) if top_edges else []
    with (output_dir / "top_weight_edges.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(top_edges)
    return {"subject": subject, "graph_structure": graph_structure(subject, directed, edges, metadata), "novelty": novelty, "random_summary": summary, "representation": representation, "top_edges": top_edges}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subjects", nargs="*", default=list(SUBJECTS))
    parser.add_argument("--results-root", type=Path, default=ROOT / "results")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    summaries = {subject: run_subject(subject, args.results_root, args.output_root) for subject in args.subjects}
    print(json.dumps({subject: value["random_summary"] for subject, value in summaries.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
