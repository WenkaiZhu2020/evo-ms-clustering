#!/usr/bin/env python3
"""Validate the isolated Stage 3B semantic-input dataset."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.stage3_method_body.isolation import (
    STAGE3B_REPORT_ROOT,
    STAGE3B_TEXT_ROOT,
    assert_declaration_source,
    assert_stage3b_write_path,
)
from scripts.stage3_method_body.method_body_normalization import extract_declaration_section
from scripts.stage3_method_body.prepare_inputs import (
    EXPECTED_COUNTS,
    STAGE3A_FILENAMES,
    STAGE3A_SCHEMA,
    BODY_SCHEMA,
    canonical_hash_lines,
    load_rows,
    write_csv,
)


SUBJECTS = ("jpetstore", "daytrader", "xerces")

LEAKAGE_PATTERNS = [
    ("fqn", re.compile(r"(?:\b[a-z_][a-z0-9_]*\.)+[A-Z][A-Za-z0-9_$]*")),
    ("path_separator", re.compile(r"/")),
    ("machine_path", re.compile(r"(?i)(?:/Users/|/home/|data/raw_projects|target/classes|src/main)")),
    ("jvm_descriptor", re.compile(r"(?:\b[BCDFIJSZ]\b|L[A-Za-z_$][\w/$]*;)")),
    ("raw_owner_signature", re.compile(r"<[^>]+:\s*[^>]+>")),
    ("edge_serialization", re.compile(r"->|-->|\bedge\(")),
    ("jimple_syntax", re.compile(r"\b(?:virtualinvoke|interfaceinvoke|specialinvoke|staticinvoke|goto|tableswitch|lookupswitch)\b")),
    ("jimple_label", re.compile(r"\b(?:label|target|loc)\d+\b", re.IGNORECASE)),
    ("temporary_local", re.compile(r"\b\$?(?:r|i|l|f|d|b|c|z|u|tmp|temp|stack|parameter|arg|local)\d+\b", re.IGNORECASE)),
    ("build_or_source_path", re.compile(r"(?i)(?:maven|gradle|target/classes|src/main|src/test|classpath/|META-INF/)")),
    ("line_or_bytecode_offset", re.compile(r"(?i)\b(?:line|offset|bytecode)\s*[:=]?\s*\d+\b")),
    ("url", re.compile(r"(?i)\b(?:https?|ftp)://|\bwww\.")),
    ("uuid", re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b")),
]


def read_body_rows(root: Path, subject: str) -> list[dict[str, str]]:
    return load_rows(root / subject / "class_semantic_inputs.csv", BODY_SCHEMA)


def leakage_checks(rows: list[dict[str, str]], subject: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for row in rows:
        text = row["semantic_text"]
        for check, pattern in LEAKAGE_PATTERNS:
            match = pattern.search(text)
            findings.append({
                "subject": subject,
                "class_id": row["class_id"],
                "check": check,
                "matched_text": match.group(0)[:120] if match else "",
                "status": "FAIL" if match else "PASS",
            })
    return findings


def manual_sample(rows: list[dict[str, str]], collision_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    ordered = sorted(rows, key=lambda row: row["class_id"])
    selected: list[str] = []
    selected.extend(row["class_id"] for row in ordered[:3])
    for collision in collision_rows:
        selected.extend(collision["class_ids"].split("|"))
    selected.extend(row["class_id"] for row in sorted(rows, key=lambda row: (-int(row["total_token_count"]), row["class_id"]))[:1])
    empty = [row["class_id"] for row in ordered if row["body_empty"] == "true"]
    selected.extend(empty[:1])
    step = max(1, len(ordered) // 10)
    selected.extend(ordered[index]["class_id"] for index in range(0, len(ordered), step))
    selected_ids = []
    for class_id in selected:
        if class_id not in selected_ids:
            selected_ids.append(class_id)
        if len(selected_ids) >= 10:
            break
    by_id = {row["class_id"]: row for row in rows}
    return [by_id[class_id] for class_id in selected_ids]


def write_leakage_report(report_root: Path, all_rows: dict[str, list[dict[str, str]]], collision_rows: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    findings = [finding for subject in SUBJECTS for finding in leakage_checks(all_rows[subject], subject)]
    write_csv(report_root / "method_body_leakage_findings.csv", [
        "subject", "class_id", "check", "matched_text", "status",
    ], findings)
    lines = [
        "# Method-body leakage audit", "",
        "The automated checks inspect the decoded `semantic_text` field only.",
        "The fixed manual sample was selected before inspection as: first three sorted class IDs, all classes in prior Stage 3A collision groups, the maximum-total-token class, the first empty-body class, then every `floor(class_count/10)`-th sorted class, retaining the first ten distinct classes.", "",
        "No embedding, graph, optimization, or downstream result was inspected.", "",
        "## Automated result", "",
        f"* Checked {len(findings)} subject/class/check combinations.",
        f"* Failures: {sum(finding['status'] == 'FAIL' for finding in findings)}.", "",
    ]
    for subject in SUBJECTS:
        lines += [f"## Manual sample: {subject}", ""]
        collision = collision_rows[subject]
        for row in manual_sample(all_rows[subject], collision):
            lines += [
                f"### `{row['class_id']}`",
                f"Tokens: declaration={row['declaration_token_count']}, body={row['appended_body_token_count']}, total={row['total_token_count']}; body_empty={row['body_empty']}",
                "", "```text", row["semantic_text"].rstrip("\n"), "```", "",
            ]
    (report_root / "method_body_leakage_audit.md").write_text("\n".join(lines), encoding="utf-8")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, default=STAGE3B_TEXT_ROOT)
    parser.add_argument("--report-root", type=Path, default=STAGE3B_REPORT_ROOT)
    args = parser.parse_args()
    input_root = args.input_root if args.input_root.is_absolute() else ROOT / args.input_root
    report_root = args.report_root if args.report_root.is_absolute() else ROOT / args.report_root
    assert_stage3b_write_path(report_root, kind="validation report")
    all_rows: dict[str, list[dict[str, str]]] = {}
    preservation_rows: list[dict[str, str]] = []
    collision_rows: dict[str, list[dict[str, str]]] = {}
    for subject in SUBJECTS:
        source = assert_declaration_source(ROOT / "data/semantic_inputs" / STAGE3A_FILENAMES[subject], subject)
        declarations = load_rows(source, STAGE3A_SCHEMA)
        rows = read_body_rows(input_root, subject)
        if len(rows) != EXPECTED_COUNTS[subject]:
            raise ValueError(f"{subject}: expected {EXPECTED_COUNTS[subject]} rows, got {len(rows)}")
        if {row["class_id"] for row in rows} != {row["class_id"] for row in declarations}:
            raise ValueError(f"{subject}: Stage 3B class scope differs from Stage 3A")
        for row in rows:
            declaration = extract_declaration_section(row["semantic_text"])
            exact = declaration == next(item["semantic_text"] for item in declarations if item["class_id"] == row["class_id"])
            preservation_rows.append({
                "subject": subject, "class_id": row["class_id"],
                "stage3a_source_path": str(source.relative_to(ROOT)),
                "stage3a_text_hash": next(item["input_hash"] for item in declarations if item["class_id"] == row["class_id"]),
                "stage3b_declaration_hash": hashlib.sha256(declaration.encode("utf-8")).hexdigest(),
                "exact_match": str(exact).lower(),
            })
        all_rows[subject] = rows
        collision_path = report_root / "input_collision_comparison.csv"
        collision_rows[subject] = []
        if collision_path.is_file():
            with collision_path.open("r", encoding="utf-8", newline="") as handle:
                collision_rows[subject] = [row for row in csv.DictReader(handle) if row["subject"] == subject]
    write_csv(report_root / "declaration_preservation.csv", [
        "subject", "class_id", "stage3a_source_path", "stage3a_text_hash", "stage3b_declaration_hash", "exact_match",
    ], preservation_rows)
    findings = write_leakage_report(report_root, all_rows, collision_rows)
    summary_path = report_root / "input_quality_summary.md"
    summary_text = summary_path.read_text(encoding="utf-8") if summary_path.is_file() else ""
    if "## Collision comparison" in summary_text:
        summary_text = summary_text.split("## Collision comparison", 1)[0].rstrip() + "\n"
    lines = [summary_text, "## Collision comparison", ""]
    for subject in SUBJECTS:
        rows = collision_rows[subject]
        stage3b_hash_groups: dict[str, list[str]] = {}
        for row in all_rows[subject]:
            stage3b_hash_groups.setdefault(row["input_hash"], []).append(row["class_id"])
        duplicate_stage3b = [ids for ids in stage3b_hash_groups.values() if len(ids) > 1]
        new_stage3b = sum(row["status"] == "new_stage3b_collision" for row in rows)
        status_counts: dict[str, int] = {}
        for row in rows:
            status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
        lines.append(
            f"* {subject}: {len(rows)} Stage 3A collision groups; statuses: "
            + json.dumps(status_counts, sort_keys=True)
            + f"; {len(duplicate_stage3b)} Stage 3B full-text collision groups; "
            + f"{new_stage3b} new Stage 3B groups."
        )
    lines += ["", "## Leakage gate", "", f"Automated failures: {sum(item['status'] == 'FAIL' for item in findings)}. Any confirmed prohibited leakage blocks input acceptance.", ""]
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    passed = all(item["status"] == "PASS" for item in findings) and all(
        row["exact_match"] == "true" for row in preservation_rows
    )
    manifest_path = report_root / "method_body_input_manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["validation_status"] = "passed" if passed else "failed"
        manifest["validated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest["validation_gates"] = {
            "exact_scope": passed,
            "declaration_preservation": all(row["exact_match"] == "true" for row in preservation_rows),
            "zero_declaration_truncation": all(row["declaration_truncated"] == "false" for subject in all_rows.values() for row in subject),
            "no_structural_leakage": all(item["status"] == "PASS" for item in findings),
            "deterministic_regeneration": "see input_reproducibility_summary.md",
            "focused_tests": "see test results",
            "soot_extractor_tests": "see Maven test results",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
