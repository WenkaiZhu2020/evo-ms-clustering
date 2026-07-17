#!/usr/bin/env python3
"""Run the shared Soot extractor into an isolated Stage 3B directory."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.extraction.subject_extraction_config import load_extraction_cli_args
from scripts.stage3_method_body.isolation import (
    EXPERIMENT_ID,
    REPRESENTATION_ID,
    assert_declaration_source,
    assert_stage3b_temporary_path,
)


SUBJECTS = ("jpetstore", "daytrader", "xerces-j")
EXPECTED_COUNTS = {"jpetstore": 24, "daytrader": 53, "xerces-j": 814}


def _replace_arg(args: list[str], name: str, value: str) -> list[str]:
    updated = list(args)
    try:
        index = updated.index(name)
    except ValueError as exc:
        raise ValueError(f"extractor arguments do not contain {name}") from exc
    if index + 1 >= len(updated):
        raise ValueError(f"extractor argument {name} has no value")
    updated[index + 1] = value
    return updated


def extract_subject(subject: str, output_root: Path, maven: str) -> dict[str, object]:
    isolated = output_root / subject
    assert_stage3b_temporary_path(isolated)
    isolated.mkdir(parents=True, exist_ok=True)
    extractor_args = load_extraction_cli_args(ROOT, subject)
    extractor_args = _replace_arg(extractor_args, "--out-dir", str(isolated))
    extractor_args = _replace_arg(
        extractor_args, "--semantic-out", str(isolated / "class_declarations.csv")
    )
    extractor_args.extend(["--method-body-out", str(isolated / "method_bodies.csv")])
    command = [
        maven,
        "-q",
        "-f",
        str(ROOT / "tools/soot_extractor/pom.xml"),
        "-DskipTests",
        "compile",
        "exec:java",
        "-Dexec.mainClass=org.evomicro.sootextractor.SootExtractorCli",
        f"-Dexec.args={shlex.join(extractor_args)}",
    ]
    environment = os.environ.copy()
    if Path("/usr/libexec/java_home").is_file():
        environment["JAVA_HOME"] = subprocess.check_output(
            ["/usr/libexec/java_home", "-v", "17"], text=True
        ).strip()
    if environment.get("JAVA_HOME"):
        environment["PATH"] = str(Path(environment["JAVA_HOME"]) / "bin") + os.pathsep + environment.get("PATH", "")
    subprocess.run(command, cwd=ROOT, check=True, env=environment)

    declaration_path = isolated / "class_declarations.csv"
    body_path = isolated / "method_bodies.csv"
    with declaration_path.open("r", encoding="utf-8", newline="") as handle:
        declaration_rows = list(csv.DictReader(handle))
    with body_path.open("r", encoding="utf-8", newline="") as handle:
        body_rows = list(csv.DictReader(handle))
    count = len(declaration_rows)
    if count != EXPECTED_COUNTS[subject]:
        raise RuntimeError(
            f"{subject}: extracted {count} classes, expected {EXPECTED_COUNTS[subject]}"
        )
    expected_declaration_path = assert_declaration_source(
        ROOT / "data/semantic_inputs" / f"{subject}_class_declarations.csv",
        "xerces" if subject == "xerces-j" else subject,
    )
    with expected_declaration_path.open("r", encoding="utf-8", newline="") as handle:
        expected_declaration_rows = list(csv.DictReader(handle))
    if {row["class_id"] for row in declaration_rows} != {
        row["class_id"]
        for row in expected_declaration_rows
    }:
        raise RuntimeError(f"{subject}: isolated declaration scope differs from frozen Stage 3A scope")
    try:
        output_directory = str(isolated.relative_to(ROOT))
    except ValueError:
        output_directory = str(isolated)
    return {
        "subject": subject,
        "class_count": count,
        "method_body_row_count": len(body_rows),
        "output_directory": output_directory,
        "command": command,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "data/semantic_text/declaration_method_body/extraction",
    )
    parser.add_argument("--subject", action="append", choices=SUBJECTS)
    parser.add_argument("--maven", default="mvn")
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    subjects = tuple(args.subject) if args.subject else SUBJECTS
    output_root = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
    records = [extract_subject(subject, output_root, args.maven) for subject in subjects]
    manifest_path = args.manifest or output_root / "extraction_manifest.json"
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "representation": "declaration_method_body",
                "representation_version": "Body V1",
                "experiment_id": EXPERIMENT_ID,
                "representation_id": REPRESENTATION_ID,
                "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source_commit": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                "subjects": records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
