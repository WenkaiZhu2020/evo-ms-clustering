#!/usr/bin/env python3
"""Generate isolated embeddings for the final Stage 3 representation."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
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
from scripts.stage3.final_paths import (  # noqa: E402
    EXPERIMENT_ID,
    REPRESENTATION_ID,
)
from evo_ms.semantic.method_body import extract_declaration_section  # noqa: E402


SUBJECTS = ("jpetstore", "daytrader", "xerces")
EXPECTED_COUNTS = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
EXPECTED_INPUT_HASHES = {
    "jpetstore": "2d9007f75a14f4a4ed6152563241b898837b6c12b66a98a2464b4cc3f969a921",
    "daytrader": "da53d434b820e3c25bc69df63ced807cd0113d412fa36acc9694d1a97631d655",
    "xerces": "65488944220cc3a503994d6f2289e0f7bdc06c619351a2e8243bca243538c8a3",
}
INPUT_ROOT = ROOT / "data/semantic_text/declaration_method_body"
OUTPUT_ROOT = ROOT / "data/embeddings/declaration_method_body"
REPORT_ROOT = ROOT / "reports/stage3/provenance"
FORMAL_CONFIG = ROOT / "configs/experiments/05_stage3_declaration_method_body.yml"
MAX_NORM_TOLERANCE = (0.999, 1.001)


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
    global_manifest = json.loads((REPORT_ROOT / "method_body_input_manifest.json").read_text(encoding="utf-8"))
    hash_rows = read_csv(REPORT_ROOT / "method_body_input_hashes.csv")
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--repro-output-root", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, default=REPORT_ROOT)
    args = parser.parse_args()
    output_root = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
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
