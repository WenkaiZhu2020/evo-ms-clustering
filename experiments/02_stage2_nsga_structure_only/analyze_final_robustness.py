"""Paired selected-solution statistics for final Stage 2 robustness runs."""

from __future__ import annotations

import argparse
import hashlib
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

PRIMARY_STRUCTURAL_METRICS = (
    "weighted_modularity",
    "coupling",
    "cohesion",
    "imbalance",
)
EXTERNAL_REFERENCE_METRICS = (
    "mojofm_vs_reference",
    "pairwise_f1",
)
PRIMARY_STRUCTURAL_FAMILY = "primary_structural"
EXTERNAL_REFERENCE_FAMILY = "external_reference_daytrader"
PRIMARY_STRUCTURAL_FAMILY_SIZE = 3 * len(PRIMARY_STRUCTURAL_METRICS)
EXTERNAL_REFERENCE_FAMILY_SIZE = len(EXTERNAL_REFERENCE_METRICS)


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _statistical_family(metric: str) -> tuple[str, int]:
    if metric in PRIMARY_STRUCTURAL_METRICS:
        return PRIMARY_STRUCTURAL_FAMILY, PRIMARY_STRUCTURAL_FAMILY_SIZE
    if metric in EXTERNAL_REFERENCE_METRICS:
        return EXTERNAL_REFERENCE_FAMILY, EXTERNAL_REFERENCE_FAMILY_SIZE
    raise ValueError(f"unregistered statistical metric: {metric}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--selected-profile",
        type=Path,
        default=ROOT / "results/cross_subject/03_stage2_nsga/modularity_band/"
        "canonical_operating_profile_metrics_per_seed.csv",
        help="full post-hoc metrics for the canonical profile",
    )
    args = parser.parse_args()
    robustness = _load_robustness_module()
    selected_profile_source = args.selected_profile.resolve()
    selected_profile = pd.read_csv(selected_profile_source)
    selector_contract_id = str(selected_profile["selector_contract_id"].iloc[0])
    selected_profile_sha256 = _sha256(selected_profile_source)
    selected_profile_display = _display_path(selected_profile_source)
    rows = []
    for subject in ("jpetstore", "daytrader", "xerces-j"):
        run_dir = ROOT / "results" / subject / "03_stage2_nsga" / "robustness_final_30seeds"
        selected = selected_profile.loc[selected_profile["subject"] == subject].copy()
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
        metrics = list(PRIMARY_STRUCTURAL_METRICS)
        metrics.extend(
            metric
            for metric in EXTERNAL_REFERENCE_METRICS
            if metric in selected.columns and baseline.get(metric) is not None
        )
        for metric in metrics:
            family_name, family_size = _statistical_family(metric)
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
                "statistical_family": family_name,
                "bonferroni_family_size": family_size,
                "selector_contract_id": selector_contract_id,
                "selected_profile_source": selected_profile_display,
                "selected_profile_sha256": selected_profile_sha256,
                "posthoc_status": "recomputed_from_frozen_front_and_labels",
            })

    requested_metric_comparisons = len(rows)
    nondegenerate_tests = sum(not bool(row["all_pairs_identical"]) for row in rows)
    for row in rows:
        alpha = 0.05 / int(row["bonferroni_family_size"])
        row["bonferroni_alpha"] = alpha
        row["bonferroni_significant"] = (
            bool(row["p_value_two_sided"] <= alpha)
            if not bool(row["all_pairs_identical"])
            else False
        )
        row["selector_contract_id"] = selector_contract_id
        row["selected_profile_source"] = selected_profile_display
        row["selected_profile_sha256"] = selected_profile_sha256
        row["posthoc_status"] = "recomputed_from_frozen_front_and_labels"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output_dir / "paired_selected_vs_leiden_wilcoxon.csv", index=False)

    family_audit = pd.DataFrame(rows)
    family_audit.to_csv(args.output_dir / "bonferroni_family_audit.csv", index=False)
    family_counts = {
        PRIMARY_STRUCTURAL_FAMILY: int(
            sum(row["statistical_family"] == PRIMARY_STRUCTURAL_FAMILY for row in rows)
        ),
        EXTERNAL_REFERENCE_FAMILY: int(
            sum(row["statistical_family"] == EXTERNAL_REFERENCE_FAMILY for row in rows)
        ),
    }
    with (args.output_dir / "analysis_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "test": "paired Wilcoxon signed-rank, two-sided",
                "requested_metric_comparisons": requested_metric_comparisons,
                "nondegenerate_tests_executed": nondegenerate_tests,
                "family_definition": {
                    "primary_structural": {
                        "subjects": ["jpetstore", "daytrader", "xerces-j"],
                        "metrics": list(PRIMARY_STRUCTURAL_METRICS),
                        "planned_comparisons": PRIMARY_STRUCTURAL_FAMILY_SIZE,
                        "alpha": 0.05 / PRIMARY_STRUCTURAL_FAMILY_SIZE,
                    },
                    "external_reference_daytrader": {
                        "subjects": ["daytrader"],
                        "metrics": list(EXTERNAL_REFERENCE_METRICS),
                        "planned_comparisons": EXTERNAL_REFERENCE_FAMILY_SIZE,
                        "alpha": 0.05 / EXTERNAL_REFERENCE_FAMILY_SIZE,
                    },
                },
                "family_row_counts": family_counts,
                "selector_contract_id": selector_contract_id,
                "selected_profile_source": selected_profile_display,
                "selected_profile_sha256": selected_profile_sha256,
                "family_audit_source": _display_path(args.output_dir / "bonferroni_family_audit.csv"),
                "posthoc_status": "recomputed_from_frozen_front_and_labels",
            },
            handle,
            indent=2,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
