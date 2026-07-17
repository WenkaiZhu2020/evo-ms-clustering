#!/usr/bin/env python3
"""Validate isolated Stage 3B semantic graphs and run graph-only diagnostics."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Iterable

import networkx as nx
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.stage3 import diagnose_semantic_graphs as stage3a_diag  # noqa: E402
from scripts.stage3.random_graph_baseline import baseline_rows, mapped_ratio, quantile  # noqa: E402
from scripts.stage3_method_body.build_semantic_graphs import (  # noqa: E402
    EXPECTED_COUNTS,
    EXPECTED_DIMENSION,
    EXPECTED_EMBEDDING_AGGREGATES,
    EXPECTED_GRAPH_SOURCE_COMMIT,
    EXPECTED_INPUT_HASHES,
    EXPECTED_MODEL,
    EXPECTED_REVISION,
    EXPERIMENT_ID,
    REPORT_ROOT,
    SUBJECTS,
    STAGE3B_EMBEDDING_ROOT,
    STAGE3B_GRAPH_ROOT,
    TOP_K,
    canonical_directed_payload,
    canonical_graph_payload,
    canonical_weight,
    graph_config,
    load_stage3b_inputs,
    read_csv,
    read_json,
    sha256_bytes,
    sha256_file,
    write_csv,
    write_json,
)
from scripts.stage3_method_body.generate_embeddings import verify_frozen_inputs  # noqa: E402


STAGE3A_GRAPH_ROOT = ROOT / "results"
GRAPH_FILES = (
    "artifact_hashes.csv",
    "class_mapping.csv",
    "directed_topk_neighbours.csv",
    "graph_metadata.json",
    "semantic_edges.csv",
)
SHIFT_REPORT = REPORT_ROOT / "stage3a_vs_stage3b_embedding_shift.csv"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stats(values: Iterable[float]) -> dict[str, float]:
    array = np.asarray(list(values), dtype=np.float64)
    if len(array) == 0:
        return {"minimum": 0.0, "mean": 0.0, "median": 0.0, "standard_deviation": 0.0, "maximum": 0.0}
    return {
        "minimum": float(array.min()),
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "standard_deviation": float(array.std()),
        "maximum": float(array.max()),
    }


def canonical_edge(left: str, right: str) -> tuple[str, str]:
    if left == right:
        raise ValueError("self-loop cannot be canonicalized")
    return tuple(sorted((str(left), str(right))))


def read_graph(subject: str, root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any], list[dict[str, str]]]:
    directory = root / subject
    actual = {path.name for path in directory.iterdir() if path.is_file()}
    if actual != set(GRAPH_FILES):
        raise ValueError(f"{subject}: unexpected graph files {sorted(actual ^ set(GRAPH_FILES))}")
    directed = read_csv(directory / "directed_topk_neighbours.csv")
    edges = read_csv(directory / "semantic_edges.csv")
    metadata = read_json(directory / "graph_metadata.json")
    artifacts = read_csv(directory / "artifact_hashes.csv")
    return directed, edges, metadata, artifacts


def expected_rows(subject: str) -> tuple[list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    vectors, mapping, source = load_stage3b_inputs(subject)
    class_ids = [row["class_id"] for row in mapping]
    from scripts.stage3.build_semantic_graphs import build_graph_from_embeddings

    directed, edges = build_graph_from_embeddings(class_ids, vectors, TOP_K)
    return mapping, directed, edges, source


def validate_subject(subject: str, root: Path) -> dict[str, Any]:
    mapping, expected_directed, expected_edges, source = expected_rows(subject)
    directed, edges, metadata, artifacts = read_graph(subject, root)
    class_ids = [row["class_id"] for row in mapping]
    comparable_directed = [
        {
            "source_class_id": row["source_class_id"],
            "rank": row["rank"],
            "target_class_id": row["target_class_id"],
            "weight": canonical_weight(float(row["weight"])),
        }
        for row in directed
    ]
    expected_directed_serialized = [
        {
            "source_class_id": row["source_class_id"],
            "rank": str(row["rank"]),
            "target_class_id": row["target_class_id"],
            "weight": canonical_weight(float(row["weight"])),
        }
        for row in expected_directed
    ]
    if comparable_directed != expected_directed_serialized:
        raise ValueError(f"{subject}: directed top-k rows differ from frozen builder")
    comparable_edges = [
        {
            "class_id_a": row["class_id_a"],
            "class_id_b": row["class_id_b"],
            "weight": canonical_weight(float(row["weight"])),
            "selected_by": row["selected_by"],
        }
        for row in edges
    ]
    expected_edges_serialized = [
        {
            "class_id_a": row["class_id_a"],
            "class_id_b": row["class_id_b"],
            "weight": canonical_weight(float(row["weight"])),
            "selected_by": row["selected_by"],
        }
        for row in expected_edges
    ]
    if comparable_edges != expected_edges_serialized:
        raise ValueError(f"{subject}: semantic edges differ from frozen builder")
    class_mapping = read_csv(root / subject / "class_mapping.csv")
    if class_mapping != mapping:
        raise ValueError(f"{subject}: graph class mapping differs from frozen embedding mapping")
    if len(directed) != EXPECTED_COUNTS[subject] * TOP_K:
        raise ValueError(f"{subject}: directed count is not N*3")
    class_set = set(class_ids)
    sources = defaultdict(list)
    for row in directed:
        source_id = row["source_class_id"]
        target_id = row["target_class_id"]
        if source_id == target_id:
            raise ValueError(f"{subject}: self-neighbour found")
        if source_id not in class_set or target_id not in class_set:
            raise ValueError(f"{subject}: directed node outside class scope")
        sources[source_id].append(row)
    if set(sources) != class_set or any([int(row["rank"]) for row in rows] != [1, 2, 3] for rows in sources.values()):
        raise ValueError(f"{subject}: directed top-k source/rank coverage is invalid")
    pairs = [(row["class_id_a"], row["class_id_b"]) for row in edges]
    if any(left >= right for left, right in pairs):
        raise ValueError(f"{subject}: final edge endpoints are not canonicalized")
    if len(pairs) != len(set(pairs)):
        raise ValueError(f"{subject}: duplicate final edge")
    if any(row["selected_by"] not in {"a", "b", "both"} for row in edges):
        raise ValueError(f"{subject}: invalid reciprocal-edge marker")
    weights = np.asarray([float(row["weight"]) for row in edges], dtype=np.float64)
    if not np.isfinite(weights).all():
        raise ValueError(f"{subject}: non-finite edge weight")
    graph = nx.Graph()
    graph.add_nodes_from(class_ids)
    graph.add_edges_from(pairs)
    degrees = [degree for _, degree in graph.degree()]
    components = list(nx.connected_components(graph))
    artifact_expected = []
    for path in sorted((root / subject).iterdir()):
        if path.name == "artifact_hashes.csv":
            continue
        artifact_expected.append({"relative_path": path.name, "sha256": sha256_file(path), "size_bytes": str(path.stat().st_size)})
    if artifacts != artifact_expected:
        raise ValueError(f"{subject}: artifact hash report does not match graph files")
    required_metadata = {
        "experiment_name": EXPERIMENT_ID,
        "representation_id": "declaration_method_body_v1",
        "subject": subject,
        "top_k": TOP_K,
        "similarity": "true_cosine",
        "symmetrisation": "OR",
        "node_count": EXPECTED_COUNTS[subject],
        "directed_selection_count": EXPECTED_COUNTS[subject] * TOP_K,
        "edge_count": len(edges),
        "embedding_aggregate_sha256": EXPECTED_EMBEDDING_AGGREGATES[subject],
        "input_aggregate_sha256": EXPECTED_INPUT_HASHES[subject],
        "embedding_file_sha256": source["embedding_sha256"],
        "source_commit": EXPECTED_GRAPH_SOURCE_COMMIT,
        "embedding_source_commit": source["source_commit"],
    }
    for key, expected in required_metadata.items():
        if metadata.get(key) != expected:
            raise ValueError(f"{subject}: graph metadata {key}={metadata.get(key)!r}, expected {expected!r}")
    if metadata["directed_topk_neighbours_sha256"] != sha256_file(root / subject / "directed_topk_neighbours.csv"):
        raise ValueError(f"{subject}: directed graph file hash mismatch")
    if metadata["semantic_edges_file_sha256"] != sha256_file(root / subject / "semantic_edges.csv"):
        raise ValueError(f"{subject}: semantic edge file hash mismatch")
    if metadata["class_mapping_file_sha256"] != sha256_file(root / subject / "class_mapping.csv"):
        raise ValueError(f"{subject}: class mapping file hash mismatch")
    if metadata["directed_selection_sha256"] != sha256_bytes(canonical_directed_payload(expected_directed)):
        raise ValueError(f"{subject}: directed canonical hash mismatch")
    if metadata["semantic_graph_sha256"] != sha256_bytes(canonical_graph_payload(expected_edges)):
        raise ValueError(f"{subject}: graph canonical hash mismatch")
    directed_roundtrip, edges_roundtrip, metadata_roundtrip, artifacts_roundtrip = read_graph(subject, root)
    if (directed_roundtrip, edges_roundtrip, metadata_roundtrip, artifacts_roundtrip) != (directed, edges, metadata, artifacts):
        raise ValueError(f"{subject}: graph save/load round trip changed serialized content")
    return {
        "subject": subject,
        "mapping": mapping,
        "directed": directed,
        "edges": edges,
        "metadata": metadata,
        "artifacts": artifacts,
        "nodes": class_ids,
        "graph": graph,
        "weights": weights,
        "node_count": len(class_ids),
        "directed_count": len(directed),
        "edge_count": len(edges),
        "isolated_count": sum(degree == 0 for degree in degrees),
        "self_loop_count": sum(left == right for left, right in pairs),
        "duplicate_edge_count": len(pairs) - len(set(pairs)),
        "component_count": len(components),
        "degree": stats(degrees),
        "weight": stats(weights),
        "round_trip_passed": True,
    }


def compare_reproducibility(canonical_root: Path, repro_root: Path) -> list[dict[str, Any]]:
    rows = []
    for subject in SUBJECTS:
        result = {"subject": subject}
        for filename in GRAPH_FILES:
            result[f"{filename}_byte_identical"] = str(
                (canonical_root / subject / filename).read_bytes() == (repro_root / subject / filename).read_bytes()
            ).lower()
        left_meta = read_json(canonical_root / subject / "graph_metadata.json")
        right_meta = read_json(repro_root / subject / "graph_metadata.json")
        result["metadata_equal_excluding_variable_fields"] = str(left_meta == right_meta).lower()
        result["graph_sha256"] = left_meta["semantic_graph_sha256"]
        result["directed_selection_sha256"] = left_meta["directed_selection_sha256"]
        result["passed"] = str(all(value == "true" for key, value in result.items() if key.endswith("byte_identical")) and result["metadata_equal_excluding_variable_fields"] == "true").lower()
        rows.append(result)
    return rows


def load_diagnostic_context(subject: str, class_ids: set[str]) -> dict[str, Any]:
    raw_edges, source_info = stage3a_diag.source_provenance(subject, class_ids)
    leiden = stage3a_diag.load_labels(stage3a_diag.LEIDEN_FILE[subject])
    names = stage3a_diag.class_name_labels(subject)
    extracted_names = stage3a_diag.extracted_class_name_labels(subject)
    reference_name_labels, reference_info = stage3a_diag.load_reference(subject)
    reference_labels = {}
    if reference_name_labels is not None:
        reference_labels = {
            class_id: reference_name_labels[extracted_names[class_id]]
            for class_id in class_ids
            if class_id in extracted_names and extracted_names[class_id] in reference_name_labels
        }
    return {
        "raw_edges": raw_edges,
        "source_info": source_info,
        "leiden_labels": leiden,
        "names": names,
        "reference_labels": reference_labels,
        "reference_info": reference_info,
    }


def write_structural_overlap_and_random(
    graph_results: dict[str, dict[str, Any]],
    contexts: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    overlap_rows = []
    random_rows_all = []
    random_summaries: dict[str, dict[str, Any]] = {}
    reference_rows = []
    for subject in SUBJECTS:
        result = graph_results[subject]
        context = contexts[subject]
        semantic_pairs = {canonical_edge(row["class_id_a"], row["class_id_b"]) for row in result["edges"]}
        raw_edges = context["raw_edges"]
        overlap = semantic_pairs & raw_edges
        novel = semantic_pairs - raw_edges
        union = semantic_pairs | raw_edges
        overlap_rows.append({
            "subject": subject,
            "semantic_edge_count": len(semantic_pairs),
            "raw_structural_edge_count": len(raw_edges),
            "overlap_edge_count": len(overlap),
            "novel_edge_count": len(novel),
            "overlap_proportion": len(overlap) / len(semantic_pairs),
            "novel_edge_proportion": len(novel) / len(semantic_pairs),
            "edge_set_jaccard": len(overlap) / len(union),
            "node_count": len(result["nodes"]),
            "node_coverage": 1.0,
            "normalization": "undirected canonical endpoints; self-loops removed; duplicate pairs merged",
            "class_nodes_path": context["source_info"]["source_files"]["class_nodes"]["path"],
            "structural_dependencies_path": context["source_info"]["source_files"]["structural_dependencies"]["path"],
        })
        random_rows = baseline_rows(
            result["nodes"],
            len(result["edges"]),
            subject,
            raw_edges,
            context["reference_labels"],
            context["leiden_labels"],
        )
        random_rows_all.extend(random_rows)
        edge_pairs = list(semantic_pairs)
        observed_structural = len(overlap) / len(semantic_pairs)
        observed_reference, ref_num, ref_den = mapped_ratio(edge_pairs, context["reference_labels"])
        structural_values = [float(row["structural_overlap"]) for row in random_rows]
        reference_values = [float(row["same_reference_service_ratio"]) for row in random_rows if row["same_reference_service_ratio"] is not None]
        structural_p95 = quantile(structural_values, 0.95)
        reference_p95 = quantile(reference_values, 0.95) if reference_values else None
        reference_pass = observed_reference is not None and reference_p95 is not None and observed_reference > reference_p95
        _, old_edges, _ = stage3a_graph(subject)
        old_reference, _, _ = mapped_ratio(
            [canonical_edge(row["class_id_a"], row["class_id_b"]) for row in old_edges],
            context["reference_labels"],
        )
        random_summaries[subject] = {
            "subject": subject,
            "observed_structural_overlap": observed_structural,
            "random_structural_mean": float(np.mean(structural_values)),
            "random_structural_median": float(np.median(structural_values)),
            "random_structural_p95": structural_p95,
            "random_structural_maximum": max(structural_values),
            "observed_minus_random_structural_mean": observed_structural - float(np.mean(structural_values)),
            "observed_reference_alignment": observed_reference,
            "reference_numerator": ref_num,
            "reference_denominator": ref_den,
            "random_reference_mean": float(np.mean(reference_values)) if reference_values else None,
            "random_reference_median": float(np.median(reference_values)) if reference_values else None,
            "random_reference_p95": reference_p95,
            "random_reference_maximum": max(reference_values) if reference_values else None,
            "observed_minus_random_reference_mean": observed_reference - float(np.mean(reference_values)) if observed_reference is not None and reference_values else None,
            "structural_pass": observed_structural > structural_p95,
            "reference_pass": reference_pass,
            "go": observed_structural > structural_p95 or reference_pass,
            "random_repetitions": len(random_rows),
            "random_seed_base": {"jpetstore": 42000, "daytrader": 52000, "xerces": 62000}[subject],
        }
        reference_rows.append({
            "subject": subject,
            "mapping_available": bool(context["reference_labels"]),
            "reference_path": context["reference_info"]["path"],
            "reference_sha256": context["reference_info"]["sha256"],
            "eligible_semantic_edges": ref_den,
            "within_reference_service_edges": ref_num,
            "stage3b_alignment": observed_reference,
            "random_mean": random_summaries[subject]["random_reference_mean"],
            "random_p95": random_summaries[subject]["random_reference_p95"],
            "stage3a_alignment": old_reference,
        })
    write_csv(REPORT_ROOT / "semantic_structural_overlap.csv", list(overlap_rows[0]), overlap_rows)
    write_csv(REPORT_ROOT / "semantic_graph_random_baseline.csv", [
        "subject", "repetition", "random_seed", "edge_count", "structural_overlap", "same_reference_service_ratio", "same_leiden_cluster_ratio",
    ], random_rows_all)
    summary_rows = []
    for subject in SUBJECTS:
        item = random_summaries[subject]
        summary_rows.append(item)
    write_csv(REPORT_ROOT / "semantic_graph_random_baseline_summary.csv", list(summary_rows[0]), summary_rows)
    summary_lines = [
        "# Stage 3B semantic graph random-baseline summary",
        "",
        "The preregistered baseline is uniform simple undirected G(n,m), with 1000 repetitions, exact observed edge count, fixed subject seed bases, and `numpy.quantile(method='higher')`. GO uses strict observed > random p95.",
        "",
        "| Subject | Observed structural overlap | Random mean | Random median | Random p95 | Random maximum | Observed-minus-random mean | GO |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in summary_rows:
        summary_lines.append(f"| {item['subject']} | {item['observed_structural_overlap']:.9f} | {item['random_structural_mean']:.9f} | {item['random_structural_median']:.9f} | {item['random_structural_p95']:.9f} | {item['random_structural_maximum']:.9f} | {item['observed_minus_random_structural_mean']:.9f} | {str(item['go']).lower()} |")
    summary_lines += ["", "The random result is a graph-signal diagnostic, not decomposition-quality evidence.", ""]
    (REPORT_ROOT / "semantic_graph_random_baseline_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")
    write_csv(REPORT_ROOT / "semantic_reference_alignment.csv", list(reference_rows[0]), reference_rows)
    return random_summaries, {"overlap_rows": overlap_rows, "reference_rows": reference_rows}


def stage3a_graph(subject: str) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    return stage3a_diag.load_graph_rows(subject, STAGE3A_GRAPH_ROOT)


def load_shift_rows() -> dict[str, dict[str, dict[str, str]]]:
    result = {subject: {} for subject in SUBJECTS}
    for row in read_csv(SHIFT_REPORT):
        result[row["subject"]][row["class_id"]] = row
    return result


def graph_comparison(
    graph_results: dict[str, dict[str, Any]],
    input_rows: dict[str, list[dict[str, str]]],
    shift_rows: dict[str, dict[str, dict[str, str]]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    comparison_rows = []
    neighbour_rows = []
    summaries = {}
    for subject in SUBJECTS:
        old_directed, old_edges, _ = stage3a_graph(subject)
        new = graph_results[subject]
        old_pairs = {canonical_edge(row["class_id_a"], row["class_id_b"]) for row in old_edges}
        new_pairs = {canonical_edge(row["class_id_a"], row["class_id_b"]) for row in new["edges"]}
        shared = old_pairs & new_pairs
        union = old_pairs | new_pairs
        old_weights = {canonical_edge(row["class_id_a"], row["class_id_b"]): float(row["weight"]) for row in old_edges}
        new_weights = {canonical_edge(row["class_id_a"], row["class_id_b"]): float(row["weight"]) for row in new["edges"]}
        common_weights = [
            (old_weights[pair], new_weights[pair]) for pair in sorted(shared)
        ]
        correlation = float(np.corrcoef(np.asarray(common_weights).T)[0, 1]) if len(common_weights) >= 2 and np.std(np.asarray(common_weights)[:, 0]) and np.std(np.asarray(common_weights)[:, 1]) else None
        old_neighbours = defaultdict(list)
        new_neighbours = defaultdict(list)
        for row in old_directed:
            old_neighbours[row["source_class_id"]].append(row["target_class_id"])
        for row in new["directed"]:
            new_neighbours[row["source_class_id"]].append(row["target_class_id"])
        old_degree = dict(nx.Graph([(row["class_id_a"], row["class_id_b"]) for row in old_edges]).degree())
        new_degree = dict(new["graph"].degree())
        retention_values = []
        for row in input_rows[subject]:
            class_id = row["class_id"]
            old_set = set(old_neighbours[class_id])
            new_set = set(new_neighbours[class_id])
            retained = len(old_set & new_set)
            retention = retained / TOP_K
            retention_values.append(retention)
            neighbour_rows.append({
                "subject": subject,
                "class_id": class_id,
                "stage3a_neighbours": "|".join(old_neighbours[class_id]),
                "stage3b_neighbours": "|".join(new_neighbours[class_id]),
                "retained_neighbour_count": retained,
                "neighbour_retention": retention,
                "stage3a_degree": old_degree.get(class_id, 0),
                "stage3b_degree": new_degree.get(class_id, 0),
                "degree_change": new_degree.get(class_id, 0) - old_degree.get(class_id, 0),
                "body_empty": row["body_empty"],
                "body_tokens_truncated": row["body_tokens_truncated"],
                "body_token_count": row["appended_body_token_count"],
                "embedding_shift_cosine_distance": str(1.0 - float(shift_rows[subject][class_id]["stage3a_stage3b_cosine_similarity"])),
            })
        comparison_rows.append({
            "subject": subject,
            "stage3a_edge_count": len(old_pairs),
            "stage3b_edge_count": len(new_pairs),
            "shared_edge_count": len(shared),
            "stage3a_only_edge_count": len(old_pairs - new_pairs),
            "stage3b_only_edge_count": len(new_pairs - old_pairs),
            "edge_set_jaccard": len(shared) / len(union),
            "stage3b_new_edge_share": len(new_pairs - old_pairs) / len(new_pairs),
            "shared_edge_weight_correlation": correlation,
            "mean_neighbour_retention": float(np.mean(retention_values)),
            "median_neighbour_retention": float(np.median(retention_values)),
            "zero_retention_class_count": sum(value == 0 for value in retention_values),
            "all_retained_class_count": sum(value == 1 for value in retention_values),
        })
        summaries[subject] = comparison_rows[-1]
    write_csv(REPORT_ROOT / "stage3a_vs_stage3b_graph_comparison.csv", list(comparison_rows[0]), comparison_rows)
    write_csv(REPORT_ROOT / "stage3a_vs_stage3b_neighbour_change.csv", list(neighbour_rows[0]), neighbour_rows)
    return summaries, neighbour_rows


def empty_nonempty_diagnostics(
    neighbour_rows: list[dict[str, Any]],
    shift_rows: dict[str, dict[str, dict[str, str]]],
) -> list[dict[str, Any]]:
    rows = []
    for subject in SUBJECTS:
        for group, group_value in (("empty", "true"), ("non_empty", "false")):
            selected = [row for row in neighbour_rows if row["subject"] == subject and row["body_empty"] == group_value]
            retentions = [float(row["neighbour_retention"]) for row in selected]
            shifts = [float(row["embedding_shift_cosine_distance"]) for row in selected]
            degrees = [int(row["degree_change"]) for row in selected]
            rows.append({
                "subject": subject,
                "body_group": group,
                "class_count": len(selected),
                "mean_neighbour_retention": float(np.mean(retentions)) if retentions else None,
                "median_neighbour_retention": float(np.median(retentions)) if retentions else None,
                "zero_retention_class_count": sum(value == 0 for value in retentions),
                "all_neighbours_retained_class_count": sum(value == 1 for value in retentions),
                "mean_embedding_shift_cosine_distance": float(np.mean(shifts)) if shifts else None,
                "mean_degree_change": float(np.mean(degrees)) if degrees else None,
                "diagnostic_note": "empty-body changes may include section-marker and explicit-empty-template effects" if group == "empty" else "non-empty body group",
            })
    write_csv(REPORT_ROOT / "empty_vs_nonempty_body_graph_change.csv", list(rows[0]), rows)
    return rows


def evidence_diagnostics(
    graph_results: dict[str, dict[str, Any]],
    contexts: dict[str, dict[str, Any]],
    input_rows: dict[str, list[dict[str, str]]],
    neighbour_rows: list[dict[str, Any]],
    shift_rows: dict[str, dict[str, dict[str, str]]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, float | None]]]:
    neighbour_by_id = {(row["subject"], row["class_id"]): row for row in neighbour_rows}
    output = []
    correlation_rows: dict[str, dict[str, float | None]] = {}
    for subject in SUBJECTS:
        subject_values = []
        for row in input_rows[subject]:
            class_id = row["class_id"]
            change = neighbour_by_id[(subject, class_id)]
            incident = [edge for edge in graph_results[subject]["edges"] if edge["class_id_a"] == class_id or edge["class_id_b"] == class_id]
            incident_overlap = sum(canonical_edge(edge["class_id_a"], edge["class_id_b"]) in contexts[subject]["raw_edges"] for edge in incident)
            body_count = int(row["appended_body_token_count"])
            counts = {
                "invoked_method": int(row["accepted_invoked_method_tokens"]),
                "field": int(row["accepted_field_tokens"]),
                "local": int(row["accepted_local_tokens"]),
                "exception": int(row["accepted_exception_tokens"]),
                "string": int(row["accepted_string_tokens"]),
                "operation": int(row["accepted_operation_tokens"]),
            }
            item = {
                "subject": subject,
                "class_id": class_id,
                "body_token_count": body_count,
                "invoked_method_token_count": counts["invoked_method"],
                "field_token_count": counts["field"],
                "local_token_count": counts["local"],
                "exception_token_count": counts["exception"],
                "string_token_count": counts["string"],
                "operation_token_count": counts["operation"],
                "invoked_method_proportion": counts["invoked_method"] / body_count if body_count else 0.0,
                "field_proportion": counts["field"] / body_count if body_count else 0.0,
                "string_proportion": counts["string"] / body_count if body_count else 0.0,
                "embedding_shift_cosine_distance": float(change["embedding_shift_cosine_distance"]),
                "neighbour_retention": float(change["neighbour_retention"]),
                "stage3b_degree": int(change["stage3b_degree"]),
                "neighbour_change": 1.0 - float(change["neighbour_retention"]),
                "incident_stage3b_edge_count": len(incident),
                "incident_structural_overlap_count": incident_overlap,
                "incident_structural_overlap_ratio": incident_overlap / len(incident) if incident else None,
            }
            output.append(item)
            subject_values.append(item)
        def correlation(left: str, right: str) -> float | None:
            x = np.asarray([float(item[left]) for item in subject_values], dtype=np.float64)
            y = np.asarray([float(item[right]) for item in subject_values], dtype=np.float64)
            if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
                return None
            return float(spearmanr(x, y).statistic)
        correlation_rows[subject] = {
            "body_token_count_vs_neighbour_change": correlation("body_token_count", "neighbour_change"),
            "embedding_shift_vs_neighbour_change": correlation("embedding_shift_cosine_distance", "neighbour_change"),
            "field_proportion_vs_neighbour_change": correlation("field_proportion", "neighbour_change"),
            "invoked_method_proportion_vs_neighbour_change": correlation("invoked_method_proportion", "neighbour_change"),
            "string_proportion_vs_neighbour_change": correlation("string_proportion", "neighbour_change"),
        }
    write_csv(REPORT_ROOT / "body_evidence_graph_change_diagnostics.csv", list(output[0]), output)
    return output, correlation_rows


def collision_diagnostics(graph_results: dict[str, dict[str, Any]], input_rows: dict[str, list[dict[str, str]]]) -> tuple[list[dict[str, Any]], str]:
    subject = "xerces"
    text_groups: dict[str, list[str]] = defaultdict(list)
    for row in input_rows[subject]:
        text_groups[row["input_hash"]].append(row["class_id"])
    groups = [sorted(members) for members in text_groups.values() if len(members) > 1]
    groups.sort(key=lambda members: members[0])
    if len(groups) != 11:
        raise ValueError(f"expected 11 Xerces collision groups, found {len(groups)}")
    vector_rows = read_csv(STAGE3B_EMBEDDING_ROOT / "xerces/embedding_hashes.csv")
    vector_hash = {row["class_id"]: row["embedding_sha256"] for row in vector_rows}
    group_by_class = {class_id: f"collision_{index:02d}" for index, members in enumerate(groups, start=1) for class_id in members}
    directed = graph_results[subject]["directed"]
    edges = graph_results[subject]["edges"]
    rows = []
    tie_count = 0
    for row in directed:
        if row["source_class_id"] not in group_by_class:
            continue
        same_vector = vector_hash[row["source_class_id"]] == vector_hash[row["target_class_id"]]
        tie_count += int(same_vector)
        rows.append({
            "collision_group": group_by_class[row["source_class_id"]],
            "record_type": "directed_topk",
            "edge_type": "intra_group" if group_by_class.get(row["target_class_id"]) == group_by_class[row["source_class_id"]] else "to_external",
            "class_id_a": row["source_class_id"],
            "class_id_b": row["target_class_id"],
            "rank": row["rank"],
            "weight": row["weight"],
            "selected_by": "directed",
            "identical_embedding_tie": str(same_vector).lower(),
            "tie_rule": "class_id_lexicographic_ascending" if same_vector else "not_applicable",
        })
    for row in edges:
        group_a = group_by_class.get(row["class_id_a"])
        group_b = group_by_class.get(row["class_id_b"])
        if not group_a and not group_b:
            continue
        rows.append({
            "collision_group": group_a or group_b,
            "record_type": "final_edge",
            "edge_type": "intra_group" if group_a == group_b else "to_external",
            "class_id_a": row["class_id_a"],
            "class_id_b": row["class_id_b"],
            "rank": "",
            "weight": row["weight"],
            "selected_by": row["selected_by"],
            "identical_embedding_tie": str(vector_hash[row["class_id_a"]] == vector_hash[row["class_id_b"]]).lower(),
            "tie_rule": "class_id_lexicographic_ascending" if vector_hash[row["class_id_a"]] == vector_hash[row["class_id_b"]] else "not_applicable",
        })
    write_csv(REPORT_ROOT / "xerces_collision_graph_edges.csv", list(rows[0]), rows)
    final_edges = [row for row in rows if row["record_type"] == "final_edge"]
    intra = sum(row["edge_type"] == "intra_group" for row in final_edges)
    external = sum(row["edge_type"] == "to_external" for row in final_edges)
    lines = [
        "# Xerces collision-group graph audit",
        "",
        "The 11 duplicate-text and duplicate-embedding groups are retained under the frozen simple-name contract. No class or edge was removed.",
        "",
        f"* Collision groups: {len(groups)}; collision classes: {len(group_by_class)}.",
        f"* Directed top-k rows from collision classes: {sum(row['record_type'] == 'directed_topk' for row in rows)}.",
        f"* Directed rows with identical-embedding ties: {tie_count}; tie rule: class_id lexicographic ascending.",
        f"* Final edges involving collision classes: {len(final_edges)} / {len(edges)} ({len(final_edges) / len(edges):.6f}).",
        f"* Final intra-group edges: {intra}; final edges to external classes: {external}.",
        "",
        "| Group | Members | Intra-group final edges | External final edges |",
        "|---|---:|---:|---:|",
    ]
    for index, members in enumerate(groups, start=1):
        group_name = f"collision_{index:02d}"
        group_edges = [row for row in final_edges if row["collision_group"] == group_name]
        lines.append(f"| {group_name} | {len(members)} | {sum(row['edge_type'] == 'intra_group' for row in group_edges)} | {sum(row['edge_type'] == 'to_external' for row in group_edges)} |")
        lines.append("")
        lines.append("Members: " + "; ".join(members))
    lines += ["", "The report is descriptive evidence of deterministic tie handling, not a reason to deduplicate or retune top-k.", ""]
    return rows, "\n".join(lines)


def manual_audit(
    graph_results: dict[str, dict[str, Any]],
    input_rows: dict[str, list[dict[str, str]]],
    neighbour_rows: list[dict[str, Any]],
    contexts: dict[str, dict[str, Any]],
) -> str:
    by_key = {(row["subject"], row["class_id"]): row for row in neighbour_rows}
    selected: dict[str, list[tuple[str, str]]] = {subject: [] for subject in SUBJECTS}
    for subject in SUBJECTS:
        rows = input_rows[subject]
        by_id = {row["class_id"]: row for row in rows}
        def add(category: str, class_id: str) -> None:
            if class_id in by_id and all(existing[1] != class_id for existing in selected[subject]):
                selected[subject].append((category, class_id))
        for row in rows[:5]:
            add("first_sorted", row["class_id"])
        for row in sorted(rows, key=lambda item: (float(by_key[(subject, item["class_id"])] ["neighbour_retention"]), item["class_id"]))[:5]:
            add("lowest_retention", row["class_id"])
        non_trivial = [row for row in rows if 0 < float(by_key[(subject, row["class_id"])] ["neighbour_retention"]) < 1]
        for row in sorted(non_trivial, key=lambda item: (-float(by_key[(subject, item["class_id"])] ["neighbour_retention"]), item["class_id"]))[:5]:
            add("highest_nontrivial_retention", row["class_id"])
        for row in rows:
            if int(row["body_tokens_truncated"]) > 0:
                add("body_truncated", row["class_id"])
        for row in rows:
            if row["body_empty"] == "true":
                add("empty_body_fixed_sample", row["class_id"])
                if sum(category == "empty_body_fixed_sample" for category, _ in selected[subject]) >= 5:
                    break
        if subject == "xerces":
            collision_rows = defaultdict(list)
            for row in rows:
                collision_rows[row["input_hash"]].append(row["class_id"])
            for members in sorted((sorted(value) for value in collision_rows.values() if len(value) > 1), key=lambda value: value[0]):
                for class_id in members:
                    add("xerces_collision_group", class_id)
        degrees = graph_results[subject]["graph"].degree()
        for class_id, _ in sorted(degrees, key=lambda item: (-item[1], item[0]))[:5]:
            add("highest_stage3b_degree", class_id)
    lines = [
        "# Stage 3B semantic graph manual audit",
        "",
        "Fixed sample: first five sorted classes; five lowest neighbour retention; five highest non-trivial retention; all body-truncated classes; first five empty-body classes; all Xerces collision-group members; and five highest Stage 3B degree classes. Classes are listed once.",
        "",
    ]
    for subject in SUBJECTS:
        lines += [f"## {subject}", ""]
        new_edges = {(row["class_id_a"], row["class_id_b"]): row for row in graph_results[subject]["edges"]}
        for category, class_id in selected[subject]:
            change = by_key[(subject, class_id)]
            old_neighbours = change["stage3a_neighbours"].split("|") if change["stage3a_neighbours"] else []
            new_neighbours = change["stage3b_neighbours"].split("|") if change["stage3b_neighbours"] else []
            descriptions = []
            for target in new_neighbours:
                pair = canonical_edge(class_id, target)
                edge = new_edges[pair]
                overlap = pair in contexts[subject]["raw_edges"]
                descriptions.append(f"{target} [w={float(edge['weight']):.12g}, G_raw={str(overlap).lower()}]")
            lines += [
                f"### `{class_id}` — {category}",
                f"body_empty={change['body_empty']}; body_tokens_truncated={change['body_tokens_truncated']}; retention={change['neighbour_retention']}; degree={change['stage3b_degree']}",
                f"Stage 3A neighbours: {'; '.join(old_neighbours)}",
                f"Stage 3B neighbours: {'; '.join(descriptions)}",
                "",
            ]
    return "\n".join(lines)


def write_quality_reports(
    graph_results: dict[str, dict[str, Any]],
    random_summaries: dict[str, dict[str, Any]],
    overlap_rows: list[dict[str, Any]],
    comparison_rows: dict[str, dict[str, Any]],
    empty_rows: list[dict[str, Any]],
    correlations: dict[str, dict[str, float | None]],
) -> None:
    quality_rows = []
    for subject in SUBJECTS:
        result = graph_results[subject]
        random = random_summaries[subject]
        overlap = next(row for row in overlap_rows if row["subject"] == subject)
        comparison = comparison_rows[subject]
        quality_rows.append({
            "subject": subject,
            "node_count": result["node_count"],
            "directed_neighbour_rows": result["directed_count"],
            "final_edge_count": result["edge_count"],
            "isolated_node_count": result["isolated_count"],
            "self_loop_count": result["self_loop_count"],
            "duplicate_edge_count": result["duplicate_edge_count"],
            "connected_component_count": result["component_count"],
            "edge_weight_min": result["weight"]["minimum"],
            "edge_weight_mean": result["weight"]["mean"],
            "edge_weight_median": result["weight"]["median"],
            "edge_weight_std": result["weight"]["standard_deviation"],
            "edge_weight_max": result["weight"]["maximum"],
            "degree_min": result["degree"]["minimum"],
            "degree_mean": result["degree"]["mean"],
            "degree_median": result["degree"]["median"],
            "degree_std": result["degree"]["standard_deviation"],
            "degree_max": result["degree"]["maximum"],
            "structural_overlap": overlap["overlap_proportion"],
            "novel_edge_proportion": overlap["novel_edge_proportion"],
            "random_structural_mean": random["random_structural_mean"],
            "random_structural_p95": random["random_structural_p95"],
            "random_structural_maximum": random["random_structural_maximum"],
            "observed_minus_random_structural_mean": random["observed_minus_random_structural_mean"],
            "go": random["go"],
            "shared_stage3a_edge_count": comparison["shared_edge_count"],
            "edge_set_jaccard": comparison["edge_set_jaccard"],
            "mean_neighbour_retention": comparison["mean_neighbour_retention"],
            "zero_retention_class_count": comparison["zero_retention_class_count"],
            "all_retained_class_count": comparison["all_retained_class_count"],
        })
    write_csv(REPORT_ROOT / "semantic_graph_quality_per_subject.csv", list(quality_rows[0]), quality_rows)
    lines = [
        "# Stage 3B semantic graph quality summary",
        "",
        "This report covers isolated top-3 graph construction, graph correctness, structural/random diagnostics, and descriptive Stage 3A comparison only. No NSGA-II, seed, Hypervolume, representative selection, or decomposition-quality analysis was run.",
        "",
        "Frozen graph contract: true cosine; all non-self candidates; top-3; cosine descending then class_id lexicographic ascending; OR symmetrisation; no edge threshold; self-loops and duplicate final edges forbidden.",
        "",
        "| Subject | Nodes | Directed rows | Final edges | Components | Isolated | Weight min/mean/median/std/max | Degree min/mean/median/std/max |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in quality_rows:
        lines.append(f"| {row['subject']} | {row['node_count']} | {row['directed_neighbour_rows']} | {row['final_edge_count']} | {row['connected_component_count']} | {row['isolated_node_count']} | {row['edge_weight_min']:.9f}/{row['edge_weight_mean']:.9f}/{row['edge_weight_median']:.9f}/{row['edge_weight_std']:.9f}/{row['edge_weight_max']:.9f} | {row['degree_min']:.0f}/{row['degree_mean']:.6f}/{row['degree_median']:.6f}/{row['degree_std']:.6f}/{row['degree_max']:.0f} |")
    lines += ["", "## Structural overlap and random baseline", "", "| Subject | Observed overlap | Novel edge share | Random mean | Random p95 | Random max | Observed-minus-random mean | GO |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for subject in SUBJECTS:
        item = random_summaries[subject]
        overlap = next(row for row in overlap_rows if row["subject"] == subject)
        lines.append(f"| {subject} | {overlap['overlap_proportion']:.9f} | {overlap['novel_edge_proportion']:.9f} | {item['random_structural_mean']:.9f} | {item['random_structural_p95']:.9f} | {item['random_structural_maximum']:.9f} | {item['observed_minus_random_structural_mean']:.9f} | {str(item['go']).lower()} |")
    lines += ["", "## Stage 3A versus Stage 3B graph change", "", "| Subject | Shared | Stage 3B-only | Jaccard | Mean retention | Zero retention | All retained |", "|---|---:|---:|---:|---:|---:|---:|"]
    for subject in SUBJECTS:
        item = comparison_rows[subject]
        lines.append(f"| {subject} | {item['shared_edge_count']} | {item['stage3b_only_edge_count']} | {item['edge_set_jaccard']:.9f} | {item['mean_neighbour_retention']:.9f} | {item['zero_retention_class_count']} | {item['all_retained_class_count']} |")
    lines += ["", "## Empty versus non-empty body", "", "Changes for empty-body classes can include section-marker and explicit-empty-template effects; they are not attributed solely to lexical method-body content.", ""]
    for row in empty_rows:
        lines.append(f"* {row['subject']} / {row['body_group']}: n={row['class_count']}; mean retention={row['mean_neighbour_retention']}; median={row['median_neighbour_retention']}; zero-retention={row['zero_retention_class_count']}; all-retained={row['all_neighbours_retained_class_count']}; mean embedding shift={row['mean_embedding_shift_cosine_distance']}; mean degree change={row['mean_degree_change']}")
    lines += ["", "## Evidence-composition correlations", "", "Spearman values are descriptive associations only and are not causal claims.", ""]
    for subject, item in correlations.items():
        lines.append(f"* {subject}: " + "; ".join(f"{key}={value}" for key, value in item.items()))
    lines += ["", "## Graph gates", "", "* All expected nodes are covered; no self-loops or duplicate final edges were found.", "* All edge weights are finite; no threshold or post-hoc collision filtering was applied.", "* Canonical and independent temporary graph generations were byte-identical.", "* Structural GO is evaluated with strict observed > random p95 using the preregistered 1000-repetition baseline.", "* The task stops before optimization.", ""]
    (REPORT_ROOT / "semantic_graph_quality_summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_artifact_hash_report(graph_results: dict[str, dict[str, Any]]) -> None:
    rows = []
    for subject in SUBJECTS:
        directory = STAGE3B_GRAPH_ROOT / subject
        for path in sorted(directory.iterdir()):
            if path.is_file():
                rows.append({"subject": subject, "relative_path": str(path.relative_to(ROOT)), "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    write_csv(REPORT_ROOT / "semantic_graph_artifact_hashes.csv", ["subject", "relative_path", "sha256", "size_bytes"], rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=STAGE3B_GRAPH_ROOT)
    parser.add_argument("--repro-output-root", type=Path, required=True)
    args = parser.parse_args()
    output_root = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
    repro_root = args.repro_output_root if args.repro_output_root.is_absolute() else ROOT / args.repro_output_root
    if output_root.resolve() != STAGE3B_GRAPH_ROOT.resolve():
        raise ValueError("validation must target the canonical Stage 3B graph root")
    _, graph_config_sha256 = graph_config()
    input_rows = verify_frozen_inputs()
    graph_results = {subject: validate_subject(subject, output_root) for subject in SUBJECTS}
    repro = compare_reproducibility(output_root, repro_root)
    if not all(row["passed"] == "true" for row in repro):
        raise RuntimeError(f"graph reproducibility failed: {repro}")
    contexts = {subject: load_diagnostic_context(subject, set(graph_results[subject]["nodes"])) for subject in SUBJECTS}
    random_summaries, overlap_context = write_structural_overlap_and_random(graph_results, contexts)
    shift_rows = load_shift_rows()
    comparison_rows, neighbour_rows = graph_comparison(graph_results, input_rows, shift_rows)
    empty_rows = empty_nonempty_diagnostics(neighbour_rows, shift_rows)
    _, correlations = evidence_diagnostics(graph_results, contexts, input_rows, neighbour_rows, shift_rows)
    collision_rows, collision_markdown = collision_diagnostics(graph_results, input_rows)
    (REPORT_ROOT / "xerces_collision_graph_audit.md").write_text(collision_markdown, encoding="utf-8")
    manual = manual_audit(graph_results, input_rows, neighbour_rows, contexts)
    (REPORT_ROOT / "semantic_graph_manual_audit.md").write_text(manual, encoding="utf-8")
    write_quality_reports(graph_results, random_summaries, overlap_context["overlap_rows"], comparison_rows, empty_rows, correlations)
    write_csv(REPORT_ROOT / "semantic_graph_reproducibility_per_subject.csv", list(repro[0]), repro)
    (REPORT_ROOT / "semantic_graph_reproducibility_summary.md").write_text(
        "\n".join([
            "# Stage 3B semantic graph reproducibility summary",
            "",
            "Canonical and independent temporary graph generations used the same frozen saved embeddings and Stage 3A graph-construction implementation.",
            "",
            "Directed neighbour files, final edge files, class mappings, graph metadata, artifact hashes, canonical graph hashes, and directed-selection hashes were byte-identical for all three subjects.",
            "",
            f"Canonical root: `{output_root.resolve()}`",
            f"Temporary root: `{repro_root.resolve()}`",
            "",
        ]),
        encoding="utf-8",
    )
    write_artifact_hash_report(graph_results)
    manifest_path = REPORT_ROOT / "semantic_graph_generation_manifest.json"
    manifest = read_json(manifest_path)
    manifest["validation_status"] = "passed"
    manifest["validated_at_utc"] = utc_now()
    manifest["graph_reproducibility_passed"] = True
    manifest["graph_config_sha256"] = graph_config_sha256
    manifest["reports"] = [
        "semantic_graph_quality_summary.md",
        "semantic_graph_quality_per_subject.csv",
        "semantic_graph_reproducibility_summary.md",
        "semantic_graph_reproducibility_per_subject.csv",
        "semantic_structural_overlap.csv",
        "semantic_graph_random_baseline.csv",
        "semantic_graph_random_baseline_summary.md",
        "semantic_graph_random_baseline_summary.csv",
        "semantic_graph_random_baseline_summary.csv",
        "semantic_reference_alignment.csv",
        "stage3a_vs_stage3b_graph_comparison.csv",
        "stage3a_vs_stage3b_neighbour_change.csv",
        "empty_vs_nonempty_body_graph_change.csv",
        "body_evidence_graph_change_diagnostics.csv",
        "xerces_collision_graph_audit.md",
        "xerces_collision_graph_edges.csv",
        "semantic_graph_manual_audit.md",
        "semantic_graph_artifact_hashes.csv",
    ]
    manifest["go_gate"] = {subject: random_summaries[subject]["go"] for subject in SUBJECTS}
    manifest["optimization_generated"] = False
    write_json(manifest_path, manifest)
    print(json.dumps({"validated": True, "subjects": list(SUBJECTS), "go_gate": manifest["go_gate"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
