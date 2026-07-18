#!/usr/bin/env python3
"""Build isolated Stage 3B top-3 semantic graphs from frozen embeddings."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from evo_ms.semantic.graph import (  # noqa: E402
    build_graph_from_embeddings as frozen_build_graph_from_embeddings,
    canonical_weight,
)
from evo_ms.semantic.inference import EXPECTED_DIMENSION  # noqa: E402
from scripts.stage3_method_body.generate_embeddings import (  # noqa: E402
    canonical_class_mapping_hash,
    EXPECTED_INPUT_HASHES,
    read_csv,
    sha256_bytes,
    sha256_file,
)
from scripts.stage3_method_body.isolation import (  # noqa: E402
    EXPERIMENT_ID,
    REPRESENTATION_ID,
    STAGE3B_EMBEDDING_ROOT,
    STAGE3B_GRAPH_ROOT,
)


SUBJECTS = ("jpetstore", "daytrader", "xerces")
EXPECTED_COUNTS = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
EXPECTED_EMBEDDING_AGGREGATES = {
    "jpetstore": "e7615e77d4f3258df46e499fd94c2dbb59bee03c0d2f6c3bb822c3aff4577139",
    "daytrader": "db7ef8d78036796c5c5c79cc95f54eb1b9b9974de5e6f035d1929391b415f66c",
    "xerces": "36bdeca0e1ef32f36631c30ebbf86a1875621490e92f9b4a7fd0860755676236",
}
EXPECTED_MODEL = "nomic-ai/nomic-embed-code"
EXPECTED_REVISION = "9a0457648f060c4279d4a3982d2d27a4df6fac59"
EXPECTED_SOURCE_COMMIT = "33074fe5a2479b9d76605cd6a507c8a66c523a19"
EXPECTED_GRAPH_SOURCE_COMMIT = "6f595208e1bde1702b7a99f00410b35a225777c8"
TOP_K = 3
CONFIG_PATH = ROOT / "configs/experiments/05_stage3_declaration_method_body.yml"
FORMAL_MANIFEST_PATH = ROOT / "reports/stage3_method_body/semantic_graph_generation_manifest.json"
EMBEDDING_MANIFEST_PATH = ROOT / "reports/stage3_method_body/embedding_generation_manifest.json"
REPORT_ROOT = ROOT / "reports/stage3_method_body"
RAW_SUBJECT = {"jpetstore": "jpetstore", "daytrader": "daytrader", "xerces": "xerces-j"}
RAW_ROOT = ROOT / "data/extracted"
LEIDEN_ROOT = ROOT / "results"
REFERENCE_PATH = ROOT / "data/references/daytrader_reference_services.csv"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            output = dict(row)
            if "weight" in output:
                output["weight"] = canonical_weight(float(output["weight"]))
            writer.writerow(output)


def canonical_directed_payload(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        f"{row['source_class_id']}\t{row['rank']}\t{row['target_class_id']}\t"
        f"{canonical_weight(float(row['weight']))}\n"
        for row in rows
    ).encode("utf-8")


def canonical_graph_payload(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        f"{row['class_id_a']}\t{row['class_id_b']}\t"
        f"{canonical_weight(float(row['weight']))}\n"
        for row in rows
    ).encode("utf-8")


def graph_config() -> tuple[dict[str, Any], str]:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    graph = config["semantic_graph"]
    checks = {
        "k": TOP_K,
        "candidate_policy": "all_non_self_nodes",
        "similarity": "true_cosine",
        "similarity_implementation": "scripts/stage3_method_body/build_semantic_graphs.py",
        "ranking": {
            "primary": "cosine_descending",
            "exact_tie_break": "class_id_lexicographic_ascending",
        },
        "directed_selection_count_per_node": TOP_K,
        "symmetrisation": "OR",
        "self_loops": "forbidden",
        "duplicate_edges": "forbidden",
        "edge_weight": "true_cosine",
        "edge_weight_threshold": None,
    }
    for key, expected in checks.items():
        if graph.get(key) != expected:
            raise ValueError(f"final Stage 3 graph config mismatch for {key}: {graph.get(key)!r} != {expected!r}")
    if graph.get("diagnostic_files_as_input") != "forbidden":
        raise ValueError("diagnostic files must not be graph inputs")
    graph_manifest = read_json(FORMAL_MANIFEST_PATH)
    if graph_manifest.get("top_k") != TOP_K:
        raise ValueError("final graph manifest does not freeze top_k=3")
    return graph, sha256_file(CONFIG_PATH)


def assert_empty_output(root: Path, *, canonical: bool) -> None:
    resolved = root.resolve()
    expected = STAGE3B_GRAPH_ROOT.resolve()
    if canonical and resolved != expected:
        raise ValueError(f"canonical Stage 3B graph output must be {expected}, got {resolved}")
    if not canonical:
        if resolved.is_relative_to(ROOT):
            raise ValueError("graph reproducibility output must be outside the repository")
        if resolved == Path("/"):
            raise ValueError("refusing to use filesystem root as graph temporary output")
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"refusing to reuse non-empty graph output: {root}")
    root.mkdir(parents=True, exist_ok=True)


def _embedding_hash(vector: np.ndarray) -> str:
    return sha256_bytes(np.asarray(vector, dtype="<f4").tobytes())


def load_stage3b_inputs(subject: str) -> tuple[np.ndarray, list[dict[str, str]], dict[str, Any]]:
    if subject not in SUBJECTS:
        raise ValueError(f"unknown subject: {subject}")
    directory = STAGE3B_EMBEDDING_ROOT / subject
    paths = {
        "embeddings": directory / "embeddings.npy",
        "class_ids": directory / "class_ids.csv",
        "embedding_hashes": directory / "embedding_hashes.csv",
        "metadata": directory / "embedding_metadata.json",
    }
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    vectors = np.load(paths["embeddings"], allow_pickle=False)
    if vectors.dtype != np.dtype("<f4") or vectors.shape != (EXPECTED_COUNTS[subject], EXPECTED_DIMENSION):
        raise ValueError(f"{subject}: embedding shape/dtype mismatch: {vectors.shape}/{vectors.dtype}")
    if not np.isfinite(vectors).all() or np.any(np.all(vectors == 0, axis=1)):
        raise ValueError(f"{subject}: invalid embedding values")
    mapping = read_csv(paths["class_ids"])
    if len(mapping) != EXPECTED_COUNTS[subject]:
        raise ValueError(f"{subject}: class mapping count mismatch")
    if [int(row["row_index"]) for row in mapping] != list(range(len(mapping))):
        raise ValueError(f"{subject}: row mapping indexes are not contiguous")
    class_ids = [row["class_id"] for row in mapping]
    if class_ids != sorted(class_ids) or len(set(class_ids)) != len(class_ids):
        raise ValueError(f"{subject}: class mapping is not unique lexicographic order")
    embedding_hash_rows = read_csv(paths["embedding_hashes"])
    actual_hashes = [_embedding_hash(vector) for vector in vectors]
    if [row["class_id"] for row in embedding_hash_rows] != class_ids:
        raise ValueError(f"{subject}: embedding hash mapping mismatch")
    if [row["embedding_sha256"] for row in embedding_hash_rows] != actual_hashes:
        raise ValueError(f"{subject}: per-class embedding hash mismatch")
    aggregate_embedding = sha256_bytes(
        "".join(f"{row['class_id']}\t{row['embedding_sha256']}\n" for row in embedding_hash_rows).encode("utf-8")
    )
    metadata = read_json(paths["metadata"])
    embedding_manifest = read_json(EMBEDDING_MANIFEST_PATH)
    if embedding_manifest.get("validation_status") != "passed" or not embedding_manifest.get("embedding_reproducibility_passed"):
        raise ValueError("Stage 3B embedding manifest is not validated")
    if embedding_manifest.get("nearest_neighbors_generated") or embedding_manifest.get("semantic_graph_generated"):
        raise ValueError("Stage 3B embedding manifest incorrectly claims downstream artifacts")
    subject_manifest = embedding_manifest.get("subjects", {}).get(subject, {})
    expected_metadata = {
        "experiment_name": EXPERIMENT_ID,
        "representation_id": REPRESENTATION_ID,
        "subject": subject,
        "class_count": EXPECTED_COUNTS[subject],
        "input_aggregate_hash": EXPECTED_INPUT_HASHES[subject],
        "model_name": EXPECTED_MODEL,
        "model_revision": EXPECTED_REVISION,
        "tokenizer_revision": EXPECTED_REVISION,
        "backend": "sentence_transformers",
        "loader": "SentenceTransformer",
        "output_dimension": EXPECTED_DIMENSION,
        "pooling": "last_token",
        "normalization": "pinned_model_repository_l2",
        "prompt_name": None,
        "query_prompt_used": False,
        "max_sequence_length": 32768,
        "formal_truncation": False,
        "source_commit": embedding_manifest.get("source_commit"),
        "aggregate_embedding_sha256": aggregate_embedding,
        "embeddings_npy_sha256": sha256_file(paths["embeddings"]),
    }
    if embedding_manifest.get("source_commit") != EXPECTED_SOURCE_COMMIT:
        raise ValueError("embedding generation source commit differs from the frozen starting commit")
    for key, expected in expected_metadata.items():
        if metadata.get(key) != expected:
            raise ValueError(f"{subject}: embedding metadata {key}={metadata.get(key)!r}, expected {expected!r}")
    for key in ("input_aggregate_hash", "aggregate_embedding_sha256", "class_count", "output_dimension"):
        if subject_manifest.get(key) != metadata.get(key):
            raise ValueError(f"{subject}: embedding generation manifest {key} disagrees with subject metadata")
    if subject_manifest.get("source_commit") != EXPECTED_SOURCE_COMMIT:
        raise ValueError(f"{subject}: subject generation source commit mismatch")
    class_mapping_hash = canonical_class_mapping_hash(class_ids)
    if metadata.get("class_mapping_sha256") != class_mapping_hash:
        raise ValueError(f"{subject}: class mapping hash mismatch")
    return vectors, mapping, {
        "subject": subject,
        "embedding_path": paths["embeddings"],
        "embedding_sha256": sha256_file(paths["embeddings"]),
        "embedding_aggregate_sha256": aggregate_embedding,
        "class_mapping_sha256": class_mapping_hash,
        "input_aggregate_sha256": metadata["input_aggregate_hash"],
        "metadata": metadata,
        "source_commit": metadata["source_commit"],
    }


def write_subject_artifacts(
    subject: str,
    mapping: list[dict[str, str]],
    directed: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    source: dict[str, Any],
    graph_config_sha256: str,
    graph_source_commit: str,
    output_root: Path,
) -> dict[str, Any]:
    output_dir = output_root / subject
    output_dir.mkdir(parents=True, exist_ok=True)
    directed_path = output_dir / "directed_topk_neighbours.csv"
    edges_path = output_dir / "semantic_edges.csv"
    mapping_path = output_dir / "class_mapping.csv"
    metadata_path = output_dir / "graph_metadata.json"
    write_csv(directed_path, ["source_class_id", "rank", "target_class_id", "weight"], directed)
    write_csv(edges_path, ["class_id_a", "class_id_b", "weight", "selected_by"], edges)
    write_csv(mapping_path, ["row_index", "class_id", "class_name", "input_hash"], mapping)
    directed_hash = sha256_bytes(canonical_directed_payload(directed))
    graph_hash = sha256_bytes(canonical_graph_payload(edges))
    weights = np.asarray([float(row["weight"]) for row in edges], dtype=np.float64)
    metadata = {
        "schema_version": 1,
        "experiment_name": EXPERIMENT_ID,
        "representation_id": REPRESENTATION_ID,
        "subject": subject,
        "top_k": TOP_K,
        "candidate_policy": "all_non_self_nodes",
        "similarity": "true_cosine",
        "similarity_implementation": "scripts/stage3/similarity.py",
        "tie_break": "cosine_descending_then_class_id_lexicographic_ascending",
        "directed_neighbour_count_per_node": TOP_K,
        "symmetrisation": "OR",
        "reciprocal_edge_rule": "retain_one_edge; selected_by=both when reciprocal",
        "duplicate_edge_rule": "forbidden",
        "edge_weight_rule": "true_cosine; symmetric matrix value",
        "self_loop_rule": "forbidden",
        "zero_weight_rule": "retain if selected; no threshold",
        "node_count": len(mapping),
        "directed_selection_count": len(directed),
        "edge_count": len(edges),
        "minimum_edge_weight": float(weights.min()),
        "maximum_edge_weight": float(weights.max()),
        "negative_edge_count": int(np.sum(weights < 0)),
        "zero_edge_count": int(np.sum(weights == 0)),
        "embedding_path": str(source["embedding_path"].relative_to(ROOT)),
        "embedding_file_sha256": source["embedding_sha256"],
        "embedding_aggregate_sha256": source["embedding_aggregate_sha256"],
        "input_aggregate_sha256": source["input_aggregate_sha256"],
        "class_mapping_sha256": source["class_mapping_sha256"],
        "graph_config_sha256": graph_config_sha256,
        "canonical_weight_format": ".17g with numerical zero canonicalised as 0",
        "directed_topk_neighbours_sha256": sha256_file(directed_path),
        "semantic_edges_file_sha256": sha256_file(edges_path),
        "class_mapping_file_sha256": sha256_file(mapping_path),
        "directed_selection_sha256": directed_hash,
        "semantic_graph_sha256": graph_hash,
        "source_commit": graph_source_commit,
        "embedding_source_commit": source["source_commit"],
    }
    write_json(metadata_path, metadata)
    artifact_rows = []
    for path in sorted(output_dir.iterdir()):
        if path.name == "artifact_hashes.csv" or not path.is_file():
            continue
        artifact_rows.append({"relative_path": path.name, "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    write_csv(output_dir / "artifact_hashes.csv", ["relative_path", "sha256", "size_bytes"], artifact_rows)
    return {"subject": subject, "metadata": metadata, "output_dir": output_dir}


def source_diagnostic_provenance(subject: str) -> dict[str, Any]:
    raw_subject = RAW_SUBJECT[subject]
    class_nodes = RAW_ROOT / raw_subject / "class_nodes.csv"
    structural = RAW_ROOT / raw_subject / "structural_dependencies.csv"
    leiden = LEIDEN_ROOT / raw_subject / "01_stage1_leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv"
    result = {
        "structural_graph": {
            "class_nodes_path": str(class_nodes.relative_to(ROOT)),
            "class_nodes_sha256": sha256_file(class_nodes),
            "structural_dependencies_path": str(structural.relative_to(ROOT)),
            "structural_dependencies_sha256": sha256_file(structural),
        },
        "fixed_leiden_path": str(leiden.relative_to(ROOT)),
        "fixed_leiden_sha256": sha256_file(leiden),
        "reference_mapping_path": str(REFERENCE_PATH.relative_to(ROOT)) if subject == "daytrader" else None,
        "reference_mapping_sha256": sha256_file(REFERENCE_PATH) if subject == "daytrader" else None,
    }
    return result


def create_generation_manifest(
    results: dict[str, dict[str, Any]],
    repro_results: dict[str, dict[str, Any]],
    output_root: Path,
    repro_root: Path,
    graph_config_sha256: str,
    generation_command: str,
) -> None:
    manifest = {
        "schema_version": 1,
        "experiment_name": EXPERIMENT_ID,
        "representation_id": REPRESENTATION_ID,
        "source_commit": results["jpetstore"]["metadata"]["source_commit"],
        "generation_command": generation_command,
        "generation_timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "graph_config_path": str(CONFIG_PATH.relative_to(ROOT)),
        "graph_config_sha256": graph_config_sha256,
        "similarity": "true_cosine",
        "top_k": TOP_K,
        "tie_break": "cosine_descending_then_class_id_lexicographic_ascending",
        "symmetrisation": "OR",
        "reciprocal_edge_rule": "retain one undirected edge; mark both when reciprocal",
        "duplicate_edge_rule": "forbidden",
        "edge_weight_rule": "true_cosine; no threshold",
        "self_loop_rule": "forbidden",
        "serialization_precision": ".17g with numerical zero canonicalised as 0",
        "canonical_output_root": str(output_root.relative_to(ROOT)) if output_root.is_relative_to(ROOT) else str(output_root),
        "reproducibility_output_root": str(repro_root),
        "embedding_validation_status": "passed",
        "random_baseline": {
            "model": "uniform_simple_undirected_gnm",
            "repetitions": 1000,
            "subject_seed_bases": {"jpetstore": 42000, "daytrader": 52000, "xerces": 62000},
            "repetition_seed_rule": "subject_seed_base + repetition_index, index 0..999",
            "sampling": "uniformly select exactly m unordered pairs without replacement",
            "quantile": "numpy.quantile(method='higher')",
        },
        "subjects": {},
        "validation_status": "generated_pending_validation",
        "graphs_generated": True,
        "optimization_generated": False,
    }
    for subject in SUBJECTS:
        metadata = results[subject]["metadata"]
        manifest["subjects"][subject] = {
            "subject": subject,
            "representation_id": REPRESENTATION_ID,
            "embedding_path": metadata["embedding_path"],
            "embedding_sha256": metadata["embedding_file_sha256"],
            "embedding_aggregate_sha256": metadata["embedding_aggregate_sha256"],
            "input_aggregate_sha256": metadata["input_aggregate_sha256"],
            "class_mapping_sha256": metadata["class_mapping_sha256"],
            "node_count": metadata["node_count"],
            "embedding_dimension": EXPECTED_DIMENSION,
            "directed_neighbour_count": metadata["directed_selection_count"],
            "undirected_edge_count": metadata["edge_count"],
            "graph_hash": metadata["semantic_graph_sha256"],
            "directed_selection_hash": metadata["directed_selection_sha256"],
            "graph_output_paths": {
                "directed": str((STAGE3B_GRAPH_ROOT / subject / "directed_topk_neighbours.csv").relative_to(ROOT)),
                "edges": str((STAGE3B_GRAPH_ROOT / subject / "semantic_edges.csv").relative_to(ROOT)),
                "metadata": str((STAGE3B_GRAPH_ROOT / subject / "graph_metadata.json").relative_to(ROOT)),
                "mapping": str((STAGE3B_GRAPH_ROOT / subject / "class_mapping.csv").relative_to(ROOT)),
                "artifact_hashes": str((STAGE3B_GRAPH_ROOT / subject / "artifact_hashes.csv").relative_to(ROOT)),
            },
            "structural_graph_provenance": source_diagnostic_provenance(subject),
            "reproducibility_graph_hash": repro_results[subject]["metadata"]["semantic_graph_sha256"],
        }
    write_json(REPORT_ROOT / "semantic_graph_generation_manifest.json", manifest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=STAGE3B_GRAPH_ROOT)
    parser.add_argument("--repro-output-root", type=Path, required=True)
    args = parser.parse_args()
    output_root = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
    repro_root = args.repro_output_root if args.repro_output_root.is_absolute() else ROOT / args.repro_output_root
    assert_empty_output(output_root, canonical=True)
    assert_empty_output(repro_root, canonical=False)
    _, graph_config_sha256 = graph_config()
    graph_source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if graph_source_commit != EXPECTED_GRAPH_SOURCE_COMMIT:
        raise ValueError(f"graph generation must start at {EXPECTED_GRAPH_SOURCE_COMMIT}, got {graph_source_commit}")
    loaded = {subject: load_stage3b_inputs(subject) for subject in SUBJECTS}
    results: dict[str, dict[str, Any]] = {}
    repro_results: dict[str, dict[str, Any]] = {}
    for subject in SUBJECTS:
        vectors, mapping, source = loaded[subject]
        class_ids = [row["class_id"] for row in mapping]
        directed, edges = frozen_build_graph_from_embeddings(class_ids, vectors, TOP_K)
        results[subject] = write_subject_artifacts(subject, mapping, directed, edges, source, graph_config_sha256, graph_source_commit, output_root)
        repro_results[subject] = write_subject_artifacts(subject, mapping, directed, edges, source, graph_config_sha256, graph_source_commit, repro_root)
    create_generation_manifest(
        results,
        repro_results,
        output_root,
        repro_root,
        graph_config_sha256,
        "python scripts/stage3_method_body/build_semantic_graphs.py --repro-output-root <temporary-outside-repository>",
    )
    print(json.dumps({subject: result["metadata"] for subject, result in results.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
