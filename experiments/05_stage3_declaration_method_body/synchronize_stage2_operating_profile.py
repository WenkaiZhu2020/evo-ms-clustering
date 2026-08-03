#!/usr/bin/env python3
"""Synchronize the Stage 2 modularity-band profile into Stage 3."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from evo_ms.repository_layout import STAGE2_OPERATING_PROFILE_ROOT, STAGE3_PREFERENCE_ANALYSIS_ROOT

STAGE3_SUBJECT = {"daytrader": "daytrader", "jpetstore": "jpetstore", "xerces-j": "xerces"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage2-dir", type=Path, default=STAGE2_OPERATING_PROFILE_ROOT)
    parser.add_argument("--stage3-root", type=Path, default=STAGE3_PREFERENCE_ANALYSIS_ROOT)
    args = parser.parse_args()
    profiles = pd.read_csv(args.stage2_dir / "profiles_per_seed.csv")
    canonical = pd.read_csv(args.stage2_dir / "canonical_operating_solution_per_seed.csv")
    baseline = pd.read_csv(args.stage3_root / "baseline/leiden_metrics.csv")
    baseline = baseline.loc[baseline["stage"] == "stage2"].rename(columns={
        "weighted_modularity": "leiden_weighted_modularity", "imbalance": "leiden_imbalance",
        "coupling": "leiden_coupling", "cohesion": "leiden_cohesion", "cluster_count": "leiden_cluster_count",
    })[["subject", "leiden_weighted_modularity", "leiden_imbalance", "leiden_coupling", "leiden_cohesion", "leiden_cluster_count"]]
    baseline["subject"] = baseline["subject"].map({v: k for k, v in STAGE3_SUBJECT.items()})
    output = args.stage3_root / "budget_response/stage2_modularity_band"
    output.mkdir(parents=True, exist_ok=True)
    profiles.to_csv(output / "per_seed.csv", index=False)
    pd.read_csv(args.stage2_dir / "profiles_summary.csv").to_csv(output / "summary.csv", index=False)
    comparison = canonical.merge(baseline, on="subject", how="left", validate="many_to_one")
    comparison["imbalance_improvement_vs_leiden"] = comparison["leiden_imbalance"] - comparison["imbalance"]
    comparison["coupling_change_vs_leiden"] = comparison["coupling"] - comparison["leiden_coupling"]
    comparison["cohesion_change_vs_leiden"] = comparison["cohesion"] - comparison["leiden_cohesion"]
    comparison["cluster_count_change_vs_leiden"] = comparison["cluster_count"] - comparison["leiden_cluster_count"]
    comparison["weighted_modularity_change_vs_leiden"] = comparison["weighted_modularity"] - comparison["leiden_weighted_modularity"]
    comparison["comparison_basis"] = "frozen Stage 2 canonical 5% profile vs frozen Stage 1 raw Leiden"
    compare_dir = args.stage3_root / "profile_comparison"
    compare_dir.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(compare_dir / "stage2_canonical_vs_leiden_per_seed.csv", index=False)
    comparison.groupby("subject", as_index=False).agg(
        seed_count=("seed", "count"),
        median_imbalance_improvement_vs_leiden=("imbalance_improvement_vs_leiden", "median"),
        median_coupling_change_vs_leiden=("coupling_change_vs_leiden", "median"),
        median_cohesion_change_vs_leiden=("cohesion_change_vs_leiden", "median"),
        median_weighted_modularity_change_vs_leiden=("weighted_modularity_change_vs_leiden", "median"),
        median_cluster_count_change_vs_leiden=("cluster_count_change_vs_leiden", "median"),
    ).to_csv(compare_dir / "stage2_canonical_vs_leiden_summary.csv", index=False)
    stage3 = pd.read_csv(args.stage3_root / "budget_response/stage3_balance/per_seed.csv")
    stage3 = stage3.loc[(stage3["budget"].round(6) == 0.05) & (stage3["status"] == "selected")].copy()
    stage3 = stage3.rename(columns={
        "subject": "stage3_subject", "solution_id": "stage3_solution_id",
        "weighted_modularity": "stage3_weighted_modularity", "coupling": "stage3_coupling",
        "cohesion": "stage3_cohesion", "imbalance": "stage3_imbalance",
        "cluster_count": "stage3_cluster_count", "realised_modularity_loss": "stage3_realised_modularity_loss",
    })
    stage3["subject"] = stage3["stage3_subject"].map({v: k for k, v in STAGE3_SUBJECT.items()})
    stage3 = stage3[["subject", "seed", "stage3_solution_id", "stage3_weighted_modularity", "stage3_coupling", "stage3_cohesion", "stage3_imbalance", "stage3_cluster_count", "stage3_realised_modularity_loss"]]
    cross = canonical.merge(stage3, on=["subject", "seed"], how="left", validate="one_to_one")
    for metric in ("weighted_modularity", "imbalance", "coupling", "cohesion"):
        cross[f"canonical_minus_stage3_{metric}"] = cross[metric] - cross[f"stage3_{metric}"]
    cross["comparison_basis"] = "Stage 2 canonical 5% profile vs saved Stage 3 balance 5% profile"
    cross.to_csv(compare_dir / "stage2_canonical_vs_stage3_balance_005_per_seed.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
