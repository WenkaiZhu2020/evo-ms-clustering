#!/usr/bin/env python3
"""Produce Stage 3 declaration-input quality diagnostics and review samples."""

from __future__ import annotations

import argparse
import csv
import random
import re
from pathlib import Path

from transformers import AutoTokenizer


SUBJECTS = ("jpetstore", "daytrader", "xerces-j")
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
FQN_PATTERN = re.compile(r"(?:\b[a-z_][a-z0-9_]*\.)+[A-Z][A-Za-z0-9_$]*")
LABEL_PATTERN = re.compile(r"leiden|cluster|nsga|reference|service_", re.IGNORECASE)
EDGE_PATTERN = re.compile(r"->|-->|edge\(")
GETTER_PATTERN = re.compile(r"^(get|set|is)[A-Z]")
METHOD_NAME_PATTERN = re.compile(r"([A-Za-z_$][A-Za-z0-9_$]*)\([^;]*\);$")


def read_rows(inputs_dir: Path, subject: str) -> list[dict[str, str]]:
    path = inputs_dir / f"{subject}_class_declarations.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != SCHEMA:
            raise ValueError(f"{path} has schema {reader.fieldnames}, expected {SCHEMA}")
        rows = list(reader)
    if [row["class_id"] for row in rows] != sorted(row["class_id"] for row in rows):
        raise ValueError(f"{path} is not sorted by class_id")
    return rows


def token_count(tokenizer, text: str) -> int:
    encoded = tokenizer(
        text,
        truncation=False,
        add_special_tokens=True,
        return_attention_mask=False,
    )
    return len(encoded["input_ids"])


def method_names(text: str) -> list[str]:
    names = []
    for line in text.splitlines():
        if line.startswith("    ") and line.endswith(";"):
            match = METHOD_NAME_PATTERN.search(line)
            if not match:
                raise ValueError(f"cannot parse method line: {line!r}")
            names.append(match.group(1))
    return names


def choose_samples(rows: list[dict[str, str]]) -> list[tuple[str, dict[str, str]]]:
    selected: dict[str, tuple[str, dict[str, str]]] = {}

    def add(category: str, candidates: list[dict[str, str]], limit: int) -> None:
        for row in candidates:
            if row["class_id"] not in selected and len(
                [item for item in selected.values() if item[0] == category]
            ) < limit:
                selected[row["class_id"]] = (category, row)

    add(
        "highest method_count",
        sorted(rows, key=lambda row: (-int(row["method_count"]), row["class_id"])),
        2,
    )
    add(
        "lowest or zero-method",
        sorted(rows, key=lambda row: (int(row["method_count"]), row["class_id"])),
        2,
    )
    add("interface", sorted((r for r in rows if r["kind"] == "interface"), key=lambda r: r["class_id"]), 1)
    add("abstract class", sorted((r for r in rows if r["kind"] == "abstract class"), key=lambda r: r["class_id"]), 1)
    add("enum", sorted((r for r in rows if r["kind"] == "enum"), key=lambda r: r["class_id"]), 1)
    add("annotated class", sorted((r for r in rows if int(r["annotation_count"]) > 0), key=lambda r: r["class_id"]), 1)
    add("class with superclass", sorted((r for r in rows if r["superclass_present"] == "true"), key=lambda r: r["class_id"]), 1)

    remaining = sorted((r for r in rows if r["class_id"] not in selected), key=lambda r: r["class_id"])
    random.Random(42).shuffle(remaining)
    for row in remaining:
        if len(selected) == 10:
            break
        selected[row["class_id"]] = ("seed-42 remainder", row)
    if len(selected) != 10:
        raise ValueError(f"could not select 10 samples; got {len(selected)}")
    return list(selected.values())


def format_sample(category: str, row: dict[str, str]) -> str:
    return (
        f"### {row['class_id']} ({category})\n"
        f"kind={row['kind']}; superclass_present={row['superclass_present']}; "
        f"method_count={row['method_count']}; annotation_count={row['annotation_count']}; "
        f"interface_count={row['interface_count']}; "
        f"truncated_method_count={row['truncated_method_count']}; "
        f"input_hash[:12]={row['input_hash'][:12]}\n\n"
        "```text\n"
        f"{row['semantic_text']}"
        "```\n"
    )


