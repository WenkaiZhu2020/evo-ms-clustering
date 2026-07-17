#!/usr/bin/env python3
"""Construct isolated Stage 3B declaration-plus-method-body inputs."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from statistics import mean, median, pstdev
from typing import Any

import yaml
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.stage3_method_body.isolation import (
    EXPERIMENT_ID,
    REPRESENTATION_ID,
    STAGE3B_CONFIG,
    STAGE3B_REPORT_ROOT,
    STAGE3B_TEXT_ROOT,
    assert_declaration_source,
    assert_stage3b_write_path,
    assert_stage3b_temporary_path,
)
from scripts.stage3_method_body.method_body_normalization import (
    BODY_TOKEN_BUDGET,
    EMPTY_BODY,
    MethodBody,
    compose_semantic_text,
    extract_declaration_section,
    normalize_class_bodies,
)

SUBJECTS = ("jpetstore", "daytrader", "xerces")
EXTRACTION_VERSION = "soot_shimple_method_body_v1"
EXTRACTION_SUBJECT = {"jpetstore": "jpetstore", "daytrader": "daytrader", "xerces": "xerces-j"}
EXPECTED_COUNTS = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
STAGE3A_FILENAMES = {
    "jpetstore": "jpetstore_class_declarations.csv",
    "daytrader": "daytrader_class_declarations.csv",
    "xerces": "xerces-j_class_declarations.csv",
}
STAGE3A_SCHEMA = [
    "subject", "class_id", "class_name", "kind", "superclass_present", "semantic_text",
    "method_count", "annotation_count", "interface_count", "truncated_method_count", "input_hash",
]
BODY_SCHEMA = STAGE3A_SCHEMA + [
    "experiment_name", "representation_id", "stage3a_source_path", "stage3a_source_file_sha256",
    "stage3a_declaration_hash", "declaration_exact_match", "declaration_token_count",
    "raw_body_candidate_count", "filtered_body_token_count_before_budget", "appended_body_token_count",
    "body_model_token_count", "total_token_count", "body_tokens_truncated", "declaration_truncated",
    "body_empty", "extracted_concrete_method_count", "normalized_method_count", "synthetic_method_count",
    "generated_code_status", "accepted_invoked_method_tokens", "accepted_field_tokens",
    "accepted_local_tokens", "accepted_exception_tokens", "accepted_operation_tokens",
    "accepted_string_tokens", "accepted_literals", "rejected_token_count", "body_hash",
]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_hash_lines(rows: list[dict[str, str]], value_key: str) -> str:
    payload = "".join(
        f"{row['class_id']}\t{row[value_key]}\n"
        for row in sorted(rows, key=lambda item: item["class_id"])
    )
    return sha256_bytes(payload.encode("utf-8"))


def canonical_class_mapping_hash(rows: list[dict[str, str]]) -> str:
    payload = "".join(
        f"{row['class_id']}\n" for row in sorted(rows, key=lambda item: item["class_id"])
    )
    return sha256_bytes(payload.encode("utf-8"))


def generation_write_path(path: Path, *, kind: str) -> Path:
    """Allow the repository namespace and disposable outside-repo reruns."""
    try:
        return assert_stage3b_write_path(path, kind=kind)
    except ValueError:
        return assert_stage3b_temporary_path(path)


def report_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_rows(path: Path, expected_fields: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_fields:
            raise ValueError(f"{path}: expected schema {expected_fields}, got {reader.fieldnames}")
        return list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "stage3-declaration-final^{commit}"], cwd=ROOT, text=True
    ).strip()


def build_source_manifest(report_root: Path) -> dict[str, Any]:
    subjects: dict[str, Any] = {}
    for subject in SUBJECTS:
        path = assert_declaration_source(
            ROOT / "data/semantic_inputs" / STAGE3A_FILENAMES[subject], subject
        )
        rows = load_rows(path, STAGE3A_SCHEMA)
        if len(rows) != EXPECTED_COUNTS[subject]:
            raise ValueError(f"{subject}: expected {EXPECTED_COUNTS[subject]} declarations, got {len(rows)}")
        if len({row["class_id"] for row in rows}) != len(rows):
            raise ValueError(f"{subject}: duplicate declaration class_id")
        for row in rows:
            if sha256_bytes(row["semantic_text"].encode("utf-8")) != row["input_hash"]:
                raise ValueError(f"{subject}/{row['class_id']}: frozen input_hash is invalid")
        subjects[subject] = {
            "subject": subject,
            "source_path": str(path.relative_to(ROOT)),
            "source_sha256": sha256_file(path),
            "class_count": len(rows),
            "class_mapping_sha256": canonical_class_mapping_hash(rows),
            "stage3a_source_commit": source_commit(),
            "stage3a_tag": "stage3-declaration-final",
        }
    manifest = {
        "manifest_type": "stage3a_declaration_source",
        "representation_id": "declaration_v1",
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "subjects": subjects,
    }
    write_json(report_root / "stage3a_declaration_source_manifest.json", manifest)
    return manifest


def load_tokenizer() -> tuple[Any, dict[str, Any]]:
    config = yaml.safe_load(
        (ROOT / "configs/experiments/04_stage3_semantic.yml").read_text(encoding="utf-8")
    )
    tokenizer_config = config["tokenizer"]
    tokenizer = AutoTokenizer.from_pretrained(
        tokenizer_config["name"],
        revision=tokenizer_config["revision"],
        use_fast=True,
        trust_remote_code=False,
    )
    actual = int(tokenizer.model_max_length)
    expected = int(tokenizer_config["max_sequence_length"])
    if actual != expected:
        raise ValueError(f"pinned tokenizer length mismatch: config={expected}, tokenizer={actual}")
    return tokenizer, {
        "name": tokenizer_config["name"],
        "revision": tokenizer_config["revision"],
        "max_sequence_length": actual,
        "truncation": False,
        "add_special_tokens": True,
    }


def count_tokens(tokenizer: Any, text: str) -> int:
    encoded = tokenizer(
        text,
        truncation=False,
        add_special_tokens=True,
        return_attention_mask=False,
    )
    return len(encoded["input_ids"])


def fit_body_tokens(
    declaration: str,
    tokens: tuple[str, ...],
    tokenizer: Any,
    maximum: int,
) -> tuple[str, tuple[str, ...], int]:
    if count_tokens(tokenizer, declaration) > maximum:
        raise ValueError("frozen Stage 3A declaration alone exceeds tokenizer maximum")
    for count in range(len(tokens), -1, -1):
        body = " ".join(tokens[:count]) if count else EMPTY_BODY
        candidate = compose_semantic_text(declaration, body)
        if count_tokens(tokenizer, candidate) <= maximum:
            return body, tokens[:count], len(tokens) - count
    raise ValueError("unable to fit the mandatory empty body marker")


def method_rows_by_class(path: Path) -> dict[str, list[MethodBody]]:
    required = ["class_id", "method_name", "method_signature", "concrete", "synthetic", "body_text"]
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != required:
            raise ValueError(f"{path}: unexpected method-body schema {reader.fieldnames}")
        output: dict[str, list[MethodBody]] = {}
        for row in reader:
            output.setdefault(row["class_id"], []).append(
                MethodBody(
                    class_id=row["class_id"],
                    method_name=row["method_name"],
                    method_signature=row["method_signature"],
                    concrete=row["concrete"].lower() == "true",
                    synthetic=row["synthetic"].lower() == "true",
                    body_text=row["body_text"],
                )
            )
        return output


def stats(values: list[int | float]) -> dict[str, float | int]:
    if not values:
        return {"min": 0, "mean": 0.0, "median": 0.0, "std": 0.0, "max": 0}
    return {
        "min": min(values), "mean": mean(values), "median": median(values),
        "std": pstdev(values), "max": max(values),
    }


def prepare_subject(
    subject: str,
    extraction_root: Path,
    output_root: Path,
    source_manifest: dict[str, Any],
    tokenizer: Any,
    tokenizer_info: dict[str, Any],
    config_hash: str,
    contract_hash: str,
) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    source_path = ROOT / source_manifest["subjects"][subject]["source_path"]
    declaration_rows = load_rows(source_path, STAGE3A_SCHEMA)
    methods_path = extraction_root / EXTRACTION_SUBJECT[subject] / "method_bodies.csv"
    methods = method_rows_by_class(methods_path)
    expected_ids = {row["class_id"] for row in declaration_rows}
    extra = set(methods) - expected_ids
    if extra:
        raise ValueError(f"{subject}: method extraction contains extra classes: {sorted(extra)[:5]}")
    source_sha = source_manifest["subjects"][subject]["source_sha256"]
    subject_output = output_root / subject
    generation_write_path(subject_output, kind="semantic text")
    subject_output.mkdir(parents=True, exist_ok=True)
    output_rows: list[dict[str, str]] = []
    preservation_rows: list[dict[str, str]] = []
    quality_rows: list[dict[str, str]] = []
    feature_totals: dict[str, int] = {}
    filter_totals: dict[str, int] = {}
    literal_rows: list[dict[str, str]] = []
    generated_status = {"not_detected": 0, "compiler_synthetic_evidence": 0}

    for row in sorted(declaration_rows, key=lambda item: item["class_id"]):
        class_methods = methods.get(row["class_id"], [])
        normalized = normalize_class_bodies(class_methods)
        body, body_tokens, model_truncated = fit_body_tokens(
            row["semantic_text"], normalized.tokens_after_budget, tokenizer,
            tokenizer_info["max_sequence_length"],
        )
        semantic_text = compose_semantic_text(row["semantic_text"], body)
        declaration_section = extract_declaration_section(semantic_text)
        declaration_hash = sha256_bytes(declaration_section.encode("utf-8"))
        exact_match = declaration_section == row["semantic_text"]
        if not exact_match:
            raise ValueError(f"{subject}/{row['class_id']}: declaration preservation failed")
        input_hash = sha256_bytes(semantic_text.encode("utf-8"))
        counts = normalized.filter_counts
        synthetic_count = sum(1 for item in class_methods if item.synthetic)
        status = "compiler_synthetic_evidence" if synthetic_count else "not_detected"
        generated_status[status] += 1
        for key in (
            "accepted_invoked_method_tokens", "accepted_field_tokens", "accepted_local_tokens",
            "accepted_exception_tokens", "accepted_operation_tokens", "accepted_string_tokens",
        ):
            feature_totals[key] = feature_totals.get(key, 0) + int(getattr(counts, key))
        for key, value in counts.rejected_tokens.items():
            filter_totals[key] = filter_totals.get(key, 0) + value
        for index, audit in enumerate(normalized.literal_audit):
            literal_rows.append({
                "subject": subject, "class_id": row["class_id"], "literal_index": str(index),
                "decision": audit["decision"], "normalized_tokens": audit["normalized_tokens"],
            })
        base = {key: row[key] for key in STAGE3A_SCHEMA}
        base.update({
            "semantic_text": semantic_text, "input_hash": input_hash,
            "experiment_name": EXPERIMENT_ID, "representation_id": REPRESENTATION_ID,
            "stage3a_source_path": str(source_path.relative_to(ROOT)),
            "stage3a_source_file_sha256": source_sha, "stage3a_declaration_hash": row["input_hash"],
            "declaration_exact_match": str(exact_match).lower(),
            "declaration_token_count": str(count_tokens(tokenizer, row["semantic_text"])),
            "raw_body_candidate_count": str(counts.raw_candidate_count),
            "filtered_body_token_count_before_budget": str(len(normalized.tokens_before_budget)),
            "appended_body_token_count": str(len(body_tokens)),
            "body_model_token_count": str(count_tokens(tokenizer, body)),
            "total_token_count": str(count_tokens(tokenizer, semantic_text)),
            "body_tokens_truncated": str(normalized.tokens_truncated + model_truncated),
            "declaration_truncated": "false", "body_empty": str(body == EMPTY_BODY).lower(),
            "extracted_concrete_method_count": str(sum(1 for item in class_methods if item.concrete)),
            "normalized_method_count": str(normalized.method_count), "synthetic_method_count": str(synthetic_count),
            "generated_code_status": status,
            "accepted_invoked_method_tokens": str(counts.accepted_invoked_method_tokens),
            "accepted_field_tokens": str(counts.accepted_field_tokens), "accepted_local_tokens": str(counts.accepted_local_tokens),
            "accepted_exception_tokens": str(counts.accepted_exception_tokens), "accepted_operation_tokens": str(counts.accepted_operation_tokens),
            "accepted_string_tokens": str(counts.accepted_string_tokens), "accepted_literals": str(counts.accepted_literals),
            "rejected_token_count": str(sum(counts.rejected_tokens.values())),
            "body_hash": sha256_bytes(body.encode("utf-8")),
        })
        output_rows.append(base)
        preservation_rows.append({
            "subject": subject, "class_id": row["class_id"],
            "stage3a_source_path": str(source_path.relative_to(ROOT)),
            "stage3a_text_hash": row["input_hash"], "stage3b_declaration_hash": declaration_hash,
            "exact_match": str(exact_match).lower(),
        })
        quality_rows.append({
            "subject": subject, "class_id": row["class_id"], "class_name": row["class_name"],
            "declaration_token_count": base["declaration_token_count"], "body_token_count": base["appended_body_token_count"],
            "total_token_count": base["total_token_count"], "body_empty": base["body_empty"],
            "body_tokens_truncated": base["body_tokens_truncated"], "declaration_truncated": "false",
            "generated_code_status": status, "input_hash": input_hash,
        })

    write_csv(subject_output / "class_semantic_inputs.csv", BODY_SCHEMA, output_rows)
    write_csv(subject_output / "class_ids.csv", ["class_id", "row_index", "input_hash"], [
        {"class_id": row["class_id"], "row_index": str(index), "input_hash": row["input_hash"]}
        for index, row in enumerate(output_rows)
    ])
    aggregate_hash = canonical_hash_lines(output_rows, "input_hash")
    subject_manifest = {
        "experiment_name": EXPERIMENT_ID, "representation_id": REPRESENTATION_ID,
        "representation_version": "Body V1", "extraction_version": EXTRACTION_VERSION,
        "subject": subject, "class_count": len(output_rows),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "stage3a_source_commit": source_manifest["subjects"][subject]["stage3a_source_commit"],
        "stage3a_source_path": str(source_path.relative_to(ROOT)), "stage3a_source_sha256": source_sha,
        "class_mapping_sha256": canonical_class_mapping_hash(output_rows),
        "aggregate_input_sha256": aggregate_hash,
        "config_sha256": config_hash,
        "normalization_source_sha256": sha256_file(ROOT / "scripts/stage3_method_body/method_body_normalization.py"),
        "contract_sha256": contract_hash, "tokenizer": tokenizer_info,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    write_json(subject_output / "manifest.json", subject_manifest)
    summary = {
        "subject": subject, "class_count": len(output_rows),
        "empty_body_count": sum(row["body_empty"] == "true" for row in output_rows),
        "body_truncated_count": sum(int(row["body_tokens_truncated"]) > 0 for row in output_rows),
        "declaration_truncated_count": 0,
        "declaration_tokens": stats([int(row["declaration_token_count"]) for row in output_rows]),
        "body_tokens": stats([int(row["appended_body_token_count"]) for row in output_rows]),
        "total_tokens": stats([int(row["total_token_count"]) for row in output_rows]),
        "feature_totals": feature_totals, "filter_totals": filter_totals,
        "generated_code_status": generated_status, "aggregate_input_sha256": aggregate_hash,
    }
    write_json(subject_output / "quality_summary.json", summary)
    feature_rows = []
    for feature in ("invoked_method", "field", "local", "exception", "string"):
        key = f"accepted_{feature}_tokens"
        if feature == "invoked_method": key = "accepted_invoked_method_tokens"
        feature_rows.append({
            "subject": subject, "feature": feature, "accepted_token_count": str(feature_totals.get(key, 0)),
            "classes_with_feature": str(sum(int(row[key]) > 0 for row in output_rows)),
            "availability": "source_available" if feature != "local" else "source_local_metadata_not_reliable",
            "unavailable_reason": "synthetic locals rejected" if feature == "local" else "",
        })
    filter_rows = [{"subject": subject, "rule": key, "count": str(value)} for key, value in sorted(filter_totals.items())]
    filter_rows += [{"subject": subject, "rule": "accepted_literals", "count": str(sum(int(row["accepted_literals"]) for row in output_rows))}]
    return summary, preservation_rows, quality_rows, feature_rows, filter_rows, literal_rows


def markdown_summary(summaries: list[dict[str, Any]]) -> str:
    lines = [
        "# Stage 3B input quality summary", "",
        "This report is limited to semantic-input construction. It does not evaluate embeddings, graphs, optimization, or decomposition quality.", "",
        "| Subject | Classes | Empty body | Body truncated | Declaration truncated | Declaration tokens min/mean/median/std/max | Body tokens min/mean/median/std/max | Total tokens min/mean/median/std/max | Aggregate input SHA-256 |",
        "| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for item in summaries:
        def fmt(stats_value: dict[str, Any]) -> str:
            return "/".join(
                f"{stats_value[key]:.2f}" if isinstance(stats_value[key], float) else str(stats_value[key])
                for key in ("min", "mean", "median", "std", "max")
            )
        lines.append(
            f"| {item['subject']} | {item['class_count']} | {item['empty_body_count']} | {item['body_truncated_count']} | {item['declaration_truncated_count']} | {fmt(item['declaration_tokens'])} | {fmt(item['body_tokens'])} | {fmt(item['total_tokens'])} | `{item['aggregate_input_sha256']}` |"
        )
    lines += [
        "", "## Fixed gates", "",
        "* Scope is compared against the frozen Stage 3A class IDs.",
        "* Declaration preservation is byte-level and recorded in `declaration_preservation.csv`.",
        "* Declaration truncation is forbidden and must remain zero.",
        "* Body truncation is deterministic and body-only under the 256-token budget and tokenizer limit.",
        "* Raw Shimple, FQNs, owner names, type contexts, paths, and graph edges are excluded.",
        "", "## Feature and generated-code policy", "",
        "See `body_feature_availability.csv` and the per-class CSV. Source-level local-variable metadata was not reliable; synthetic locals were rejected. No class was removed for repetitive content; compiler synthetic-method evidence is reported.", "",
    ]
    return "\n".join(lines)


def compare_collision_groups(
    subject: str,
    declaration_rows: list[dict[str, str]],
    body_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    stage3a_groups: dict[str, list[str]] = {}
    stage3b_groups: dict[str, list[str]] = {}
    for row in declaration_rows:
        stage3a_groups.setdefault(row["input_hash"], []).append(row["class_id"])
    for row in body_rows:
        stage3b_groups.setdefault(row["input_hash"], []).append(row["class_id"])
    rows: list[dict[str, str]] = []
    by_class = {row["class_id"]: row for row in body_rows}
    for stage3a_hash, class_ids in sorted(stage3a_groups.items()):
        if len(class_ids) < 2:
            continue
        stage3b_hashes = {by_class[class_id]["input_hash"] for class_id in class_ids}
        if len(stage3b_hashes) == len(class_ids):
            status = "fully_resolved"
        elif len(stage3b_hashes) > 1:
            status = "partially_resolved"
        else:
            status = "unchanged"
        rows.append({
            "subject": subject,
            "stage3a_declaration_hash": stage3a_hash,
            "class_ids": "|".join(sorted(class_ids)),
            "stage3a_group_size": str(len(class_ids)),
            "stage3b_full_text_hashes": "|".join(sorted(stage3b_hashes)),
            "stage3b_distinct_hash_count": str(len(stage3b_hashes)),
            "status": status,
            "empty_body_classes": "|".join(sorted(class_id for class_id in class_ids if by_class[class_id]["body_empty"] == "true")),
        })
    stage3a_class_sets = {
        frozenset(class_ids) for class_ids in stage3a_groups.values() if len(class_ids) >= 2
    }
    for stage3b_hash, class_ids in sorted(stage3b_groups.items()):
        if len(class_ids) < 2 or frozenset(class_ids) in stage3a_class_sets:
            continue
        rows.append({
            "subject": subject,
            "stage3a_declaration_hash": "",
            "class_ids": "|".join(sorted(class_ids)),
            "stage3a_group_size": "",
            "stage3b_full_text_hashes": stage3b_hash,
            "stage3b_distinct_hash_count": "1",
            "status": "new_stage3b_collision",
            "empty_body_classes": "|".join(sorted(class_id for class_id in class_ids if by_class[class_id]["body_empty"] == "true")),
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extraction-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=STAGE3B_TEXT_ROOT)
    parser.add_argument("--report-root", type=Path, default=STAGE3B_REPORT_ROOT)
    parser.add_argument("--config", type=Path, default=STAGE3B_CONFIG)
    parser.add_argument("--contract", type=Path, default=STAGE3B_REPORT_ROOT / "method_body_input_contract.md")
    args = parser.parse_args()
    config = args.config if args.config.is_absolute() else ROOT / args.config
    if config.resolve() != STAGE3B_CONFIG.resolve():
        raise ValueError("Stage 3B generation must use the explicit 05 Stage 3B config")
    config_data = yaml.safe_load(config.read_text(encoding="utf-8"))
    if config_data["experiment_name"] != EXPERIMENT_ID or config_data["representation_id"] != REPRESENTATION_ID:
        raise ValueError("Stage 3B config identity is not frozen")
    output_root = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
    report_root = args.report_root if args.report_root.is_absolute() else ROOT / args.report_root
    extraction_root = args.extraction_root if args.extraction_root.is_absolute() else ROOT / args.extraction_root
    generation_write_path(output_root, kind="semantic text")
    generation_write_path(report_root, kind="input report")
    contract = args.contract if args.contract.is_absolute() else ROOT / args.contract
    config_hash = sha256_file(config)
    contract_hash = sha256_file(contract)
    source_manifest = build_source_manifest(report_root)
    tokenizer, tokenizer_info = load_tokenizer()
    summaries: list[dict[str, Any]] = []
    preservation_rows: list[dict[str, str]] = []
    quality_rows: list[dict[str, str]] = []
    feature_rows: list[dict[str, str]] = []
    filter_rows: list[dict[str, str]] = []
    literal_rows: list[dict[str, str]] = []
    collision_rows: list[dict[str, str]] = []
    input_hash_rows: list[dict[str, str]] = []
    for subject in SUBJECTS:
        result = prepare_subject(
            subject, extraction_root, output_root, source_manifest,
            tokenizer, tokenizer_info, config_hash, contract_hash,
        )
        summary, preservation, quality, features, filters, literals = result
        summaries.append(summary)
        preservation_rows.extend(preservation)
        quality_rows.extend(quality)
        feature_rows.extend(features)
        filter_rows.extend(filters)
        literal_rows.extend(literals)
        input_hash_rows.extend(
            {"subject": row["subject"], "class_id": row["class_id"], "input_hash": row["input_hash"]}
            for row in quality
        )
        declarations = load_rows(ROOT / source_manifest["subjects"][subject]["source_path"], STAGE3A_SCHEMA)
        body_rows = load_rows(output_root / subject / "class_semantic_inputs.csv", BODY_SCHEMA)
        collision_rows.extend(compare_collision_groups(subject, declarations, body_rows))
    write_csv(report_root / "declaration_preservation.csv", [
        "subject", "class_id", "stage3a_source_path", "stage3a_text_hash", "stage3b_declaration_hash", "exact_match"
    ], preservation_rows)
    write_csv(report_root / "input_quality_per_class.csv", list(quality_rows[0]), quality_rows)
    write_csv(report_root / "body_feature_availability.csv", [
        "subject", "feature", "accepted_token_count", "classes_with_feature", "availability", "unavailable_reason"
    ], feature_rows)
    write_csv(report_root / "body_token_filter_summary.csv", ["subject", "rule", "count"], filter_rows)
    write_csv(report_root / "body_string_literal_audit.csv", [
        "subject", "class_id", "literal_index", "decision", "normalized_tokens"
    ], literal_rows)
    write_csv(report_root / "method_body_input_hashes.csv", [
        "subject", "class_id", "input_hash",
    ], sorted(input_hash_rows, key=lambda row: (row["subject"], row["class_id"])))
    write_csv(report_root / "input_collision_comparison.csv", [
        "subject", "stage3a_declaration_hash", "class_ids", "stage3a_group_size",
        "stage3b_full_text_hashes", "stage3b_distinct_hash_count", "status", "empty_body_classes",
    ], collision_rows)
    manifest = {
        "experiment_name": EXPERIMENT_ID,
        "representation_id": REPRESENTATION_ID,
        "representation_version": "Body V1",
        "extraction_version": EXTRACTION_VERSION,
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "stage3a_source_manifest": report_path(report_root / "stage3a_declaration_source_manifest.json"),
        "config_sha256": config_hash,
        "contract_sha256": contract_hash,
        "tokenizer": tokenizer_info,
        "subjects": summaries,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    write_json(report_root / "stage3b_generation_summary.json", manifest)
    write_json(report_root / "method_body_input_manifest.json", {
        "status": "post_hoc_exploratory",
        "validation_status": "pending",
        "experiment_name": EXPERIMENT_ID,
        "representation_id": REPRESENTATION_ID,
        "extraction_version": EXTRACTION_VERSION,
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "stage3a_source_manifest": report_path(report_root / "stage3a_declaration_source_manifest.json"),
        "config_sha256": config_hash,
        "contract_sha256": contract_hash,
        "declaration_source": "frozen Stage 3A semantic_text bytes from data/semantic_inputs/*.csv",
        "body_evidence_types": [
            "invoked_method_simple_names", "field_simple_names", "permitted_local_identifiers",
            "exception_simple_names", "controlled_operation_words", "filtered_string_literal_tokens",
        ],
        "unavailable_evidence_types": [
            "reliable_source_level_local_metadata", "source_file_paths", "raw_jimple_statements",
        ],
        "structural_exclusions": [
            "package_paths", "fully_qualified_names", "invocation_owners", "declaring_classes",
            "source_paths", "imports", "dependency_edges", "caller_callee_pairs", "jvm_descriptors",
            "raw_signatures", "line_numbers", "bytecode_offsets", "jimple_labels", "soot_identifiers",
            "synthetic_locals", "type_context_after_new_instanceof_cast",
        ],
        "normalization": {
            "unicode": "NFKC", "identifier_splitting": ["camelCase", "PascalCase", "acronym", "snake_case", "kebab-case"],
            "lowercase": True, "token_pattern": "[a-z][a-z0-9]*", "minimum_token_length": 2,
            "getter_setter_policy": "drop leading get/set/is and retain remaining meaningful words",
            "generic_method_stopwords": sorted(["toString", "hashCode", "equals", "init", "clinit", "main", "run"]),
            "repeated_token_cap": 2,
        },
        "string_literal_policy": "deterministic 2-80 character lexical filter; reject URL/path/UUID/hash/numeric/encoded/boilerplate values",
        "generated_code_policy": "retain all classes; record compiler synthetic-method evidence; no downstream filtering",
        "tokenizer": tokenizer_info,
        "body_token_budget": BODY_TOKEN_BUDGET,
        "truncation_priority": ["complete_declaration", "unique_high_information_body_tokens", "lower_priority_body_tokens"],
        "declaration_truncated": False,
        "class_order": "class_id lexicographic",
        "method_order": "method_name then method_signature lexicographic",
        "artifact_paths": {
            "semantic_text_root": "data/semantic_text/declaration_method_body/",
            "report_root": "reports/stage3_method_body/",
            "input_hashes": "reports/stage3_method_body/method_body_input_hashes.csv",
        },
        "expected_class_counts": EXPECTED_COUNTS,
        "aggregate_input_sha256": {item["subject"]: item["aggregate_input_sha256"] for item in summaries},
        "validation_gates": {
            "exact_scope": "required", "declaration_preservation": "required",
            "zero_declaration_truncation": "required", "no_structural_leakage": "required",
            "deterministic_regeneration": "required", "focused_tests": "required",
            "soot_extractor_tests": "required",
        },
        "downstream_unchanged": ["embedding", "graph", "objective", "NSGA-II", "seeds", "evaluation"],
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    (report_root / "input_quality_summary.md").write_text(markdown_summary(summaries), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
