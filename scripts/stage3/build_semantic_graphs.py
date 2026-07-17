#!/usr/bin/env python3
"""Build the frozen Stage 3 top-3 semantic graphs from saved embeddings."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import yaml

try:
    from .similarity import true_cosine_similarity
except ImportError:  # pragma: no cover - direct script execution
    from similarity import true_cosine_similarity


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs/experiments/04_stage3_semantic.yml"
MANIFEST_PATH = ROOT / "reports/stage3/formal_run_manifest.json"
SUBJECTS = {
    "jpetstore": 24,
    "daytrader": 53,
    "xerces": 814,
}
EXPECTED_EMBEDDING_HASHES = {
    "jpetstore": "0ae28938fef7b0c0295a5b1d33527708af7493b4f43d524436ffbf258db8802a",
    "daytrader": "c7d2cbeec9d4c6ff5f9054b7d66563e98cffc6774771d5727030248299b7756e",
    "xerces": "9504e21bb305a60cdfce58421b64240d1af893fd549b40b9441a00bf0fee8cb1",
}
EXPECTED_INPUT_HASHES = {
    "jpetstore": "1ecdb9083a37668fd07388454095a317268c8b736e6fd45957ab16bf87f6ad23",
    "daytrader": "ab09380f87119e4fe4621efbbdd8fdfd8cfc92cd383ed812169e2427a35eae44",
    "xerces": "f81d0f9bda5aa0fcdf3a35c75876cc73c8b419eccfb8c9e00634ec13fad4d60a",
}
DIMENSION = 3584


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_weight(weight: float) -> str:
    value = float(weight)
    if value == 0.0:
        return "0"
    return format(value, ".17g")


def canonical_directed_payload(rows: list[dict[str, object]]) -> bytes:
    return "".join(
        f"{row['source_class_id']}\t{row['rank']}\t{row['target_class_id']}\t"
        f"{canonical_weight(float(row['weight']))}\n"
        for row in rows
    ).encode("utf-8")


def canonical_graph_payload(rows: list[dict[str, object]]) -> bytes:
    return "".join(
        f"{row['class_id_a']}\t{row['class_id_b']}\t"
        f"{canonical_weight(float(row['weight']))}\n"
        for row in rows
    ).encode("utf-8")


def subject_embedding_dir(subject: str, output_root: Path = ROOT / "results") -> Path:
    return output_root / subject / "04_stage3_semantic" / "embeddings"


def subject_graph_dir(subject: str, output_root: Path = ROOT / "results") -> Path:
    return output_root / subject / "04_stage3_semantic" / "graph"


def load_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    graph = config["semantic_graph"]
    if graph["k"] != 3 or graph["similarity"] != "true_cosine":
        raise ValueError("semantic graph contract is not the frozen top-3 true-cosine rule")
    if graph["symmetrisation"] != "OR" or graph["self_loops"] != "forbidden":
        raise ValueError("semantic graph symmetrisation/self-loop contract mismatch")
    if graph["diagnostic_files_as_input"] != "forbidden":
        raise ValueError("diagnostic files must be forbidden as graph inputs")
    if manifest["semantic_graph"]["k"] != 3:
        raise ValueError("manifest semantic graph k does not equal 3")
    return config, manifest


def _embedding_hash(vector: np.ndarray) -> str:
    return sha256_bytes(np.asarray(vector, dtype="<f4").tobytes())


def load_embedding_inputs(subject: str, output_root: Path, manifest: dict[str, Any]) -> tuple[np.ndarray, list[dict[str, str]], dict[str, Any]]:
    if subject not in SUBJECTS:
        raise ValueError(f"unknown subject: {subject}")
    directory = subject_embedding_dir(subject, output_root)
    embeddings_path = directory / "embeddings.npy"
    class_ids_path = directory / "class_ids.csv"
    hashes_path = directory / "embedding_hashes.csv"
    metadata_path = directory / "embedding_metadata.json"
    for path in (embeddings_path, class_ids_path, hashes_path, metadata_path):
        if not path.exists():
            raise FileNotFoundError(path)

    vectors = np.load(embeddings_path, allow_pickle=False)
    if vectors.dtype != np.dtype("<f4") and vectors.dtype != np.dtype("float32"):
        raise ValueError(f"{subject}: saved dtype is {vectors.dtype}, expected float32")
    expected_count = SUBJECTS[subject]
    if vectors.shape != (expected_count, DIMENSION):
        raise ValueError(f"{subject}: shape {vectors.shape}, expected {(expected_count, DIMENSION)}")
    if not np.isfinite(vectors).all():
        raise ValueError(f"{subject}: embeddings contain non-finite values")
    if np.any(np.all(vectors == 0, axis=1)):
        raise ValueError(f"{subject}: embeddings contain an all-zero vector")

    with class_ids_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"row_index", "class_id", "class_name", "input_hash"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"{subject}: class_ids.csv schema is incomplete")
    if len(rows) != expected_count:
        raise ValueError(f"{subject}: class_ids row count {len(rows)} != {expected_count}")
    if [int(row["row_index"]) for row in rows] != list(range(expected_count)):
        raise ValueError(f"{subject}: row_index does not match embeddings.npy order")
    class_ids = [row["class_id"] for row in rows]
    if len(set(class_ids)) != len(class_ids) or class_ids != sorted(class_ids):
        raise ValueError(f"{subject}: class_ids are not unique and lexicographically sorted")
    input_payload = "".join(f"{row['class_id']}\t{row['input_hash']}\n" for row in rows).encode()
    expected_input = manifest["input_hashes"][subject]["aggregate_sha256"]
    if sha256_bytes(input_payload) != expected_input or expected_input != EXPECTED_INPUT_HASHES[subject]:
        raise ValueError(f"{subject}: input hash aggregate mismatch")

    with hashes_path.open(encoding="utf-8", newline="") as handle:
        hash_rows = list(csv.DictReader(handle))
    if [row["class_id"] for row in hash_rows] != class_ids:
        raise ValueError(f"{subject}: embedding hash class order mismatch")
    actual_vector_hashes = [_embedding_hash(vector) for vector in vectors]
    if [row["embedding_sha256"] for row in hash_rows] != actual_vector_hashes:
        raise ValueError(f"{subject}: per-class embedding hash mismatch")
    aggregate_embedding = sha256_bytes(
        "".join(f"{row['class_id']}\t{row['embedding_sha256']}\n" for row in hash_rows).encode()
    )
    expected_embedding = manifest["embedding_hashes"][subject]["aggregate_sha256"]
    if aggregate_embedding != expected_embedding or expected_embedding != EXPECTED_EMBEDDING_HASHES[subject]:
        raise ValueError(f"{subject}: aggregate embedding hash mismatch")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("aggregate_embedding_sha256") != aggregate_embedding:
        raise ValueError(f"{subject}: embedding metadata aggregate mismatch")
    if metadata.get("embeddings_npy_sha256") != sha256_file(embeddings_path):
        raise ValueError(f"{subject}: embedding metadata file hash mismatch")
    return vectors, rows, {
        "embeddings_path": embeddings_path,
        "class_ids_path": class_ids_path,
        "hashes_path": hashes_path,
        "metadata_path": metadata_path,
        "embedding_metadata": metadata,
        "source_embedding_aggregate_sha256": aggregate_embedding,
    }


def select_directed_top3(class_ids: list[str], similarity: np.ndarray, k: int = 3) -> list[dict[str, object]]:
    n = len(class_ids)
    if similarity.shape != (n, n):
        raise ValueError("similarity matrix shape does not match class_ids")
    if n <= k:
        raise ValueError("formal graph requires more nodes than k")
    rows: list[dict[str, object]] = []
    for source_index, source_id in enumerate(class_ids):
        candidates = [
            (float(similarity[source_index, target_index]), class_ids[target_index])
            for target_index in range(n)
            if target_index != source_index
        ]
        candidates.sort(key=lambda item: (-item[0], item[1]))
        for rank, (weight, target_id) in enumerate(candidates[:k], start=1):
            rows.append(
                {
                    "source_class_id": source_id,
                    "rank": rank,
                    "target_class_id": target_id,
                    "weight": weight,
                }
            )
    return rows


def symmetrise_or(class_ids: list[str], directed_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    index = {class_id: i for i, class_id in enumerate(class_ids)}
    selected = {(str(row["source_class_id"]), str(row["target_class_id"])) for row in directed_rows}
    weights = {(str(row["source_class_id"]), str(row["target_class_id"])): float(row["weight"]) for row in directed_rows}
    pairs = set()
    for source, target in selected:
        a, b = sorted((source, target))
        pairs.add((a, b))
    result: list[dict[str, object]] = []
    for a, b in sorted(pairs):
        a_to_b = (a, b) in selected
        b_to_a = (b, a) in selected
        if a_to_b and b_to_a:
            selected_by = "both"
        elif a_to_b:
            selected_by = "a"
        else:
            selected_by = "b"
        # Use the matrix-derived weight. The directed values are symmetric by construction,
        # and this assertion catches accidental use of a diagnostic edge value.
        weight_a = weights.get((a, b), weights.get((b, a)))
        weight_b = weights.get((b, a), weights.get((a, b)))
        if weight_a is None or weight_b is None or not np.isclose(weight_a, weight_b, atol=1e-12):
            raise ValueError(f"inconsistent symmetric edge weight for {a}, {b}")
        if a not in index or b not in index:
            raise ValueError("semantic edge endpoint is outside formal class scope")
        result.append({"class_id_a": a, "class_id_b": b, "weight": float(weight_a), "selected_by": selected_by})
    return result


def build_graph_from_embeddings(class_ids: list[str], embeddings: np.ndarray, k: int = 3) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Build directed top-k and OR-symmetrised rows from saved vectors."""
    matrix = true_cosine_similarity(embeddings)
    if matrix.shape != (len(class_ids), len(class_ids)) or not np.isfinite(matrix).all():
        raise ValueError("invalid true-cosine matrix")
    if not np.allclose(matrix, matrix.T, atol=1e-12) or not np.allclose(np.diag(matrix), 1.0, atol=1e-12):
        raise ValueError("true-cosine matrix symmetry/diagonal check failed")
    if matrix.min() < -1.0 or matrix.max() > 1.0:
        raise ValueError("true-cosine values outside [-1, 1]")
    directed = select_directed_top3(class_ids, matrix, k)
    return directed, symmetrise_or(class_ids, directed)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            output = dict(row)
            if "weight" in output:
                output["weight"] = canonical_weight(float(output["weight"]))
            writer.writerow(output)


