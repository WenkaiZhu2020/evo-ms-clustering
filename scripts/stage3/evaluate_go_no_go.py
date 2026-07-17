#!/usr/bin/env python3
"""Evaluate the frozen Stage 3 semantic-graph technical and evidence gates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    from .build_semantic_graphs import ROOT, SUBJECTS, subject_embedding_dir, subject_graph_dir
except ImportError:  # pragma: no cover - direct script execution
    from build_semantic_graphs import ROOT, SUBJECTS, subject_embedding_dir, subject_graph_dir


RESULT_SUBJECT = {"jpetstore": "jpetstore", "daytrader": "daytrader", "xerces": "xerces-j"}
SCOPE_PATH = {subject: ROOT / "data/extracted" / RESULT_SUBJECT[subject] / "class_nodes.csv" for subject in SUBJECTS}
CONFIG_PATH = ROOT / "configs/experiments/04_stage3_semantic.yml"
MANIFEST_PATH = ROOT / "reports/stage3/formal_run_manifest.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def criterion(observed: Any, operator: str, expected: Any, passed: bool, evidence: str) -> dict[str, Any]:
    return {
        "observed": observed,
        "operator": operator,
        "expected": expected,
        "pass": bool(passed),
        "evidence_source": evidence,
    }


def evaluate_subject(subject: str, config: dict[str, Any], manifest: dict[str, Any], results_root: Path) -> dict[str, Any]:
    embedding_dir = subject_embedding_dir(subject, results_root)
    graph_dir = subject_graph_dir(subject, results_root)
    diagnostics_dir = results_root / subject / "04_stage3_semantic" / "diagnostics"
    metadata = json.loads((graph_dir / "graph_metadata.json").read_text(encoding="utf-8"))
    embedding_metadata = json.loads((embedding_dir / "embedding_metadata.json").read_text(encoding="utf-8"))
    class_rows = read_csv(embedding_dir / "class_ids.csv")
    scope_rows = read_csv(SCOPE_PATH[subject])
    graph_rows = read_csv(graph_dir / "semantic_edges.csv")
    manifest_graph = manifest["semantic_graph_hashes"][subject]
    expected_class_count = len(scope_rows)
    class_ids = {row["class_id"] for row in class_rows}
    scope_ids = {row["class_id"] for row in scope_rows}
    pairs = [(row["class_id_a"], row["class_id_b"]) for row in graph_rows]
    pair_set = set(pairs)
    no_self = all(left != right for left, right in pairs)
    no_duplicate = len(pair_set) == len(pairs)
    source_contract = (
        metadata.get("similarity_implementation") == "scripts/stage3/similarity.py"
        and metadata.get("source_embeddings_path", "").endswith("embeddings.npy")
        and metadata.get("source_class_ids_path", "").endswith("class_ids.csv")
        and metadata.get("duplicate_handling") == "none"
    )
    provenance_contract = source_contract and metadata.get("k") == 3 and metadata.get("symmetrisation") == "OR"
    technical = {
        "embedding_coverage": criterion(
            len(class_rows) / expected_class_count,
            "==",
            1.0,
            len(class_rows) == expected_class_count and class_ids == scope_ids,
            str((embedding_dir / "class_ids.csv").relative_to(ROOT)),
        ),
        "embedding_nan_count": criterion(
            embedding_metadata.get("nan_count"), "==", 0,
            embedding_metadata.get("nan_count") == 0,
            str((embedding_dir / "embedding_metadata.json").relative_to(ROOT)),
        ),
        "embedding_inf_count": criterion(
            embedding_metadata.get("inf_count"), "==", 0,
            embedding_metadata.get("inf_count") == 0,
            str((embedding_dir / "embedding_metadata.json").relative_to(ROOT)),
        ),
        "embedding_all_zero_vector_count": criterion(
            embedding_metadata.get("all_zero_vector_count"), "==", 0,
            embedding_metadata.get("all_zero_vector_count") == 0,
            str((embedding_dir / "embedding_metadata.json").relative_to(ROOT)),
        ),
        "semantic_graph_total_weight": criterion(
            metadata["total_edge_weight"], ">", 0.0,
            metadata["total_edge_weight"] > 0.0,
            str((graph_dir / "graph_metadata.json").relative_to(ROOT)),
        ),
        "node_coverage": criterion(
            float(json.loads((diagnostics_dir / "graph_structure.json").read_text())["node_coverage"])
            if (diagnostics_dir / "graph_structure.json").exists() else None,
            ">=", config["go_no_go"]["technical"]["node_coverage_minimum"],
            (diagnostics_dir / "graph_structure.json").exists() and float(json.loads((diagnostics_dir / "graph_structure.json").read_text())["node_coverage"]) >= config["go_no_go"]["technical"]["node_coverage_minimum"],
            str((diagnostics_dir / "graph_structure.json").relative_to(ROOT)),
        ),
        "isolated_node_ratio": criterion(
            float(json.loads((diagnostics_dir / "graph_structure.json").read_text())["isolated_node_ratio"]) if (diagnostics_dir / "graph_structure.json").exists() else None,
            "<=", config["go_no_go"]["technical"]["isolated_node_ratio_maximum"],
            (diagnostics_dir / "graph_structure.json").exists() and float(json.loads((diagnostics_dir / "graph_structure.json").read_text())["isolated_node_ratio"]) <= config["go_no_go"]["technical"]["isolated_node_ratio_maximum"],
            str((diagnostics_dir / "graph_structure.json").relative_to(ROOT)),
        ),
        "class_scope_exact_match": criterion(
            sorted(class_ids) == sorted(scope_ids), "==", True,
            class_ids == scope_ids, str((embedding_dir / "class_ids.csv").relative_to(ROOT)),
        ),
        "graph_source_embedding_hash_match": criterion(
            metadata["source_aggregate_embedding_sha256"], "==", manifest_graph["source_embedding_aggregate_sha256"],
            metadata["source_aggregate_embedding_sha256"] == manifest_graph["source_embedding_aggregate_sha256"],
            str((graph_dir / "graph_metadata.json").relative_to(ROOT)),
        ),
        "graph_construction_provenance_test": criterion(
            provenance_contract, "==", True, provenance_contract,
            "tests/test_stage3_semantic_graph.py",
        ),
        "graph_construction_excludes_diagnostic_and_structural_data": criterion(
            "embeddings.npy + class_ids.csv only", "==", "formal source contract", source_contract,
            str((graph_dir / "graph_metadata.json").relative_to(ROOT)),
        ),
        "no_self_loop_or_duplicate_semantic_edge": criterion(
            {"self_loops": int(not no_self), "duplicate_edges": len(pairs) - len(pair_set)},
            "==", {"self_loops": 0, "duplicate_edges": 0}, no_self and no_duplicate,
            str((graph_dir / "semantic_edges.csv").relative_to(ROOT)),
        ),
    }
    technical_pass = all(item["pass"] for item in technical.values())
    novelty = json.loads((diagnostics_dir / "novelty_alignment.json").read_text())
    random_summary = json.loads((diagnostics_dir / "random_baseline_summary.json").read_text())
    novelty_threshold = config["go_no_go"]["evidence"]["novel_edge_ratio_minimum_per_subject"]
    structural = random_summary["metrics"]["structural_overlap"]
    reference = random_summary["metrics"]["same_reference_service_ratio"]
    structural_pass = bool(structural["observed"] > structural["random_p95"])
    reference_pass = bool(reference["observed"] is not None and reference["random_p95"] is not None and reference["observed"] > reference["random_p95"])
    return {
        "technical_criteria": technical,
        "technical_pass": technical_pass,
        "novelty": {
            "observed": novelty["novel_edge_ratio"],
            "threshold": novelty_threshold,
            "operator": ">=",
            "pass": novelty["novel_edge_ratio"] >= novelty_threshold,
            "evidence_source": str((diagnostics_dir / "novelty_alignment.json").relative_to(ROOT)),
        },
        "random_baseline": {
            "baseline_code_path": random_summary["baseline_code_path"],
            "repetitions": random_summary["repetitions"],
            "structural_overlap_observed": structural["observed"],
            "structural_overlap_p50": structural["random_p50"],
            "structural_overlap_p95": structural["random_p95"],
            "structural_overlap_valid_random_values": structural["valid_random_value_count"],
            "structural_overlap_strict_gt_p95": structural_pass,
            "same_reference_observed": reference["observed"],
            "same_reference_p50": reference["random_p50"],
            "same_reference_p95": reference["random_p95"],
            "same_reference_valid_random_values": reference["valid_random_value_count"],
            "same_reference_strict_gt_p95": reference_pass,
            "pass": structural_pass or reference_pass,
            "evidence_source": str((diagnostics_dir / "random_baseline_summary.json").relative_to(ROOT)),
        },
    }


def evaluate(results_root: Path = ROOT / "results") -> dict[str, Any]:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    subjects = {subject: evaluate_subject(subject, config, manifest, results_root) for subject in SUBJECTS}
    novelty_pass = all(value["novelty"]["pass"] for value in subjects.values())
    random_pass_count = sum(value["random_baseline"]["pass"] for value in subjects.values())
    required_count = config["go_no_go"]["evidence"]["random_baseline"]["subjects_required_to_pass"]
    technical_pass = all(value["technical_pass"] for value in subjects.values())
    evidence_pass = novelty_pass and random_pass_count >= required_count
    status = "NO_GO_TECHNICAL" if not technical_pass else "NO_GO_EVIDENCE" if not evidence_pass else "GO"
    return {
        "schema_version": 1,
        "evaluated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "threshold_source": {"path": str(CONFIG_PATH.relative_to(ROOT)), "sha256": sha256_file(CONFIG_PATH)},
        "subjects": subjects,
        "cross_subject_evidence": {
            "all_subjects_novelty_pass": novelty_pass,
            "random_baseline_subject_pass_count": random_pass_count,
            "required_random_baseline_subject_pass_count": required_count,
            "pass": evidence_pass,
        },
        "overall_technical_pass": technical_pass,
        "overall_evidence_pass": evidence_pass,
        "overall_status": status,
        "same_leiden_cluster_ratio": "diagnostic_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, default=ROOT / "results")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/stage3/go_no_go_status.json")
    args = parser.parse_args()
    result = evaluate(args.results_root)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
