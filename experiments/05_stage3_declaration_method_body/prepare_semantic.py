#!/usr/bin/env python3
"""Generate isolated embeddings for the final Stage 3 representation."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
import platform
from pathlib import Path
import shlex
import subprocess
import sys
import time
from collections.abc import Mapping
from typing import Any

import numpy as np
import torch
import yaml
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.semantic.inference import (  # noqa: E402
    EXPECTED_DIMENSION,
    EXPECTED_MODEL,
    MAX_SEQUENCE_LENGTH,
    MODEL_REVISION,
    SEED,
    clear_model,
    dtype_from_name,
    encode_texts,
    load_model,
    validate_vectors,
    vector_hash,
)
from evo_ms.semantic.graph import build_graph_from_embeddings  # noqa: E402
from evo_ms.analysis.provenance import graph_compatibility_digest  # noqa: E402
from evo_ms.analysis.provenance import normalized_graph_compatibility_contract  # noqa: E402
from evo_ms.semantic.input_contract import aggregate_input_hash  # noqa: E402
from evo_ms.semantic.input_contract import canonical_text_hash  # noqa: E402
from evo_ms.semantic.method_body import MethodBody  # noqa: E402
from evo_ms.semantic.method_body import compose_semantic_text  # noqa: E402
from evo_ms.semantic.method_body import extract_declaration_section  # noqa: E402
from evo_ms.semantic.method_body import normalize_class_bodies  # noqa: E402


SUBJECTS = ("jpetstore", "daytrader", "xerces")
EXPECTED_COUNTS = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
EXPECTED_INPUT_HASHES = {
    "jpetstore": "2d9007f75a14f4a4ed6152563241b898837b6c12b66a98a2464b4cc3f969a921",
    "daytrader": "da53d434b820e3c25bc69df63ced807cd0113d412fa36acc9694d1a97631d655",
    "xerces": "65488944220cc3a503994d6f2289e0f7bdc06c619351a2e8243bca243538c8a3",
}
INPUT_ROOT = ROOT / "data/semantic_text/declaration_method_body"
OUTPUT_ROOT = ROOT / "data/embeddings/declaration_method_body"
REPORT_ROOT = ROOT / "results/cross_subject/05_stage3_declaration_method_body/provenance"
INPUT_PROVENANCE_ROOT = REPORT_ROOT / "inputs"
FORMAL_CONFIG = ROOT / "configs/experiments/05_stage3_declaration_method_body.yml"
MAX_NORM_TOLERANCE = (0.999, 1.001)
EXPERIMENT_ID = "stage3_declaration_method_body"
REPRESENTATION_ID = "declaration_method_body_v1"
GRAPH_ROOT = ROOT / "data/semantic_graphs/declaration_method_body"
EXTRACTOR_SUBJECT = {"jpetstore": "jpetstore", "daytrader": "daytrader", "xerces": "xerces-j"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(payload)


def canonical_class_mapping_hash(class_ids: list[str]) -> str:
    return sha256_bytes("".join(f"{class_id}\n" for class_id in sorted(class_ids)).encode("utf-8"))


def canonical_input_hash(rows: list[dict[str, str]]) -> str:
    payload = "".join(
        f"{row['class_id']}\t{row['input_hash']}\n"
        for row in sorted(rows, key=lambda row: row["class_id"])
    )
    return sha256_bytes(payload.encode("utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def source_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def verify_frozen_inputs(input_root: Path = INPUT_ROOT) -> dict[str, list[dict[str, str]]]:
    """Verify Stage 3B input rows and both independent aggregate-hash records."""
    global_manifest = json.loads((INPUT_PROVENANCE_ROOT / "method_body_input_manifest.json").read_text(encoding="utf-8"))
    hash_rows = read_csv(INPUT_PROVENANCE_ROOT / "method_body_input_hashes.csv")
    rows_by_subject: dict[str, list[dict[str, str]]] = {}
    for subject in SUBJECTS:
        path = input_root / subject / "class_semantic_inputs.csv"
        rows = read_csv(path)
        if len(rows) != EXPECTED_COUNTS[subject]:
            raise ValueError(f"{subject}: expected {EXPECTED_COUNTS[subject]} input rows, got {len(rows)}")
        if len({row["class_id"] for row in rows}) != len(rows):
            raise ValueError(f"{subject}: duplicate input class_id")
        rows = sorted(rows, key=lambda row: row["class_id"])
        if any(row.get("representation_id") != REPRESENTATION_ID for row in rows):
            raise ValueError(f"{subject}: representation_id mismatch")
        for row in rows:
            if sha256_bytes(row["semantic_text"].encode("utf-8")) != row["input_hash"]:
                raise ValueError(f"{subject}/{row['class_id']}: semantic_text hash mismatch")
        actual = canonical_input_hash(rows)
        report_rows = sorted(
            [row for row in hash_rows if row["subject"] == subject],
            key=lambda row: row["class_id"],
        )
        if [(row["class_id"], row["input_hash"]) for row in report_rows] != [
            (row["class_id"], row["input_hash"]) for row in rows
        ]:
            raise ValueError(f"{subject}: method_body_input_hashes.csv does not match semantic inputs")
        if actual != EXPECTED_INPUT_HASHES[subject]:
            raise ValueError(f"{subject}: aggregate input hash {actual} != frozen {EXPECTED_INPUT_HASHES[subject]}")
        if global_manifest["aggregate_input_sha256"].get(subject) != actual:
            raise ValueError(f"{subject}: method input manifest aggregate hash mismatch")
        subject_manifest = json.loads((path.parent / "manifest.json").read_text(encoding="utf-8"))
        mapping = canonical_class_mapping_hash([row["class_id"] for row in rows])
        if subject_manifest.get("class_mapping_sha256") != mapping:
            raise ValueError(f"{subject}: class mapping hash mismatch")
        if subject_manifest.get("aggregate_input_sha256") != actual:
            raise ValueError(f"{subject}: subject manifest aggregate hash mismatch")
        rows_by_subject[subject] = rows
    return rows_by_subject


def load_frozen_runtime() -> tuple[dict[str, Any], dict[str, Any], Any]:
    config = yaml.safe_load(FORMAL_CONFIG.read_text(encoding="utf-8"))
    runtime_config = dict(config["embedding_runtime"])
    expected = {
        "device": "mps",
        "dtype": "float16",
        "batch_size": 8,
        "runtime_frozen": True,
    }
    for key, value in expected.items():
        if runtime_config.get(key) != value:
            raise ValueError(f"final Stage 3 runtime {key}={runtime_config.get(key)!r}, expected {value!r}")
    if not torch.backends.mps.is_available():
        raise RuntimeError("final Stage 3 runtime requires MPS, but MPS is unavailable")
    runtime = {
        "device": runtime_config["device"],
        "device_name": runtime_config["device_name"],
        "dtype": runtime_config["dtype"],
        "batch_size": int(runtime_config["batch_size"]),
        "storage_dtype": "float32",
        "prompt_name": None,
        "prompt": None,
        "normalize_embeddings": False,
        "precision": "float32",
        "convert_to_numpy": True,
        "convert_to_tensor": False,
        "formal_truncation": False,
        "inference_mode": True,
        "model_eval": True,
    }
    identity = {
        "model_name": EXPECTED_MODEL,
        "model_revision": MODEL_REVISION,
        "tokenizer_revision": MODEL_REVISION,
        "backend": "sentence_transformers",
        "loader": "SentenceTransformer",
        "representation_id": REPRESENTATION_ID,
        "experiment_name": EXPERIMENT_ID,
        "output_dimension": EXPECTED_DIMENSION,
        "max_sequence_length": MAX_SEQUENCE_LENGTH,
        "pooling": "last_token",
        "normalization": "pinned_model_repository_l2",
        **runtime,
    }
    identity["inference_config_sha256"] = canonical_json_hash(identity)
    tokenizer = AutoTokenizer.from_pretrained(
        EXPECTED_MODEL,
        revision=MODEL_REVISION,
        use_fast=True,
        trust_remote_code=False,
    )
    if int(tokenizer.model_max_length) != MAX_SEQUENCE_LENGTH:
        raise RuntimeError(f"pinned tokenizer max length {tokenizer.model_max_length} != {MAX_SEQUENCE_LENGTH}")
    return runtime, identity, tokenizer


def token_count(tokenizer: Any, text: str) -> int:
    encoded = tokenizer(text, truncation=False, add_special_tokens=True, return_attention_mask=False)
    return len(encoded["input_ids"])


def body_section(text: str) -> str:
    marker = "[METHOD_BODY]\n"
    if marker not in text:
        raise ValueError("Stage 3B semantic_text is missing METHOD_BODY section")
    return text.split(marker, 1)[1].rstrip("\n")


def token_length_rows(subject: str, rows: list[dict[str, str]], tokenizer: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        declaration = extract_declaration_section(row["semantic_text"])
        body = body_section(row["semantic_text"])
        count = token_count(tokenizer, row["semantic_text"])
        max_length = MAX_SEQUENCE_LENGTH
        unexpected = count > max_length
        result.append({
            "subject": subject,
            "class_id": row["class_id"],
            "model_token_count": count,
            "model_max_sequence_length": max_length,
            "tokenizer_truncated": str(unexpected).lower(),
            "declaration_token_count": token_count(tokenizer, declaration),
            "body_section_token_count": token_count(tokenizer, body),
            "contract_body_tokens_truncated": row["body_tokens_truncated"],
            "declaration_section_affected": "false",
            "body_section_affected": "true" if int(row["body_tokens_truncated"]) > 0 else "false",
        })
    return result


def assert_empty_output(root: Path, *, canonical: bool) -> None:
    resolved = root.resolve()
    expected = OUTPUT_ROOT.resolve()
    if canonical and resolved != expected:
        raise ValueError(f"canonical Stage 3B output must be {expected}, got {resolved}")
    if not canonical:
        if resolved.is_relative_to(ROOT):
            raise ValueError("reproducibility output must be outside the repository")
        if resolved == Path("/"):
            raise ValueError("refusing to use filesystem root as temporary output")
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"refusing to reuse non-empty Stage 3B embedding output: {root}")
    root.mkdir(parents=True, exist_ok=True)


def generate_once(
    model: Any,
    rows_by_subject: dict[str, list[dict[str, str]]],
    runtime: dict[str, Any],
    identity: dict[str, Any],
    tokenizer: Any,
    output_root: Path,
    run_label: str,
) -> dict[str, Any]:
    records: dict[str, Any] = {}
    commit = source_commit()
    for subject in SUBJECTS:
        rows = rows_by_subject[subject]
        lengths = token_length_rows(subject, rows, tokenizer)
        unexpected = [row for row in lengths if row["tokenizer_truncated"] == "true"]
        if unexpected:
            raise RuntimeError(f"{subject}: unexpected tokenizer-level truncation: {unexpected[:3]}")
        directory = output_root / subject
        directory.mkdir(parents=True, exist_ok=True)
        texts = [row["semantic_text"] for row in rows]
        started = time.perf_counter()
        vectors = encode_texts(model, texts, runtime["batch_size"])
        elapsed = time.perf_counter() - started
        vector_stats = validate_vectors(vectors)
        np.save(directory / "embeddings.npy", vectors)
        mapping_rows = [
            {
                "row_index": index,
                "class_id": row["class_id"],
                "class_name": row["class_name"],
                "input_hash": row["input_hash"],
            }
            for index, row in enumerate(rows)
        ]
        write_csv(directory / "class_ids.csv", ["row_index", "class_id", "class_name", "input_hash"], mapping_rows)
        hash_rows = [
            {"class_id": row["class_id"], "input_hash": row["input_hash"], "embedding_sha256": vector_hash(vector)}
            for row, vector in zip(rows, vectors)
        ]
        write_csv(directory / "embedding_hashes.csv", ["class_id", "input_hash", "embedding_sha256"], hash_rows)
        aggregate_embedding = sha256_bytes(
            "".join(f"{row['class_id']}\t{row['embedding_sha256']}\n" for row in hash_rows).encode("utf-8")
        )
        metadata = {
            "schema_version": 1,
            "experiment_name": EXPERIMENT_ID,
            "representation_id": REPRESENTATION_ID,
            "subject": subject,
            "class_count": len(rows),
            "input_root": str(INPUT_ROOT.relative_to(ROOT)),
            "input_aggregate_hash": EXPECTED_INPUT_HASHES[subject],
            "class_mapping_sha256": canonical_class_mapping_hash([row["class_id"] for row in rows]),
            "model_name": EXPECTED_MODEL,
            "model_revision": MODEL_REVISION,
            "tokenizer_revision": MODEL_REVISION,
            "backend": "sentence_transformers",
            "loader": "SentenceTransformer",
            "pooling": "last_token",
            "normalization": "pinned_model_repository_l2",
            "prompt_name": None,
            "query_prompt_used": False,
            "max_sequence_length": MAX_SEQUENCE_LENGTH,
            "formal_truncation": False,
            "device": runtime["device"],
            "device_name": runtime["device_name"],
            "runtime_dtype": runtime["dtype"],
            "saved_storage_dtype": "float32",
            "batch_size": runtime["batch_size"],
            "output_dimension": EXPECTED_DIMENSION,
            "random_seed": SEED,
            "python_version": platform.python_version(),
            "torch_version": torch.__version__,
            "transformers_version": __import__("transformers").__version__,
            "sentence_transformers_version": __import__("sentence_transformers").__version__,
            "numpy_version": np.__version__,
            "scipy_version": __import__("scipy").__version__,
            "inference_config_sha256": identity["inference_config_sha256"],
            "exact_encode_arguments": {
                "prompt_name": None,
                "prompt": None,
                "normalize_embeddings": False,
                "precision": "float32",
                "convert_to_numpy": True,
                "convert_to_tensor": False,
                "truncation": False,
            },
            "embedding_output_path": str(directory.resolve()),
            "generation_run": run_label,
            "creation_timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "encoding_elapsed_seconds": elapsed,
            "tokenizer_truncated_count": 0,
            "contract_body_truncated_count": sum(int(row["body_tokens_truncated"]) > 0 for row in rows),
            "token_count_minimum": min(row["model_token_count"] for row in lengths),
            "token_count_maximum": max(row["model_token_count"] for row in lengths),
            "token_count_mean": float(np.mean([row["model_token_count"] for row in lengths])),
            "embeddings_npy_sha256": sha256_file(directory / "embeddings.npy"),
            "class_ids_csv_sha256": sha256_file(directory / "class_ids.csv"),
            "embedding_hashes_csv_sha256": sha256_file(directory / "embedding_hashes.csv"),
            "aggregate_embedding_sha256": aggregate_embedding,
            "source_commit": commit,
            **vector_stats,
        }
        write_csv(directory / "token_lengths.csv", list(lengths[0]), lengths)
        metadata["token_lengths_csv_sha256"] = sha256_file(directory / "token_lengths.csv")
        write_json(directory / "embedding_metadata.json", metadata)
        records[subject] = metadata
    return records


def _canonical_graph_hash(rows: list[dict[str, Any]]) -> str:
    payload = "".join(
        f"{row['class_id_a']}\t{row['class_id_b']}\t{format(float(row['weight']), '.17g') if float(row['weight']) != 0.0 else '0'}\n"
        for row in rows
    ).encode("utf-8")
    return sha256_bytes(payload)


def build_graph_once(
    subject: str,
    *,
    embedding_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Build one isolated top-3 graph from already-saved embeddings."""
    if subject not in SUBJECTS:
        raise ValueError(f"unknown subject: {subject}")
    output = output_root / subject
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite graph output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    embedding_dir = embedding_root / subject
    mapping = read_csv(embedding_dir / "class_ids.csv")
    class_ids = [row["class_id"] for row in sorted(mapping, key=lambda row: int(row["row_index"]))]
    vectors = np.load(embedding_dir / "embeddings.npy", allow_pickle=False)
    directed, edges = build_graph_from_embeddings(class_ids, vectors, k=3)
    with (output / "directed_topk_neighbours.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_class_id", "rank", "target_class_id", "weight"],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in directed:
            writer.writerow({**row, "weight": format(float(row["weight"]), ".17g")})
    with (output / "semantic_edges.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["class_id_a", "class_id_b", "weight", "selected_by"],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in edges:
            writer.writerow({**row, "weight": format(float(row["weight"]), ".17g")})
    graph_hash = _canonical_graph_hash(edges)
    embedding_metadata = json.loads((embedding_dir / "embedding_metadata.json").read_text(encoding="utf-8"))
    graph_config = yaml.safe_load((ROOT / "configs/experiments/05_stage3_declaration_method_body.yml").read_text(encoding="utf-8"))
    graph_settings = graph_config["semantic_graph"]
    contract_values = {
        "contract_version": 1,
        "experiment_name": EXPERIMENT_ID,
        "representation_id": REPRESENTATION_ID,
        "class_scope_digest": canonical_class_mapping_hash(class_ids),
        "semantic_input_aggregate_sha256": embedding_metadata["input_aggregate_hash"],
        "embedding_aggregate_sha256": embedding_metadata["aggregate_embedding_sha256"],
        "model_name": embedding_metadata["model_name"],
        "model_revision": embedding_metadata["model_revision"],
        "tokenizer_name": embedding_metadata["model_name"],
        "tokenizer_revision": embedding_metadata["tokenizer_revision"],
        "tokenizer_max_sequence_length": embedding_metadata["max_sequence_length"],
        "tokenizer_truncation": embedding_metadata["formal_truncation"],
        "pooling": embedding_metadata["pooling"],
        "pooling_source": "pinned_model_repository",
        "l2_normalize": True,
        "storage_dtype": embedding_metadata["saved_storage_dtype"],
        "similarity": graph_settings["similarity"],
        "similarity_implementation": graph_settings["similarity_implementation"],
        "top_k": graph_settings["k"],
        "directed_selection_count_per_node": graph_settings["directed_selection_count_per_node"],
        "candidate_policy": graph_settings["candidate_policy"],
        "tie_break": "cosine_descending_then_class_id_lexicographic_ascending",
        "symmetrisation": graph_settings["symmetrisation"],
        "reciprocal_edge_policy": "retain_one_edge; selected_by=both when reciprocal",
        "self_loop_policy": graph_settings["self_loops"],
        "duplicate_edge_policy": graph_settings["duplicate_edges"],
        "edge_weight_rule": graph_settings["edge_weight"],
        "edge_weight_threshold": graph_settings["edge_weight_threshold"],
        "edge_serialization_precision": ".17g with numerical zero canonicalised as 0",
    }
    contract = normalized_graph_compatibility_contract(contract_values)
    metadata = {
        "schema_version": 1,
        "experiment_name": EXPERIMENT_ID,
        "representation_id": REPRESENTATION_ID,
        "subject": subject,
        "node_count": len(class_ids),
        "top_k": 3,
        "directed_selection_count": 3,
        "similarity": "true_cosine",
        "similarity_implementation": "evo_ms.semantic.graph.true_cosine_similarity",
        "tie_break": "cosine_descending_then_class_id_lexicographic_ascending",
        "symmetrisation": "OR",
        "self_loop_rule": "forbidden",
        "duplicate_edge_rule": "forbidden",
        "semantic_graph_sha256": graph_hash,
        "embedding_path": str((embedding_root / subject / "embeddings.npy").relative_to(ROOT))
        if embedding_root.resolve().is_relative_to(ROOT.resolve())
        else str((embedding_root / subject / "embeddings.npy").resolve()),
        "class_mapping_sha256": canonical_class_mapping_hash(class_ids),
        "source_commit": source_commit(),
        "compatibility_contract": contract,
        "compatibility_contract_sha256": graph_compatibility_digest(contract),
    }
    write_csv(output / "class_mapping.csv", ["row_index", "class_id", "class_name", "input_hash"], mapping)
    write_json(output / "graph_metadata.json", metadata)
    return metadata


def build_graphs(
    *,
    subjects: tuple[str, ...] = SUBJECTS,
    embedding_root: Path = OUTPUT_ROOT,
    output_root: Path = GRAPH_ROOT,
) -> dict[str, Any]:
    """Build isolated graph artifacts from saved embedding arrays."""
    return {
        subject: build_graph_once(
            subject,
            embedding_root=embedding_root,
            output_root=output_root,
        )
        for subject in subjects
    }


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _subject_project_root(subject: str, source_root: Path) -> Path:
    configured_name = Path(str(_load_subject_config(subject)["project_root"])).name
    candidate = source_root / configured_name
    if candidate.is_dir():
        return candidate
    if source_root.is_dir():
        return source_root
    raise FileNotFoundError(f"source root does not exist: {source_root}")


def _load_subject_config(subject: str) -> dict[str, Any]:
    extractor_subject = EXTRACTOR_SUBJECT[subject]
    path = ROOT / "configs/subjects" / f"{extractor_subject}.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _source_paths(subject: str, source_root: Path) -> tuple[Path, Path, str, list[str], list[str]]:
    config = _load_subject_config(subject)
    project_root = _subject_project_root(subject, source_root)
    classes_dir = project_root / str(config["classes_dir"])
    classpath = os.pathsep.join(str(project_root / str(entry)) for entry in config["classpath_entries"])
    app_packages = [str(value) for value in config["app_packages"]]
    exclude_packages = [str(value) for value in config.get("exclude_packages", [])]
    return project_root, classes_dir, classpath, app_packages, exclude_packages


def _run_soot_extraction(
    subject: str,
    source_root: Path,
    extraction_root: Path,
) -> tuple[Path, Path, dict[str, Any]]:
    project_root, classes_dir, classpath, app_packages, exclude_packages = _source_paths(subject, source_root)
    if not classes_dir.is_dir():
        raise FileNotFoundError(
            f"compiled classes are missing for {subject}: {classes_dir}; "
            "run the configured subject build before semantic preparation"
        )
    out_dir = extraction_root / "soot"
    semantic_out = extraction_root / "class_declarations.csv"
    method_body_out = extraction_root / "method_bodies.csv"
    args = [
        "--subject", EXTRACTOR_SUBJECT[subject],
        "--classes-dir", str(classes_dir),
        "--classpath", classpath,
        "--app-packages", ",".join(app_packages),
        "--out-dir", str(out_dir),
        "--semantic-out", str(semantic_out),
        "--method-body-out", str(method_body_out),
    ]
    if exclude_packages:
        args.extend(["--exclude-packages", ",".join(exclude_packages)])
    command = [
        "mvn", "-q", "-f", str(ROOT / "tools/soot_extractor/pom.xml"),
        "exec:java", "-Dexec.mainClass=org.evomicro.sootextractor.SootExtractorCli",
        f"-Dexec.args={shlex.join(args)}",
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    if not semantic_out.is_file() or not method_body_out.is_file():
        raise RuntimeError(f"Soot did not produce isolated semantic outputs for {subject}")
    return semantic_out, method_body_out, {
        "project_root": str(project_root),
        "classes_dir": str(classes_dir),
        "command": shlex.join(command),
        "source_subject": EXTRACTOR_SUBJECT[subject],
    }


def _frozen_rows(subject: str, frozen_root: Path) -> dict[str, dict[str, str]]:
    path = frozen_root / subject / "class_semantic_inputs.csv"
    rows = _read_rows(path)
    return {row["class_id"]: row for row in rows}


def _declaration_map(path: Path) -> dict[str, dict[str, str]]:
    rows = _read_rows(path)
    return {row["class_id"]: row for row in rows}


def _method_map(path: Path) -> dict[str, list[MethodBody]]:
    result: dict[str, list[MethodBody]] = {}
    for row in _read_rows(path):
        result.setdefault(row["class_id"], []).append(
            MethodBody(
                class_id=row["class_id"],
                method_name=row["method_name"],
                method_signature=row["method_signature"],
                concrete=row["concrete"].lower() == "true",
                synthetic=row["synthetic"].lower() == "true",
                body_text=row["body_text"],
            )
        )
    return result


def _declaration_diff(expected: str, observed: str) -> str:
    return "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            observed.splitlines(keepends=True),
            fromfile="frozen_declaration",
            tofile="generated_declaration",
        )
    )


