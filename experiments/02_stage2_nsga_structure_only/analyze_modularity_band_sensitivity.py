#!/usr/bin/env python3
"""Post-hoc sensitivity analysis for the frozen Stage 2 Pareto fronts.

The 5% modularity-band profile remains canonical.  This command evaluates the
same deterministic selector at 1%, 3%, 5%, and 10% using only frozen fronts,
candidate labels, raw Stage 2 inputs, and the frozen Stage 1 Leiden baseline.
It never invokes NSGA-II and never writes into a formal seed directory.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.repository_layout import STAGE2_OPERATING_PROFILE_ROOT, stage2_subject_root

SUBJECTS = ("jpetstore", "daytrader", "xerces-j")
SEEDS = tuple(range(30))
BUDGETS = (0.01, 0.03, 0.05, 0.10)
CANONICAL_BUDGET = 0.05
TOL = 1e-12
SELECTOR_CONTRACT_ID = "stage2-raw-structure-only-modularity-band-v1"
SELECTOR_CONTRACT = (
    "feasible retained Pareto candidates; fallback to all retained candidates "
    "only when feasible is empty; selected budget b relative "
    "weighted-modularity-loss band "
    "with 1e-12 tolerance; minimum imbalance; maximum weighted modularity; "
    "minimum coupling; solution_id; canonical label tuple"
)
EXTERNAL_METRICS = (
    "mojofm_vs_reference",
    "pairwise_f1",
    "ari_vs_reference",
    "nmi_vs_reference",
    "pairwise_precision",
    "pairwise_recall",
    "reference_coverage_ratio",
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_dependencies():
    selector = _load_module(
        "stage2_modularity_band_selector",
        ROOT / "experiments/02_stage2_nsga_structure_only/analyze_modularity_band.py",
    )
    refresh = _load_module(
        "stage2_modularity_band_refresh",
        ROOT / "experiments/02_stage2_nsga_structure_only/refresh_modularity_band_downstream.py",
    )
    robustness = refresh._load_robustness_module()
    return selector, refresh, robustness


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_delta(value: float, baseline: float) -> float:
    if abs(baseline) <= TOL:
        return float(value - baseline)
    return float((value - baseline) / abs(baseline))


def _relative_difference(delta: float, baseline: float) -> float:
    if abs(baseline) <= TOL:
        return float(delta)
    return float(delta / abs(baseline))


def _relative_loss(value: float, baseline: float) -> float:
    if abs(baseline) <= TOL:
        return float(baseline - value)
    return float((baseline - value) / abs(baseline))


def _optional_float(value: Any) -> float:
    if value is None:
        return float("nan")
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return numeric if np.isfinite(numeric) else float("nan")


def _label_tuple(stage2, clusters: pd.DataFrame) -> str:
    labels = stage2._label_key(clusters["cluster_id"].to_numpy(dtype=int))
    return json.dumps(list(labels), separators=(",", ":"))


def _baseline_profile(robustness, context: dict[str, Any]) -> dict[str, Any]:
    baseline = context["stage1_raw_baseline"]
    mapping = robustness.encoding.to_cluster_by_class(
        baseline["cluster_id"].to_numpy(dtype=int), context["class_nodes"]
    )
    profile = robustness.stage2._partition_metrics_row(
        subject=context["subject"],
        seed=0,
        solution_id="leiden",
        class_nodes=context["class_nodes"],
        clusters=baseline,
        raw_edges=context["raw_edges"],
        cluster_by_class=mapping,
        reference_mapping=context["reference_mapping"],
    )
    coupling, cohesion, imbalance = robustness.stage2.evaluate_structural_objectives(
        context["raw_edges"], mapping, robustness.stage2.RAW_WEIGHT_COLUMN
    )
    profile.update({
        "coupling": float(coupling),
        "cohesion": float(cohesion),
        "imbalance": float(imbalance),
    })
    return profile


def _metric_specs() -> list[tuple[str, str, str | None, str]]:
    return [
        ("weighted_modularity", "higher_is_better", "weighted_modularity_delta_vs_leiden", "structural"),
        ("relative_modularity_loss_vs_leiden", "lower_is_better", "relative_modularity_loss_vs_leiden", "structural"),
        ("imbalance", "lower_is_better", "imbalance_delta_vs_leiden", "structural"),
        ("relative_imbalance_improvement_vs_leiden", "higher_is_better", "relative_imbalance_improvement_vs_leiden", "structural"),
        ("coupling", "lower_is_better", "coupling_delta_vs_leiden", "structural"),
        ("relative_coupling_change_vs_leiden", "lower_is_better", "relative_coupling_change_vs_leiden", "structural"),
        ("cohesion", "higher_is_better", "cohesion_delta_vs_leiden", "structural"),
        ("relative_cohesion_change_vs_leiden", "higher_is_better", "relative_cohesion_change_vs_leiden", "structural"),
        ("cluster_count", "descriptive", None, "structural"),
        ("cluster_count_change_vs_leiden", "descriptive", None, "structural"),
        ("max_cluster_ratio", "descriptive", None, "structural"),
        ("max_cluster_ratio_change_vs_leiden", "descriptive", None, "structural"),
        ("singleton_count", "descriptive", None, "structural"),
        ("ari_vs_leiden", "descriptive", None, "partition_similarity"),
        ("nmi_vs_leiden", "descriptive", None, "partition_similarity"),
        ("changed_class_ratio", "descriptive", None, "partition_similarity"),
        *[(metric, "descriptive", None, "external") for metric in EXTERNAL_METRICS],
    ]


def _selected_rows(selector, refresh, robustness) -> list[dict[str, Any]]:
    config_path = ROOT / "configs/experiments/02_stage2_nsga_structure_only.yml"
    contexts = {
        subject: robustness._load_context(subject, config_path)
        for subject in SUBJECTS
    }
    baselines = {
        subject: _baseline_profile(robustness, context)
        for subject, context in contexts.items()
    }
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        context = contexts[subject]
        baseline = baselines[subject]
        for seed in SEEDS:
            front_path = (
                stage2_subject_root(subject, ROOT)
                / "robustness_final_30seeds"
                / f"seed_{seed:02d}"
                / "pareto_front.csv"
            )
            labels_path = front_path.with_name("pareto_labels.csv.xz")
            front = pd.read_csv(front_path)
            feasible_available = bool(front["feasible"].astype(bool).any())
            for budget in BUDGETS:
                selected, q_max, eligible_count = selector.select(front, budget)
                solution_id = str(selected["solution_id"])
                clusters = refresh._selected_clusters(
                    robustness.stage2, context, labels_path, solution_id
                )
                profile = refresh._posthoc_profile(
                    robustness, context, subject, seed, selected.to_dict(), clusters
                )
                ari, nmi = robustness.stage2.partition_similarity(
                    context["class_nodes"], clusters, context["stage1_raw_baseline"]
                )
                changed_count, changed_ratio = robustness.stage2._changed_partition_ratio(
                    context["class_nodes"], clusters, context["stage1_raw_baseline"]
                )
                selected_modularity = float(profile["weighted_modularity"])
                selected_imbalance = float(profile["imbalance"])
                selected_coupling = float(profile["coupling"])
                selected_cohesion = float(profile["cohesion"])
                row = {
                    "subject": subject,
                    "seed": seed,
                    "budget": budget,
                    "budget_label": f"{budget:.0%}",
                    "selector_contract_id": SELECTOR_CONTRACT_ID,
                    "selector_contract": SELECTOR_CONTRACT,
                    "feasible_candidates_available": feasible_available,
                    "used_infeasible_fallback": not feasible_available,
                    "selected_candidate_feasible": bool(selected["feasible"]),
                    "q_max": q_max,
                    "eligible_candidate_count": eligible_count,
                    "solution_id": solution_id,
                    "weighted_modularity": selected_modularity,
                    "realised_relative_modularity_loss": float(selected["modularity_loss"]),
                    "imbalance": selected_imbalance,
                    "coupling": selected_coupling,
                    "cohesion": selected_cohesion,
                    "cluster_count": int(profile["cluster_count"]),
                    "max_cluster_ratio": float(profile["max_cluster_ratio"]),
                    "singleton_count": int((clusters.groupby("cluster_id").size() == 1).sum()),
                    "singleton_ratio": float(profile["singleton_ratio"]),
                    "selected_equals_leiden": robustness.stage2._label_key(
                        clusters["cluster_id"].to_numpy(dtype=int)
                    ) == robustness.stage2._label_key(
                        context["stage1_raw_baseline"]["cluster_id"].to_numpy(dtype=int)
                    ),
                    "ari_vs_leiden": float(ari),
                    "nmi_vs_leiden": float(nmi),
                    "changed_class_count": int(changed_count),
                    "changed_class_ratio": float(changed_ratio),
                    "source_front_path": str(front_path.relative_to(ROOT)),
                    "source_front_sha256": _sha256(front_path),
                    "source_candidate_label_path": str(labels_path.relative_to(ROOT)),
                    "source_candidate_label_sha256": _sha256(labels_path),
                    "selected_label_tuple": _label_tuple(robustness.stage2, clusters),
                    "leiden_weighted_modularity": float(baseline["weighted_modularity"]),
                    "leiden_imbalance": float(baseline["imbalance"]),
                    "leiden_coupling": float(baseline["coupling"]),
                    "leiden_cohesion": float(baseline["cohesion"]),
                    "leiden_cluster_count": int(baseline["cluster_count"]),
                    "leiden_max_cluster_ratio": float(baseline["max_cluster_ratio"]),
                    "weighted_modularity_delta_vs_leiden": selected_modularity - float(baseline["weighted_modularity"]),
                    "relative_modularity_loss_vs_leiden": _relative_loss(selected_modularity, float(baseline["weighted_modularity"])),
                    "imbalance_delta_vs_leiden": selected_imbalance - float(baseline["imbalance"]),
                    "relative_imbalance_improvement_vs_leiden": _relative_difference(float(baseline["imbalance"]) - selected_imbalance, float(baseline["imbalance"])),
                    "coupling_delta_vs_leiden": selected_coupling - float(baseline["coupling"]),
                    "relative_coupling_change_vs_leiden": _relative_delta(selected_coupling, float(baseline["coupling"])),
                    "cohesion_delta_vs_leiden": selected_cohesion - float(baseline["cohesion"]),
                    "relative_cohesion_change_vs_leiden": _relative_delta(selected_cohesion, float(baseline["cohesion"])),
                    "cluster_count_change_vs_leiden": int(profile["cluster_count"]) - int(baseline["cluster_count"]),
                    "max_cluster_ratio_change_vs_leiden": float(profile["max_cluster_ratio"]) - float(baseline["max_cluster_ratio"]),
                }
                for metric in EXTERNAL_METRICS:
                    row[metric] = _optional_float(profile.get(metric))
                rows.append(row)
    return rows


def _comparison_counts(values: pd.Series, direction: str) -> tuple[int | None, int | None, int | None]:
    if direction == "descriptive":
        return None, None, None
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if direction == "higher_is_better":
        better = int((numeric > TOL).sum())
        worse = int((numeric < -TOL).sum())
    else:
        better = int((numeric < -TOL).sum())
        worse = int((numeric > TOL).sum())
    tie = int(len(numeric) - better - worse)
    return better, tie, worse


def _write_summaries(profiles: pd.DataFrame, output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    stats_rows: list[dict[str, Any]] = []
    for (subject, budget), group in profiles.groupby(["subject", "budget"], sort=True):
        for metric, direction, comparison_column, category in _metric_specs():
            values = pd.to_numeric(group[metric], errors="coerce")
            available = values.dropna()
            better, tie, worse = _comparison_counts(
                group[comparison_column] if comparison_column else values,
                direction,
            )
            stats_rows.append({
                "subject": subject,
                "budget": budget,
                "budget_label": f"{budget:.0%}",
                "metric": metric,
                "metric_category": category,
                "metric_direction": direction,
                "availability_count": int(available.size),
                "mean": float(available.mean()) if not available.empty else float("nan"),
                "median": float(available.median()) if not available.empty else float("nan"),
                "std": float(available.std(ddof=1)) if len(available) > 1 else 0.0 if len(available) == 1 else float("nan"),
                "minimum": float(available.min()) if not available.empty else float("nan"),
                "maximum": float(available.max()) if not available.empty else float("nan"),
                "better_count": better,
                "tie_count": tie,
                "worse_count": worse,
            })
    stats = pd.DataFrame(stats_rows)

    summary_rows: list[dict[str, Any]] = []
    median_columns = [
        "weighted_modularity", "relative_modularity_loss_vs_leiden",
        "relative_imbalance_improvement_vs_leiden", "relative_coupling_change_vs_leiden",
        "relative_cohesion_change_vs_leiden", "cluster_count_change_vs_leiden",
        "max_cluster_ratio_change_vs_leiden", "ari_vs_leiden", "nmi_vs_leiden",
        *EXTERNAL_METRICS,
    ]
    for (subject, budget), group in profiles.groupby(["subject", "budget"], sort=True):
        row: dict[str, Any] = {
            "subject": subject,
            "budget": budget,
            "budget_label": f"{budget:.0%}",
            "profile_count": int(len(group)),
            "selected_equals_leiden_count": int(group["selected_equals_leiden"].sum()),
            "fallback_count": int(group["used_infeasible_fallback"].sum()),
        }
        for column in median_columns:
            values = pd.to_numeric(group[column], errors="coerce").dropna()
            row[f"median_{column}"] = float(values.median()) if not values.empty else float("nan")
        for metric in EXTERNAL_METRICS:
            row[f"availability_{metric}"] = int(group[metric].notna().sum())
        for metric, direction, comparison_column, _ in _metric_specs():
            if comparison_column:
                better, tie, worse = _comparison_counts(group[comparison_column], direction)
                row[f"{metric}_better_count"] = better
                row[f"{metric}_tie_count"] = tie
                row[f"{metric}_worse_count"] = worse
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows).sort_values(["subject", "budget"], kind="stable")

    transition_rows: list[dict[str, Any]] = []
    for subject, group in summary.groupby("subject", sort=True):
        ordered = group.sort_values("budget")
        for previous, current in zip(ordered.iloc[:-1].itertuples(), ordered.iloc[1:].itertuples(), strict=True):
            transition_rows.append({
                "subject": subject,
                "from_budget": previous.budget,
                "to_budget": current.budget,
                "from_budget_label": previous.budget_label,
                "to_budget_label": current.budget_label,
                "additional_modularity_loss": current.median_relative_modularity_loss_vs_leiden - previous.median_relative_modularity_loss_vs_leiden,
                "additional_imbalance_improvement": current.median_relative_imbalance_improvement_vs_leiden - previous.median_relative_imbalance_improvement_vs_leiden,
                "additional_coupling_cost": current.median_relative_coupling_change_vs_leiden - previous.median_relative_coupling_change_vs_leiden,
                "additional_cohesion_change": current.median_relative_cohesion_change_vs_leiden - previous.median_relative_cohesion_change_vs_leiden,
            })
    transitions = pd.DataFrame(transition_rows)
    stats.to_csv(output_dir / "sensitivity_metric_summary.csv", index=False)
    summary.to_csv(output_dir / "budget_response_summary.csv", index=False)
    transitions.to_csv(output_dir / "budget_response_transitions.csv", index=False)
    return summary, transitions


def _write_figures(summary: pd.DataFrame, output_dir: Path) -> None:
    plt.rcParams.update({"font.size": 10, "figure.dpi": 120})
    colors = {"jpetstore": "#1b9e77", "daytrader": "#d95f02", "xerces-j": "#7570b3"}
    labels = {"jpetstore": "JPetStore", "daytrader": "DayTrader", "xerces-j": "Xerces-J"}
    annotation_offsets = {
        "daytrader": {0.01: (3, -12), 0.03: (3, 5), 0.05: (3, -12), 0.10: (3, 5)},
        "jpetstore": {0.01: (3, -12), 0.03: (3, 5), 0.05: (-15, 5), 0.10: (3, -12)},
        "xerces-j": {0.01: (3, 5), 0.03: (3, 5), 0.05: (3, 5), 0.10: (3, 5)},
    }

    for y_column, filename, ylabel in [
        ("median_relative_imbalance_improvement_vs_leiden", "modularity_loss_vs_imbalance_improvement.png", "Median relative imbalance improvement vs Leiden"),
        ("median_relative_coupling_change_vs_leiden", "modularity_loss_vs_coupling_change.png", "Median relative coupling change vs Leiden"),
    ]:
        fig, ax = plt.subplots(figsize=(7.2, 4.6))
        for subject, group in summary.groupby("subject", sort=True):
            group = group.sort_values("budget")
            ax.plot(group["median_relative_modularity_loss_vs_leiden"], group[y_column], marker="o", label=labels[subject], color=colors[subject])
            for row in group.itertuples():
                ax.annotate(
                    row.budget_label,
                    (getattr(row, "median_relative_modularity_loss_vs_leiden"), getattr(row, y_column)),
                    textcoords="offset points",
                    xytext=annotation_offsets[subject][float(row.budget)],
                    fontsize=8,
                )
        ax.axvline(0.0, color="#777777", linewidth=0.8)
        ax.axhline(0.0, color="#777777", linewidth=0.8)
        ax.set_xlabel("Median relative modularity loss vs Leiden")
        ax.set_ylabel(ylabel)
        ax.legend(frameon=False)
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=160)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for subject, group in summary.groupby("subject", sort=True):
        group = group.sort_values("budget")
        ax.plot(group["budget"] * 100, group["median_cluster_count_change_vs_leiden"], marker="o", label=labels[subject], color=colors[subject])
    ax.axhline(0.0, color="#777777", linewidth=0.8)
    ax.set_xlabel("Modularity-band budget (%)")
    ax.set_ylabel("Median cluster-count change vs Leiden")
    ax.set_xticks([1, 3, 5, 10])
    ax.legend(frameon=False)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_dir / "budget_vs_cluster_count_change.png", dpi=160)
    plt.close(fig)


def run(output_dir: Path, make_figures: bool = True) -> dict[str, Any]:
    selector, refresh, robustness = _load_dependencies()
    rows = _selected_rows(selector, refresh, robustness)
    profiles = pd.DataFrame(rows).sort_values(["subject", "seed", "budget"], kind="stable")
    expected = len(SUBJECTS) * len(SEEDS) * len(BUDGETS)
    if len(profiles) != expected:
        raise ValueError(f"expected {expected} profiles, found {len(profiles)}")
    if profiles[["subject", "seed", "budget"]].duplicated().any():
        raise ValueError("duplicate subject/seed/budget profiles")
    profiles.to_csv(output_dir / "sensitivity_profiles_per_seed.csv", index=False)
    summary, transitions = _write_summaries(profiles, output_dir)

    canonical_path = STAGE2_OPERATING_PROFILE_ROOT / "canonical_operating_solution_per_seed.csv"
    canonical = pd.read_csv(canonical_path)
    canonical_rows = profiles.loc[profiles["budget"] == CANONICAL_BUDGET].merge(
        canonical[["subject", "seed", "solution_id", "weighted_modularity", "label_vector"]],
        on=["subject", "seed"], suffixes=("_sensitivity", "_canonical"), validate="one_to_one",
    )
    id_mismatches = int((canonical_rows["solution_id_sensitivity"] != canonical_rows["solution_id_canonical"]).sum())
    objective_mismatches = int((canonical_rows["weighted_modularity_sensitivity"] - canonical_rows["weighted_modularity_canonical"]).abs().gt(1e-12).sum())
    canonical_labels = canonical_rows["label_vector"].map(
        lambda value: json.dumps(
            list(selector.canonical_label_tuple(value)), separators=(",", ":")
        )
    )
    label_mismatches = int((canonical_rows["selected_label_tuple"] != canonical_labels).sum())
    validation = {
        "subjects": list(SUBJECTS),
        "seeds_per_subject": len(SEEDS),
        "budgets": list(BUDGETS),
        "expected_selected_rows": expected,
        "actual_selected_rows": len(profiles),
        "duplicate_rows": int(profiles[["subject", "seed", "budget"]].duplicated().sum()),
        "5_percent_selected_id_mismatches": id_mismatches,
        "5_percent_objective_mismatches": objective_mismatches,
        "5_percent_label_mismatches": label_mismatches,
        "canonical_source_path": str(canonical_path.relative_to(ROOT)),
        "canonical_source_sha256": _sha256(canonical_path),
    }
    (output_dir / "sensitivity_validation.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    existing = pd.read_csv(STAGE2_OPERATING_PROFILE_ROOT / "profiles_per_seed.csv")
    manifest = {
        "analysis": "stage2_modularity_band_sensitivity",
        "selector_contract_id": SELECTOR_CONTRACT_ID,
        "selector_contract": SELECTOR_CONTRACT,
        "subjects": list(SUBJECTS),
        "seeds": list(SEEDS),
        "budgets": list(BUDGETS),
        "canonical_budget": CANONICAL_BUDGET,
        "existing_profile_budgets": sorted(float(v) for v in existing["budget"].unique()),
        "new_profile_budgets": [0.03],
        "baseline": "frozen Stage 1 raw Leiden baseline",
        "q_max_role": "band-construction anchor only; scientific comparisons use Leiden",
        "cohesion_role": "report-only; not used for selection",
        "source_policy": "frozen formal Stage 2 Pareto fronts and candidate-label mappings",
        "no_optimizer_run": True,
        "no_seed_rerun": True,
        "no_graph_regeneration": True,
        "no_pareto_front_regeneration": True,
        "no_reference_mapping_regeneration": True,
        "validation": validation,
        "transition_count": len(transitions),
        "figure_sources": ["budget_response_summary.csv", "sensitivity_metric_summary.csv"],
    }
    (output_dir / "sensitivity_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if make_figures:
        _write_figures(summary, output_dir)
    if id_mismatches or objective_mismatches or label_mismatches:
        raise ValueError(f"5% canonical mismatches: {validation}")
    return validation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    validation = run(args.output_dir, make_figures=not args.no_figures)
    print(json.dumps(validation, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
