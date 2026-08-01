#!/usr/bin/env python3
"""Read-only analysis helpers for the final Stage 3 experiment.

The final method is the Declaration + Method Body representation.  This
module deliberately reads Stage 2 and final Stage 3 artifacts only; it has no
Stage 3A loader, path, or comparison branch.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.analysis.stage3 import availability
from evo_ms.analysis.statistics import deterministic_rows


def _load_experiment_module(filename: str, name: str):
    path = ROOT / "experiments/05_stage3_declaration_method_body" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load experiment module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = _load_experiment_module("run.py", "stage3_final_experiment_run")
formal = _load_experiment_module("run_robustness.py", "stage3_final_experiment_robustness")


SUBJECTS = adapter.SUBJECTS
SEEDS = tuple(range(30))
STORAGE_SUBJECT = adapter.STORAGE_SUBJECT
CLASS_COUNTS = adapter.EXPECTED_COUNTS
REPORT_ROOT = ROOT / "results/cross_subject/05_stage3_declaration_method_body"
STAGE2_CONFIG = adapter.STAGE2_CONFIG_PATH
STAGE3_CONFIG = adapter.STAGE3_CONFIG


def stage2_dir(subject: str, seed: int) -> Path:
    """Return the frozen Stage 2 formal result directory used for comparison."""
    return ROOT / "results" / STORAGE_SUBJECT[subject] / "03_stage2_nsga" / "robustness_final_30seeds" / f"seed_{seed:02d}"


def stage3_dir(subject: str, seed: int) -> Path:
    """Return the final Stage 3 directory."""
    return adapter.output_dir(subject, seed=seed)


def load_final_context(subject: str) -> dict[str, Any]:
    """Load the final Stage 3 context without any declaration-only fallback."""
    return adapter.load_context(subject)


def validate_final_seed(subject: str, seed: int) -> dict[str, Any]:
    context = load_final_context(subject)
    output = stage3_dir(subject, seed)
    if seed == 0:
        result = adapter.validate_run_output(output, context)
    else:
        result = formal.validate_formal_seed(subject, seed, output)
    return {"subject": subject, "seed": seed, **result, "representation_id": adapter.REPRESENTATION_ID}


def formal_inventory() -> pd.DataFrame:
    rows = []
    for subject in SUBJECTS:
        for seed in SEEDS:
            metadata_path = stage3_dir(subject, seed) / "run_metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            rows.append({
                "subject": subject,
                "seed": seed,
                "representation_id": metadata.get("representation_id"),
                "input_aggregate_sha256": metadata.get("input_aggregate_sha256"),
                "embedding_aggregate_sha256": metadata.get("embedding_aggregate_sha256"),
                "graph_sha256": metadata.get("graph_sha256"),
                "selected_solution_id": json.loads((stage3_dir(subject, seed) / "selected_solution.json").read_text(encoding="utf-8")).get("selected_solution_id"),
                "completion_status": metadata.get("completion_status"),
            })
    return pd.DataFrame(deterministic_rows(rows))


def validate_inventory() -> pd.DataFrame:
    rows = [validate_final_seed(subject, seed) for subject in SUBJECTS for seed in SEEDS]
    ordered = deterministic_rows(rows)
    if availability(ordered, "representation_id")["missing"]:
        raise ValueError("final Stage 3 inventory contains missing representation metadata")
    frame = pd.DataFrame(ordered)
    if set(frame["representation_id"]) != {adapter.REPRESENTATION_ID}:
        raise ValueError("final Stage 3 inventory contains an unexpected representation")
    return frame


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate final Stage 3 saved formal artifacts")
    parser.add_argument("--inventory-only", action="store_true")
    args = parser.parse_args()
    frame = formal_inventory() if args.inventory_only else validate_inventory()
    print(json.dumps({"status": "PASS", "rows": len(frame), "representation_id": adapter.REPRESENTATION_ID}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
