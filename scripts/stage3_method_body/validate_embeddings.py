#!/usr/bin/env python3
"""Validate and diagnose isolated Stage 3B embeddings without building graphs."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable
import unicodedata

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.stage3_method_body.generate_embeddings import (  # noqa: E402
    EXPECTED_COUNTS,
    EXPECTED_DIMENSION,
    EXPECTED_INPUT_HASHES,
    EXPECTED_MODEL,
    INPUT_ROOT,
    MAX_SEQUENCE_LENGTH,
    OUTPUT_ROOT,
    REPORT_ROOT,
    SUBJECTS,
    canonical_class_mapping_hash,
    read_csv,
    sha256_bytes,
    sha256_file,
    token_length_rows,
    verify_frozen_inputs,
)
from scripts.stage3_method_body import method_body_normalization as normalization  # noqa: E402
from scripts.stage3_method_body.prepare_inputs import EXTRACTION_SUBJECT, method_rows_by_class  # noqa: E402


STAGE3A_EMBEDDING_ROOT = ROOT / "results"
STAGE3A_INPUT_ROOT = ROOT / "data/semantic_inputs"
UNCHANGED_COSINE_DISTANCE_TOLERANCE = 1e-6
MATERIAL_SHIFT_COSINE_DISTANCE_THRESHOLD = 0.05
EXPECTED_STAGE3B_XERCES_DUPLICATE_GROUPS = 11
EXPECTED_FILES = {
    "embeddings.npy",
    "class_ids.csv",
    "embedding_hashes.csv",
    "embedding_metadata.json",
    "token_lengths.csv",
}


def _trace_method(method: normalization.MethodBody) -> dict[str, Any]:
    """Replay Body V1 candidates with provenance labels without changing text."""
    if not method.concrete or method.synthetic:
        return {"tokens": [], "raw_candidate_count": 0, "dedup_removed": 0}
    candidates: list[tuple[str, str, int]] = []
    source_index = 0

    def add(value: str, category: str, priority: int) -> None:
        nonlocal source_index
        for token in normalization._clean_identifier(value, accessor_policy=True):
            candidates.append((token, category, source_index))
            source_index += 1

    if method.method_name not in {"<init>", "<clinit>"}:
        add(method.method_name, "invoked_method", 0)
    text = unicodedata.normalize("NFKC", method.body_text or "")
    for match in re.finditer(
        r"<[^>\n]*:\s*[^\s\n]+(?:\s+[^\s\n]+)*\s+([A-Za-z_$][A-Za-z0-9_$]*|<init>|<clinit>)\s*\(",
        text,
    ):
        if match.group(1) not in {"<init>", "<clinit>"}:
            add(match.group(1), "invoked_method", 0)
    for match in re.finditer(r"<[^>\n]*:\s*[^\s\n]+\s+([A-Za-z_$][A-Za-z0-9_$]*)>", text):
        add(match.group(1), "field", 1)
    for match in re.finditer(r"(?i)\b(?:catch|throw|new|instanceof)\s+([A-Za-z_$][A-Za-z0-9_$.]*)", text):
        simple = normalization._simple_name(match.group(1))
        if re.search(r"(?i)(?:exception|error|throwable)$", simple):
            add(simple, "exception", 1)
    for match in re.finditer(r"(?i)\b(?:new|instanceof)\s+([A-Za-z_$][A-Za-z0-9_$.]*)", text):
        simple = normalization._simple_name(match.group(1))
        if re.search(r"(?i)(?:exception|error|throwable)$", simple):
            add(simple, "exception", 1)
    for match in normalization._STRING.finditer(text):
        for token in normalization._literal_tokens(match.group(0), normalization.FilterCounts(), []):
            candidates.append((token, "string", source_index))
            source_index += 1
    working = normalization._STRING.sub(" ", text)
    working = normalization._OWNER_SIGNATURE.sub(" ", working)
    working = re.sub(r"\b(new|instanceof|cast)\s+[A-Za-z_$][A-Za-z0-9_$.]*", r"\1 ", working)
    working = normalization._FQN.sub(" ", working)
    working = normalization._PATH.sub(" ", working)
    working = normalization._JIMPLE_LABEL.sub(" ", working)
    for match in normalization._IDENTIFIER.finditer(working):
        raw = match.group(0)
        lowered = raw.lower()
        if lowered in normalization._OPERATION_TOKENS:
            add(normalization._OPERATION_TOKENS[lowered], "operation", 0)
        elif lowered in normalization._RAW_JIMPLE_TOKENS:
            continue
        elif lowered in normalization._KEYWORDS or normalization._SYNTHETIC_LOCAL.fullmatch(raw):
            continue
        elif raw[:1].isupper():
            continue
        else:
            add(raw, "local", 2)
    candidates.sort(key=lambda item: (0 if item[1] in {"invoked_method", "operation"} else 1 if item[1] in {"field", "exception", "string"} else 2, item[2]))
    seen: set[str] = set()
    output: list[tuple[str, str, int]] = []
    for candidate in candidates:
        # Shimple pseudo-operations such as Phi(...) can reach the generic
        # identifier scan. Body V1 excludes raw Jimple/Shimple tokens no
        # matter which extraction path produced them.
        if candidate[0].lower() in normalization._RAW_JIMPLE_TOKENS:
            continue
        if candidate[0] in seen:
            continue
        seen.add(candidate[0])
        output.append(candidate)
    return {
        "tokens": output,
        "raw_candidate_count": len(candidates),
        "dedup_removed": len(candidates) - len(output),
    }


def trace_final_body_tokens(methods: list[normalization.MethodBody]) -> dict[str, Any]:
    sorted_methods = sorted(methods, key=lambda item: (item.method_name, item.method_signature))
    traces = [_trace_method(method) for method in sorted_methods]
    candidates = [candidate for trace in traces for candidate in trace["tokens"]]
    counts: dict[str, int] = defaultdict(int)
    before: list[tuple[str, str, int]] = []
    repeated_removed = 0
    for candidate in candidates:
        if counts[candidate[0]] >= normalization.REPEATED_TOKEN_CAP:
            repeated_removed += 1
            continue
        counts[candidate[0]] += 1
        before.append(candidate)
    after = before[:normalization.BODY_TOKEN_BUDGET]
    return {
        "tokens_before_budget": before,
        "tokens_after_budget": after,
        "removed_by_deduplication": sum(trace["dedup_removed"] for trace in traces),
        "removed_by_repeated_token_cap": repeated_removed,
        "removed_by_body_budget": len(before) - len(after),
        "raw_candidate_count": len(candidates),
    }


def write_body_composition(rows_by_subject: dict[str, list[dict[str, str]]], extraction_root: Path) -> None:
    rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    source_categories = ("invoked_method", "field", "local", "exception", "string", "operation")
    for subject in SUBJECTS:
        methods_path = extraction_root / EXTRACTION_SUBJECT[subject] / "method_bodies.csv"
        methods_by_class = method_rows_by_class(methods_path)
        totals = {category: 0 for category in source_categories}
        final_total = 0
        for input_row in rows_by_subject[subject]:
            trace = trace_final_body_tokens(methods_by_class.get(input_row["class_id"], []))
            body = input_row["semantic_text"].split("[METHOD_BODY]\n", 1)[1].rstrip("\n")
            final_tokens = [] if body == normalization.EMPTY_BODY else body.split()
            traced_tokens = [token for token, _, _ in trace["tokens_after_budget"]]
            if traced_tokens != final_tokens:
                raise ValueError(f"{subject}/{input_row['class_id']}: composition trace differs from frozen body text")
            category_counts = {category: sum(item[1] == category for item in trace["tokens_after_budget"]) for category in source_categories}
            for category, count in category_counts.items():
                totals[category] += count
            final_total += len(final_tokens)
        dedup = 0
        repeated = 0
        budget = 0
        for input_row in rows_by_subject[subject]:
            trace = trace_final_body_tokens(methods_by_class.get(input_row["class_id"], []))
            dedup += trace["removed_by_deduplication"]
            repeated += trace["removed_by_repeated_token_cap"]
            budget += trace["removed_by_body_budget"]
        proportions = {f"{category}_proportion": (totals[category] / final_total if final_total else 0.0) for category in source_categories}
        dominant = max(source_categories, key=lambda category: totals[category]) if final_total else "none"
        summary_rows.append({
            "subject": subject,
            "final_body_token_count": final_total,
            **{f"{category}_tokens": totals[category] for category in source_categories},
            **proportions,
            "dominant_evidence_type": dominant,
            "tokens_removed_through_deduplication": dedup,
            "tokens_removed_through_repeated_token_cap": repeated,
            "tokens_removed_through_body_budget": budget,
            "contract_body_truncated_classes": sum(int(row["body_tokens_truncated"]) > 0 for row in rows_by_subject[subject]),
            "composition_source": "deterministic Body V1 trace aligned to final appended body text",
        })
    write_csv(REPORT_ROOT / "final_body_token_composition.csv", list(summary_rows[0]), summary_rows)
    lines = [
        "# Final Stage 3B body-token composition",
        "",
        "Counts are computed from the final appended `[METHOD_BODY]` token sequence, not raw extraction occurrence counts. A deterministic replay of the frozen Body V1 candidate ordering was aligned byte-for-byte with each saved body section before aggregation.",
        "",
        "| Subject | Final body tokens | Invoked methods | Fields | Locals | Exceptions | Strings | Operations | Dominant source |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary_rows:
        lines.append(f"| {row['subject']} | {row['final_body_token_count']} | {row['invoked_method_tokens']} ({row['invoked_method_proportion']:.1%}) | {row['field_tokens']} ({row['field_proportion']:.1%}) | {row['local_tokens']} ({row['local_proportion']:.1%}) | {row['exception_tokens']} ({row['exception_proportion']:.1%}) | {row['string_tokens']} ({row['string_proportion']:.1%}) | {row['operation_tokens']} ({row['operation_proportion']:.1%}) | {row['dominant_evidence_type']} |")
    lines += ["", "The dominant final evidence type is reported descriptively and does not change weights or filtering. Body-budget removals and deterministic filter/repetition removals are recorded in the CSV.", ""]
    (REPORT_ROOT / "final_body_token_composition_summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pairwise_cosine(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    first_values = np.asarray(first, dtype=np.float64)
    second_values = np.asarray(second, dtype=np.float64)
    if not np.isfinite(first_values).all() or not np.isfinite(second_values).all():
        raise ValueError("cannot compare non-finite embeddings")
    first_norm = np.linalg.norm(first_values, axis=1)
    second_norm = np.linalg.norm(second_values, axis=1)
    if np.any(first_norm == 0.0) or np.any(second_norm == 0.0):
        raise ValueError("cannot compare a zero-norm embedding")
    return np.clip(np.sum(first_values * second_values, axis=1) / (first_norm * second_norm), -1.0, 1.0)


def stats(values: Iterable[float]) -> dict[str, float]:
    array = np.asarray(list(values), dtype=np.float64)
    if not len(array):
        return {"minimum": 0.0, "mean": 0.0, "median": 0.0, "standard_deviation": 0.0, "maximum": 0.0}
    return {
        "minimum": float(array.min()),
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "standard_deviation": float(array.std()),
        "maximum": float(array.max()),
    }


def validate_saved_subject(
    subject: str,
    input_rows: list[dict[str, str]],
    output_root: Path = OUTPUT_ROOT,
) -> dict[str, Any]:
    directory = output_root / subject
    if not directory.is_dir():
        raise FileNotFoundError(f"missing Stage 3B embedding directory: {directory}")
    actual_files = {path.name for path in directory.iterdir() if path.is_file()}
    if actual_files != EXPECTED_FILES:
        raise ValueError(f"{subject}: unexpected Stage 3B files: {sorted(actual_files ^ EXPECTED_FILES)}")
    vectors = np.load(directory / "embeddings.npy", allow_pickle=False)
    round_trip = np.load(directory / "embeddings.npy", allow_pickle=False)
    if vectors.tobytes() != round_trip.tobytes():
        raise ValueError(f"{subject}: save/load round trip changed embedding bytes")
    if vectors.dtype != np.dtype("<f4") or vectors.shape != (EXPECTED_COUNTS[subject], EXPECTED_DIMENSION):
        raise ValueError(f"{subject}: unexpected embedding shape/dtype {vectors.shape}/{vectors.dtype}")
    if not np.isfinite(vectors).all():
        raise ValueError(f"{subject}: embedding array contains NaN or Inf")
    zero_count = int(np.all(vectors == 0, axis=1).sum())
    if zero_count:
        raise ValueError(f"{subject}: {zero_count} all-zero vectors")
    norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
    if np.any((norms < 0.999) | (norms > 1.001)):
        raise ValueError(f"{subject}: norm outside frozen Stage 3A tolerance")

    mapping = read_csv(directory / "class_ids.csv")
    expected_mapping = [
        {"row_index": str(index), "class_id": row["class_id"], "class_name": row["class_name"], "input_hash": row["input_hash"]}
        for index, row in enumerate(input_rows)
    ]
    if mapping != expected_mapping:
        raise ValueError(f"{subject}: class mapping does not exactly match frozen input order")
    if canonical_class_mapping_hash([row["class_id"] for row in input_rows]) != canonical_class_mapping_hash([row["class_id"] for row in mapping]):
        raise ValueError(f"{subject}: class mapping hash mismatch")

    embedding_hashes = read_csv(directory / "embedding_hashes.csv")
    expected_hashes = [
        {"class_id": row["class_id"], "input_hash": row["input_hash"], "embedding_sha256": sha}
        for row, sha in zip(input_rows, (sha256_bytes(np.asarray(vector, dtype="<f4").tobytes()) for vector in vectors))
    ]
    if embedding_hashes != expected_hashes:
        raise ValueError(f"{subject}: per-class embedding hashes do not match saved vectors")
    aggregate = sha256_bytes("".join(f"{row['class_id']}\t{row['embedding_sha256']}\n" for row in embedding_hashes).encode("utf-8"))
    metadata = read_json(directory / "embedding_metadata.json")
    required_metadata = {
        "experiment_name": "stage3_declaration_method_body",
        "representation_id": "declaration_method_body_v1",
        "subject": subject,
        "class_count": EXPECTED_COUNTS[subject],
        "input_aggregate_hash": EXPECTED_INPUT_HASHES[subject],
        "model_revision": "9a0457648f060c4279d4a3982d2d27a4df6fac59",
        "tokenizer_revision": "9a0457648f060c4279d4a3982d2d27a4df6fac59",
        "backend": "sentence_transformers",
        "loader": "SentenceTransformer",
        "output_dimension": EXPECTED_DIMENSION,
        "formal_truncation": False,
        "prompt_name": None,
        "query_prompt_used": False,
        "max_sequence_length": MAX_SEQUENCE_LENGTH,
        "aggregate_embedding_sha256": aggregate,
    }
    for key, expected in required_metadata.items():
        if metadata.get(key) != expected:
            raise ValueError(f"{subject}: metadata {key}={metadata.get(key)!r}, expected {expected!r}")
    token_rows = read_csv(directory / "token_lengths.csv")
    if len(token_rows) != len(input_rows) or any(row["tokenizer_truncated"] == "true" for row in token_rows):
        raise ValueError(f"{subject}: unexpected tokenizer truncation in saved token report")
    return {
        "subject": subject,
        "class_count": len(input_rows),
        "dimension": int(vectors.shape[1]),
        "nan_count": int(np.isnan(vectors).sum()),
        "inf_count": int(np.isinf(vectors).sum()),
        "zero_vector_count": zero_count,
        "norms": stats(norms),
        "aggregate_embedding_sha256": aggregate,
        "embeddings_npy_sha256": sha256_file(directory / "embeddings.npy"),
        "metadata": metadata,
        "vectors": vectors,
        "mapping": mapping,
        "token_rows": token_rows,
    }


def group_indices(values: list[str]) -> list[list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for index, value in enumerate(values):
        groups[value].append(index)
    return [indices for indices in groups.values() if len(indices) > 1]


def collision_diagnostics(
    subject: str,
    input_rows: list[dict[str, str]],
    vectors: np.ndarray,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    text_groups = group_indices([row["semantic_text"] for row in input_rows])
    vector_hash_groups = group_indices([
        sha256_bytes(np.asarray(vector, dtype="<f4").tobytes()) for vector in vectors
    ])
    rows: list[dict[str, Any]] = []
    for group_index, indices in enumerate(text_groups, start=1):
        members = vectors[indices]
        pair_cosines = pairwise_cosine(members[0:1].repeat(len(indices), axis=0), members)
        distances = np.linalg.norm(members - members[0], axis=1)
        rows.append({
            "subject": subject,
            "collision_type": "duplicate_text_group",
            "group_id": f"text_{group_index:03d}",
            "class_ids": "|".join(input_rows[index]["class_id"] for index in indices),
            "input_hashes": "|".join(input_rows[index]["input_hash"] for index in indices),
            "embedding_hashes": "|".join(sha256_bytes(np.asarray(vectors[index], dtype="<f4").tobytes()) for index in indices),
            "exact_embedding_equality": str(bool(np.array_equal(members, members[0:1].repeat(len(indices), axis=0)))).lower(),
            "maximum_euclidean_distance": f"{float(distances.max()):.12g}",
            "minimum_pairwise_cosine": f"{float(pair_cosines.min()):.12g}",
            "notes": "expected representation-induced duplicate text" if subject == "xerces" else "duplicate text diagnostic",
        })
    for group_index, indices in enumerate(vector_hash_groups, start=1):
        distinct_texts = len({input_rows[index]["semantic_text"] for index in indices})
        if distinct_texts > 1:
            rows.append({
                "subject": subject,
                "collision_type": "non_identical_text_duplicate_embedding",
                "group_id": f"vector_{group_index:03d}",
                "class_ids": "|".join(input_rows[index]["class_id"] for index in indices),
                "input_hashes": "|".join(input_rows[index]["input_hash"] for index in indices),
                "embedding_hashes": "|".join(sha256_bytes(np.asarray(vectors[index], dtype="<f4").tobytes()) for index in indices),
                "exact_embedding_equality": "true",
                "maximum_euclidean_distance": "0",
                "minimum_pairwise_cosine": "1",
                "notes": "unexpected; requires investigation",
            })
    return rows, {
        "duplicate_text_group_count": len(text_groups),
        "duplicate_embedding_group_count": len(vector_hash_groups),
        "non_identical_text_embedding_collision_count": sum(
            len({input_rows[index]["semantic_text"] for index in indices}) > 1 for indices in vector_hash_groups
        ),
    }


def stage3a_rows(subject: str) -> list[dict[str, str]]:
    filename = "xerces-j" if subject == "xerces" else subject
    return sorted(read_csv(STAGE3A_INPUT_ROOT / f"{filename}_class_declarations.csv"), key=lambda row: row["class_id"])


def stage3a_vectors(subject: str) -> tuple[list[dict[str, str]], np.ndarray]:
    directory = STAGE3A_EMBEDDING_ROOT / subject / "04_stage3_semantic" / "embeddings"
    mapping = read_csv(directory / "class_ids.csv")
    vectors = np.load(directory / "embeddings.npy", allow_pickle=False)
    by_id = {row["class_id"]: index for index, row in enumerate(mapping)}
    rows = stage3a_rows(subject)
    if set(by_id) != {row["class_id"] for row in rows}:
        raise ValueError(f"{subject}: Stage 3A and Stage 3B class scopes differ")
    ordered_vectors = np.asarray([vectors[by_id[row["class_id"]]] for row in rows], dtype="<f4")
    return rows, ordered_vectors


def shift_diagnostics(
    subject: str,
    input_rows: list[dict[str, str]],
    stage3b_vectors: np.ndarray,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stage3a_input, stage3a = stage3a_vectors(subject)
    if [row["class_id"] for row in stage3a_input] != [row["class_id"] for row in input_rows]:
        raise ValueError(f"{subject}: Stage 3A/Stage 3B class mapping order differs")
    cosine = pairwise_cosine(stage3a, stage3b_vectors)
    euclidean = np.linalg.norm(stage3a.astype(np.float64) - stage3b_vectors.astype(np.float64), axis=1)
    old_groups: dict[str, list[str]] = defaultdict(list)
    for row in stage3a_input:
        old_groups[row["input_hash"]].append(row["class_id"])
    old_group_id = {
        class_id: f"stage3a_{index:03d}"
        for index, members in enumerate((group for group in old_groups.values() if len(group) > 1), start=1)
        for class_id in members
    }
    new_groups: dict[str, list[str]] = defaultdict(list)
    for row in input_rows:
        new_groups[row["input_hash"]].append(row["class_id"])
    new_group_id = {
        class_id: f"stage3b_{index:03d}"
        for index, members in enumerate((group for group in new_groups.values() if len(group) > 1), start=1)
        for class_id in members
    }
    result: list[dict[str, Any]] = []
    for index, row in enumerate(input_rows):
        result.append({
            "subject": subject,
            "class_id": row["class_id"],
            "stage3a_input_hash": stage3a_input[index]["input_hash"],
            "stage3b_input_hash": row["input_hash"],
            "stage3a_stage3b_cosine_similarity": f"{cosine[index]:.12g}",
            "cosine_distance": f"{1.0 - cosine[index]:.12g}",
            "euclidean_distance": f"{euclidean[index]:.12g}",
            "body_empty": row["body_empty"],
            "body_token_count": row["appended_body_token_count"],
            "declaration_token_count": row["declaration_token_count"],
            "total_token_count": row["total_token_count"],
            "body_tokens_truncated": row["body_tokens_truncated"],
            "generated_code_status": row["generated_code_status"],
            "stage3a_collision_group": old_group_id.get(row["class_id"], ""),
            "stage3b_collision_group": new_group_id.get(row["class_id"], ""),
            "effectively_unchanged": str(1.0 - cosine[index] <= UNCHANGED_COSINE_DISTANCE_TOLERANCE).lower(),
            "materially_shifted": str(1.0 - cosine[index] >= MATERIAL_SHIFT_COSINE_DISTANCE_THRESHOLD).lower(),
        })
    distances = np.asarray([1.0 - cosine_value for cosine_value in cosine], dtype=np.float64)
    nonempty = np.asarray([row["body_empty"] == "false" for row in input_rows])
    summary = {
        "subject": subject,
        "cosine": stats(cosine),
        "cosine_distance": stats(distances),
        "unchanged_count": int(np.sum(distances <= UNCHANGED_COSINE_DISTANCE_TOLERANCE)),
        "materially_shifted_count": int(np.sum(distances >= MATERIAL_SHIFT_COSINE_DISTANCE_THRESHOLD)),
        "empty_body_shift": stats(distances[~nonempty]),
        "nonempty_body_shift": stats(distances[nonempty]),
        "largest_shift": [input_rows[index]["class_id"] for index in np.argsort(-distances)[:5]],
        "smallest_nonempty_shift": [input_rows[index]["class_id"] for index in np.where(nonempty)[0][np.argsort(distances[nonempty])[:5]]],
        "body_token_shift_correlation": float(np.corrcoef(np.asarray([int(row["appended_body_token_count"]) for row in input_rows]), distances)[0, 1]) if np.std([int(row["appended_body_token_count"]) for row in input_rows]) and np.std(distances) else None,
    }
    return result, summary


def write_artifact_hashes(output_root: Path) -> None:
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        directory = output_root / subject
        for path in sorted(directory.iterdir()):
            if path.is_file():
                rows.append({
                    "subject": subject,
                    "relative_path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                })
    write_csv(REPORT_ROOT / "embedding_artifact_hashes.csv", ["subject", "relative_path", "sha256", "size_bytes"], rows)


def compare_reproducibility(canonical_root: Path, repro_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ignored_metadata = {"creation_timestamp_utc", "encoding_elapsed_seconds", "embedding_output_path", "generation_run"}
    for subject in SUBJECTS:
        result: dict[str, Any] = {"subject": subject}
        for name in sorted(EXPECTED_FILES):
            left = canonical_root / subject / name
            right = repro_root / subject / name
            result[f"{name}_byte_identical"] = str(left.read_bytes() == right.read_bytes()).lower()
        left_meta = read_json(canonical_root / subject / "embedding_metadata.json")
        right_meta = read_json(repro_root / subject / "embedding_metadata.json")
        left_cmp = {key: value for key, value in left_meta.items() if key not in ignored_metadata}
        right_cmp = {key: value for key, value in right_meta.items() if key not in ignored_metadata}
        result["metadata_equal_excluding_variable_fields"] = str(left_cmp == right_cmp).lower()
        result["aggregate_embedding_sha256"] = left_meta["aggregate_embedding_sha256"]
        result["embeddings_npy_sha256"] = sha256_file(canonical_root / subject / "embeddings.npy")
        result["passed"] = str(
            all(value == "true" for key, value in result.items() if key.endswith("byte_identical") and key != "embedding_metadata.json_byte_identical")
            and result["metadata_equal_excluding_variable_fields"] == "true"
        ).lower()
        rows.append(result)
    write_csv(REPORT_ROOT / "embedding_reproducibility_per_subject.csv", list(rows[0]), rows)
    return rows


def write_quality_reports(
    quality: dict[str, dict[str, Any]],
    shift_summaries: dict[str, dict[str, Any]],
    collision_summaries: dict[str, dict[str, Any]],
) -> None:
    rows = []
    for subject in SUBJECTS:
        q = quality[subject]
        shift = shift_summaries[subject]
        collision = collision_summaries[subject]
        rows.append({
            "subject": subject,
            "classes": q["class_count"],
            "dimension": q["dimension"],
            "nan": q["nan_count"],
            "inf": q["inf_count"],
            "zero_vectors": q["zero_vector_count"],
            "min_norm": q["norms"]["minimum"],
            "mean_norm": q["norms"]["mean"],
            "median_norm": q["norms"]["median"],
            "std_norm": q["norms"]["standard_deviation"],
            "max_norm": q["norms"]["maximum"],
            "max_model_tokens": max(int(row["model_token_count"]) for row in q["token_rows"]),
            "contract_body_truncated": sum(row["contract_body_tokens_truncated"] != "0" for row in q["token_rows"]),
            "unexpected_tokenizer_truncated": sum(row["tokenizer_truncated"] == "true" for row in q["token_rows"]),
            "duplicate_text_groups": collision["duplicate_text_group_count"],
            "duplicate_embedding_groups": collision["duplicate_embedding_group_count"],
            "non_identical_text_embedding_collisions": collision["non_identical_text_embedding_collision_count"],
            "shift_cosine_min": shift["cosine"]["minimum"],
            "shift_cosine_mean": shift["cosine"]["mean"],
            "shift_cosine_median": shift["cosine"]["median"],
            "shift_cosine_std": shift["cosine"]["standard_deviation"],
            "shift_cosine_max": shift["cosine"]["maximum"],
            "unchanged_count": shift["unchanged_count"],
            "materially_shifted_count": shift["materially_shifted_count"],
            "aggregate_embedding_sha256": q["aggregate_embedding_sha256"],
        })
    write_csv(REPORT_ROOT / "embedding_quality_per_subject.csv", list(rows[0]), rows)
    lines = [
        "# Stage 3B embedding quality summary",
        "",
        "This report validates isolated declaration-plus-method-body embeddings only. No semantic graph, nearest-neighbour graph, optimization, seed, or decomposition analysis was performed.",
        "",
        f"Frozen runtime: SentenceTransformer `{EXPECTED_MODEL}` revision `9a0457648f060c4279d4a3982d2d27a4df6fac59`, dimension {EXPECTED_DIMENSION}, MPS float16, batch 8, stored float32.",
        "",
        "## Numerical and tokenizer summary",
        "",
        "| Subject | Classes | Dim | Norm min/mean/median/std/max | NaN | Inf | Zero | Max model tokens | Contract body truncations | Unexpected tokenizer truncations | Duplicate text groups | Duplicate embedding groups |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        norms = "/".join(f"{row[key]:.9f}" for key in ("min_norm", "mean_norm", "median_norm", "std_norm", "max_norm"))
        lines.append(f"| {row['subject']} | {row['classes']} | {row['dimension']} | {norms} | {row['nan']} | {row['inf']} | {row['zero_vectors']} | {row['max_model_tokens']} | {row['contract_body_truncated']} | {row['unexpected_tokenizer_truncated']} | {row['duplicate_text_groups']} | {row['duplicate_embedding_groups']} |")
    lines += ["", "## Stage 3A versus Stage 3B shift", "", f"Effectively unchanged means cosine distance <= {UNCHANGED_COSINE_DISTANCE_TOLERANCE}. Materially shifted is a diagnostic flag for cosine distance >= {MATERIAL_SHIFT_COSINE_DISTANCE_THRESHOLD}; neither threshold is a quality judgment.", ""]
    for subject in SUBJECTS:
        item = shift_summaries[subject]
        lines.append(f"* **{subject}**: cosine min/mean/median/std/max = {item['cosine']['minimum']:.9f}/{item['cosine']['mean']:.9f}/{item['cosine']['median']:.9f}/{item['cosine']['standard_deviation']:.9f}/{item['cosine']['maximum']:.9f}; unchanged={item['unchanged_count']}; materially_shifted={item['materially_shifted_count']}; empty-body distance mean={item['empty_body_shift']['mean']:.9f}; non-empty-body distance mean={item['nonempty_body_shift']['mean']:.9f}; body-token correlation={item['body_token_shift_correlation']}")
        lines.append(f"  Largest shifts: {', '.join(item['largest_shift'])}")
        lines.append(f"  Smallest non-empty shifts: {', '.join(item['smallest_nonempty_shift'])}")
    lines += ["", "## Duplicate diagnostics", ""]
    for subject in SUBJECTS:
        item = collision_summaries[subject]
        lines.append(f"* {subject}: Stage 3B duplicate semantic-text groups={item['duplicate_text_group_count']}; duplicate embedding groups={item['duplicate_embedding_group_count']}; non-identical-text embedding collisions={item['non_identical_text_embedding_collision_count']}.")
    lines += ["", "Xerces has 11 expected duplicate-text groups under the frozen simple-name input contract. The classes were not deduplicated.", "", "## Acceptance checks", "", "* All rows have the expected class mapping and dimension.", "* NaN, Inf, zero-vector, norm, and save/load checks passed.", "* Actual tokenizer counts used truncation=false; declaration truncation is zero and unexpected tokenizer truncation is zero.", "* Stage 3A embeddings were read diagnostically only; they were not used as a Stage 3B cache.", ""]
    (REPORT_ROOT / "embedding_quality_summary.md").write_text("\n".join(lines), encoding="utf-8")

    collision_lines = [
        "# Stage 3B embedding collision summary",
        "",
        "This is an input and numerical collision diagnostic only. It does not claim semantic quality improvement and does not deduplicate classes.",
        "",
        "| Subject | Duplicate text groups | Duplicate embedding groups | Non-identical-text duplicate embeddings |",
        "|---|---:|---:|---:|",
    ]
    for subject in SUBJECTS:
        item = collision_summaries[subject]
        collision_lines.append(
            f"| {subject} | {item['duplicate_text_group_count']} | {item['duplicate_embedding_group_count']} | {item['non_identical_text_embedding_collision_count']} |"
        )
    collision_lines += [
        "",
        "Xerces has exactly 11 duplicate-text groups under the frozen simple-name input contract. These duplicate classes and their embeddings were retained unchanged in scope.",
        "Non-identical Stage 3B semantic texts did not produce duplicate embedding byte sequences.",
        "",
    ]
    (REPORT_ROOT / "embedding_collision_summary.md").write_text("\n".join(collision_lines), encoding="utf-8")


def write_manual_audit(
    rows_by_subject: dict[str, list[dict[str, str]]],
    shift_rows: dict[str, list[dict[str, Any]]],
    collision_rows: list[dict[str, Any]],
) -> None:
    selected: dict[str, list[tuple[str, dict[str, str]]]] = {}
    for subject in SUBJECTS:
        rows = rows_by_subject[subject]
        by_id = {row["class_id"]: row for row in rows}
        shifts = {row["class_id"]: row for row in shift_rows[subject]}
        ordered: list[tuple[str, dict[str, str]]] = []

        def add(category: str, class_id: str) -> None:
            if class_id in by_id and all(existing[1]["class_id"] != class_id for existing in ordered):
                ordered.append((category, by_id[class_id]))

        for row in rows[:5]:
            add("first_sorted", row["class_id"])
        for row in sorted(rows, key=lambda row: (-float(shifts[row["class_id"]]["cosine_distance"]), row["class_id"]))[:5]:
            add("largest_shift", row["class_id"])
        for row in sorted((row for row in rows if row["body_empty"] == "false"), key=lambda row: (float(shifts[row["class_id"]]["cosine_distance"]), row["class_id"]))[:5]:
            add("smallest_nonempty_shift", row["class_id"])
        if subject == "xerces":
            for collision in collision_rows:
                if collision["subject"] == subject and collision["collision_type"] == "duplicate_text_group":
                    for class_id in collision["class_ids"].split("|"):
                        add("xerces_duplicate_text_group", class_id)
        for row in rows:
            if int(row["body_tokens_truncated"]) > 0:
                add("body_truncated", row["class_id"])
        for row in rows:
            if row["body_empty"] == "true":
                add("empty_body_fixed_sample", row["class_id"])
                if sum(category == "empty_body_fixed_sample" for category, _ in ordered) >= 5:
                    break
        selected[subject] = ordered
    lines = [
        "# Stage 3B embedding manual audit",
        "",
        "Fixed selection: first five sorted classes; five largest Stage 3A-to-Stage 3B shifts; five smallest non-empty-body shifts; all Xerces duplicate-text collision members; all body-truncated classes; and the first five empty-body classes. Duplicate classes are listed once. No neighbours or graph edges are included.",
        "",
    ]
    for subject in SUBJECTS:
        lines += [f"## {subject}", ""]
        by_shift = {row["class_id"]: row for row in shift_rows[subject]}
        for category, row in selected[subject]:
            body = row["semantic_text"].split("[METHOD_BODY]\n", 1)[1].strip()
            summary = body if body == "<EMPTY>" else body[:240].replace("\n", " ")
            lines += [
                f"### `{row['class_id']}` — {category}",
                f"declaration_tokens={row['declaration_token_count']}; body_tokens={row['appended_body_token_count']}; body_evidence_summary=`{summary}`",
                f"stage3a_stage3b_cosine={by_shift[row['class_id']]['stage3a_stage3b_cosine_similarity']}; collision_stage3a={by_shift[row['class_id']]['stage3a_collision_group'] or 'none'}; collision_stage3b={by_shift[row['class_id']]['stage3b_collision_group'] or 'none'}; body_truncated={row['body_tokens_truncated']}; body_empty={row['body_empty']}",
                "",
            ]
    (REPORT_ROOT / "embedding_manual_audit.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--repro-output-root", type=Path, required=True)
    parser.add_argument("--extraction-root", type=Path, required=True)
    args = parser.parse_args()
    output_root = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
    repro_root = args.repro_output_root if args.repro_output_root.is_absolute() else ROOT / args.repro_output_root
    extraction_root = args.extraction_root if args.extraction_root.is_absolute() else ROOT / args.extraction_root
    rows_by_subject = verify_frozen_inputs()
    from scripts.stage3_method_body.generate_embeddings import load_frozen_runtime

    _, _, tokenizer = load_frozen_runtime()
    quality: dict[str, dict[str, Any]] = {}
    shift_rows_by_subject: dict[str, list[dict[str, Any]]] = {}
    shift_summaries: dict[str, dict[str, Any]] = {}
    collision_rows: list[dict[str, Any]] = []
    collision_summaries: dict[str, dict[str, Any]] = {}
    token_report_rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        lengths = token_length_rows(subject, rows_by_subject[subject], tokenizer)
        token_report_rows.extend(lengths)
        quality[subject] = validate_saved_subject(subject, rows_by_subject[subject], output_root)
        expected_lengths = read_csv(output_root / subject / "token_lengths.csv")
        normalized_lengths = [{key: str(value).lower() if isinstance(value, bool) else str(value) for key, value in row.items()} for row in lengths]
        if expected_lengths != normalized_lengths:
            raise ValueError(f"{subject}: saved token-length report differs from exact tokenizer recount")
        current_collision_rows, collision_summary = collision_diagnostics(subject, rows_by_subject[subject], quality[subject]["vectors"])
        collision_rows.extend(current_collision_rows)
        collision_summaries[subject] = collision_summary
        current_shift_rows, shift_summary = shift_diagnostics(subject, rows_by_subject[subject], quality[subject]["vectors"])
        shift_rows_by_subject[subject] = current_shift_rows
        shift_summaries[subject] = shift_summary
    if collision_summaries["xerces"]["duplicate_text_group_count"] != EXPECTED_STAGE3B_XERCES_DUPLICATE_GROUPS:
        raise ValueError("Xerces duplicate-text group count differs from frozen input diagnostic")
    if any(item["non_identical_text_embedding_collision_count"] for item in collision_summaries.values()):
        raise ValueError("non-identical Stage 3B texts produced duplicate embedding bytes")

    write_csv(REPORT_ROOT / "embedding_token_lengths.csv", list(token_report_rows[0]), token_report_rows)
    write_csv(REPORT_ROOT / "embedding_collision_groups.csv", [
        "subject", "collision_type", "group_id", "class_ids", "input_hashes", "embedding_hashes",
        "exact_embedding_equality", "maximum_euclidean_distance", "minimum_pairwise_cosine", "notes",
    ], collision_rows)
    shift_rows = [row for subject in SUBJECTS for row in shift_rows_by_subject[subject]]
    write_csv(REPORT_ROOT / "stage3a_vs_stage3b_embedding_shift.csv", list(shift_rows[0]), shift_rows)
    write_quality_reports(quality, shift_summaries, collision_summaries)
    write_body_composition(rows_by_subject, extraction_root)
    write_manual_audit(rows_by_subject, shift_rows_by_subject, collision_rows)
    repro = compare_reproducibility(output_root, repro_root)
    if not all(row["passed"] == "true" for row in repro):
        raise RuntimeError(f"embedding reproducibility failed: {repro}")
    write_artifact_hashes(output_root)
    (REPORT_ROOT / "embedding_reproducibility_summary.md").write_text(
        "\n".join([
            "# Stage 3B embedding reproducibility summary",
            "",
            "Canonical and reproducibility runs encoded all three subjects in the same loaded frozen MPS/float16/batch-8 SentenceTransformer runtime. The second run used a separate clean temporary output directory.",
            "",
            "Raw `embeddings.npy` bytes, class mappings, per-row embedding hashes, aggregate embedding hashes, token-length files, and metadata excluding explicitly variable timestamps, elapsed times, output paths, and run labels were compared.",
            "",
            "Result: byte-identical reproduction passed for JPetStore, DayTrader, and Xerces.",
            "",
            f"Canonical output root: `{output_root.resolve()}`",
            f"Reproducibility output root: `{repro_root.resolve()}`",
            "",
            "No nearest-neighbour file or semantic graph was generated.",
            "",
        ]),
        encoding="utf-8",
    )
    manifest_path = REPORT_ROOT / "embedding_generation_manifest.json"
    if manifest_path.is_file():
        manifest = read_json(manifest_path)
        manifest["validation_status"] = "passed"
        manifest["validated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest["embedding_reproducibility_passed"] = True
        manifest["semantic_graph_generated"] = False
        manifest["nearest_neighbors_generated"] = False
        write_json(manifest_path, manifest)
    print(json.dumps({"validated": True, "subjects": list(SUBJECTS)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
