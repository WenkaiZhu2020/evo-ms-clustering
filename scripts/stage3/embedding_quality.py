#!/usr/bin/env python3
"""Create diagnostics from saved Stage 3 embeddings without loading the model."""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from transformers import AutoTokenizer

try:  # Supports both package imports and direct script execution.
    from .generate_embeddings import INPUT_PATHS, MODEL_REVISION, SUBJECTS, nearest_neighbors, read_subject
    from .similarity import true_cosine_similarity
except ImportError:  # pragma: no cover - direct CLI path
    from generate_embeddings import INPUT_PATHS, MODEL_REVISION, SUBJECTS, nearest_neighbors, read_subject
    from similarity import true_cosine_similarity


MODEL = "nomic-ai/nomic-embed-code"
MAX_LENGTH = 32768
SUBJECT_ORDER = tuple(SUBJECTS)


def output_dir(subject: str) -> Path:
    return Path("results") / subject / "04_stage3_semantic" / "embeddings"


def groups(values: list[str]) -> list[list[int]]:
    by_value: dict[str, list[int]] = defaultdict(list)
    for index, value in enumerate(values):
        by_value[value].append(index)
    return [indices for indices in by_value.values() if len(indices) > 1]


def token_count(tokenizer, text: str) -> int:
    encoded = tokenizer(text, truncation=False, add_special_tokens=True, return_attention_mask=False)
    return len(encoded["input_ids"])


