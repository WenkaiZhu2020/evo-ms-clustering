"""Post-hoc max-cluster sensitivity for observed final Stage 2 fronts.

Thresholds above the source run's 0.40 guardrail are explicitly marked as
right-censored: those fronts cannot reveal solutions excluded during search.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from evo_ms.repository_layout import stage2_subject_root


def _robustness_module():
    path = ROOT / "experiments" / "02_stage2_nsga_structure_only" / "run_robustness.py"
    spec = importlib.util.spec_from_file_location("stage2_max_cluster_posthoc", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _selected(frame: pd.DataFrame, stage2) -> dict:
    """Delegate to the formal selector so post-hoc ties use identical ordering."""
    pareto_rows = frame.to_dict("records")
    posthoc_rows = [
        {
            "solution_id": row["solution_id"],
            "weighted_modularity": row["weighted_modularity"],
            "cluster_count": row["cluster_count"],
            "max_cluster_ratio": row["max_cluster_ratio"],
            "singleton_ratio": row["singleton_ratio"],
        }
        for row in pareto_rows
    ]
    return stage2._select_solution(posthoc_rows, pareto_rows)


def _assert_selector_adapter_matches_formal_helper(stage2) -> None:
    """Pure in-memory check for the selector adapter's formal tie-break path."""
    frame = pd.DataFrame(
        [
            {
                "solution_id": "injected",
                "weighted_modularity": 0.5,
                "feasible": True,
                "is_injected_seed": True,
                "coupling": 0.2,
                "cohesion": 1.0,
                "imbalance": 0.3,
                "label_vector": "[0, 1]",
                "cluster_count": 2,
                "max_cluster_ratio": 0.5,
                "singleton_ratio": 0.0,
            },
            {
                "solution_id": "evolved",
                "weighted_modularity": 0.5,
                "feasible": True,
                "is_injected_seed": False,
                "coupling": 0.2,
                "cohesion": 1.0,
                "imbalance": 0.3,
                "label_vector": "[1, 0]",
                "cluster_count": 2,
                "max_cluster_ratio": 0.5,
                "singleton_ratio": 0.0,
            },
        ]
    )
    direct = stage2._select_solution(
        [
            {
                "solution_id": row["solution_id"],
                "weighted_modularity": row["weighted_modularity"],
                "cluster_count": row["cluster_count"],
                "max_cluster_ratio": row["max_cluster_ratio"],
                "singleton_ratio": row["singleton_ratio"],
            }
            for row in frame.to_dict("records")
        ],
        frame.to_dict("records"),
    )
    adapted = _selected(frame, stage2)
    if direct["solution_id"] != adapted["solution_id"]:
        raise AssertionError("post-hoc selector adapter differs from formal selector")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    thresholds = [0.30, 0.35, 0.40, 0.45, 0.50, 0.60]
    robustness = _robustness_module()
    _assert_selector_adapter_matches_formal_helper(robustness.stage2)
    rows = []
    for subject in ("daytrader", "xerces-j"):
        run_dir = stage2_subject_root(subject, ROOT) / "robustness_final_30seeds"
        context = robustness._load_context(subject, ROOT / "configs" / "experiments" / "02_stage2_nsga_structure_only.yml")
        baseline = context["stage1_raw_baseline"]
        mapping = robustness.encoding.to_cluster_by_class(
            baseline["cluster_id"].to_numpy(dtype=int), context["class_nodes"]
        )
        _, _, leiden_imbalance = robustness.stage2.evaluate_structural_objectives(
            context["raw_edges"], mapping, robustness.stage2.RAW_WEIGHT_COLUMN
        )
        baseline_metrics = robustness.stage2._partition_metrics_row(
            subject, 0, "leiden", context["class_nodes"], baseline, context["raw_edges"], mapping,
            context["reference_mapping"],
        )
        for seed in range(30):
            front = pd.read_csv(run_dir / f"seed_{seed:02d}" / "pareto_front.csv")
            for threshold in thresholds:
                retained = front.loc[front["max_cluster_ratio"] <= threshold + 1e-12]
                if retained.empty:
                    continue
                chosen = _selected(retained, robustness.stage2)
                rows.append({
                    "subject": subject, "seed": seed, "threshold": threshold,
                    "source_front_size": len(front), "retained_front_size": len(retained),
                    "trimmed_count": int(len(front) - len(retained)),
                    "trimmed_ratio": float(1.0 - len(retained) / len(front)),
                    "retained_pathological_gt_050_ratio": float((retained["max_cluster_ratio"] > 0.5).mean()),
                    "source_front_right_censored": bool(threshold > 0.40),
                    "weighted_modularity": float(chosen["weighted_modularity"]),
                    "imbalance": float(chosen["imbalance"]), "coupling": float(chosen["coupling"]),
                    "cohesion": float(chosen["cohesion"]), "cluster_count": int(chosen["cluster_count"]),
                    "max_cluster_ratio": float(chosen["max_cluster_ratio"]),
                    "distance_to_threshold": float(threshold - chosen["max_cluster_ratio"]),
                    "imbalance_lower_than_leiden": bool(chosen["imbalance"] < leiden_imbalance),
                    "modularity_not_higher_than_leiden": bool(chosen["weighted_modularity"] <= baseline_metrics["weighted_modularity"] + 1e-12),
                })
    detail = pd.DataFrame(rows)
    summary = detail.groupby(["subject", "threshold"], as_index=False).agg(
        selected_weighted_modularity_median=("weighted_modularity", "median"),
        selected_imbalance_median=("imbalance", "median"),
        selected_coupling_median=("coupling", "median"),
        selected_cohesion_median=("cohesion", "median"),
        selected_cluster_count_median=("cluster_count", "median"),
        selected_max_cluster_ratio_median=("max_cluster_ratio", "median"),
        selected_distance_to_threshold_median=("distance_to_threshold", "median"),
        trimmed_ratio_mean=("trimmed_ratio", "mean"),
        retained_pathological_gt_050_ratio_mean=("retained_pathological_gt_050_ratio", "mean"),
        imbalance_lower_than_leiden_count=("imbalance_lower_than_leiden", "sum"),
        modularity_not_higher_than_leiden_count=("modularity_not_higher_than_leiden", "sum"),
        source_front_right_censored=("source_front_right_censored", "max"),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail.to_csv(args.output_dir / "posthoc_max_cluster_sensitivity_per_seed.csv", index=False)
    summary.to_csv(args.output_dir / "posthoc_max_cluster_sensitivity_summary.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
