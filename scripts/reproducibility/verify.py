#!/usr/bin/env python3
"""Verify frozen repository stages without running an experiment."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_PATH = ROOT / "configs" / "reproducibility" / "environments.json"
SUBJECTS = ("jpetstore", "daytrader", "xerces-j")
FORMAL_SEED_FILES = (
    "pareto_front.csv",
    "pareto_labels.csv.xz",
    "run_metadata.json",
    "run_metrics.json",
)
CORE_SOURCES = (
    # run.py contains the post-hoc operating-profile selector and is therefore
    # intentionally excluded from frozen-search source fingerprint checks.
    "experiments/02_stage2_nsga_structure_only/run_robustness.py",
    "src/evo_ms/extraction/dependency_extractor.py",
    "src/evo_ms/optimization/encoding.py",
    "src/evo_ms/optimization/objectives.py",
    "src/evo_ms/optimization/problem.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"could not read JSON {path.relative_to(ROOT)}: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"JSON object expected in {path.relative_to(ROOT)}")
        return None
    return value


def load_environment(errors: list[str]) -> dict[str, Any] | None:
    value = _load_json(ENVIRONMENT_PATH, errors)
    if value is None:
        return None
    if value.get("schema_version") != 1:
        errors.append("environments.json schema_version must be 1")
    supported = value.get("supported_reproduction_environment")
    if not isinstance(supported, dict):
        errors.append("environments.json is missing supported_reproduction_environment")
        return value
    if supported.get("dependency_manager") != "uv":
        errors.append("supported dependency_manager must be uv")
    if supported.get("lockfile") != "uv.lock":
        errors.append("supported lockfile must be uv.lock")
    if not (ROOT / "pyproject.toml").is_file():
        errors.append("pyproject.toml is missing")
    if not (ROOT / "uv.lock").is_file():
        errors.append("uv.lock is missing")
    for key in ("python", "packages", "dev_packages"):
        if key not in supported:
            errors.append(f"supported environment is missing {key}")
    stages = value.get("stages")
    if not isinstance(stages, dict):
        errors.append("environments.json is missing stages")
    else:
        required_stage_status = {
            "stage1": "frozen outputs; environment not formally recorded",
            "stage2": "frozen",
            "stage3": "not present in stage2-nsga",
        }
        for stage, status in required_stage_status.items():
            entry = stages.get(stage)
            if not isinstance(entry, dict):
                errors.append(f"environments.json is missing stages.{stage}")
                continue
            if entry.get("status") != status:
                errors.append(f"stages.{stage}.status is not {status!r}")
    return value


def check_environment() -> list[str]:
    errors: list[str] = []
    spec = load_environment(errors)
    if spec is None:
        return errors
    supported = spec.get("supported_reproduction_environment", {})
    expected_python = str(supported.get("python", ""))
    actual_python = ".".join(str(part) for part in sys.version_info[:3])
    if actual_python != expected_python:
        errors.append(f"python expected {expected_python}, found {actual_python}")
    for group_name in ("packages", "dev_packages"):
        packages = supported.get(group_name, {})
        if not isinstance(packages, dict):
            errors.append(f"{group_name} must be an object")
            continue
        for package, expected in packages.items():
            try:
                actual = metadata.version(package)
            except metadata.PackageNotFoundError:
                errors.append(f"{package} expected {expected}, found not installed")
            else:
                if actual != expected:
                    errors.append(f"{package} expected {expected}, found {actual}")
    return errors


def check_formal_manifest_environment(spec: dict[str, Any], errors: list[str]) -> None:
    evidence = spec.get("formal_manifest_evidence", {})
    expected_python = evidence.get("python")
    expected_packages = evidence.get("packages", {})
    locations = evidence.get("manifest_locations", [])
    if not isinstance(expected_packages, dict) or not isinstance(locations, list):
        errors.append("formal_manifest_evidence has an invalid shape")
        return
    for relative in locations:
        path = ROOT / str(relative)
        manifest = _load_json(path, errors)
        if manifest is None:
            continue
        recorded_python = str(manifest.get("python_version", "")).split()[0]
        if recorded_python != expected_python:
            errors.append(f"formal manifest Python mismatch: {relative}")
        for package, expected in expected_packages.items():
            manifest_key = f"{package}_version"
            if str(manifest.get(manifest_key)) != str(expected):
                errors.append(f"formal manifest {manifest_key} mismatch: {relative}")


def verify_stage2(skip_environment: bool) -> dict[str, Any]:
    errors: list[str] = []
    verified: dict[str, dict[str, Any]] = {}
    spec = load_environment(errors)
    if spec is not None:
        check_formal_manifest_environment(spec, errors)
    if not skip_environment:
        errors.extend(check_environment())

    expected_config_sha: str | None = None
    expected_bounds_sha: str | None = None
    for subject in SUBJECTS:
        subject_errors: list[str] = []
        run_dir = ROOT / "results" / subject / "03_stage2_nsga" / "robustness_final_30seeds"
        manifest_path = run_dir / "robustness_manifest.json"
        manifest = _load_json(manifest_path, subject_errors)
        if manifest is None:
            errors.extend(f"{subject}: {error}" for error in subject_errors)
            continue
        if manifest.get("formal_seeds") != list(range(30)):
            subject_errors.append("formal_seeds is not exactly 0..29")
        for seed in range(30):
            seed_dir = run_dir / f"seed_{seed:02d}"
            for filename in FORMAL_SEED_FILES:
                if not (seed_dir / filename).is_file():
                    subject_errors.append(f"missing seed_{seed:02d}/{filename}")
        for filename in ("class_nodes.csv", "structural_dependencies.csv"):
            path = ROOT / "data" / "extracted" / subject / filename
            expected = manifest.get("input_graph_hashes", {}).get(filename)
            if not path.is_file() or not expected or _sha256(path) != expected:
                subject_errors.append(f"input hash mismatch: {path.relative_to(ROOT)}")
        for relative in CORE_SOURCES:
            expected = manifest.get("source_fingerprint", {}).get(relative)
            path = ROOT / relative
            if not path.is_file() or not expected or _sha256(path) != expected:
                subject_errors.append(f"source fingerprint mismatch: {relative}")
        config_sha = manifest.get("algorithm_config_sha256")
        bounds_sha = manifest.get("bounds_config_sha256")
        if expected_config_sha is None:
            expected_config_sha = config_sha
            expected_bounds_sha = bounds_sha
        elif (config_sha, bounds_sha) != (expected_config_sha, expected_bounds_sha):
            subject_errors.append("config or bounds hash differs across subjects")
        if subject_errors:
            errors.extend(f"{subject}: {error}" for error in subject_errors)
        verified[subject] = {"passed": not subject_errors, "errors": subject_errors}

    config_path = ROOT / "configs/experiments/02_stage2_nsga_structure_only.yml"
    bounds_path = ROOT / "configs/experiments/stage2_robustness_bounds.yml"
    if expected_config_sha and _sha256(config_path) != expected_config_sha:
        errors.append("algorithm config hash mismatch")
    if expected_bounds_sha and _sha256(bounds_path) != expected_bounds_sha:
        errors.append("bounds config hash mismatch")
    return {"stage": "stage2", "passed": not errors, "subjects": verified, "errors": errors}


def stage_status(stage: str) -> dict[str, Any]:
    if stage == "stage1":
        return {
            "stage": "stage1",
            "passed": False,
            "status": "not implemented / not formally frozen",
            "errors": ["Stage 1 has no formal repository verifier or environment record."],
        }
    return {
        "stage": "stage3",
        "passed": True,
        "status": "not present in this branch",
        "errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("stage2", "all"), required=True)
    parser.add_argument("--environment-only", action="store_true")
    parser.add_argument("--skip-environment", action="store_true")
    args = parser.parse_args()
    if args.environment_only and args.skip_environment:
        parser.error("--environment-only and --skip-environment are mutually exclusive")

    if args.environment_only:
        environment_errors = check_environment()
        stage2 = {
            "stage": "stage2",
            "passed": not environment_errors,
            "environment_only": True,
            "errors": environment_errors,
        }
    else:
        stage2 = verify_stage2(skip_environment=args.skip_environment)

    if args.stage == "stage2":
        result = stage2
    else:
        stage1 = stage_status("stage1")
        stage3 = stage_status("stage3")
        errors = list(stage2.get("errors", []))
        errors.extend(f"stage1: {error}" for error in stage1["errors"])
        result = {
            "stage": "all",
            "passed": bool(stage2["passed"] and stage3["passed"] and stage1["passed"]),
            "stage2": stage2,
            "stage1": stage1,
            "stage3": stage3,
            "errors": errors,
        }
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
