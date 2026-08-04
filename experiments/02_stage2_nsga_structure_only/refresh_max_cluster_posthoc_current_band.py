#!/usr/bin/env python3
"""Refresh max-cluster post-hoc evidence using the current 5% selector.

This is a separate constraint sensitivity from the modularity-band sensitivity.
It reads the frozen fronts and candidate labels only, and leaves the original
historical max-cluster tables untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.repository_layout import stage2_subject_root

SUBJECTS = ("daytrader", "xerces-j")
SEEDS = tuple(range(30))
THRESHOLDS = (0.30, 0.35, 0.40, 0.45, 0.50, 0.60)
BAND_BUDGET = 0.05
SELECTOR_CONTRACT_ID = "stage2-raw-structure-only-modularity-band-v1"
SELECTOR_CONTRACT = (
    "feasible retained Pareto candidates; fallback to all retained candidates "
    "only when feasible is empty; 5% relative weighted-modularity-loss band "
    "with 1e-12 tolerance; minimum imbalance; maximum weighted modularity; "
    "minimum coupling; solution_id; canonical label tuple"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _label_tuple(stage2, clusters: pd.DataFrame) -> str:
    return json.dumps(
        list(stage2._label_key(clusters["cluster_id"].to_numpy(dtype=int))),
        separators=(",", ":"),
    )


def run(output_dir: Path) -> dict[str, Any]:
    selector = _load_module(
        "stage2_max_cluster_selector",
        ROOT / "experiments/02_stage2_nsga_structure_only/analyze_modularity_band.py",
    )
    refresh = _load_module(
        "stage2_max_cluster_refresh",
        ROOT / "experiments/02_stage2_nsga_structure_only/refresh_modularity_band_downstream.py",
    )
    robustness = refresh._load_robustness_module()
    config_path = ROOT / "configs/experiments/02_stage2_nsga_structure_only.yml"
    rows: list[dict[str, Any]] = []
    contexts = {
        subject: robustness._load_context(subject, config_path)
        for subject in SUBJECTS
    }
    for subject in SUBJECTS:
        context = contexts[subject]
        baseline = context["stage1_raw_baseline"]
        baseline_mapping = robustness.encoding.to_cluster_by_class(
            baseline["cluster_id"].to_numpy(dtype=int), context["class_nodes"]
        )
        _, _, leiden_imbalance = robustness.stage2.evaluate_structural_objectives(
            context["raw_edges"], baseline_mapping, robustness.stage2.RAW_WEIGHT_COLUMN
        )
        baseline_metrics = robustness.stage2._partition_metrics_row(
            subject,
            0,
            "leiden",
            context["class_nodes"],
            baseline,
            context["raw_edges"],
            baseline_mapping,
            context["reference_mapping"],
        )
        for seed in SEEDS:
            front_path = (
                stage2_subject_root(subject, ROOT)
                / "robustness_final_30seeds"
                / f"seed_{seed:02d}"
                / "pareto_front.csv"
            )
            labels_path = front_path.with_name("pareto_labels.csv.xz")
            front = pd.read_csv(front_path)
            for threshold in THRESHOLDS:
                retained = front.loc[front["max_cluster_ratio"] <= threshold + 1e-12].copy()
                if retained.empty:
                    continue
                selected, q_max, eligible_count = selector.select(retained, BAND_BUDGET)
                solution_id = str(selected["solution_id"])
                clusters = refresh._selected_clusters(
                    robustness.stage2, context, labels_path, solution_id
                )
                profile = refresh._posthoc_profile(
                    robustness, context, subject, seed, selected.to_dict(), clusters
                )
                rows.append({
                    "subject": subject,
                    "seed": seed,
                    "threshold": threshold,
                    "band_budget": BAND_BUDGET,
                    "selector_contract_id": SELECTOR_CONTRACT_ID,
                    "selector_contract": SELECTOR_CONTRACT,
                    "source_front_size": len(front),
                    "retained_front_size": len(retained),
                    "trimmed_count": int(len(front) - len(retained)),
                    "trimmed_ratio": float(1.0 - len(retained) / len(front)),
                    "retained_pathological_gt_050_ratio": float((retained["max_cluster_ratio"] > 0.5).mean()),
                    "source_front_right_censored": bool(threshold > 0.40),
                    "q_max_in_retained_front": q_max,
                    "eligible_candidate_count": eligible_count,
                    "solution_id": solution_id,
                    "weighted_modularity": float(profile["weighted_modularity"]),
                    "realised_relative_modularity_loss": float(selected["modularity_loss"]),
                    "imbalance": float(profile["imbalance"]),
                    "coupling": float(profile["coupling"]),
                    "cohesion": float(profile["cohesion"]),
                    "cluster_count": int(profile["cluster_count"]),
                    "max_cluster_ratio": float(profile["max_cluster_ratio"]),
                    "distance_to_threshold": float(threshold - profile["max_cluster_ratio"]),
                    "imbalance_lower_than_leiden": bool(profile["imbalance"] < leiden_imbalance),
                    "modularity_not_higher_than_leiden": bool(profile["weighted_modularity"] <= baseline_metrics["weighted_modularity"] + 1e-12),
                    "source_front_path": str(front_path.relative_to(ROOT)),
                    "source_front_sha256": _sha256(front_path),
                    "source_candidate_label_path": str(labels_path.relative_to(ROOT)),
                    "source_candidate_label_sha256": _sha256(labels_path),
                    "selected_label_tuple": _label_tuple(robustness.stage2, clusters),
                })
    detail = pd.DataFrame(rows).sort_values(["subject", "seed", "threshold"], kind="stable")
    expected = len(SUBJECTS) * len(SEEDS) * len(THRESHOLDS)
    if len(detail) != expected:
        raise ValueError(f"expected {expected} current max-cluster rows, found {len(detail)}")
    summary = detail.groupby(["subject", "threshold"], as_index=False).agg(
        band_budget=("band_budget", "first"),
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
    output_dir.mkdir(parents=True, exist_ok=True)
    detail.to_csv(output_dir / "posthoc_max_cluster_sensitivity_per_seed.csv", index=False)
    summary.to_csv(output_dir / "posthoc_max_cluster_sensitivity_summary.csv", index=False)
    manifest = {
        "analysis": "stage2_max_cluster_posthoc_under_current_modularity_band",
        "subjects": list(SUBJECTS),
        "seeds": list(SEEDS),
        "thresholds": list(THRESHOLDS),
        "band_budget": BAND_BUDGET,
        "selector_contract_id": SELECTOR_CONTRACT_ID,
        "selector_contract": SELECTOR_CONTRACT,
        "source_policy": "frozen formal Stage 2 Pareto fronts and candidate-label mappings",
        "historical_originals_retained": False,
        "historical_cleanup_inventory": (
            "results/stage2/cross_subject/formal_statistics/"
            "historical_output_cleanup_inventory.csv"
        ),
        "no_optimizer_run": True,
        "no_seed_rerun": True,
        "no_graph_regeneration": True,
        "no_pareto_front_regeneration": True,
        "no_reference_mapping_regeneration": True,
        "rows": len(detail),
    }
    (output_dir / "max_cluster_sensitivity_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
