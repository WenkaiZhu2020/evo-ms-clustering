#!/usr/bin/env python3
"""Produce the Stage 3A inheritance and hard-coded path audit records."""

from __future__ import annotations

import csv
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports/stage3_method_body"
PATTERN = re.compile(
    r"04_stage3_semantic|reports/stage3|stage3_semantic|semantic_embeddings|semantic_graph|semantic_text"
)


def repository_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
    )
    return [ROOT / line for line in output.splitlines() if line]


def classify_file(path: Path) -> tuple[str, str, str, str]:
    rel = path.relative_to(ROOT).as_posix()
    if (
        rel.startswith("scripts/stage3_method_body/")
        or rel == "configs/experiments/05_stage3_declaration_method_body.yml"
        or rel.startswith("reports/stage3_method_body/")
        or rel == "tests/test_stage3_method_body_isolation.py"
        or (
            rel
            == "tools/soot_extractor/src/main/java/org/evomicro/sootextractor/SootExtractorCli.java"
        )
    ):
        return "Group D", "yes", "yes", "continue only under Stage 3B namespace"
    if (
        rel.startswith("reports/stage3/")
        or rel.startswith("results/") and "/04_stage3_semantic/" in f"/{rel}/"
        or rel.startswith("data/semantic_inputs/")
        or rel.startswith("docs/stage3/")
    ):
        return "Group B", "evaluation-only", "no", "retain frozen Stage 3A evidence"
    if rel.startswith("configs/experiments/04_stage3_semantic") or rel.startswith(
        "experiments/04_stage3_semantic/"
    ) or rel.startswith("scripts/stage3/"):
        return "Group C", "selectively", "no", "reuse only through explicit Stage 3B adapter"
    if rel.startswith("src/") or rel.startswith("scripts/") or rel.startswith("tests/"):
        return "Group A", "yes", "no", "reuse unchanged unless identity guard is required"
    return "Group A", "yes", "no", "retain; no Stage 3B boundary change required"


def write_file_audit() -> None:
    rows: list[dict[str, str]] = []
    for path in repository_files():
        if not path.is_file() or path.stat().st_size > 8_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        group, read_allowed, write_allowed, action = classify_file(path)
        rel = path.relative_to(ROOT).as_posix()
        rows.append(
            {
                "path": rel,
                "classification": group,
                "needed_by_stage3b": read_allowed,
                "read_allowed": read_allowed,
                "write_allowed": write_allowed,
                "action": action,
            }
        )
    output = REPORT_ROOT / "inherited_stage3a_file_audit.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "path",
                "classification",
                "needed_by_stage3b",
                "read_allowed",
                "write_allowed",
                "action",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: row["path"]))


def write_path_reference_audit() -> None:
    rows: list[dict[str, str]] = []
    for path in repository_files():
        if not path.is_file() or path.stat().st_size > 8_000_000:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith("reports/stage3_method_body/") and rel.endswith(".csv"):
            continue
        for line_number, line in enumerate(lines, start=1):
            for match in PATTERN.finditer(line):
                matched = match.group(0)
                source_code = rel.startswith(("scripts/", "experiments/", "src/", "tests/", "configs/"))
                if rel.startswith(("scripts/stage3_method_body/", "reports/stage3_method_body/")) or rel == "tests/test_stage3_method_body_isolation.py":
                    classification = "intentional Stage 3B boundary/audit reference"
                    risk = "low"
                    action = "retain; these references enforce isolation"
                elif rel == "configs/experiments/05_stage3_declaration_method_body.yml":
                    classification = "explicit Stage 3B boundary configuration"
                    risk = "low"
                    action = "retain; Stage 3A references are declaration-source or forbidden-boundary declarations"
                elif source_code and ("04_stage3_semantic" in line or "reports/stage3" in line):
                    classification = "dangerous hard-coded Stage 3A route"
                    risk = "high"
                    action = "route Stage 3B through explicit 05 config and identity guards"
                elif rel.startswith(("reports/", "docs/")):
                    classification = "historical or documentation-only Stage 3A reference"
                    risk = "low"
                    action = "preserve; do not rewrite frozen provenance"
                elif "semantic_text" in matched or "semantic_graph" in matched:
                    classification = "reusable semantic concept"
                    risk = "review"
                    action = "parameterize only if used as an artifact path"
                else:
                    classification = "Stage 3A artifact/config reference"
                    risk = "medium"
                    action = "keep read-only or use explicit Stage 3B adapter"
                rows.append(
                    {
                        "path": rel,
                        "line": str(line_number),
                        "matched_text": matched,
                        "classification": classification,
                        "stage3b_risk": risk,
                        "required_action": action,
                    }
                )
    output = REPORT_ROOT / "stage3a_path_reference_audit.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "path",
                "line",
                "matched_text",
                "classification",
                "stage3b_risk",
                "required_action",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    write_file_audit()
    write_path_reference_audit()
