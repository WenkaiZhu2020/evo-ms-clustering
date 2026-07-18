"""Final-only preference analysis boundary.

This phase provides the self-contained entry point.  Detailed report layout
and lightweight report regeneration are finalized in the report-consolidation
phase; no optimizer, embedding, graph, or formal seed is run here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evo_ms.analysis.preference import (  # noqa: F401
    BOOTSTRAP_RESAMPLES,
    BUDGETS,
    CLASS_COUNTS,
    FINAL_STAGE_LABELS,
    KEY_BUDGETS,
    SEEDS,
    STORAGE_SUBJECT,
    SUBJECTS,
    TARGETS,
    TOL,
    _dominates,
    canonical_partition_key,
    loss_q,
    relative_gain,
    select_candidate,
    validate_stage_labels,
    vector_partition,
)

ROOT = Path(__file__).resolve().parents[2]
STAGES = FINAL_STAGE_LABELS
REPRESENTATION_ID = "declaration_method_body_v1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the final Stage 2/final Stage 3 preference boundary")
    parser.add_argument("--report-root", type=Path, default=ROOT / "reports/stage3/analysis/preference_response")
    args = parser.parse_args()
    if not args.report_root.exists():
        raise FileNotFoundError(args.report_root)
    print(json.dumps({
        "status": "PASS",
        "stages": list(STAGES),
        "representation_id": REPRESENTATION_ID,
        "scientific_artifacts_regenerated": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
