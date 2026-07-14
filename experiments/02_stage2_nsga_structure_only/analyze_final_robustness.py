"""Paired selected-solution statistics for final Stage 2 robustness runs."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata, wilcoxon


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


def _load_robustness_module():
    path = ROOT / "experiments" / "02_stage2_nsga_structure_only" / "run_robustness.py"
    spec = importlib.util.spec_from_file_location("stage2_robustness_stats", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _rank_biserial(differences: np.ndarray) -> float | None:
    nonzero = differences[~np.isclose(differences, 0.0)]
    if len(nonzero) == 0:
        return None
    ranks = rankdata(np.abs(nonzero))
    return float((ranks[nonzero > 0].sum() - ranks[nonzero < 0].sum()) / ranks.sum())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bonferroni-family-size", type=int, default=None)
    args = parser.parse_args()
    robustness = _load_robustness_module()
    rows = []
    for subject in ("jpetstore", "daytrader", "xerces-j"):
        run_dir = ROOT / "results" / subject / "03_stage2_nsga" / "robustness_final_30seeds"
        selected = pd.DataFrame(
            [pd.read_csv(run_dir / f"seed_{seed:02d}" / "selected_solution.csv").iloc[0] for seed in range(30)]
        )
        context = robustness._load_context(subject, ROOT / "configs" / "experiments" / "02_stage2_nsga_structure_only.yml")
        leiden = context["stage1_raw_baseline"]
        cluster_by_class = robustness.encoding.to_cluster_by_class(
            leiden["cluster_id"].to_numpy(dtype=int), context["class_nodes"]
        )
        baseline = robustness.stage2._partition_metrics_row(
            subject, 0, "leiden", context["class_nodes"], leiden, context["raw_edges"],
            cluster_by_class, context["reference_mapping"],
        )
        coupling, cohesion, imbalance = robustness.stage2.evaluate_structural_objectives(
            context["raw_edges"], cluster_by_class, robustness.stage2.RAW_WEIGHT_COLUMN
        )
        baseline.update({"coupling": coupling, "cohesion": cohesion, "imbalance": imbalance})
        metrics = ["weighted_modularity", "coupling", "cohesion", "imbalance"]
        metrics.extend(metric for metric in ("mojofm_vs_reference", "pairwise_f1") if metric in selected.columns and baseline.get(metric) is not None)
        for metric in metrics:
            nsga = selected[metric].to_numpy(dtype=float)
            leiden_values = np.full(len(nsga), float(baseline[metric]))
            delta = nsga - leiden_values
            # Objectives recomputed from the saved partitions differ from the
            # Leiden baseline by float round-off (~1e-17) on pairs that are in
            # fact identical. Snap those to exact zero with a single tolerance so
            # the tie mask, the direction counts, and scipy's zero handling all
            # agree; scipy.wilcoxon only discards *exact* zeros, so unsnapped
            # round-off would otherwise enter the test as real signed ranks.
            tie_mask = np.isclose(delta, 0.0)
            delta = np.where(tie_mask, 0.0, delta)
            all_zero = bool(np.all(tie_mask))
            if all_zero:
                statistic = p_value = rbc = np.nan
                nonzero = 0
            else:
                test = wilcoxon(delta, alternative="two-sided", method="auto")
                statistic, p_value = float(test.statistic), float(test.pvalue)
                rbc = _rank_biserial(delta)
                nonzero = int(np.count_nonzero(delta))
            rows.append({
                "subject": subject, "metric": metric, "n_pairs": len(nsga),
                "nsga_median": float(np.median(nsga)), "leiden_median": float(np.median(leiden_values)),
                "median_difference_nsga_minus_leiden": float(np.median(delta)),
                "wilcoxon_statistic": statistic, "p_value_two_sided": p_value,
                "rank_biserial_nsga_minus_leiden": rbc, "nonzero_pairs": nonzero,
                "all_pairs_identical": all_zero,
                "nsga_lower_count": int(np.sum(delta < 0)), "ties": int(np.sum(tie_mask)),
                "nsga_higher_count": int(np.sum(delta > 0)),
            })

    requested_metric_comparisons = len(rows)
    nondegenerate_tests = sum(not bool(row["all_pairs_identical"]) for row in rows)
    family_size = args.bonferroni_family_size or nondegenerate_tests
    if family_size <= 0:
        raise ValueError("Bonferroni family size must be positive")
    alpha = 0.05 / family_size
    # The correction family is based on the statistical tests actually
    # executed; all-zero paired comparisons are descriptive, not Wilcoxon tests.
    for row in rows:
        row["bonferroni_family_size"] = family_size
        row["bonferroni_alpha"] = alpha
        row["bonferroni_significant"] = (
            bool(row["p_value_two_sided"] <= alpha)
            if not bool(row["all_pairs_identical"])
            else False
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output_dir / "paired_selected_vs_leiden_wilcoxon.csv", index=False)

    # Sensitivity of every executed test to the Bonferroni family size: the
    # executed-test family (10) versus the wider family (12). Degenerate
    # all-identical comparisons run no test and are excluded.
    alpha_10 = 0.05 / 10
    alpha_12 = 0.05 / 12
    comparison = []
    for row in rows:
        if bool(row["all_pairs_identical"]):
            continue
        significant_10 = bool(row["p_value_two_sided"] <= alpha_10)
        significant_12 = bool(row["p_value_two_sided"] <= alpha_12)
        comparison.append(
            {
                key: row[key]
                for key in (
                    "subject", "metric", "n_pairs", "nsga_median", "leiden_median",
                    "median_difference_nsga_minus_leiden", "wilcoxon_statistic",
                    "p_value_two_sided", "rank_biserial_nsga_minus_leiden",
                    "nonzero_pairs",
                )
            }
            | {
                "bonferroni_alpha_12": alpha_12,
                "bonferroni_significant": significant_12,
                "all_pairs_identical": bool(row["all_pairs_identical"]),
                "nsga_lower_count": row["nsga_lower_count"],
                "ties": row["ties"],
                "nsga_higher_count": row["nsga_higher_count"],
                "bonferroni_alpha_10": alpha_10,
                "significant_family_10": significant_10,
                "significant_family_12": significant_12,
                "decision_changed_10_vs_12": significant_10 != significant_12,
            }
        )
    pd.DataFrame(comparison).to_csv(
        args.output_dir / "bonferroni_10_vs_12_comparison.csv", index=False
    )
    with (args.output_dir / "analysis_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "test": "paired Wilcoxon signed-rank, two-sided",
                "requested_metric_comparisons": requested_metric_comparisons,
                "nondegenerate_tests_executed": nondegenerate_tests,
                "bonferroni_family_size": family_size,
                "bonferroni_alpha": alpha,
            },
            handle,
            indent=2,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
