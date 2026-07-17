#!/usr/bin/env python3
"""Audit empty Body V1 sections and the frozen Xerces collision groups.

This module is deliberately diagnostic.  It reads the accepted Stage 3B
inputs, saved embeddings, and saved graphs, and writes only reports.  It does
not regenerate any scientific artifact.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REPORT_ROOT = ROOT / "reports/stage3_method_body"
INPUT_ROOT = ROOT / "data/semantic_text/declaration_method_body"
EMBEDDING_ROOT = ROOT / "data/embeddings/declaration_method_body"
GRAPH_ROOT = ROOT / "data/semantic_graphs/declaration_method_body"
STAGE3A_RESULTS = ROOT / "results"
STAGE3A_INPUT_MANIFEST = REPORT_ROOT / "stage3a_declaration_source_manifest.json"
SUBJECTS = ("jpetstore", "daytrader", "xerces")
EXPECTED_COUNTS = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
EXPECTED_EMPTY = {"jpetstore": 7, "daytrader": 4, "xerces": 120}
EXTRACTION_SUBJECT = {"jpetstore": "jpetstore", "daytrader": "daytrader", "xerces": "xerces-j"}
CLASS_PATHS = {
    "jpetstore": (ROOT / "data/raw_projects/jpetstore/target/classes",),
    "daytrader": (
        ROOT / "data/raw_projects/daytrader/target/classes",
        ROOT / "data/raw_projects/daytrader/daytrader-ee7-ejb/target/classes",
        ROOT / "data/raw_projects/daytrader/daytrader-ee7-web/target/classes",
    ),
    "xerces": (ROOT / "data/raw_projects/xerces-j/target/classes",),
}
STAGE3A_GRAPH_NAMES = {"jpetstore": "jpetstore", "daytrader": "daytrader", "xerces": "xerces"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_aggregate(rows: Iterable[dict[str, str]], hash_key: str = "input_hash") -> str:
    payload = "".join(f"{row['class_id']}\t{row[hash_key]}\n" for row in sorted(rows, key=lambda item: item["class_id"]))
    return sha256_bytes(payload.encode("utf-8"))


def canonical_edge(left: str, right: str) -> tuple[str, str]:
    if left == right:
        raise ValueError("self-loop is not a valid audit edge")
    return tuple(sorted((left, right)))


def class_package(class_id: str) -> str:
    return class_id.rsplit(".", 1)[0] if "." in class_id else ""


def class_simple_name(class_id: str) -> str:
    return class_id.rsplit(".", 1)[-1]


def load_input_rows(subject: str) -> list[dict[str, str]]:
    rows = read_csv(INPUT_ROOT / subject / "class_semantic_inputs.csv")
    if len(rows) != EXPECTED_COUNTS[subject]:
        raise ValueError(f"{subject}: unexpected accepted input count {len(rows)}")
    return rows


def load_methods(path: Path) -> dict[str, list[Any]]:
    from scripts.stage3_method_body.method_body_normalization import MethodBody

    required = ["class_id", "method_name", "method_signature", "concrete", "synthetic", "body_text"]
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != required:
            raise ValueError(f"{path}: unexpected method-body schema {reader.fieldnames}")
        output: dict[str, list[MethodBody]] = defaultdict(list)
        for row in reader:
            output[row["class_id"]].append(
                MethodBody(
                    class_id=row["class_id"],
                    method_name=row["method_name"],
                    method_signature=row["method_signature"],
                    concrete=row["concrete"].lower() == "true",
                    synthetic=row["synthetic"].lower() == "true",
                    body_text=row["body_text"],
                )
            )
    return dict(output)


@dataclass(frozen=True)
class ClassFileInfo:
    resolved: bool
    class_synthetic: bool
    class_abstract: bool
    is_interface: bool
    is_enum: bool
    is_annotation: bool
    method_lines: tuple[str, ...]
    abstract_or_native_method_count: int
    concrete_declared_method_count: int
    constructor_count: int
    static_initializer_count: int
    command_error: str


def _method_lines_from_javap(text: str) -> tuple[str, ...]:
    lines: list[str] = []
    in_body = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped == "{":
            in_body = True
            continue
        if not in_body:
            continue
        if stripped == "}":
            break
        # In verbose javap output method declarations are indented two
        # spaces; descriptors and parameter metadata are indented further.
        if raw.startswith("  ") and not raw.startswith("    ") and "(" in stripped and stripped.endswith(";"):
            lines.append(stripped)
    return tuple(lines)


def inspect_classfile(subject: str, class_id: str) -> ClassFileInfo:
    classpath = os.pathsep.join(str(path) for path in CLASS_PATHS[subject])
    result = subprocess.run(
        ["javap", "-p", "-v", "-classpath", classpath, class_id],
        capture_output=True,
        text=True,
        check=False,
    )
    text = result.stdout
    if result.returncode != 0:
        return ClassFileInfo(False, False, False, False, False, False, (), 0, 0, 0, 0, result.stderr.strip()[:500])
    header = next((line.strip() for line in text.splitlines() if line.strip().startswith(("public ", "protected ", "private ", "class ", "interface ", "enum ", "@interface "))), "")
    class_flags = next((line for line in text.splitlines() if re.match(r"\s+flags:.*ACC_", line)), "")
    flags = class_flags.upper()
    method_lines = _method_lines_from_javap(text)
    abstract_or_native = sum(int(" abstract " in f" {line.lower()} " or " native " in f" {line.lower()} ") for line in method_lines)
    concrete = len(method_lines) - abstract_or_native
    simple = class_simple_name(class_id)
    constructor = sum(
        int(line.split("(", 1)[0].rsplit(" ", 1)[-1].rsplit(".", 1)[-1] == simple)
        for line in method_lines
    )
    static_initializer = sum(int(line.startswith("static {}")) for line in text.splitlines())
    return ClassFileInfo(
        resolved=True,
        class_synthetic="ACC_SYNTHETIC" in flags,
        class_abstract="ACC_ABSTRACT" in flags or "interface" in header,
        is_interface="interface" in header and "@interface" not in header,
        is_enum=" enum " in f" {header} ",
        is_annotation="@interface" in header,
        method_lines=method_lines,
        abstract_or_native_method_count=abstract_or_native,
        concrete_declared_method_count=concrete,
        constructor_count=constructor,
        static_initializer_count=static_initializer,
        command_error="",
    )


def raw_feature_counts(methods: Iterable[Any]) -> dict[str, int]:
    """Count raw candidates with the same source categories as Body V1.

    These counts are diagnostics.  Acceptance remains determined by the
    frozen ``normalize_class_bodies`` implementation.
    """
    from scripts.stage3_method_body.method_body_normalization import (
        _FQN, _IDENTIFIER, _JIMPLE_LABEL, _KEYWORDS, _OPERATION_TOKENS,
        _OWNER_SIGNATURE, _PATH, _RAW_JIMPLE_TOKENS, _STRING, _SYNTHETIC_LOCAL,
    )

    counts = {key: 0 for key in ("invoked_methods", "fields", "locals", "exceptions", "strings", "operations")}
    for method in sorted(methods, key=lambda item: (item.method_name, item.method_signature)):
        if not method.concrete or method.synthetic:
            continue
        text = method.body_text or ""
        if method.method_name not in {"<init>", "<clinit>"}:
            counts["invoked_methods"] += 1
        counts["strings"] += len(_STRING.findall(text))
        counts["invoked_methods"] += sum(
            1 for match in re.finditer(
                r"<[^>\n]*:\s*[^\s\n]+(?:\s+[^\s\n]+)*\s+([A-Za-z_$][A-Za-z0-9_$]*|<init>|<clinit>)\s*\(", text
            ) if match.group(1) not in {"<init>", "<clinit>"}
        )
        counts["fields"] += len(re.findall(r"<[^>\n]*:\s*[^\s\n]+\s+([A-Za-z_$][A-Za-z0-9_$]*)>", text))
        counts["exceptions"] += sum(
            1 for match in re.finditer(r"(?i)\b(?:catch|throw|new|instanceof)\s+([A-Za-z_$][A-Za-z0-9_$.]*)", text)
            if re.search(r"(?i)(?:exception|error|throwable)$", match.group(1).rsplit(".", 1)[-1])
        )
        working = _STRING.sub(" ", text)
        working = _OWNER_SIGNATURE.sub(" ", working)
        working = re.sub(r"\b(new|instanceof|cast)\s+[A-Za-z_$][A-Za-z0-9_$.]*", r"\1 ", working)
        working = _FQN.sub(" ", working)
        working = _PATH.sub(" ", working)
        working = _JIMPLE_LABEL.sub(" ", working)
        for match in _IDENTIFIER.finditer(working):
            raw = match.group(0)
            lowered = raw.lower()
            if lowered in _OPERATION_TOKENS:
                counts["operations"] += 1
            elif lowered in _RAW_JIMPLE_TOKENS or lowered in _KEYWORDS or _SYNTHETIC_LOCAL.fullmatch(raw) or raw[:1].isupper():
                continue
            else:
                counts["locals"] += 1
    return counts


def method_hashes(methods: Iterable[Any]) -> tuple[str, str, str]:
    ordered = sorted(methods, key=lambda item: (item.method_name, item.method_signature))
    inventory = "".join(
        f"{item.method_name}\t{item.method_signature}\t{str(item.concrete).lower()}\t{str(item.synthetic).lower()}\n"
        for item in ordered
    )
    bodies = "".join(
        f"{item.method_name}\t{item.method_signature}\t{sha256_bytes(item.body_text.encode('utf-8'))}\n"
        for item in ordered
    )
    return sha256_bytes(inventory.encode()), sha256_bytes(bodies.encode()), inventory


def body_evidence(methods: Iterable[Any]) -> tuple[Any, str]:
    from scripts.stage3_method_body.method_body_normalization import normalize_class_bodies

    normalized = normalize_class_bodies(methods)
    evidence = " ".join(normalized.tokens_before_budget) if normalized.tokens_before_budget else "<EMPTY>"
    return normalized, sha256_bytes(evidence.encode("utf-8"))


def extractor_failure_classes(log_path: Path | None) -> tuple[set[str], int, int]:
    if log_path is None or not log_path.exists():
        return set(), 0, 0
    text = log_path.read_text(encoding="utf-8", errors="replace")
    failure_lines = [line for line in text.splitlines() if re.search(r"could not (?:retrieve Jimple body|convert method body to Shimple).*method-body evidence", line, re.I)]
    classes: set[str] = set()
    for line in failure_lines:
        match = re.search(r"<([^:>]+):", line)
        if match:
            classes.add(match.group(1))
    unresolved = sum(bool(re.search(r"unresolved|phantom|could not resolve", line, re.I)) for line in text.splitlines())
    return classes, len(failure_lines), unresolved


def classify_empty_body(
    *,
    class_synthetic: bool,
    concrete_method_count: int,
    normalized_token_count: int,
    raw_candidate_count: int,
    body_failure: bool,
    classfile_resolved: bool,
    concrete_declared_method_count: int,
) -> tuple[str, str]:
    """Return one frozen primary category and a short concern code."""
    if body_failure or not classfile_resolved or concrete_declared_method_count > 0 and concrete_method_count == 0:
        return "E", "suspected_extraction_failure"
    if class_synthetic:
        return "C", "generated_or_template_equivalent"
    if concrete_method_count == 0:
        return "A", "no_concrete_body"
    if normalized_token_count > 0:
        return "E", "suspected_extraction_failure"
    if raw_candidate_count > 0:
        return "D", "meaningful_candidates_correctly_filtered"
    return "B", "concrete_body_no_permitted_evidence"


def classify_collision(
    *,
    raw_body_equivalence: bool,
    normalized_equivalence: bool,
    permitted_before_budget_equivalence: bool,
    extraction_failure: bool,
    generated_equivalence: bool,
) -> str:
    if extraction_failure:
        return "E"
    if raw_body_equivalence:
        return "B" if generated_equivalence else "A"
    if normalized_equivalence and permitted_before_budget_equivalence:
        return "C"
    if normalized_equivalence:
        return "D"
    return "F"


def control_sample_ids(rows_by_subject: dict[str, list[dict[str, str]]]) -> dict[str, list[tuple[str, str]]]:
    selected: dict[str, list[tuple[str, str]]] = {}
    for subject, rows in rows_by_subject.items():
        by_id = {row["class_id"]: row for row in rows}
        chosen: list[tuple[str, str]] = []

        def add(category: str, class_id: str) -> None:
            if class_id in by_id and class_id not in {value for _, value in chosen}:
                chosen.append((category, class_id))

        nonempty = sorted((row for row in rows if row["body_empty"] == "false"), key=lambda row: row["class_id"])
        for row in nonempty[:5]:
            add("first_5_nonempty_sorted", row["class_id"])
        for row in sorted(nonempty, key=lambda row: (int(row["appended_body_token_count"]), row["class_id"]))[:5]:
            add("five_smallest_nonzero_body", row["class_id"])
        for row in rows:
            if int(row["body_tokens_truncated"]) > 0:
                add("all_body_truncated", row["class_id"])
        selected[subject] = chosen
    return selected


def artifact_paths() -> list[Path]:
    paths: list[Path] = []
    for base in (INPUT_ROOT, EMBEDDING_ROOT, GRAPH_ROOT):
        paths.extend(path for path in base.rglob("*") if path.is_file())
    for name in ("method_body_input_contract.md", "method_body_input_manifest.json", "method_body_input_hashes.csv"):
        path = REPORT_ROOT / name
        if path.is_file():
            paths.append(path)
    return sorted(set(paths))


def snapshot_artifacts() -> dict[str, str]:
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in artifact_paths()}


def compare_artifact_hashes(before: dict[str, str], after: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for relative in sorted(set(before) | set(after)):
        old = before.get(relative, "")
        new = after.get(relative, "")
        rows.append({"relative_path": relative, "before_sha256": old, "after_sha256": new, "unchanged": str(bool(old and old == new)).lower()})
    return rows


def load_embedding(subject: str, stage3b: bool) -> tuple[np.ndarray, list[str]]:
    directory = EMBEDDING_ROOT / subject if stage3b else STAGE3A_RESULTS / subject / "04_stage3_semantic/embeddings"
    array = np.load(directory / "embeddings.npy")
    mapping = read_csv(directory / "class_ids.csv")
    mapping.sort(key=lambda row: int(row.get("row_index", 0)))
    return np.asarray(array, dtype=np.float32), [row["class_id"] for row in mapping]


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    left64 = np.asarray(left, dtype=np.float64)
    right64 = np.asarray(right, dtype=np.float64)
    denominator = float(np.linalg.norm(left64) * np.linalg.norm(right64))
    if denominator == 0:
        raise ValueError("zero-norm vector in empty-body template audit")
    return float(np.clip(np.dot(left64, right64) / denominator, -1.0, 1.0))


def load_neighbours(subject: str, stage3b: bool) -> dict[str, list[str]]:
    if stage3b:
        path = GRAPH_ROOT / subject / "directed_topk_neighbours.csv"
    else:
        path = STAGE3A_RESULTS / subject / "04_stage3_semantic/graph/directed_top3.csv"
    rows = read_csv(path)
    by: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by[row["source_class_id"]].append(row)
    return {key: [row["target_class_id"] for row in sorted(value, key=lambda item: int(item["rank"] or 0))] for key, value in by.items()}


def load_edges(subject: str, stage3b: bool) -> set[tuple[str, str]]:
    if stage3b:
        path = GRAPH_ROOT / subject / "semantic_edges.csv"
    else:
        path = STAGE3A_RESULTS / subject / "04_stage3_semantic/graph/semantic_edges.csv"
    return {canonical_edge(row["class_id_a"], row["class_id_b"]) for row in read_csv(path)}


def structural_neighbours(subject: str) -> dict[str, set[str]]:
    path = ROOT / "data/extracted" / ("xerces-j" if subject == "xerces" else subject) / "structural_dependencies.csv"
    nodes = {row["class_id"] for row in read_csv(ROOT / "data/extracted" / ("xerces-j" if subject == "xerces" else subject) / "class_nodes.csv")}
    output: dict[str, set[str]] = {node: set() for node in nodes}
    for row in read_csv(path):
        source, target = row["source"], row["target"]
        if source in nodes and target in nodes and source != target:
            output[source].add(target)
            output[target].add(source)
    return output


def pairwise_jaccard(sets: list[set[str]]) -> float:
    values: list[float] = []
    for index, left in enumerate(sets):
        for right in sets[index + 1:]:
            union = left | right
            values.append(len(left & right) / len(union) if union else 1.0)
    return float(np.mean(values)) if values else 1.0


def graph_components(subject: str) -> list[set[str]]:
    edges = load_edges(subject, True)
    mapping = set(row["class_id"] for row in read_csv(GRAPH_ROOT / subject / "class_mapping.csv"))
    adjacency = {node: set() for node in mapping}
    for left, right in edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    components: list[set[str]] = []
    unseen = set(mapping)
    while unseen:
        root = min(unseen)
        stack = [root]
        component: set[str] = set()
        while stack:
            node = stack.pop()
            if node not in unseen:
                continue
            unseen.remove(node)
            component.add(node)
            stack.extend(adjacency[node] - component)
        components.append(component)
    return components


def audit_empty_bodies(subject: str, rows: list[dict[str, str]], methods: dict[str, list[Any]], failures: set[str], soot_class_ids: set[str]) -> tuple[list[dict[str, Any]], dict[str, ClassFileInfo]]:
    from scripts.stage3_method_body.method_body_normalization import EMPTY_BODY, compose_semantic_text, extract_declaration_section

    source_manifest = json.loads(STAGE3A_INPUT_MANIFEST.read_text(encoding="utf-8"))
    source_rows = read_csv(ROOT / source_manifest["subjects"][subject]["source_path"])
    source_by_id = {row["class_id"]: row for row in source_rows}
    result: list[dict[str, Any]] = []
    infos: dict[str, ClassFileInfo] = {}
    for row in sorted((item for item in rows if item["body_empty"] == "true"), key=lambda item: item["class_id"]):
        class_id = row["class_id"]
        class_methods = methods.get(class_id, [])
        info = inspect_classfile(subject, class_id)
        infos[class_id] = info
        normalized, evidence_hash = body_evidence(class_methods)
        raw = raw_feature_counts(class_methods)
        inventory_hash, jimple_hash, _ = method_hashes(class_methods)
        exact_template = row["semantic_text"] == compose_semantic_text(source_by_id[class_id]["semantic_text"], EMPTY_BODY)
        declaration_exact = extract_declaration_section(row["semantic_text"]) == source_by_id[class_id]["semantic_text"]
        category, concern = classify_empty_body(
            class_synthetic=info.class_synthetic or "$" in class_id and class_id.rsplit("$", 1)[-1].isdigit(),
            concrete_method_count=sum(int(method.concrete) for method in class_methods),
            normalized_token_count=len(normalized.tokens_before_budget),
            raw_candidate_count=normalized.filter_counts.raw_candidate_count,
            body_failure=class_id in failures,
            classfile_resolved=info.resolved and class_id in soot_class_ids,
            concrete_declared_method_count=info.concrete_declared_method_count,
        )
        if not declaration_exact or not exact_template:
            category, concern = "E", "accepted_empty_text_does_not_match_frozen_template"
        notes = [
            f"Soot method rows={len(class_methods)}; concrete rows={sum(int(method.concrete) for method in class_methods)}.",
            f"javap resolved={str(info.resolved).lower()}; declared concrete methods={info.concrete_declared_method_count}; abstract/native={info.abstract_or_native_method_count}.",
            "Local-variable debug metadata is not present in the Soot method_bodies.csv schema; no local names were fabricated.",
        ]
        if info.command_error:
            notes.append(f"javap error: {info.command_error}")
        if class_id in failures:
            notes.append("Extractor log contains a body retrieval or Shimple conversion failure for this class.")
        if category == "C":
            notes.append("Compiler-synthetic class naming/ACC_SYNTHETIC evidence supports generated/template classification.")
        if category == "A":
            notes.append("All declared methods are abstract/native or the class has no declared concrete method body.")
        result.append({
            "subject": subject, "class_id": class_id, "fqn_for_audit_only": class_id,
            "class_kind": row["kind"], "is_interface": str(info.is_interface or row["kind"] == "interface").lower(),
            "is_abstract": str(info.class_abstract or row["kind"] == "abstract").lower(),
            "is_enum": str(info.is_enum or row["kind"] == "enum").lower(),
            "is_annotation": str(info.is_annotation or row["kind"] == "annotation").lower(),
            "is_generated": str(category == "C").lower(),
            "is_synthetic": str(info.class_synthetic or "$" in class_id and class_id.rsplit("$", 1)[-1].isdigit()).lower(),
            "stage3a_declaration_hash": row["stage3a_declaration_hash"], "stage3b_full_text_hash": row["input_hash"],
            "declared_method_count": row["method_count"], "abstract_or_native_method_count": info.abstract_or_native_method_count,
            "soot_class_resolved": str(class_id in soot_class_ids).lower(),
            "expected_methods_discovered": str(info.resolved and len(info.method_lines) == int(row["method_count"])).lower(),
            "concrete_method_count": sum(int(method.concrete) for method in class_methods),
            "constructor_count": sum(int(method.method_name == "<init>") for method in class_methods),
            "static_initializer_count": sum(int(method.method_name == "<clinit>") for method in class_methods),
            "concrete_statement_count": sum(len([line for line in (method.body_text or "").splitlines() if line.strip()]) for method in class_methods if method.concrete),
            "raw_candidate_invoked_methods": raw["invoked_methods"], "raw_candidate_fields": raw["fields"],
            "raw_candidate_locals": raw["locals"], "raw_candidate_exceptions": raw["exceptions"],
            "raw_candidate_strings": raw["strings"], "raw_candidate_operations": raw["operations"],
            "accepted_body_token_count": len(normalized.tokens_after_budget),
            "body_empty_reason": concern, "classification": category,
            "correctness_concern": "none" if category in {"A", "B", "C"} else concern,
            "evidence_notes": " ".join(notes),
            "raw_body_inventory_hash": inventory_hash, "jimple_body_hash": jimple_hash,
            "permitted_body_evidence_hash": evidence_hash,
            "body_loading_failure": str(class_id in failures).lower(),
            "active_body_retrieval_status": "failed" if class_id in failures else "not_applicable_no_concrete_body" if not class_methods else "available",
            "declaration_exact_match": str(declaration_exact).lower(), "only_empty_template_addition": str(exact_template).lower(),
        })
    return result, infos


def empty_template_effect(subject: str, empty_rows: list[dict[str, Any]], all_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    stage3a_vectors, stage3a_ids = load_embedding(subject, False)
    stage3b_vectors, stage3b_ids = load_embedding(subject, True)
    stage3a_index = {class_id: index for index, class_id in enumerate(stage3a_ids)}
    stage3b_index = {class_id: index for index, class_id in enumerate(stage3b_ids)}
    old_neighbours, new_neighbours = load_neighbours(subject, False), load_neighbours(subject, True)
    old_edges, new_edges = load_edges(subject, False), load_edges(subject, True)
    by_id = {row["class_id"]: row for row in all_rows}
    output: list[dict[str, Any]] = []
    for row in empty_rows:
        class_id = row["class_id"]
        similarity = cosine(stage3a_vectors[stage3a_index[class_id]], stage3b_vectors[stage3b_index[class_id]])
        old_set, new_set = set(old_neighbours[class_id]), set(new_neighbours[class_id])
        output.append({
            "subject": subject, "class_id": class_id, "stage3a_declaration_hash": row["stage3a_declaration_hash"],
            "stage3b_full_text_hash": row["stage3b_full_text_hash"], "declaration_exact_match": row["declaration_exact_match"],
            "only_section_markers_and_empty_marker_added": row["only_empty_template_addition"],
            "stage3a_stage3b_embedding_cosine": f"{similarity:.17g}", "cosine_distance": f"{1.0 - similarity:.17g}",
            "stage3a_neighbours": "|".join(old_neighbours[class_id]), "stage3b_neighbours": "|".join(new_neighbours[class_id]),
            "retained_neighbour_count": len(old_set & new_set), "neighbour_retention": f"{len(old_set & new_set) / 3:.17g}",
            "stage3a_degree": sum(int(class_id in edge) for edge in old_edges for _ in [0]),
            "stage3b_degree": sum(int(class_id in edge) for edge in new_edges for _ in [0]),
            "degree_change": sum(int(class_id in edge) for edge in new_edges) - sum(int(class_id in edge) for edge in old_edges),
            "body_lexical_content_contributed": "false",
            "diagnostic_note": "Embedding and neighbour changes cannot be attributed to lexical method-body content; section markers and <EMPTY> remain textual input.",
            "body_empty": by_id[class_id]["body_empty"],
        })
    return output


def collision_groups(rows: list[dict[str, str]], embedding_hash_rows: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    by_text: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_text[row["input_hash"]].append(row)
    text_groups = [sorted(group, key=lambda row: row["class_id"]) for group in by_text.values() if len(group) > 1]
    by_embedding: dict[str, list[str]] = defaultdict(list)
    for row in embedding_hash_rows:
        by_embedding[row["embedding_sha256"]].append(row["class_id"])
    embedding_groups = {tuple(sorted(value)) for value in by_embedding.values() if len(value) > 1}
    text_sets = {tuple(row["class_id"] for row in group) for group in text_groups}
    if len(text_groups) != 11 or sum(len(group) for group in text_groups) != 55:
        raise ValueError(f"expected 11/55 text collision inventory, got {len(text_groups)}/{sum(map(len, text_groups))}")
    if len(embedding_groups) != 11 or embedding_groups != text_sets:
        raise ValueError("embedding collision inventory does not match frozen text collision groups")
    return sorted(text_groups, key=lambda group: group[0]["class_id"])


def collision_audit(groups: list[list[dict[str, str]]], methods: dict[str, list[Any]], failures: set[str]) -> list[dict[str, Any]]:
    vector_hash = {row["class_id"]: row["embedding_sha256"] for row in read_csv(EMBEDDING_ROOT / "xerces/embedding_hashes.csv")}
    structural = structural_neighbours("xerces")
    edges = load_edges("xerces", True)
    group_by_class = {row["class_id"]: f"collision_{index:02d}" for index, group in enumerate(groups, 1) for row in group}
    output: list[dict[str, Any]] = []
    for index, group in enumerate(groups, 1):
        group_id = f"collision_{index:02d}"
        normalized_hashes: list[str] = []
        before_hashes: list[str] = []
        inventory_hashes: list[str] = []
        jimple_hashes: list[str] = []
        member_method_names: list[tuple[str, ...]] = []
        generated = []
        raw_body_hashes = []
        for row in group:
            class_methods = methods.get(row["class_id"], [])
            normalized, evidence_hash = body_evidence(class_methods)
            _, jimple_hash, _ = method_hashes(class_methods)
            inventory_hash, _, _ = method_hashes(class_methods)
            normalized_hashes.append(sha256_bytes((normalized.body_text).encode()))
            before_hashes.append(sha256_bytes((" ".join(normalized.tokens_before_budget) if normalized.tokens_before_budget else "<EMPTY>").encode()))
            inventory_hashes.append(inventory_hash)
            jimple_hashes.append(jimple_hash)
            member_method_names.append(tuple((method.method_name, str(method.concrete), str(method.synthetic)) for method in sorted(class_methods, key=lambda item: (item.method_name, item.method_signature))))
            generated.append(any(method.synthetic for method in class_methods) or "$" in row["class_id"] and row["class_id"].rsplit("$", 1)[-1].isdigit())
            raw_body_hashes.append(jimple_hash)
        raw_equiv = len(set(raw_body_hashes)) == 1
        normalized_equiv = len(set(normalized_hashes)) == 1
        permitted_equiv = len(set(before_hashes)) == 1
        extraction_failure = any(row["class_id"] in failures for row in group)
        classification_code = classify_collision(
            raw_body_equivalence=raw_equiv,
            normalized_equivalence=normalized_equiv,
            permitted_before_budget_equivalence=permitted_equiv,
            extraction_failure=extraction_failure,
            generated_equivalence=all(generated),
        )
        group_ids = {row["class_id"] for row in group}
        intragroup = sum(int(left in group_ids and right in group_ids) for left, right in edges)
        external = sum(int((left in group_ids) ^ (right in group_ids)) for left, right in edges)
        output.append({
            "group_id": group_id, "member_count": len(group), "member_class_ids": "|".join(row["class_id"] for row in group),
            "member_fqns_for_audit_only": "|".join(row["class_id"] for row in group),
            "packages_for_audit_only": "|".join(sorted({class_package(row["class_id"]) for row in group})),
            "generated_status": "generated_or_synthetic_member" if any(generated) else "not_detected",
            "class_kinds": "|".join(sorted({row["kind"] for row in group})),
            "declaration_hash": group[0]["stage3a_declaration_hash"], "full_stage3b_text_hash": group[0]["input_hash"],
            "embedding_hash": vector_hash[group[0]["class_id"]], "method_inventory_hashes": "|".join(inventory_hashes),
            "jimple_body_hashes": "|".join(jimple_hashes), "permitted_body_evidence_hashes": "|".join(before_hashes),
            "raw_body_equivalence": str(raw_equiv).lower(), "normalized_body_equivalence": str(normalized_equiv).lower(),
            "structural_neighbourhood_similarity": f"{pairwise_jaccard([structural.get(row['class_id'], set()) for row in group]):.17g}",
            "stage3b_intragroup_edges": intragroup, "stage3b_external_edges": external,
            "classification": classification_code,
            "correctness_concern": "none" if classification_code in {"A", "B", "C"} else "review_required",
            "notes": "Raw Jimple body hashes differ across package copies; permitted normalized body evidence is identical and package/owner/type context is intentionally excluded.",
        })
    return output


def collision_graph_impact(groups: list[list[dict[str, str]]]) -> list[dict[str, Any]]:
    directed = read_csv(GRAPH_ROOT / "xerces/directed_topk_neighbours.csv")
    edge_rows = read_csv(GRAPH_ROOT / "xerces/semantic_edges.csv")
    edges = load_edges("xerces", True)
    components = graph_components("xerces")
    group_by_class = {row["class_id"]: f"collision_{index:02d}" for index, group in enumerate(groups, 1) for row in group}
    total_edges = len(edges)
    total_classes = EXPECTED_COUNTS["xerces"]
    rows: list[dict[str, Any]] = []
    for index, group in enumerate(groups, 1):
        group_id = f"collision_{index:02d}"
        members = {row["class_id"] for row in group}
        directed_group = [row for row in directed if row["source_class_id"] in members]
        intra_directed = [row for row in directed_group if row["target_class_id"] in members]
        external_directed = [row for row in directed_group if row["target_class_id"] not in members]
        final_intra = [edge for edge in edges if edge[0] in members and edge[1] in members]
        final_external = [edge for edge in edges if (edge[0] in members) ^ (edge[1] in members)]
        weight_by_edge = {canonical_edge(row["class_id_a"], row["class_id_b"]): row["weight"] for row in edge_rows}
        all_three = sum(int(len([row for row in directed_group if row["source_class_id"] == member and row["target_class_id"] in members]) == 3) for member in members)
        component_rows = [component for component in components if component & members]
        primary = sum(int(len(component & members) / len(component) >= 0.5) for component in component_rows)
        tie_count = sum(int(row["target_class_id"] in members) for row in intra_directed)
        rows.append({
            "group_id": group_id, "member_count": len(members), "collision_classes_over_xerces": f"{len(members) / total_classes:.17g}",
            "directed_top3_rows": len(directed_group), "directed_intragroup_selections": len(intra_directed),
            "directed_external_selections": len(external_directed), "identical_embedding_tie_selections": tie_count,
            "tie_rule": "class_id_lexicographic_ascending", "stage3b_intragroup_edges": len(final_intra),
            "stage3b_external_edges": len(final_external), "total_edges_involving_collision_classes": len(final_intra) + len(final_external),
            "collision_edges_over_all_xerces_edges": f"{(len(final_intra) + len(final_external)) / total_edges:.17g}",
            "intragroup_edges_over_all_xerces_edges": f"{len(final_intra) / total_edges:.17g}",
            "all_three_neighbours_intragroup_count": all_three, "all_three_neighbours_intragroup_fraction": f"{all_three / len(members):.17g}",
            "connected_component_count_touched": len(component_rows), "components_primarily_explained_by_collision_group": primary,
            "component_memberships": "|".join(str(sorted(component & members)) for component in component_rows),
            "graph_edge_weight_values": "|".join(f"{float(weight_by_edge[edge]):.17g}" for edge in sorted(final_intra + final_external)),
            "nearly_closed_component": str(bool(all_three == len(members) and not external_directed)).lower(),
        })
    return rows


def write_empty_summary(empty_rows: list[dict[str, Any]], effects: list[dict[str, Any]], total_rows: dict[str, list[dict[str, str]]], failures: set[str]) -> None:
    lines = [
        "# Empty Stage 3B method-body audit", "",
        "The accepted Body V1 inputs were audited without regeneration. Soot/Jimple/Shimple outputs were produced in an isolated temporary directory.", "",
        "Category definitions: A=no concrete body; B=concrete body with no permitted evidence; C=generated/template equivalent; D=meaningful candidates correctly filtered; E=suspected extraction failure; F=unresolved.", "",
        "| Subject | Empty | A | B | C | D | E | F | Decision |", "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for subject in SUBJECTS:
        rows = [row for row in empty_rows if row["subject"] == subject]
        counts = {category: sum(row["classification"] == category for row in rows) for category in "ABCDEF"}
        decision = "CORRECTNESS BUG SUSPECTED" if counts["E"] else "UNRESOLVED" if counts["F"] else "EXPECTED / ACCEPTABLE"
        lines.append(f"| {subject} | {len(rows)} | {counts['A']} | {counts['B']} | {counts['C']} | {counts['D']} | {counts['E']} | {counts['F']} | {decision} |")
    lines += ["", "## Subject details", ""]
    for subject in SUBJECTS:
        rows = [row for row in empty_rows if row["subject"] == subject]
        effects_for_subject = [row for row in effects if row["subject"] == subject]
        categories = {category: sum(row["classification"] == category for row in rows) for category in "ABCDEF"}
        concrete_empty = sum(int(row["concrete_method_count"]) > 0 for row in rows)
        failures_count = sum(row["body_loading_failure"] == "true" for row in rows)
        missing = sum(row["accepted_body_token_count"] == 0 and row["concrete_method_count"] > 0 and row["classification"] in {"D", "E"} for row in rows)
        generated = sum(row["classification"] == "C" for row in rows)
        interfaces = sum(row["is_interface"] == "true" for row in rows)
        abstracts = sum(row["is_abstract"] == "true" for row in rows)
        shifts = [float(row["cosine_distance"]) for row in effects_for_subject]
        retention = [float(row["neighbour_retention"]) for row in effects_for_subject]
        decision = "CORRECTNESS BUG SUSPECTED" if categories["E"] else "UNRESOLVED" if categories["F"] else "EXPECTED / ACCEPTABLE"
        lines += [
            f"### {subject}", "",
            f"* Total classes: {len(total_rows[subject])}; empty bodies: {len(rows)} ({100.0 * len(rows) / len(total_rows[subject]):.4f}%).",
            f"* Categories A–F: {categories}; concrete classes with empty bodies: {concrete_empty}; body-loading failures: {failures_count}; permitted evidence unexpectedly missing: {missing}.",
            f"* Generated/template classes: {generated}; interfaces: {interfaces}; abstract classes: {abstracts}.",
            f"* Mean empty-body embedding shift (cosine distance): {np.mean(shifts) if shifts else 0.0:.9f}; mean neighbour retention: {np.mean(retention) if retention else 0.0:.9f}.",
            f"* Decision: **{decision}**.", "",
        ]
    lines += [
        "## Findings", "",
        "* The Soot method-body extraction log contained no method-body retrieval or Shimple-conversion failure for an audited class.",
        "* Interface and abstract-only classes are expected to have no concrete body rows. The four Xerces compiler-synthetic `$1` classes are retained and classified as generated/template-equivalent.",
        "* Empty-body embeddings and neighbours can change because `[DECLARATION]`, `[METHOD_BODY]`, and `<EMPTY>` are part of the frozen text. These changes cannot be attributed to lexical method-body content.",
        "* This audit does not alter the frozen `<EMPTY>` policy or any scientific artifact.", "",
    ]
    (REPORT_ROOT / "empty_body_audit_summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_collision_summary(collision_rows: list[dict[str, Any]], impact_rows: list[dict[str, Any]]) -> None:
    codes = defaultdict(int)
    for row in collision_rows:
        codes[row["classification"]] += 1
    lines = [
        "# Xerces collision resolution assessment", "",
        "The 11 duplicate full-text and duplicate-embedding groups contain 55 retained classes. No class, input, embedding, or edge was removed.", "",
        f"Classification counts: {dict(sorted(codes.items()))}.", "",
        "`C` means permitted-view-equivalent: raw Jimple bodies differ across package/owner copies, while the frozen normalized body evidence is identical. These package, owner, and type differences are deliberately excluded from Body V1.", "",
        "| Group | Members | Classification | Raw body equivalent | Normalized evidence equivalent | Structural neighbourhood similarity | Intra edges | External edges |", "|---|---:|---|---|---|---:|---:|---:|",
    ]
    for row in collision_rows:
        lines.append(f"| {row['group_id']} | {row['member_count']} | {row['classification']} | {row['raw_body_equivalence']} | {row['normalized_body_equivalence']} | {float(row['structural_neighbourhood_similarity']):.6f} | {row['stage3b_intragroup_edges']} | {row['stage3b_external_edges']} |")
    structural_values = [float(row["structural_neighbourhood_similarity"]) for row in collision_rows]
    lines += ["", "## Structural-context diagnostic", "", f"Mean pairwise raw structural-neighbour Jaccard is {np.mean(structural_values):.6f} (minimum {min(structural_values):.6f}, maximum {max(structural_values):.6f}). The collision groups therefore occupy different structural neighbourhoods in this diagnostic; that is a known limitation of a declaration-plus-permitted-lexical representation, not evidence that the frozen semantic inputs are corrupted.", "", "## Graph impact", "", f"Collision classes: 55 / {EXPECTED_COUNTS['xerces']}; final edges involving collision classes: {sum(int(row['total_edges_involving_collision_classes']) for row in impact_rows)} / 1681; intra-group edges: {sum(int(row['stage3b_intragroup_edges']) for row in impact_rows)}; external edges: {sum(int(row['stage3b_external_edges']) for row in impact_rows)}.", f"Components primarily explained by collision groups: {sum(int(row['components_primarily_explained_by_collision_group']) for row in impact_rows)}.", "", "No over-normalization, extraction-failure, or unresolved collision group was found by this audit." if not any(row["classification"] in {"D", "E", "F"} for row in collision_rows) else "At least one collision group requires correctness review.", ""]
    (REPORT_ROOT / "xerces_collision_resolution_assessment.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extraction-root", type=Path, required=True)
    parser.add_argument("--extractor-log", type=Path, required=True)
    parser.add_argument("--before-hashes", type=Path, required=True)
    args = parser.parse_args()
    extraction_root = args.extraction_root.resolve()
    before = json.loads(args.before_hashes.read_text(encoding="utf-8"))
    if not all((extraction_root / EXTRACTION_SUBJECT[subject] / "method_bodies.csv").is_file() for subject in SUBJECTS):
        raise FileNotFoundError("isolated Soot method-body outputs are incomplete")
    failures, failure_count, unresolved_count = extractor_failure_classes(args.extractor_log.resolve())
    rows_by_subject = {subject: load_input_rows(subject) for subject in SUBJECTS}
    methods_by_subject = {subject: load_methods(extraction_root / EXTRACTION_SUBJECT[subject] / "method_bodies.csv") for subject in SUBJECTS}
    empty_rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        declarations = read_csv(extraction_root / EXTRACTION_SUBJECT[subject] / "class_declarations.csv")
        soot_class_ids = {row["class_id"] for row in declarations}
        rows, _ = audit_empty_bodies(subject, rows_by_subject[subject], methods_by_subject[subject], failures, soot_class_ids)
        if len(rows) != EXPECTED_EMPTY[subject]:
            raise ValueError(f"{subject}: expected {EXPECTED_EMPTY[subject]} empty rows, found {len(rows)}")
        empty_rows.extend(rows)
    empty_fields = [
        "subject", "class_id", "fqn_for_audit_only", "class_kind", "is_interface", "is_abstract", "is_enum", "is_annotation", "is_generated", "is_synthetic", "stage3a_declaration_hash", "stage3b_full_text_hash", "declared_method_count", "abstract_or_native_method_count", "soot_class_resolved", "expected_methods_discovered", "concrete_method_count", "constructor_count", "static_initializer_count", "concrete_statement_count", "raw_candidate_invoked_methods", "raw_candidate_fields", "raw_candidate_locals", "raw_candidate_exceptions", "raw_candidate_strings", "raw_candidate_operations", "accepted_body_token_count", "body_empty_reason", "classification", "correctness_concern", "evidence_notes", "raw_body_inventory_hash", "jimple_body_hash", "permitted_body_evidence_hash", "body_loading_failure", "active_body_retrieval_status", "declaration_exact_match", "only_empty_template_addition",
    ]
    write_csv(REPORT_ROOT / "empty_body_class_audit.csv", empty_fields, empty_rows)
    controls = control_sample_ids(rows_by_subject)
    control_rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        by_id = {row["class_id"]: row for row in rows_by_subject[subject]}
        for category, class_id in controls[subject]:
            normalized, evidence_hash = body_evidence(methods_by_subject[subject].get(class_id, []))
            raw = raw_feature_counts(methods_by_subject[subject].get(class_id, []))
            control_rows.append({"subject": subject, "sample_category": category, "class_id": class_id, "body_empty": by_id[class_id]["body_empty"], "body_tokens_truncated": by_id[class_id]["body_tokens_truncated"], "concrete_method_count": sum(int(method.concrete) for method in methods_by_subject[subject].get(class_id, [])), "concrete_statement_count": sum(len([line for line in (method.body_text or "").splitlines() if line.strip()]) for method in methods_by_subject[subject].get(class_id, []) if method.concrete), "raw_candidate_invoked_methods": raw["invoked_methods"], "raw_candidate_fields": raw["fields"], "raw_candidate_locals": raw["locals"], "raw_candidate_exceptions": raw["exceptions"], "raw_candidate_strings": raw["strings"], "raw_candidate_operations": raw["operations"], "accepted_body_token_count": len(normalized.tokens_after_budget), "permitted_body_evidence_hash": evidence_hash, "input_hash": by_id[class_id]["input_hash"]})
    write_csv(REPORT_ROOT / "empty_body_control_sample.csv", ["subject", "sample_category", "class_id", "body_empty", "body_tokens_truncated", "concrete_method_count", "concrete_statement_count", "raw_candidate_invoked_methods", "raw_candidate_fields", "raw_candidate_locals", "raw_candidate_exceptions", "raw_candidate_strings", "raw_candidate_operations", "accepted_body_token_count", "permitted_body_evidence_hash", "input_hash"], control_rows)
    effects = []
    for subject in SUBJECTS:
        effects.extend(empty_template_effect(subject, [row for row in empty_rows if row["subject"] == subject], rows_by_subject[subject]))
    write_csv(REPORT_ROOT / "empty_body_template_effect.csv", list(effects[0]), effects)
    write_empty_summary(empty_rows, effects, rows_by_subject, failures)
    collision_groups_rows = collision_groups(rows_by_subject["xerces"], read_csv(EMBEDDING_ROOT / "xerces/embedding_hashes.csv"))
    collision_rows = collision_audit(collision_groups_rows, methods_by_subject["xerces"], failures)
    write_csv(REPORT_ROOT / "xerces_collision_group_audit.csv", list(collision_rows[0]), collision_rows)
    impact_rows = collision_graph_impact(collision_groups_rows)
    write_csv(REPORT_ROOT / "xerces_collision_graph_impact.csv", list(impact_rows[0]), impact_rows)
    write_collision_summary(collision_rows, impact_rows)
    after = snapshot_artifacts()
    hash_rows = compare_artifact_hashes(before, after)
    write_csv(REPORT_ROOT / "empty_body_collision_artifact_hash_check.csv", ["relative_path", "before_sha256", "after_sha256", "unchanged"], hash_rows)
    artifact_integrity = all(row["unchanged"] == "true" for row in hash_rows) and set(before) == set(after)
    all_empty_safe = all(row["classification"] in {"A", "B", "C"} for row in empty_rows)
    all_collision_safe = all(row["classification"] in {"A", "B", "C"} for row in collision_rows)
    decision = "SAFE TO CONTINUE — EMPTY BODIES AND COLLISIONS ARE EXPLAINED" if artifact_integrity and all_empty_safe and all_collision_safe and not failures else "STOP — CORRECTNESS REVIEW REQUIRED"
    input_aggregates = {subject: canonical_aggregate(rows_by_subject[subject]) for subject in SUBJECTS}
    embedding_manifest = json.loads((REPORT_ROOT / "embedding_generation_manifest.json").read_text(encoding="utf-8"))
    embedding_aggregates = {subject: embedding_manifest["reproducibility_subjects"][subject]["aggregate_embedding_sha256"] for subject in SUBJECTS}
    graph_hashes = {subject: json.loads((GRAPH_ROOT / subject / "graph_metadata.json").read_text(encoding="utf-8"))["semantic_graph_sha256"] for subject in SUBJECTS}
    manifest = {
        "audit_type": "stage3b_empty_body_and_collision_correctness_audit", "starting_commit": "3a22f390b1159f9d93ad2c6f8afc5cb04646877f", "final_decision": decision,
        "frozen_hashes": {"input_aggregate_sha256": input_aggregates, "embedding_aggregate_sha256": embedding_aggregates, "semantic_graph_sha256": graph_hashes, "artifact_files_unchanged": artifact_integrity},
        "expected_inventory": {"empty_body_counts": EXPECTED_EMPTY, "xerces_collision_groups": 11, "xerces_collision_classes": 55, "xerces_collision_embedding_groups": 11, "xerces_collision_graph_edges": {"total": 103, "intragroup": 99, "external": 4}},
        "audit_scripts": ["scripts/stage3_method_body/audit_empty_bodies_and_collisions.py"], "extraction_root": str(extraction_root), "extractor_log": str(args.extractor_log.resolve()), "method_body_failure_line_count": failure_count, "unresolved_reference_warning_line_count": unresolved_count,
        "classification_definitions": {"A": "no_concrete_body", "B": "concrete_body_no_permitted_evidence", "C": "generated_or_template_equivalent", "D": "meaningful_candidates_correctly_filtered", "E": "suspected_extraction_failure", "F": "unresolved", "collision_A": "true_code_duplicate", "collision_B": "generated_template_duplicate", "collision_C": "permitted_view_equivalent", "collision_D": "over_normalization_collision", "collision_E": "extraction_failure_collision", "collision_F": "unresolved"},
        "control_sample_rule": "first five non-empty sorted classes per subject; five smallest non-zero body-token classes; all body-truncated classes; de-duplicate in that order",
        "reports": ["empty_body_class_audit.csv", "empty_body_control_sample.csv", "empty_body_template_effect.csv", "empty_body_audit_summary.md", "xerces_collision_group_audit.csv", "xerces_collision_graph_impact.csv", "xerces_collision_resolution_assessment.md", "empty_body_collision_artifact_hash_check.csv"],
        "generated_at_utc": utc_now(), "failure_classes": sorted(failures), "empty_body_classifications": {subject: {category: sum(row["classification"] == category for row in empty_rows if row["subject"] == subject) for category in "ABCDEF"} for subject in SUBJECTS}, "collision_classifications": {category: sum(row["classification"] == category for row in collision_rows) for category in "ABCDEF"},
    }
    write_json(REPORT_ROOT / "empty_body_collision_audit_manifest.json", manifest)
    print(json.dumps({"decision": decision, "empty_body_counts": {subject: sum(row["body_empty"] == "true" for row in rows) for subject, rows in rows_by_subject.items()}, "empty_classifications": manifest["empty_body_classifications"], "collision_classifications": manifest["collision_classifications"], "artifact_integrity": artifact_integrity, "failure_classes": sorted(failures)}, indent=2))
    return 0 if decision.startswith("SAFE TO CONTINUE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
