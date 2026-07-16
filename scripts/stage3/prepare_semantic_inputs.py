#!/usr/bin/env python3
"""Apply the frozen tokenizer contract to Soot class-declaration CSV output."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

from transformers import AutoTokenizer


SCHEMA = [
    "subject",
    "class_id",
    "class_name",
    "kind",
    "superclass_present",
    "semantic_text",
    "method_count",
    "annotation_count",
    "interface_count",
    "truncated_method_count",
    "input_hash",
]


def _render(header: list[str], methods: list[str]) -> str:
    return "\n".join([*header, *methods, "} ".rstrip()]) + "\n"


def _split_declaration(text: str) -> tuple[list[str], list[str]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        raise ValueError("semantic_text must end with exactly one newline")
    lines = normalized[:-1].split("\n")
    if not lines or lines[-1] != "}":
        raise ValueError("semantic_text must end with a declaration closing brace")
    try:
        header_end = next(i for i, line in enumerate(lines) if line.endswith(" {"))
    except StopIteration as exc:
        raise ValueError("semantic_text has no declaration header") from exc
    header = lines[: header_end + 1]
    methods = lines[header_end + 1 : -1]
    for method in methods:
        if not method.startswith("    ") or not method.endswith(";"):
            raise ValueError(f"unexpected declaration body line: {method!r}")
    return header, methods


def _token_count(tokenizer, text: str) -> int:
    encoded = tokenizer(
        text,
        truncation=False,
        add_special_tokens=True,
        return_attention_mask=False,
    )
    return len(encoded["input_ids"])


def _truncate(
    tokenizer,
    text: str,
    method_count: int,
    max_sequence_length: int,
) -> tuple[str, int, int]:
    header, methods = _split_declaration(text)
    if len(methods) != method_count:
        raise ValueError(
            f"method_count mismatch: CSV={method_count}, rendered={len(methods)}"
        )

    candidates: list[tuple[int, str, int]] = []
    for count in range(len(methods) + 1):
        candidate = _render(header, methods[:count])
        candidates.append((count, candidate, _token_count(tokenizer, candidate)))

    fitting = [item for item in candidates if item[2] <= max_sequence_length]
    if not fitting:
        raise ValueError("entity header exceeds max_sequence_length")
    kept_count, selected_text, selected_tokens = fitting[-1]
    return selected_text, method_count - kept_count, selected_tokens


def transform_csv(
    input_path: Path,
    output_path: Path,
    subject: str,
    model: str,
    revision: str,
    max_sequence_length: int,
) -> None:
    tokenizer = AutoTokenizer.from_pretrained(
        model,
        revision=revision,
        use_fast=True,
        trust_remote_code=False,
    )
    actual_max_length = int(tokenizer.model_max_length)
    if actual_max_length != max_sequence_length:
        raise ValueError(
            "tokenizer model_max_length mismatch: "
            f"expected contract {max_sequence_length}, revision reports {actual_max_length}"
        )

    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("input CSV has no header")
        required = {
            "subject",
            "class_id",
            "class_name",
            "kind",
            "superclass_present",
            "semantic_text",
            "method_count",
            "annotation_count",
            "interface_count",
            "input_hash",
        }
        missing = required.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"input CSV missing columns: {sorted(missing)}")
        rows = list(reader)

    output_rows: list[dict[str, str]] = []
    for row in sorted(rows, key=lambda item: item["class_id"]):
        if row["subject"] != subject:
            raise ValueError(
                f"subject mismatch for {row['class_id']}: {row['subject']} != {subject}"
            )
        method_count = int(row["method_count"])
        semantic_text, truncated_count, _ = _truncate(
            tokenizer,
            row["semantic_text"],
            method_count,
            max_sequence_length,
        )
        output_rows.append(
            {
                "subject": subject,
                "class_id": row["class_id"],
                "class_name": row["class_name"],
                "kind": row["kind"],
                "superclass_present": row["superclass_present"],
                "semantic_text": semantic_text,
                "method_count": str(method_count),
                "annotation_count": row["annotation_count"],
                "interface_count": row["interface_count"],
                "truncated_method_count": str(truncated_count),
                "input_hash": hashlib.sha256(semantic_text.encode("utf-8")).hexdigest(),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCHEMA, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--max-sequence-length", type=int, required=True)
    args = parser.parse_args()
    transform_csv(
        args.input,
        args.output,
        args.subject,
        args.model,
        args.revision,
        args.max_sequence_length,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
