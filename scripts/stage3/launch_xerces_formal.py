#!/usr/bin/env python3
"""Durably run the remaining formal Xerces Stage 3 seeds.

This is a thin orchestration layer around the frozen single-seed runner. It
does not change the optimization contract and refuses to overwrite partial
seed output. A process lock prevents two launchers from running concurrently.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "experiments/04_stage3_semantic/run.py"
DEFAULT_OUTPUT_ROOT = ROOT / "results/xerces/04_stage3_semantic/formal"
DEFAULT_LOCK = ROOT / "reports/stage3/xerces_formal_seed_launcher.lock"
FORMAL_SEEDS = tuple(range(30))


def completed_seed(path: Path) -> bool:
    metadata_path = path / "run_metadata.json"
    if not metadata_path.exists():
        return False
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return (
        metadata.get("subject") == "xerces"
        and int(metadata.get("seed", -1)) in FORMAL_SEEDS
        and metadata.get("run_type") == "formal"
        and metadata.get("completion_status") == "completed"
        and bool(metadata.get("validation", {}).get("validation_pass"))
    )


def run_remaining(output_root: Path, lock_path: Path) -> list[int]:
    output_root.mkdir(parents=True, exist_ok=True)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"another Xerces formal launcher is active: {lock_path}") from exc

        completed: list[int] = []
        launched: list[int] = []
        for seed in FORMAL_SEEDS[1:]:
            seed_dir = output_root / f"seed_{seed:02d}"
            if completed_seed(seed_dir):
                completed.append(seed)
                continue
            if seed_dir.exists() and any(seed_dir.iterdir()):
                raise RuntimeError(f"refusing to overwrite incomplete output: {seed_dir}")
            command = [
                sys.executable,
                str(RUNNER),
                "--subject",
                "xerces",
                "--seed",
                str(seed),
                "--output-dir",
                str(seed_dir.resolve()),
                "--run-type",
                "formal",
            ]
            print("launching", " ".join(command), flush=True)
            subprocess.run(command, cwd=ROOT, check=True)
            launched.append(seed)
        print(json.dumps({"completed_before_launch": completed, "launched": launched}), flush=True)
        return launched


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--lock-path", type=Path, default=DEFAULT_LOCK)
    args = parser.parse_args()
    run_remaining(args.output_root.resolve(), args.lock_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