def build_report(inputs_dir: Path, model: str, revision: str, max_length: int) -> tuple[str, str]:
    tokenizer = AutoTokenizer.from_pretrained(
        model,
        revision=revision,
        use_fast=True,
        trust_remote_code=False,
    )
    actual_max_length = int(tokenizer.model_max_length)
    if actual_max_length != max_length:
        raise ValueError(f"tokenizer reports {actual_max_length}, expected {max_length}")

    all_rows: dict[str, list[dict[str, str]]] = {}
    token_values: dict[str, dict[str, int]] = {}
    for subject in SUBJECTS:
        rows = read_rows(inputs_dir, subject)
        all_rows[subject] = rows
        token_values[subject] = {
            row["class_id"]: token_count(tokenizer, row["semantic_text"]) for row in rows
        }
        for row in rows:
            if token_values[subject][row["class_id"]] > max_length:
                raise ValueError(
                    f"post-truncation text still exceeds limit: {subject}/{row['class_id']}"
                )

    lines = [
        "# Stage 3 Semantic Input Quality Summary",
        "",
        "Tokenizer counting used `nomic-ai/nomic-embed-code` at revision "
        f"`{revision}` with `model_max_length={actual_max_length}`, "
        "`truncation=false`, and `add_special_tokens=true`. No generic tokenizer "
        "was used. Truncation was applied before this report; the fixed CSV "
        "records every dropped method in `truncated_method_count`.",
        "",
        "## 1. Summary",
        "",
        "| subject | classes | zero-method classes | mean/max methods | mean/max text chars | mean/max token count | truncated classes | total truncated methods |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for subject in SUBJECTS:
        rows = all_rows[subject]
        methods = [int(row["method_count"]) for row in rows]
        chars = [len(row["semantic_text"]) for row in rows]
        tokens = list(token_values[subject].values())
        truncated = [int(row["truncated_method_count"]) for row in rows]
        lines.append(
            f"| {subject} | {len(rows)} | {sum(value == 0 for value in methods)} | "
            f"{sum(methods) / len(methods):.2f}/{max(methods)} | "
            f"{sum(chars) / len(chars):.2f}/{max(chars)} | "
            f"{sum(tokens) / len(tokens):.2f}/{max(tokens)} | "
            f"{sum(value > 0 for value in truncated)} | {sum(truncated)} |"
        )

    lines.extend(["", "## 2. Truncation risk", ""])
    for subject in SUBJECTS:
        risky = [
            (row, token_values[subject][row["class_id"]])
            for row in all_rows[subject]
            if token_values[subject][row["class_id"]] > 0.8 * max_length
        ]
        lines.append(f"### {subject}")
        if not risky:
            lines.append("No class exceeded 80% of the 32768-token limit.")
        else:
            lines.append("| class_id | tokens | method_count | truncated_method_count |")
            lines.append("| --- | ---: | ---: | ---: |")
            for row, count in risky:
                lines.append(
                    f"| `{row['class_id']}` | {count} | {row['method_count']} | "
                    f"{row['truncated_method_count']} |"
                )
        lines.append("")

    lines.extend(["## 3. Getter/setter saturation diagnosis", "", "No filtering was applied.", ""])
    for subject in SUBJECTS:
        lines.append(f"### {subject}")
        lines.append("| class_id | method_count | getter/setter count | ratio |")
        lines.append("| --- | ---: | ---: | ---: |")
        for row in sorted(all_rows[subject], key=lambda r: (-int(r["method_count"]), r["class_id"]))[:10]:
            names = method_names(row["semantic_text"])
            matching = sum(bool(GETTER_PATTERN.match(name)) for name in names)
            ratio = matching / len(names) if names else 0.0
            lines.append(
                f"| `{row['class_id']}` | {row['method_count']} | {matching} | {ratio:.3f} |"
            )
        lines.append("")

    lines.extend(["## 4. Contamination checks on decoded `semantic_text` only", ""])
    for subject in SUBJECTS:
        fqn_hits = []
        path_hits = []
        edge_hits = []
        label_hits = []
        for row in all_rows[subject]:
            text = row["semantic_text"]
            if FQN_PATTERN.search(text):
                fqn_hits.append(row["class_id"])
            if "/" in text:
                path_hits.append(row["class_id"])
            if EDGE_PATTERN.search(text):
                edge_hits.append(row["class_id"])
            matches = sorted(set(match.group(0).lower() for match in LABEL_PATTERN.finditer(text)))
            if matches:
                label_hits.append((row["class_id"], matches))
        lines.append(f"### {subject}")
        lines.append(f"- FQN pattern hits: `{len(fqn_hits)}` (must be zero)")
        lines.append(f"- Path separator hits: `{len(path_hits)}` (must be zero)")
        lines.append(f"- Edge notation hits: `{len(edge_hits)}` (must be zero)")
        if label_hits:
            lines.append("- Label-word hits for manual review:")
            for class_id, matches in label_hits:
                lines.append(f"  - `{class_id}`: {', '.join(matches)}")
        else:
            lines.append("- Label-word hits for manual review: none")
        if fqn_hits or path_hits or edge_hits:
            raise ValueError(f"contamination check failed for {subject}")
        lines.append("")

    lines.extend(["## 5. Zero-method classes", ""])
    for subject in SUBJECTS:
        zero_rows = [row for row in all_rows[subject] if int(row["method_count"]) == 0]
        lines.append(f"### {subject}")
        if not zero_rows:
            lines.append("None.")
        else:
            lines.append(
                "All listed rows use the frozen non-empty empty-body template "
                "(header, no method lines, closing brace, final newline)."
            )
            lines.append("")
            for row in zero_rows:
                if not row["semantic_text"] or int(row["truncated_method_count"]) != 0:
                    raise ValueError(f"invalid zero-method template: {subject}/{row['class_id']}")
                body_lines = row["semantic_text"].splitlines()
                header_end = next(
                    (index for index, line in enumerate(body_lines) if line.endswith(" {")),
                    None,
                )
                if (
                    header_end is None
                    or body_lines[-1] != "}"
                    or body_lines[header_end + 1 : -1]
                    or not row["semantic_text"].endswith("\n")
                ):
                    raise ValueError(
                        f"invalid zero-method template shape: {subject}/{row['class_id']}"
                    )
                lines.append(f"#### `{row['class_id']}`")
                lines.extend(["```text", row["semantic_text"].rstrip("\n"), "```", ""])

    lines.extend(["## 6. Manual review samples", "", "Exactly 10 distinct classes per subject; category order and seed-42 remainder are frozen by the Day 2 procedure.", ""])
    printed = []
    for subject in SUBJECTS:
        lines.append(f"### {subject}")
        samples = choose_samples(all_rows[subject])
        for category, row in samples:
            block = format_sample(category, row)
            lines.append(block.rstrip("\n"))
            printed.append((subject, block))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n", "\n".join(
        f"===== {subject} =====\n{block}" for subject, block in printed
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--max-sequence-length", type=int, required=True)
    args = parser.parse_args()
    report, samples = build_report(
        args.inputs_dir, args.model, args.revision, args.max_sequence_length
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(samples)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
