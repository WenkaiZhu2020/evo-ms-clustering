#!/usr/bin/env python3
"""Probe the pinned Nomic runtime and generate formal Stage 3 embeddings."""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import os
import platform
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import torch
import yaml


MODEL_REVISION = "9a0457648f060c4279d4a3982d2d27a4df6fac59"
EXPECTED_MODEL = "nomic-ai/nomic-embed-code"
EXPECTED_DIMENSION = 3584
MAX_SEQUENCE_LENGTH = 32768
SEED = 42
SUBJECTS = {
    "jpetstore": (24, "1ecdb9083a37668fd07388454095a317268c8b736e6fd45957ab16bf87f6ad23"),
    "daytrader": (53, "ab09380f87119e4fe4621efbbdd8fdfd8cfc92cd383ed812169e2427a35eae44"),
    "xerces": (814, "f81d0f9bda5aa0fcdf3a35c75876cc73c8b419eccfb8c9e00634ec13fad4d60a"),
}
INPUT_PATHS = {
    subject: Path("data/semantic_inputs") / f"{subject if subject != 'xerces' else 'xerces-j'}_class_declarations.csv"
    for subject in SUBJECTS
}
OUTPUT_ROOT = Path("results")


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_contract(config: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    semantic_model = config["semantic_model"]
    tokenizer = config["tokenizer"]
    runtime = config["embedding_runtime"]
    if semantic_model["name"] != EXPECTED_MODEL or semantic_model["revision"] != MODEL_REVISION:
        raise ValueError("semantic model does not match the pinned Nomic contract")
    if tokenizer["revision"] != MODEL_REVISION or tokenizer["max_sequence_length"] != MAX_SEQUENCE_LENGTH:
        raise ValueError("tokenizer does not match the pinned Nomic contract")
    expected_runtime = {
        "backend": "sentence_transformers",
        "loader": "SentenceTransformer",
        "formal_custom_pooling_implementation": False,
        "pooling_source": "pinned_model_repository",
        "pooling": "last_token",
        "normalization_source": "pinned_model_repository",
        "l2_normalize": True,
        "output_dimension": EXPECTED_DIMENSION,
        "prompt_name": None,
        "query_prompt_used": False,
        "max_sequence_length": MAX_SEQUENCE_LENGTH,
        "formal_truncation": False,
        "input_column": "semantic_text",
    }
    for key, expected in expected_runtime.items():
        if runtime.get(key) != expected:
            raise ValueError(f"config embedding_runtime.{key}={runtime.get(key)!r}, expected {expected!r}")
    manifest_runtime = manifest["embedding_runtime"]
    manifest_expected = {
        "backend": "sentence_transformers",
        "loader": "SentenceTransformer",
        "custom_pooling": False,
        "prompt_name": None,
        "query_prompt_used": False,
        "pooling_source": "pinned_model_repository",
        "pooling": "last_token",
        "l2_normalize": True,
        "output_dimension": EXPECTED_DIMENSION,
        "similarity": "cosine",
        "max_sequence_length": MAX_SEQUENCE_LENGTH,
        "formal_truncation": False,
        "input_column": "semantic_text",
    }
    for key, expected in manifest_expected.items():
        if manifest_runtime.get(key) != expected:
            raise ValueError(f"manifest embedding_runtime.{key}={manifest_runtime.get(key)!r}, expected {expected!r}")
    if manifest["model"]["revision"] != MODEL_REVISION or manifest["tokenizer"]["revision"] != MODEL_REVISION:
        raise ValueError("manifest model/tokenizer revision is not pinned revision")
    return runtime


def read_subject(subject: str) -> list[dict[str, str]]:
    expected_count, expected_hash = SUBJECTS[subject]
    path = INPUT_PATHS[subject]
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != expected_count:
        raise ValueError(f"{subject}: expected {expected_count} rows, found {len(rows)}")
    rows = sorted(rows, key=lambda row: row["class_id"])
    payload = "".join(f"{row['class_id']}\t{row['input_hash']}\n" for row in rows).encode("utf-8")
    actual_hash = hashlib.sha256(payload).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError(f"{subject}: input aggregate hash {actual_hash} != {expected_hash}")
    if any(row["semantic_text"] is None for row in rows):
        raise ValueError(f"{subject}: missing semantic_text")
    return rows


def all_rows() -> dict[str, list[dict[str, str]]]:
    return {subject: read_subject(subject) for subject in SUBJECTS}


def select_device() -> tuple[str, list[str], str]:
    if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK"):
        raise RuntimeError("PYTORCH_ENABLE_MPS_FALLBACK is set; refusing implicit CPU fallback")
    available: list[str] = []
    if torch.backends.mps.is_available():
        available.append("mps")
    if torch.cuda.is_available():
        available.append("cuda")
    available.append("cpu")
    device = available[0]
    if device == "mps":
        name = f"Apple Silicon MPS ({platform.machine()})"
    elif device == "cuda":
        name = torch.cuda.get_device_name(0)
    else:
        name = platform.processor() or platform.machine()
    return device, available, name


def dtype_candidates(device: str) -> list[torch.dtype]:
    if device == "mps":
        return [torch.float16, torch.float32]
    if device == "cuda":
        candidates: list[torch.dtype] = []
        if torch.cuda.is_bf16_supported():
            candidates.append(torch.bfloat16)
        candidates.extend([torch.float16, torch.float32])
        return candidates
    return [torch.float32]


def dtype_name(dtype: torch.dtype) -> str:
    return str(dtype).removeprefix("torch.")


def dtype_from_name(name: str) -> torch.dtype:
    values = {"float16": torch.float16, "float32": torch.float32, "bfloat16": torch.bfloat16}
    if name not in values:
        raise ValueError(f"unsupported frozen dtype: {name}")
    return values[name]


def load_model(device: str, dtype: torch.dtype):
    from sentence_transformers import SentenceTransformer

    started = time.perf_counter()
    model = SentenceTransformer(
        EXPECTED_MODEL,
        revision=MODEL_REVISION,
        device=device,
        trust_remote_code=False,
        model_kwargs={"torch_dtype": dtype},
        config_kwargs={"revision": MODEL_REVISION},
    )
    model.eval()
    if int(model.max_seq_length) != MAX_SEQUENCE_LENGTH:
        raise RuntimeError(f"loaded model max_seq_length={model.max_seq_length}, expected {MAX_SEQUENCE_LENGTH}")
    return model, time.perf_counter() - started


def clear_model(model: Any) -> None:
    del model
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def encode_texts(model: Any, texts: list[str], batch_size: int) -> np.ndarray:
    encoded = model.encode(
        texts,
        batch_size=batch_size,
        prompt_name=None,
        prompt=None,
        output_value="sentence_embedding",
        precision="float32",
        convert_to_numpy=True,
        convert_to_tensor=False,
        normalize_embeddings=False,
        show_progress_bar=False,
    )
    array = np.asarray(encoded, dtype="<f4")
    if array.ndim != 2 or array.shape[1] != EXPECTED_DIMENSION:
        raise ValueError(f"unexpected embedding shape {array.shape}")
    return np.ascontiguousarray(array, dtype="<f4")


def validate_vectors(array: np.ndarray) -> dict[str, Any]:
    if array.ndim != 2 or array.shape[1] != EXPECTED_DIMENSION:
        raise ValueError(f"unexpected vector shape {array.shape}")
    nan_count = int(np.isnan(array).sum())
    inf_count = int(np.isinf(array).sum())
    norms = np.linalg.norm(array.astype(np.float64), axis=1)
    zero_count = int(np.all(array == 0, axis=1).sum())
    if nan_count or inf_count or zero_count:
        raise ValueError(f"invalid vectors: nan={nan_count}, inf={inf_count}, zero={zero_count}")
    if np.any((norms < 0.999) | (norms > 1.001)):
        raise ValueError(f"vector norm outside [0.999, 1.001]: min={norms.min()}, max={norms.max()}")
    return {
        "minimum_norm": float(norms.min()),
        "mean_norm": float(norms.mean()),
        "maximum_norm": float(norms.max()),
        "nan_count": nan_count,
        "inf_count": inf_count,
        "all_zero_vector_count": zero_count,
    }


def longest_rows(rows_by_subject: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    return [max(rows_by_subject[subject], key=lambda row: (len(row["semantic_text"]), row["class_id"])) for subject in SUBJECTS]


def select_smoke_rows(rows_by_subject: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    selected_ids: set[str] = set()

    def add(row: dict[str, str] | None) -> None:
        if row is not None and row["class_id"] not in selected_ids:
            selected.append(row)
            selected_ids.add(row["class_id"])

    for row in longest_rows(rows_by_subject):
        add(row)
    jpetstore = rows_by_subject["jpetstore"]
    daytrader = rows_by_subject["daytrader"]
    xerces = rows_by_subject["xerces"]
    add(next((row for row in jpetstore if row["kind"] == "interface"), None))
    add(next((row for row in daytrader if int(row["method_count"]) == 0), None))
    add(next((row for row in xerces if int(row["method_count"]) == 0), None))
    add(next((row for rows in rows_by_subject.values() for row in rows if int(row["annotation_count"]) > 0), None))
    add(next((row for rows in rows_by_subject.values() for row in rows if "abstract" in row["kind"]), None))
    for subject in SUBJECTS:
        for row in rows_by_subject[subject]:
            if len(selected) >= 10:
                return selected
            add(row)
    return selected[:10]


def smoke_check(model: Any, rows: list[dict[str, str]], batch_size: int) -> dict[str, Any]:
    texts = [row["semantic_text"] for row in rows]
    first_started = time.perf_counter()
    first = encode_texts(model, texts, batch_size)
    first_elapsed = time.perf_counter() - first_started
    second_started = time.perf_counter()
    second = encode_texts(model, texts, batch_size)
    second_elapsed = time.perf_counter() - second_started
    first_stats = validate_vectors(first)
    validate_vectors(second)
    exact = bool(np.array_equal(first.tobytes(), second.tobytes()))
    abs_diff = float(np.max(np.abs(first.astype(np.float64) - second.astype(np.float64))))
    cosine = np.sum(first.astype(np.float64) * second.astype(np.float64), axis=1) / (
        np.linalg.norm(first.astype(np.float64), axis=1) * np.linalg.norm(second.astype(np.float64), axis=1)
    )
    min_cosine = float(cosine.min())
    if not exact and (min_cosine < 0.999999 or abs_diff > 0.00001):
        offenders = [
            {"class_id": row["class_id"], "max_abs_diff": float(np.max(np.abs(a - b))), "cosine": float(c)}
            for row, a, b, c in zip(rows, first, second, cosine)
            if np.max(np.abs(a - b)) > 0.00001 or c < 0.999999
        ]
        raise RuntimeError(f"smoke repeated-run stability failed: {offenders}")
    if len(first) > 1 and np.allclose(first, first[0]):
        raise RuntimeError("all smoke embeddings are identical")
    diagonal = np.sum(first.astype(np.float64) * first.astype(np.float64), axis=1)
    if not np.allclose(diagonal, 1.0, atol=0.001):
        raise RuntimeError("smoke diagonal cosine validation failed")
    return {
        "shape": list(first.shape),
        "stats": first_stats,
        "exact_byte_equality": exact,
        "maximum_absolute_difference": abs_diff,
        "minimum_corresponding_cosine": min_cosine,
        "first_elapsed_seconds": first_elapsed,
        "second_elapsed_seconds": second_elapsed,
    }


def device_memory() -> dict[str, Any]:
    if torch.cuda.is_available():
        return {"allocated_bytes": int(torch.cuda.memory_allocated()), "reserved_bytes": int(torch.cuda.memory_reserved())}
    return {}


def run_probe(rows_by_subject: dict[str, list[dict[str, str]]], device: str) -> tuple[Any, dict[str, Any]]:
    candidates = dtype_candidates(device)
    dtype_records: list[dict[str, Any]] = []
    selected_model = None
    selected_dtype = None
    selected_batch = None
    load_duration = None
    batch_records: list[dict[str, Any]] = []
    probe_texts = [row["semantic_text"] for row in longest_rows(rows_by_subject)]
    for candidate in candidates:
        record: dict[str, Any] = {"dtype": dtype_name(candidate), "load_succeeded": False}
        model = None
        try:
            model, duration = load_model(device, candidate)
            record["load_succeeded"] = True
            record["model_load_duration_seconds"] = duration
            dtype_records.append(record)
            passing_batch = None
            for batch_size in (1, 2, 4, 8):
                if passing_batch is not None and batch_size <= passing_batch:
                    continue
                texts = [probe_texts[index % len(probe_texts)] for index in range(batch_size)]
                batch_record: dict[str, Any] = {
                    "dtype": dtype_name(candidate),
                    "batch_size": batch_size,
                    "memory_before": device_memory(),
                }
                try:
                    started = time.perf_counter()
                    warmup = encode_texts(model, texts, batch_size)
                    encode_texts(model, texts, batch_size)
                    elapsed = time.perf_counter() - started
                    stats = validate_vectors(warmup)
                    batch_record.update({"succeeded": True, "elapsed_seconds": elapsed, "stats": stats, "memory_after": device_memory()})
                    batch_records.append(batch_record)
                    passing_batch = batch_size
                except Exception as exc:
                    batch_record.update({"succeeded": False, "error": repr(exc), "memory_after": device_memory()})
                    batch_records.append(batch_record)
                    break
            if passing_batch is not None:
                selected_model = model
                selected_dtype = candidate
                selected_batch = passing_batch
                load_duration = float(record["model_load_duration_seconds"])
                break
        except Exception as exc:
            record["error"] = repr(exc)
            dtype_records.append(record)
        if model is not None:
            clear_model(model)
    if selected_model is None or selected_dtype is None or selected_batch is None:
        raise RuntimeError(f"no dtype passed the runtime probe: {dtype_records}")
    return selected_model, {
        "dtype_candidates": dtype_records,
        "batch_candidates": batch_records,
        "selected_dtype": dtype_name(selected_dtype),
        "selected_batch_size": selected_batch,
        "model_load_duration_seconds": load_duration,
    }


def resolve_cache_location() -> str:
    candidates = [os.environ.get("SENTENCE_TRANSFORMERS_HOME"), os.environ.get("HF_HOME")]
    candidates = [value for value in candidates if value]
    if candidates:
        path = Path(candidates[0]).expanduser().resolve()
    else:
        path = (Path.home() / ".cache" / "huggingface").resolve()
    repo = Path.cwd().resolve()
    if repo == path or repo in path.parents:
        raise RuntimeError(f"model cache is inside repository: {path}")
    try:
        from huggingface_hub import snapshot_download

        snapshot = snapshot_download(EXPECTED_MODEL, revision=MODEL_REVISION, local_files_only=True)
        return str(Path(snapshot).resolve())
    except Exception:
        return str(path)


def disk_available_bytes() -> int:
    return int(os.statvfs(Path.cwd()).f_bavail * os.statvfs(Path.cwd()).f_frsize)


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vector_hash(vector: np.ndarray) -> str:
    little = np.ascontiguousarray(np.asarray(vector, dtype="<f4"))
    return hashlib.sha256(little.tobytes()).hexdigest()


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def nearest_neighbors(rows: list[dict[str, str]], vectors: np.ndarray) -> list[dict[str, Any]]:
    similarities = vectors.astype(np.float64) @ vectors.astype(np.float64).T
    output: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        candidates = [candidate for candidate in range(len(rows)) if candidate != index]
        candidates.sort(key=lambda candidate: (-float(similarities[index, candidate]), rows[candidate]["class_id"]))
        for rank, candidate in enumerate(candidates[:5], start=1):
            output.append({
                "class_id": row["class_id"],
                "neighbor_rank": rank,
                "neighbor_class_id": rows[candidate]["class_id"],
                "cosine_similarity": f"{similarities[index, candidate]:.12f}",
            })
    return output


def output_dir(subject: str) -> Path:
    return OUTPUT_ROOT / subject / "04_stage3_semantic" / "embeddings"


def encode_subject(model: Any, subject: str, rows: list[dict[str, str]], runtime: dict[str, Any], git_commit: str) -> dict[str, Any]:
    directory = output_dir(subject)
    directory.mkdir(parents=True, exist_ok=True)
    texts = [row["semantic_text"] for row in rows]
    started = time.perf_counter()
    vectors = encode_texts(model, texts, int(runtime["batch_size"]))
    elapsed = time.perf_counter() - started
    stats = validate_vectors(vectors)
    np.save(directory / "embeddings.npy", vectors)
    class_rows = [
        {"row_index": index, "class_id": row["class_id"], "class_name": row["class_name"], "input_hash": row["input_hash"]}
        for index, row in enumerate(rows)
    ]
    write_csv(directory / "class_ids.csv", ["row_index", "class_id", "class_name", "input_hash"], class_rows)
    hash_rows = [
        {"class_id": row["class_id"], "input_hash": row["input_hash"], "embedding_sha256": vector_hash(vector)}
        for row, vector in zip(rows, vectors)
    ]
    write_csv(directory / "embedding_hashes.csv", ["class_id", "input_hash", "embedding_sha256"], hash_rows)
    aggregate_payload = "".join(f"{row['class_id']}\t{row['embedding_sha256']}\n" for row in hash_rows).encode("utf-8")
    aggregate_hash = hashlib.sha256(aggregate_payload).hexdigest()
    write_csv(
        directory / "nearest_neighbors.csv",
        ["class_id", "neighbor_rank", "neighbor_class_id", "cosine_similarity"],
        nearest_neighbors(rows, vectors),
    )
    metadata = {
        "schema_version": 1,
        "subject": subject,
        "class_count": len(rows),
        "input_csv_path": str(INPUT_PATHS[subject]),
        "input_aggregate_hash": SUBJECTS[subject][1],
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
        "truncation": False,
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
        "platform": platform.platform(),
        "creation_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "encoding_elapsed_seconds": elapsed,
        **stats,
        "embeddings_npy_sha256": sha256_file(directory / "embeddings.npy"),
        "class_ids_csv_sha256": sha256_file(directory / "class_ids.csv"),
        "embedding_hashes_csv_sha256": sha256_file(directory / "embedding_hashes.csv"),
        "aggregate_embedding_sha256": aggregate_hash,
        "exact_encode_arguments": {
            "prompt_name": None,
            "prompt": None,
            "normalize_embeddings": False,
            "precision": "float32",
            "convert_to_numpy": True,
            "convert_to_tensor": False,
            "truncation": False,
        },
        "git_commit": git_commit,
    }
    save_json(directory / "embedding_metadata.json", metadata)
    return metadata


def deterministic_reencode_rows(subject: str, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if subject == "jpetstore":
        return rows
    selected: list[dict[str, str]] = []
    ids: set[str] = set()

    def add(row: dict[str, str] | None) -> None:
        if row and row["class_id"] not in ids:
            selected.append(row)
            ids.add(row["class_id"])

    add(max(rows, key=lambda row: (len(row["semantic_text"]), row["class_id"])))
    add(max(rows, key=lambda row: (int(row["method_count"]), row["class_id"])))
    add(next((row for row in rows if int(row["method_count"]) == 0), None))
    add(next((row for row in rows if row["kind"] == "interface"), None))
    add(next((row for row in rows if int(row["annotation_count"]) > 0), None))
    for row in rows:
        if len(selected) >= 10:
            break
        add(row)
    return selected[:10]


def run_reencoding(model: Any, rows_by_subject: dict[str, list[dict[str, str]]], runtime: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for subject, rows in rows_by_subject.items():
        selected = deterministic_reencode_rows(subject, rows)
        saved = np.load(output_dir(subject) / "embeddings.npy")
        index_by_id = {row["class_id"]: index for index, row in enumerate(rows)}
        repeated = encode_texts(model, [row["semantic_text"] for row in selected], int(runtime["batch_size"]))
        reference = np.asarray([saved[index_by_id[row["class_id"]]] for row in selected], dtype="<f4")
        exact_count = sum(np.array_equal(a.tobytes(), b.tobytes()) for a, b in zip(reference, repeated))
        abs_diffs = np.max(np.abs(reference.astype(np.float64) - repeated.astype(np.float64)), axis=1)
        cosine = np.sum(reference.astype(np.float64) * repeated.astype(np.float64), axis=1) / (
            np.linalg.norm(reference.astype(np.float64), axis=1) * np.linalg.norm(repeated.astype(np.float64), axis=1)
        )
        offenders = [
            {"class_id": row["class_id"], "maximum_absolute_difference": float(diff), "cosine": float(cos)}
            for row, diff, cos in zip(selected, abs_diffs, cosine)
            if diff > 0.00001 or cos < 0.999999
        ]
        if offenders:
            raise RuntimeError(f"{subject} re-encoding stability failed: {offenders}")
        results[subject] = {
            "class_count": len(selected),
            "exact_byte_matches": int(exact_count),
            "maximum_absolute_difference": float(abs_diffs.max()),
            "minimum_corresponding_cosine": float(cosine.min()),
            "passed": True,
            "class_ids": [row["class_id"] for row in selected],
        }
    return results


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/experiments/04_stage3_semantic.yml"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/stage3/formal_run_manifest.json"))
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--runtime-json", type=Path, default=Path("reports/stage3/day3_runtime_probe.json"))
    parser.add_argument("--stability-json", type=Path, default=Path("reports/stage3/embedding_stability.json"))
    args = parser.parse_args()
    if args.probe_only and args.generate:
        raise SystemExit("choose only one of --probe-only and --generate")
    config = load_config(args.config)
    manifest = load_manifest(args.manifest)
    runtime_config = validate_contract(config, manifest)
    rows_by_subject = all_rows()
    set_seed()
    disk_before = disk_available_bytes()
    if args.generate:
        if runtime_config.get("runtime_frozen") is not True:
            raise RuntimeError("formal generation requires a frozen embedding runtime")
        runtime = {
            "device": runtime_config["device"],
            "device_name": runtime_config["device_name"],
            "dtype": runtime_config["dtype"],
            "batch_size": runtime_config["batch_size"],
        }
        model, _ = load_model(runtime["device"], dtype_from_name(runtime["dtype"]))
        probe_result = None
    else:
        device, available_devices, device_name = select_device()
        model, probe = run_probe(rows_by_subject, device)
        smoke_rows = select_smoke_rows(rows_by_subject)
        smoke_first = smoke_check(model, smoke_rows, int(probe["selected_batch_size"]))
        smoke_second = smoke_check(model, smoke_rows, int(probe["selected_batch_size"]))
        runtime = {
            "device": device,
            "device_name": device_name,
            "dtype": probe["selected_dtype"],
            "batch_size": probe["selected_batch_size"],
        }
        probe_result = {
            "branch": subprocess.check_output(["git", "branch", "--show-current"], text=True).strip(),
            "starting_commit": git_commit(),
            "platform": platform.platform(),
            "torch_version": torch.__version__,
            "transformers_version": __import__("transformers").__version__,
            "sentence_transformers_version": __import__("sentence_transformers").__version__,
            "model": EXPECTED_MODEL,
            "revision": MODEL_REVISION,
            "cache_location": resolve_cache_location(),
            "disk_available_before_model_download_bytes": disk_before,
            "disk_available_after_model_download_bytes": disk_available_bytes(),
            "available_devices": available_devices,
            "selected_runtime": runtime,
            "dtype_candidates_tested": probe["dtype_candidates"],
            "batch_sizes_tested": probe["batch_candidates"],
            "model_load_duration_seconds": probe["model_load_duration_seconds"],
            "smoke_rows": [{"subject": row.get("subject"), "class_id": row["class_id"]} for row in smoke_rows],
            "smoke_test_first": smoke_first,
            "smoke_test_second": smoke_second,
            "smoke_test_passed": True,
            "storage_dtype": "float32",
            "random_seed": SEED,
            "inference_mode": True,
            "model_eval": True,
            "encode_normalize_embeddings_argument": False,
        }
        save_json(args.runtime_json, probe_result)
    if args.probe_only or not args.generate:
        clear_model(model)
        print(json.dumps(probe_result, indent=2))
        return 0
    for subject, rows in rows_by_subject.items():
        encode_subject(model, subject, rows, runtime, git_commit())
    stability = run_reencoding(model, rows_by_subject, runtime)
    save_json(args.stability_json, stability)
    clear_model(model)
    print(json.dumps({"runtime": probe_result, "stability": stability}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