def load_neighbors(subject: str) -> dict[str, list[tuple[str, float]]]:
    result: dict[str, list[tuple[str, float]]] = defaultdict(list)
    with (output_dir(subject) / "nearest_neighbors.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            result[row["class_id"]].append((row["neighbor_class_id"], float(row["cosine_similarity"])))
    return result


def regenerate_neighbors(subject: str, rows: list[dict[str, str]]) -> None:
    directory = output_dir(subject)
    vectors = np.load(directory / "embeddings.npy")
    with (directory / "nearest_neighbors.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["class_id", "neighbor_rank", "neighbor_class_id", "cosine_similarity"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(nearest_neighbors(rows, vectors))


def select_manual_rows(rows: list[dict[str, str]], token_values: dict[str, int]) -> list[tuple[str, dict[str, str]]]:
    selected: dict[str, tuple[str, dict[str, str]]] = {}

    def add(category: str, candidates: list[dict[str, str]]) -> None:
        for row in candidates:
            if row["class_id"] not in selected:
                selected[row["class_id"]] = (category, row)
                return

    add("longest-token", sorted(rows, key=lambda row: (-token_values[row["class_id"]], row["class_id"])))
    add("highest-method-count", sorted(rows, key=lambda row: (-int(row["method_count"]), row["class_id"])))
    add("lowest-method-count", sorted(rows, key=lambda row: (int(row["method_count"]), row["class_id"])))
    add("zero-method", sorted((row for row in rows if int(row["method_count"]) == 0), key=lambda row: row["class_id"]))
    add("interface", sorted((row for row in rows if row["kind"] == "interface"), key=lambda row: row["class_id"]))
    add("abstract", sorted((row for row in rows if "abstract" in row["kind"]), key=lambda row: row["class_id"]))
    add("enum", sorted((row for row in rows if row["kind"] == "enum"), key=lambda row: row["class_id"]))
    add("annotated", sorted((row for row in rows if int(row["annotation_count"]) > 0), key=lambda row: row["class_id"]))
    add("superclass", sorted((row for row in rows if row["superclass_present"] == "true"), key=lambda row: row["class_id"]))
    remainder = [row for row in rows if row["class_id"] not in selected]
    random.Random(42).shuffle(remainder)
    for row in remainder:
        if len(selected) >= 10:
            break
        selected[row["class_id"]] = ("seed-42-remainder", row)
    if len(selected) != 10:
        raise ValueError(f"could not select 10 rows; got {len(selected)}")
    return list(selected.values())


def fmt_group(rows: list[dict[str, str]], indices: list[int], field: str) -> str:
    return ", ".join(f"`{rows[index]['class_id']}`" for index in indices) + f" ({field})"


def build_report(inputs_dir: Path) -> str:
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=MODEL_REVISION, use_fast=True, trust_remote_code=False)
    if int(tokenizer.model_max_length) != MAX_LENGTH:
        raise ValueError(f"tokenizer max length {tokenizer.model_max_length} != {MAX_LENGTH}")
    all_rows: dict[str, list[dict[str, str]]] = {}
    all_tokens: dict[str, dict[str, int]] = {}
    all_neighbors: dict[str, dict[str, list[tuple[str, float]]]] = {}
    lines = [
        "# Stage 3 Embedding Quality Summary",
        "",
        "This diagnostic report uses only the saved `embeddings.npy`, CSV mapping,",
        "per-class hashes, and saved nearest-neighbour files. It does not load the",
        "Nomic model and does not construct `semantic_edges.csv`.",
        "",
        f"Tokenizer metadata for token display: `{MODEL}` revision `{MODEL_REVISION}`",
        f"with `model_max_length={MAX_LENGTH}`, `truncation=false`, and special tokens enabled.",
        "",
        "## 1. Cross-subject summary",
        "",
        "| subject | classes | dimension | min norm | mean norm | max norm | NaN | Inf | all-zero | duplicate semantic_text groups | duplicate embedding groups | min off-diagonal cosine | mean off-diagonal cosine | median off-diagonal cosine | max off-diagonal cosine | mean top-1 | median top-1 | min top-1 | max top-1 | encoding seconds | aggregate embedding SHA-256 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    summary: dict[str, dict[str, object]] = {}
    for subject in SUBJECT_ORDER:
        rows = read_subject(inputs_dir, subject) if inputs_dir != Path("data/semantic_inputs") else read_subject(subject)
        regenerate_neighbors(subject, rows)
        all_rows[subject] = rows
        all_tokens[subject] = {row["class_id"]: token_count(tokenizer, row["semantic_text"]) for row in rows}
        vectors = np.load(output_dir(subject) / "embeddings.npy")
        metadata = __import__("json").loads((output_dir(subject) / "embedding_metadata.json").read_text(encoding="utf-8"))
        matrix = true_cosine_similarity(vectors)
        off_diagonal = matrix[~np.eye(len(rows), dtype=bool)]
        neighbors = load_neighbors(subject)
        all_neighbors[subject] = neighbors
        top1 = np.asarray([neighbors[row["class_id"]][0][1] for row in rows], dtype=np.float64)
        text_groups = groups([row["semantic_text"] for row in rows])
        vector_groups = groups([hashlib.sha256(np.asarray(vector, dtype="<f4").tobytes()).hexdigest() for vector in vectors])
        norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
        summary[subject] = {
            "class_count": len(rows),
            "dimension": int(vectors.shape[1]),
            "min_norm": float(norms.min()),
            "mean_norm": float(norms.mean()),
            "max_norm": float(norms.max()),
            "nan": int(np.isnan(vectors).sum()),
            "inf": int(np.isinf(vectors).sum()),
            "zero": int(np.all(vectors == 0, axis=1).sum()),
            "text_groups": text_groups,
            "vector_groups": vector_groups,
            "off_diagonal": off_diagonal,
            "top1": top1,
            "encoding_seconds": metadata["encoding_elapsed_seconds"],
            "aggregate": metadata["aggregate_embedding_sha256"],
        }
        s = summary[subject]
        lines.append(
            f"| {subject} | {s['class_count']} | {s['dimension']} | {s['min_norm']:.9f} | {s['mean_norm']:.9f} | {s['max_norm']:.9f} | {s['nan']} | {s['inf']} | {s['zero']} | {len(s['text_groups'])} | {len(s['vector_groups'])} | {s['off_diagonal'].min():.9f} | {s['off_diagonal'].mean():.9f} | {np.median(s['off_diagonal']):.9f} | {s['off_diagonal'].max():.9f} | {s['top1'].mean():.9f} | {np.median(s['top1']):.9f} | {s['top1'].min():.9f} | {s['top1'].max():.9f} | {s['encoding_seconds']:.6f} | `{s['aggregate']}` |"
        )

    lines.extend(["", "## 2. Duplicate diagnostics", ""])
    for subject in SUBJECT_ORDER:
        rows = all_rows[subject]
        s = summary[subject]
        lines.append(f"### {subject}")
        lines.append("Identical text groups:")
        if s["text_groups"]:
            lines.extend(f"- {fmt_group(rows, indices, 'same semantic_text')}" for indices in s["text_groups"])
        else:
            lines.append("- None.")
        lines.append("Identical saved embedding groups:")
        if s["vector_groups"]:
            lines.extend(f"- {fmt_group(rows, indices, 'same saved embedding bytes')}" for indices in s["vector_groups"])
        else:
            lines.append("- None.")
        if subject == "xerces":
            lines.append(
                "These 11 duplicate-text/vector groups are expected diagnostic "
                "evidence under the frozen simple-name input contract. The input "
                "classes were not deduplicated."
            )
        lines.append("")

    lines.extend(["## 3. Manual nearest-neighbour review", "", "Every entry is unreviewed. Reviewer status must be one of `plausible`, `questionable`, or `unclear`; this report does not declare a neighbour correct or incorrect.", ""])
    for subject in SUBJECT_ORDER:
        lines.append(f"### {subject}")
        for category, row in select_manual_rows(all_rows[subject], all_tokens[subject]):
            lines.extend([
                f"#### `{row['class_id']}` — {category}",
                f"kind={row['kind']}; method_count={row['method_count']}; token_count={all_tokens[subject][row['class_id']]}; input_hash[:12]={row['input_hash'][:12]}",
                "manual_review: unreviewed (`plausible` / `questionable` / `unclear`)",
                "reviewer_note:",
                "semantic_text:",
                "```text",
                row["semantic_text"].rstrip("\n"),
                "```",
                "top_5_neighbors:",
            ])
            for neighbor, similarity in all_neighbors[subject][row["class_id"]]:
                lines.append(f"- `{neighbor}`: {similarity:.12f}")
            lines.append("")

    lines.extend(["## 4. Re-encoding stability", "", "| subject | classes re-encoded | exact byte matches | maximum absolute difference | minimum corresponding cosine | result |", "| --- | ---: | ---: | ---: | ---: | --- |"])
    stability = __import__("json").loads(Path("reports/stage3/embedding_stability.json").read_text(encoding="utf-8"))
    for subject in SUBJECT_ORDER:
        item = stability[subject]
        lines.append(f"| {subject} | {item['class_count']} | {item['exact_byte_matches']} | {item['maximum_absolute_difference']:.12g} | {item['minimum_corresponding_cosine']:.12g} | {'PASS' if item['passed'] else 'FAIL'} |")

    lines.extend([
        "",
        "## 5. Current limitations",
        "",
        "- Embeddings are generated from class declarations, not method bodies.",
        "- Nomic was trained mainly for code retrieval; nearest-neighbour plausibility is diagnostic only, not external validation.",
        "- Package paths are excluded, while method signatures still carry local type information.",
        "- Runtime embeddings may not be bitwise identical across MPS, CUDA, and CPU. The saved hashes certify the frozen MPS/float16/batch-8 runtime and platform recorded in metadata.",
        "- The formal top-3 semantic graph has not been generated.",
        "",
        f"Report generated at UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs-dir", type=Path, default=Path("data/semantic_inputs"))
    parser.add_argument("--output", type=Path, default=Path("reports/stage3/embedding_quality_summary.md"))
    args = parser.parse_args()
    args.output.write_text(build_report(args.inputs_dir), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
