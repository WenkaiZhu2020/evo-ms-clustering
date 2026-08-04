#!/usr/bin/env python3
"""Verify the final Stage 1-3 repository without running an experiment."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.repository_layout import (
    SUBJECTS,
    stage1_baseline_root,
    stage1_seed_robustness_root,
    stage3_subject_root,
)


ENVIRONMENT_PATH = ROOT / "configs" / "reproducibility" / "environments.json"


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
    contract = _load_json(ENVIRONMENT_PATH, errors)
    if contract is None:
        return None
    if contract.get("schema_version") != 1:
        errors.append("environments.json schema_version must be 1")
    supported = contract.get("supported_final_environment")
    if not isinstance(supported, dict):
        errors.append("environments.json is missing supported_final_environment")
        return contract
    if not str(supported.get("dependency_manager", "")).startswith("uv "):
        errors.append("supported dependency_manager must identify a pinned uv version")
    if supported.get("lockfile") != "uv.lock":
        errors.append("supported lockfile must be uv.lock")
    if supported.get("installation_command") != "uv sync --frozen":
        errors.append("supported installation command must be uv sync --frozen")
    if supported.get("scope") != ["stage1", "stage2", "stage3"]:
        errors.append("supported environment scope must be Stage 1, Stage 2, and Stage 3")
    for relative in ("pyproject.toml", "uv.lock"):
        if not (ROOT / relative).is_file():
            errors.append(f"{relative} is missing")
    for key in ("python", "common_packages", "stage3_semantic_packages", "dev_packages"):
        if key not in supported:
            errors.append(f"supported final environment is missing {key}")
    return contract


def check_environment() -> list[str]:
    errors: list[str] = []
    contract = load_environment(errors)
    if contract is None:
        return errors
    supported = contract.get("supported_final_environment", {})
    expected_python = str(supported.get("python", ""))
    actual_python = ".".join(str(part) for part in sys.version_info[:3])
    if actual_python != expected_python:
        errors.append(f"python expected {expected_python}, found {actual_python}")
    for group_name in ("common_packages", "stage3_semantic_packages", "dev_packages"):
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


def verify_stage1() -> dict[str, Any]:
    errors: list[str] = []
    for subject in SUBJECTS:
        if not stage1_baseline_root(subject, ROOT).is_dir():
            errors.append(f"{subject}: missing frozen Leiden baseline")
        if not stage1_seed_robustness_root(subject, ROOT).is_dir():
            errors.append(f"{subject}: missing seed-robustness control")
    return {
        "stage": "stage1",
        "passed": not errors,
        "status": "frozen outputs present; historical runtime was not fully recorded",
        "errors": errors,
    }


def verify_stage2(skip_environment: bool) -> dict[str, Any]:
    """Delegate formal historical-byte checks to the Stage 2 verifier."""
    command = [
        sys.executable,
        str(ROOT / "scripts/reproducibility/verify_stage2_formal_provenance.py"),
    ]
    if skip_environment:
        command.append("--skip-environment")
    completed = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        result = {
            "passed": False,
            "errors": [
                "Stage 2 verifier did not return JSON",
                completed.stderr.strip() or completed.stdout.strip(),
            ],
        }
    result["stage"] = "stage2"
    return result


def verify_stage3() -> dict[str, Any]:
    errors: list[str] = []
    for subject in SUBJECTS:
        subject_root = stage3_subject_root(subject, ROOT)
        seed_dirs = [subject_root / "validation" / "seed_00"]
        seed_dirs.extend(subject_root / "formal" / f"seed_{seed:02d}" for seed in range(1, 30))
        for seed, seed_dir in enumerate(seed_dirs):
            for filename in (
                "pareto_front_4d.csv",
                "projected_front_3d.csv",
                "selected_solution.json",
            ):
                if not (seed_dir / filename).is_file():
                    errors.append(f"{subject}: missing seed_{seed:02d}/{filename}")
    return {
        "stage": "stage3",
        "passed": not errors,
        "status": "final Declaration + Method Body artifacts present",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("stage1", "stage2", "stage3", "all"), required=True)
    parser.add_argument("--environment-only", action="store_true")
    parser.add_argument("--skip-environment", action="store_true")
    args = parser.parse_args()
    if args.environment_only and args.skip_environment:
        parser.error("--environment-only and --skip-environment are mutually exclusive")

    if args.environment_only:
        errors = check_environment()
        result: dict[str, Any] = {
            "stage": args.stage,
            "passed": not errors,
            "environment_only": True,
            "errors": errors,
        }
    elif args.stage == "stage1":
        result = verify_stage1()
    elif args.stage == "stage2":
        result = verify_stage2(skip_environment=args.skip_environment)
    elif args.stage == "stage3":
        result = verify_stage3()
    else:
        stage1 = verify_stage1()
        stage2 = verify_stage2(skip_environment=args.skip_environment)
        stage3 = verify_stage3()
        environment_errors = [] if args.skip_environment else check_environment()
        errors = list(environment_errors)
        for stage in (stage1, stage2, stage3):
            errors.extend(f"{stage['stage']}: {error}" for error in stage.get("errors", []))
        result = {
            "stage": "all",
            "passed": not errors,
            "environment": {"passed": not environment_errors, "errors": environment_errors},
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3,
            "errors": errors,
        }
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
