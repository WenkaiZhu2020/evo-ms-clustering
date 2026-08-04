#!/usr/bin/env python3
"""Verify recorded Stage 2 formal provenance without running NSGA-II."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from evo_ms.repository_layout import stage2_subject_root

SUBJECTS = ("jpetstore", "daytrader", "xerces-j")
CORE_SOURCES = (
    "experiments/02_stage2_nsga_structure_only/run.py",
    "experiments/02_stage2_nsga_structure_only/run_robustness.py",
    "src/evo_ms/extraction/dependency_extractor.py",
    "src/evo_ms/optimization/encoding.py",
    "src/evo_ms/optimization/objectives.py",
    "src/evo_ms/optimization/problem.py",
)
FORMAL_SOURCE_REF = "stage2-frozen"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob_sha256(ref: str, relative: str) -> str:
    """Hash historical source bytes without replacing the current worktree."""
    try:
        blob = subprocess.check_output(
            ["git", "show", f"{ref}:{relative}"],
            cwd=ROOT,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"cannot read {relative} from {ref}: {detail}") from exc
    return hashlib.sha256(blob).hexdigest()


def _manifest(subject: str) -> tuple[Path, dict]:
    run_dir = stage2_subject_root(subject, ROOT) / "robustness_final_30seeds"
    return run_dir, json.loads((run_dir / "robustness_manifest.json").read_text(encoding="utf-8"))


def _check_environment(errors: list[str]) -> None:
    if sys.version_info[:3] != (3, 13, 7):
        errors.append(f"python expected 3.13.7, found {sys.version.split()[0]}")
    for package, expected in (("numpy", "2.4.4"), ("pymoo", "0.6.2")):
        try:
            actual = metadata.version(package)
        except metadata.PackageNotFoundError:
            errors.append(f"{package} expected {expected}, found not installed")
        else:
            if actual != expected:
                errors.append(f"{package} expected {expected}, found {actual}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-environment", action="store_true")
    parser.add_argument(
        "--source-ref",
        default=FORMAL_SOURCE_REF,
        help="historical Git ref whose source/config bytes must match the formal manifests",
    )
    args = parser.parse_args()

    errors: list[str] = []
    verified: dict[str, dict[str, object]] = {}
    expected_config_sha: str | None = None
    expected_bounds_sha: str | None = None

    for subject in SUBJECTS:
        run_dir, manifest = _manifest(subject)
        subject_errors: list[str] = []
        if manifest.get("formal_seeds") != list(range(30)):
            subject_errors.append("formal_seeds is not exactly 0..29")
        for seed in range(30):
            seed_dir = run_dir / f"seed_{seed:02d}"
            for filename in (
                "pareto_front.csv",
                "pareto_labels.csv.xz",
                "run_metadata.json",
                "run_metrics.json",
            ):
                if not (seed_dir / filename).is_file():
                    subject_errors.append(f"missing seed_{seed:02d}/{filename}")
        for filename in ("class_nodes.csv", "structural_dependencies.csv"):
            path = ROOT / "data" / "extracted" / subject / filename
            expected = manifest["input_graph_hashes"][filename]
            if _sha256(path) != expected:
                subject_errors.append(f"input hash mismatch: {path.relative_to(ROOT)}")
        for relative in CORE_SOURCES:
            expected = manifest["source_fingerprint"][relative]
            try:
                actual = _git_blob_sha256(args.source_ref, relative)
            except RuntimeError as exc:
                subject_errors.append(str(exc))
            else:
                if actual != expected:
                    subject_errors.append(
                        f"source fingerprint mismatch at {args.source_ref}: {relative}"
                    )
        if expected_config_sha is None:
            expected_config_sha = manifest["algorithm_config_sha256"]
            expected_bounds_sha = manifest["bounds_config_sha256"]
        elif (manifest["algorithm_config_sha256"], manifest["bounds_config_sha256"]) != (expected_config_sha, expected_bounds_sha):
            subject_errors.append("config or bounds hash differs across subjects")
        verified[subject] = {"passed": not subject_errors, "errors": subject_errors}
        errors.extend(f"{subject}: {error}" for error in subject_errors)

    if expected_config_sha is not None:
        for relative, expected, label in (
            ("configs/experiments/02_stage2_nsga_structure_only.yml", expected_config_sha, "algorithm"),
            ("configs/experiments/stage2_robustness_bounds.yml", expected_bounds_sha, "bounds"),
        ):
            try:
                actual = _git_blob_sha256(args.source_ref, relative)
            except RuntimeError as exc:
                errors.append(str(exc))
            else:
                if actual != expected:
                    errors.append(f"{label} config hash mismatch at {args.source_ref}")

    operating_profile = (
        ROOT
        / "results"
        / "stage2"
        / "cross_subject"
        / "operating_profile"
        / "canonical_operating_solution_per_seed.csv"
    )
    with operating_profile.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    profile_pairs = {(row["subject"], int(row["seed"])) for row in rows}
    expected_pairs = {(subject, seed) for subject in SUBJECTS for seed in range(30)}
    if len(rows) != 90 or profile_pairs != expected_pairs:
        errors.append("canonical operating profile is not exactly three subjects x seeds 0..29")
    if not args.skip_environment:
        _check_environment(errors)

    print(
        json.dumps(
            {
                "passed": not errors,
                "historical_source_ref": args.source_ref,
                "subjects": verified,
                "errors": errors,
            },
            indent=2,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
