#!/usr/bin/env python3
"""Run and validate formal Stage 3B seeds 1--29.

Seed 0 is deliberately excluded.  It remains authoritative under the
validated ``validation/seed_00`` directory and is never copied or overwritten.
"""

from __future__ import annotations

import argparse
import csv
import errno
import hashlib
import importlib.util
import json
import os
import shlex
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.repository_layout import STAGE3_ROOT, stage3_subject_root

def _load_run_module():
    path = ROOT / "experiments/05_stage3_declaration_method_body/run.py"
    spec = importlib.util.spec_from_file_location("stage3_final_experiment_run", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load Stage 3 experiment runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = _load_run_module()


SUBJECTS = adapter.SUBJECTS
FORMAL_SEEDS = tuple(range(1, 30))
REPORT_ROOT = STAGE3_ROOT
RUNTIME_ROOT = REPORT_ROOT / "runtime"
LOG_ROOT = RUNTIME_ROOT / "logs"
LOCK_ROOT = RUNTIME_ROOT / "locks"
PID_ROOT = RUNTIME_ROOT / "pids"
EXPECTED_FILES = {
    "artifact_hashes.csv",
    "config_snapshot.yml",
    "graph_provenance.json",
    "objective_redundancy.json",
    "pareto_front_4d.csv",
    "partition_labels.csv",
    # posthoc_metrics.csv, run_metrics.json removed: the current
    # run_seed()/validate_run_output() implementation in run.py never writes
    # either file for any subject (verified by full-text search across
    # experiments/ and src/); posthoc_metrics.csv is consumed only by three
    # visualization scripts hardcoded to specific existing jpetstore/daytrader/
    # xerces seed paths from an earlier, richer version of run_seed(), and
    # run_metrics.json under a Stage 3 formal seed directory is not consumed
    # anywhere. This set now matches the artifacts run_seed() actually produces.
    "projected_front_3d.csv",
    "projected_hypervolume.json",
    "run.log",
    "run_metadata.json",
    "selected_partition.csv",
    "selected_solution.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def formal_output_dir(subject: str, seed: int) -> Path:
    if seed not in FORMAL_SEEDS:
        raise ValueError(f"formal Stage 3B runner accepts seeds 1..29 only, got {seed}")
    path = adapter.output_dir(subject, seed=seed)
    expected = stage3_subject_root(subject, ROOT) / "formal" / f"seed_{seed:02d}"
    resolved = path.resolve()
    root_resolved = ROOT.resolve()
    # Check by ROOT-relative path segment, not an absolute-path substring: a
    # substring check on the full path incorrectly trips whenever the repository
    # checkout itself lives under a directory whose name happens to contain
    # "validation" (e.g. a dedicated validation worktree), even though the
    # equality check above already verifies the output location is canonical.
    relative_parts = resolved.relative_to(root_resolved).parts if resolved.is_relative_to(root_resolved) else ()
    if resolved != expected.resolve() or "validation" in relative_parts:
        raise ValueError(f"formal output path isolation failure: {path}")
    return path


def _identity(
    context: dict[str, Any],
    subject: str,
    seed: int,
    *,
    config_hash: str | None = None,
) -> dict[str, Any]:
    source = context["graph_provenance"]["embedding_source"]
    return {
        "experiment_id": adapter.EXPERIMENT_ID,
        "experiment_name": adapter.EXPERIMENT_ID,
        "representation_id": adapter.REPRESENTATION_ID,
        "subject": subject,
        "seed": seed,
        "input_hash": context["semantic_graph_metadata"]["input_aggregate_sha256"],
        "input_aggregate_sha256": context["semantic_graph_metadata"]["input_aggregate_sha256"],
        "embedding_aggregate_sha256": source["embedding_aggregate_sha256"],
        "embedding_file_sha256": source["embedding_sha256"],
        "class_mapping_sha256": context["semantic_graph_metadata"]["class_mapping_sha256"],
        "graph_sha256": context["semantic_graph_hash"],
        "config_hash": config_hash or sha256_file(adapter.STAGE3_CONFIG),
    }


def _rewrite_artifact_hashes(output: Path, identity: dict[str, Any]) -> None:
    rows = []
    for path in sorted(output.iterdir()):
        if not path.is_file() or path.name == "artifact_hashes.csv":
            continue
        rows.append({
            **identity,
            "path": path.name,
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        })
    with (output / "artifact_hashes.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_formal_provenance(output: Path, context: dict[str, Any], subject: str, seed: int, command: str) -> None:
    identity = _identity(context, subject, seed)
    config_text = adapter.STAGE3_CONFIG.read_text(encoding="utf-8")
    (output / "config_snapshot.yml").write_text(config_text, encoding="utf-8")
    provenance = {
        **identity,
        "subject": subject,
        "seed": seed,
        "graph_metadata": context["semantic_graph_metadata"],
        "graph_edges_path": str(context["graph_provenance"]["paths"]["edges"].relative_to(ROOT)),
        "graph_metadata_path": str(context["graph_provenance"]["paths"]["metadata"].relative_to(ROOT)),
        "class_mapping_path": str(context["graph_provenance"]["paths"]["mapping"].relative_to(ROOT)),
        "source_commit": context["semantic_graph_metadata"]["source_commit"],
        "generation_command": command,
        "generated_at_utc": utc_now(),
    }
    (output / "graph_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _rewrite_artifact_hashes(output, identity)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class SeedLock:
    def __init__(self, subject: str, seed: int, command: str) -> None:
        self.subject = subject
        self.seed = seed
        self.command = command
        self.path = LOCK_ROOT / f"{subject}_seed_{seed:02d}.lock"
        self.pid_path = PID_ROOT / f"{subject}_seed_{seed:02d}.pid"
        self.acquired = False

    def __enter__(self):
        LOCK_ROOT.mkdir(parents=True, exist_ok=True)
        PID_ROOT.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": os.getpid(), "subject": self.subject, "seed": self.seed,
            "command": self.command, "started_at_utc": utc_now(),
        }
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError as exc:
            try:
                existing = json.loads(self.path.read_text(encoding="utf-8"))
                owner_pid = int(existing["pid"])
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as parse_error:
                raise RuntimeError(f"cannot safely inspect existing lock {self.path}") from parse_error
            if _pid_alive(owner_pid):
                raise RuntimeError(f"formal seed lock is held by active pid {owner_pid}: {self.path}") from exc
            # The process was checked non-blockingly and is gone; stale lock
            # removal is therefore safe and explicit.
            self.path.unlink()
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        self.pid_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        self.acquired = True
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.acquired:
            for path in (self.pid_path, self.path):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass


def validate_formal_seed(subject: str, seed: int, output: Path) -> dict[str, Any]:
    if seed not in FORMAL_SEEDS:
        raise ValueError("formal validation cannot validate seed 0")
    expected_path = formal_output_dir(subject, seed)
    if output.resolve() != expected_path.resolve():
        raise ValueError(f"formal output path mismatch: {output}")
    if not output.is_dir():
        raise ValueError(f"missing formal seed directory: {output}")
    actual_files = {path.name for path in output.iterdir() if path.is_file()}
    if actual_files != EXPECTED_FILES:
        raise ValueError(f"{subject} seed {seed}: artifact set mismatch: {sorted(actual_files ^ EXPECTED_FILES)}")
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    context = adapter.load_context(subject)
    config_snapshot = output / "config_snapshot.yml"
    snapshot_hash = sha256_file(config_snapshot)
    if snapshot_hash != metadata["config_sha256"] or snapshot_hash != metadata["config_hash"]:
        raise ValueError(f"{subject} seed {seed}: configuration snapshot hash mismatch")
    expected = _identity(context, subject, seed, config_hash=snapshot_hash)
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(f"{subject} seed {seed}: metadata {key} mismatch")
    required_metadata = {
        "run_type": "formal", "completion_status": "completed",
        "population_size": context["population_size"], "generations": context["generations"],
        "objective_order": adapter.STAGE3_OBJECTIVE_ORDER,
        "report_objective_order": ["coupling", "cohesion", "imbalance", "f_semantic"],
        "semantic_objective_used_for_selection": False,
    }
    for key, value in required_metadata.items():
        if metadata.get(key) != value:
            raise ValueError(f"{subject} seed {seed}: required metadata {key} mismatch")
    graph_provenance = json.loads((output / "graph_provenance.json").read_text(encoding="utf-8"))
    for key, value in expected.items():
        if graph_provenance.get(key) != value:
            raise ValueError(f"{subject} seed {seed}: graph provenance {key} mismatch")
    log_text = (output / "run.log").read_text(encoding="utf-8")
    if f"completed runtime_seconds=" not in log_text:
        raise ValueError(f"{subject} seed {seed}: completion marker missing from run log")
    adapter.validate_run_output(output, context)
    return {
        "subject": subject, "seed": seed, "path": str(output.relative_to(ROOT)),
        "representation_id": metadata["representation_id"], "graph_hash": metadata["graph_sha256"],
        "config_hash": metadata["config_hash"], "completion_status": metadata["completion_status"],
        "artifact_hash_status": "passed", "validation_status": "passed",
    }


def run_one(subject: str, seed: int) -> dict[str, Any]:
    if seed not in FORMAL_SEEDS:
        raise ValueError("run_one refuses seed 0; validation seed 0 is authoritative")
    output = formal_output_dir(subject, seed)
    command = " ".join(shlex.quote(value) for value in [
        sys.executable, str(ROOT / "experiments/05_stage3_declaration_method_body/run_robustness.py"),
        "--subject", subject, "--seeds", str(seed),
    ])
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = LOG_ROOT / f"formal_{subject}.log"
    with SeedLock(subject, seed, command):
        if output.exists():
            try:
                return validate_formal_seed(subject, seed, output)
            except Exception as exc:
                raise RuntimeError(f"refusing to overwrite partial or invalid formal output {output}: {exc}") from exc
        output.parent.mkdir(parents=True, exist_ok=True)
        start_line = f"start_utc={utc_now()} subject={subject} seed={seed} pid={os.getpid()} command={command}\n"
        with log_path.open("a", encoding="utf-8") as log:
            log.write(start_line)
        try:
            context = adapter.load_context(subject)
            adapter.run_seed(subject, seed, output, run_type="formal", allow_formal=True)
            _write_formal_provenance(output, context, subject, seed, command)
            result = validate_formal_seed(subject, seed, output)
            with log_path.open("a", encoding="utf-8") as log:
                log.write(f"complete_utc={utc_now()} subject={subject} seed={seed} status=passed\n")
            return result
        except Exception as exc:
            with log_path.open("a", encoding="utf-8") as log:
                log.write(f"failure_utc={utc_now()} subject={subject} seed={seed} error={type(exc).__name__}: {exc}\n")
            raise


def parse_seeds(value: str | None) -> list[int]:
    if not value:
        return list(FORMAL_SEEDS)
    values: set[int] = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            start, end = (int(part) for part in item.split("-", 1))
            values.update(range(start, end + 1))
        else:
            values.add(int(item))
    seeds = sorted(values)
    if not seeds or any(seed not in FORMAL_SEEDS for seed in seeds):
        raise ValueError("formal seed list must contain only seeds 1..29")
    return seeds


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", choices=SUBJECTS, required=True)
    parser.add_argument("--seeds", default=None, help="comma-separated seeds or inclusive ranges; seed 0 is forbidden")
    args = parser.parse_args()
    results = []
    for seed in parse_seeds(args.seeds):
        results.append(run_one(args.subject, seed))
        print(json.dumps(results[-1], sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
