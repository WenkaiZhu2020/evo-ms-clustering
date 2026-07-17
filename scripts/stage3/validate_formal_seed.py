#!/usr/bin/env python3
"""Independently validate one saved Stage 3 formal seed.

The validator reloads only saved Stage 3 and frozen Stage 2 artifacts.  It
does not run NSGA-II, load a model, regenerate embeddings, or rebuild a
semantic graph.  The Xerces inventory validator provides the independent
checks; this entry point supplies the subject-specific scope and provenance
for JPetStore and DayTrader as well.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.stage3 import validate_xerces_formal as formal


SUBJECT_CONFIG = formal.SUBJECT_CONFIG
FROZEN_ALGORITHM_FINGERPRINTS = {
    # Original validated runs and the serialization-only correction below
    # share the same optimizer, objectives, graphs, and selection rule.
    "c8d68cdadd19e61b576e487136ec78b8f16f50ef85e4e1bafb732c325818fb3c",
    "dcc6034374ace8742c01f4114d55fc81ac041900a3629fc108dc46693d5316fe",
    "50f71a17345aef815fe354d2c0c83cccd896936d6a0199cc088ed2bb138663cb",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_source(subject: str, seed: int) -> Path:
    if subject not in SUBJECT_CONFIG:
        raise ValueError(f"unknown subject: {subject}")
    if seed == 0:
        return ROOT / "results" / subject / "04_stage3_semantic/validation/seed_00"
    return ROOT / "results" / subject / "04_stage3_semantic/formal" / f"seed_{seed:02d}"


def default_report(subject: str, seed: int) -> Path:
    return ROOT / "reports/stage3/seed_validation" / subject / f"seed_{seed:02d}.json"


def validate_saved_seed(subject: str, seed: int, source: Path) -> dict[str, Any]:
    if subject not in SUBJECT_CONFIG:
        raise ValueError(f"unknown subject: {subject}")
    if seed not in range(30):
        raise ValueError("seed must be in 0..29")
    if not source.is_dir():
        raise formal.ValidationFailure(f"missing saved seed directory: {source}")

    config = SUBJECT_CONFIG[subject]
    context = formal.stage3_runner.load_context(subject)
    expected_config_sha = formal.sha256_file(formal.CONFIG_PATH)
    expected_graph_sha = context["semantic_graph_hash"]
    expected_raw_edge_hash = formal.stage2._frame_sha256(context["raw_edges"])
    record = formal.validate_seed(
        seed,
        source,
        context,
        expected_config_sha,
        expected_graph_sha,
        expected_raw_edge_hash,
        subject=subject,
        storage_subject=config["storage_subject"],
        expected_class_count=config["class_count"],
    )

    metadata = formal.load_json(source / "run_metadata.json")
    fingerprint = formal.algorithm_fingerprint(metadata["implementation_commit"])
    if fingerprint["sha256"] not in FROZEN_ALGORITHM_FINGERPRINTS:
        raise formal.ValidationFailure(
            f"seed {seed}: algorithm fingerprint mismatch: {fingerprint['sha256']}"
        )

    record.update(
        {
            "subject": subject,
            "expected_class_count": config["class_count"],
            "validated_at_utc": utc_now(),
            "algorithm_fingerprint": fingerprint,
            "provenance": {
                "config_sha256": expected_config_sha,
                "semantic_graph_sha256": expected_graph_sha,
                "raw_edge_hash": expected_raw_edge_hash,
                "stage2_config_path": metadata["stage2_config_path"],
                "semantic_input_source": metadata["semantic_input_source"],
                "no_model_inference": metadata["no_model_inference"],
                "no_graph_fusion": metadata["no_graph_fusion"],
            },
            "validation_checks": {
                "four_dimensional_non_dominance": True,
                "projected_three_dimensional_non_dominance": True,
                "projected_hypervolume_recomputed": True,
                "semantic_objective_non_constant": True,
                "representative_selection_recomputed": True,
                "class_partition_integrity": True,
                "stage2_objective_invariance": metadata["structural_objective_invariance"]["pass"],
                "semantic_graph_is_separate_input": metadata["no_graph_fusion"],
            },
        }
    )
    return record


def write_report(record: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", choices=sorted(SUBJECT_CONFIG), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    source = args.source or default_source(args.subject, args.seed)
    report = args.report or default_report(args.subject, args.seed)
    record = validate_saved_seed(args.subject, args.seed, source)
    write_report(record, report)
    print(json.dumps({
        "subject": args.subject,
        "seed": args.seed,
        "status": record["status"],
        "source": str(source.relative_to(ROOT)),
        "report": str(report.relative_to(ROOT)),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