def _build_subject_input(
    subject: str,
    *,
    source_root: Path,
    output_root: Path,
    frozen_root: Path,
    verify_against_frozen: bool,
) -> dict[str, Any]:
    extraction_root = output_root / ".extraction" / subject
    extraction_root.mkdir(parents=True, exist_ok=True)
    semantic_path, method_path, source_metadata = _run_soot_extraction(
        subject, source_root, extraction_root
    )
    declarations = _declaration_map(semantic_path)
    methods = _method_map(method_path)
    frozen = _frozen_rows(subject, frozen_root)
    expected_ids = set(frozen)
    generated_ids = set(declarations)
    if generated_ids != expected_ids:
        missing = sorted(expected_ids - generated_ids)
        extra = sorted(generated_ids - expected_ids)
        raise ValueError(f"{subject}: class scope mismatch; missing={missing}; extra={extra}")
    output_dir = output_root / subject
    output_dir.mkdir(parents=True, exist_ok=True)
    output_rows: list[dict[str, str]] = []
    for class_id in sorted(expected_ids):
        baseline = dict(frozen[class_id])
        declaration = declarations[class_id]["semantic_text"]
        frozen_declaration = extract_declaration_section(baseline["semantic_text"])
        if declaration != frozen_declaration:
            raise ValueError(
                f"{subject}/{class_id}: declaration mismatch\n"
                f"{_declaration_diff(frozen_declaration, declaration)}"
            )
        normalized = normalize_class_bodies(methods.get(class_id, []))
        semantic_text = compose_semantic_text(declaration, normalized.body_text)
        baseline["semantic_text"] = semantic_text
        baseline["input_hash"] = canonical_text_hash(semantic_text)
        baseline["experiment_name"] = EXPERIMENT_ID
        baseline["representation_id"] = REPRESENTATION_ID
        baseline["declaration_exact_match"] = "true"
        baseline["declaration_truncated"] = "false"
        baseline["body_empty"] = str(normalized.body_text == "<EMPTY>").lower()
        baseline["body_tokens_truncated"] = str(normalized.tokens_truncated)
        baseline["raw_body_candidate_count"] = str(normalized.filter_counts.raw_candidate_count)
        baseline["filtered_body_token_count_before_budget"] = str(len(normalized.tokens_before_budget))
        baseline["appended_body_token_count"] = str(len(normalized.tokens_after_budget))
        baseline["extracted_concrete_method_count"] = str(normalized.method_count)
        baseline["normalized_method_count"] = str(normalized.method_count)
        baseline["synthetic_method_count"] = str(normalized.filter_counts.skipped_synthetic_methods)
        baseline["accepted_invoked_method_tokens"] = str(normalized.filter_counts.accepted_invoked_method_tokens)
        baseline["accepted_field_tokens"] = str(normalized.filter_counts.accepted_field_tokens)
        baseline["accepted_local_tokens"] = str(normalized.filter_counts.accepted_local_tokens)
        baseline["accepted_exception_tokens"] = str(normalized.filter_counts.accepted_exception_tokens)
        baseline["accepted_operation_tokens"] = str(normalized.filter_counts.accepted_operation_tokens)
        baseline["accepted_string_tokens"] = str(normalized.filter_counts.accepted_string_tokens)
        baseline["accepted_literals"] = str(normalized.filter_counts.accepted_literals)
        baseline["rejected_token_count"] = str(sum(normalized.filter_counts.rejected_tokens.values()))
        baseline["body_hash"] = canonical_text_hash(normalized.body_text)
        output_rows.append(baseline)
    fieldnames = list(output_rows[0])
    with (output_dir / "class_semantic_inputs.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)
    aggregate = aggregate_input_hash(output_rows)
    manifest = {
        "experiment_name": EXPERIMENT_ID,
        "representation_id": REPRESENTATION_ID,
        "subject": subject,
        "class_count": len(output_rows),
        "aggregate_input_sha256": aggregate,
        "source": source_metadata,
        "verified_against_frozen": verify_against_frozen,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    write_json(output_dir / "manifest.json", manifest)
    if verify_against_frozen:
        frozen_hashes = {class_id: row["input_hash"] for class_id, row in frozen.items()}
        observed_hashes = {row["class_id"]: row["input_hash"] for row in output_rows}
        if observed_hashes != frozen_hashes:
            raise ValueError(f"{subject}: generated semantic input hashes differ from frozen accepted inputs")
    return manifest


def prepare_semantic_inputs(
    *,
    subjects: tuple[str, ...],
    source_root: Path,
    output_root: Path,
    frozen_root: Path = INPUT_ROOT,
    verify_against_frozen: bool = True,
) -> dict[str, Any]:
    """Generate isolated final semantic inputs from compiled subject classes."""
    if output_root.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("semantic preparation output must be outside the repository")
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"refusing to reuse non-empty semantic output: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    return {
        subject: _build_subject_input(
            subject,
            source_root=source_root,
            output_root=output_root,
            frozen_root=frozen_root,
            verify_against_frozen=verify_against_frozen,
        )
        for subject in subjects
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", choices=("input", "embeddings", "graphs"), default="embeddings")
    parser.add_argument("--subject", choices=SUBJECTS)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--repro-output-root", type=Path)
    parser.add_argument("--report-root", type=Path, default=REPORT_ROOT)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--frozen-input-root", type=Path, default=INPUT_ROOT)
    parser.add_argument("--verify-against-frozen", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--embedding-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    subjects = (args.subject,) if args.subject else SUBJECTS
    if args.operation == "input":
        if args.source_root is None:
            parser.error("input preparation requires --source-root containing the raw project or project parent")
        if args.output_root is None:
            parser.error("input preparation requires an explicit temporary --output-root")
        output_root = args.output_root.expanduser().resolve()
        frozen_root = args.frozen_input_root.expanduser().resolve()
        result = prepare_semantic_inputs(
            subjects=subjects,
            source_root=args.source_root.expanduser().resolve(),
            output_root=output_root,
            frozen_root=frozen_root,
            verify_against_frozen=args.verify_against_frozen,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0
    if args.operation == "graphs":
        output_root = (args.output_root or GRAPH_ROOT).expanduser().resolve()
        embedding_root = args.embedding_root.expanduser().resolve()
        print(json.dumps(build_graphs(subjects=subjects, embedding_root=embedding_root, output_root=output_root), indent=2, default=str))
        return 0
    if args.repro_output_root is None:
        parser.error("embedding generation requires --repro-output-root")
    output_root = (args.output_root or OUTPUT_ROOT).expanduser()
    output_root = output_root if output_root.is_absolute() else ROOT / output_root
    repro_root = args.repro_output_root if args.repro_output_root.is_absolute() else ROOT / args.repro_output_root
    report_root = args.report_root if args.report_root.is_absolute() else ROOT / args.report_root
    assert_empty_output(output_root, canonical=True)
    assert_empty_output(repro_root, canonical=False)
    rows_by_subject = verify_frozen_inputs()
    runtime, identity, tokenizer = load_frozen_runtime()
    started = time.perf_counter()
    model, model_load_seconds = load_model(runtime["device"], dtype_from_name(runtime["dtype"]))
    model.eval()
    if int(model.max_seq_length) != MAX_SEQUENCE_LENGTH:
        raise RuntimeError(f"loaded SentenceTransformer max_seq_length={model.max_seq_length}")
    canonical = generate_once(model, rows_by_subject, runtime, identity, tokenizer, output_root, "canonical")
    reproducibility = generate_once(model, rows_by_subject, runtime, identity, tokenizer, repro_root, "reproducibility")
    clear_model(model)
    manifest = {
        "schema_version": 1,
        "experiment_name": EXPERIMENT_ID,
        "representation_id": REPRESENTATION_ID,
        "source_commit": source_commit(),
        "input_root": str(INPUT_ROOT.relative_to(ROOT)),
        "output_root": str(output_root.resolve()),
        "reproducibility_output_root": str(repro_root.resolve()),
        "model_load_seconds": model_load_seconds,
        "total_elapsed_seconds": time.perf_counter() - started,
        "runtime": runtime,
        "identity": identity,
        "subjects": canonical,
        "reproducibility_subjects": reproducibility,
        "generation_timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nearest_neighbors_generated": False,
        "semantic_graph_generated": False,
    }
    write_json(report_root / "embedding_generation_manifest.json", manifest)
    print(json.dumps({"subjects": list(canonical), "reproducibility": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