def current_git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def build_subject(
    subject: str,
    output_root: Path = ROOT / "results",
    git_commit: str | None = None,
    source_root: Path | None = None,
) -> dict[str, Any]:
    _, manifest = load_contract()
    vectors, class_rows, source = load_embedding_inputs(subject, source_root or output_root, manifest)
    class_ids = [row["class_id"] for row in class_rows]
    directed, edges = build_graph_from_embeddings(class_ids, vectors, 3)
    graph_dir = subject_graph_dir(subject, output_root)
    directed_path = graph_dir / "directed_top3.csv"
    edges_path = graph_dir / "semantic_edges.csv"
    write_csv(directed_path, ["source_class_id", "rank", "target_class_id", "weight"], directed)
    write_csv(edges_path, ["class_id_a", "class_id_b", "weight", "selected_by"], edges)
    directed_hash = sha256_bytes(canonical_directed_payload(directed))
    graph_hash = sha256_bytes(canonical_graph_payload(edges))
    weights = np.asarray([float(row["weight"]) for row in edges], dtype=float)
    metadata = {
        "schema_version": 1,
        "subject": subject,
        "k": 3,
        "candidate_policy": "all_non_self_nodes",
        "similarity": "true_cosine",
        "similarity_implementation": "scripts/stage3/similarity.py",
        "tie_break": "cosine_descending_then_class_id_lexicographic_ascending",
        "symmetrisation": "OR",
        "self_loops": "forbidden",
        "duplicate_handling": "none",
        "node_count": len(class_ids),
        "directed_selection_count": len(directed),
        "edge_count": len(edges),
        "minimum_possible_or_edge_count": int(np.ceil(len(class_ids) * 3 / 2)),
        "maximum_possible_or_edge_count": len(class_ids) * 3,
        "total_edge_weight": float(weights.sum()),
        "minimum_edge_weight": float(weights.min()),
        "maximum_edge_weight": float(weights.max()),
        "negative_edge_count": int(np.sum(weights < 0)),
        "zero_edge_count": int(np.sum(weights == 0)),
        "source_embeddings_path": str(source["embeddings_path"].relative_to(ROOT)),
        "source_embeddings_file_sha256": sha256_file(source["embeddings_path"]),
        "source_class_ids_path": str(source["class_ids_path"].relative_to(ROOT)),
        "source_class_ids_file_sha256": sha256_file(source["class_ids_path"]),
        "source_aggregate_embedding_sha256": source["source_embedding_aggregate_sha256"],
        "canonical_weight_format": ".17g with numerical zero canonicalised as 0",
        "directed_top3_file_sha256": sha256_file(directed_path),
        "semantic_edges_file_sha256": sha256_file(edges_path),
        "directed_selection_sha256": directed_hash,
        "semantic_graph_sha256": graph_hash,
        "construction_git_commit": git_commit or current_git_commit(),
        "creation_timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    metadata_path = graph_dir / "graph_metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {"subject": subject, "directed": directed, "edges": edges, "metadata": metadata}


def update_manifest(results: dict[str, dict[str, Any]]) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for subject, result in results.items():
        metadata = result["metadata"]
        manifest["semantic_graph_hashes"][subject] = {
            "aggregate_sha256": metadata["semantic_graph_sha256"],
            "directed_selection_sha256": metadata["directed_selection_sha256"],
            "node_count": metadata["node_count"],
            "edge_count": metadata["edge_count"],
            "k": metadata["k"],
            "symmetrisation": metadata["symmetrisation"],
            "metadata_path": f"results/{subject}/04_stage3_semantic/graph/graph_metadata.json",
            "source_embedding_aggregate_sha256": metadata["source_aggregate_embedding_sha256"],
            "generated_at_utc": metadata["creation_timestamp_utc"],
        }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subjects", nargs="*", default=list(SUBJECTS))
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    parser.add_argument("--no-manifest", action="store_true")
    args = parser.parse_args()
    results = {subject: build_subject(subject, args.output_root) for subject in args.subjects}
    if not args.no_manifest and args.output_root.resolve() == (ROOT / "results").resolve():
        update_manifest(results)
    print(json.dumps({subject: value["metadata"] for subject, value in results.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
