"""Paired, read-only-input diagnostic of Stage 2 initialisation modes."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.optimization import encoding
from evo_ms.optimization.objectives import admissibility_violation, evaluate_structural_objectives

STAGE2_PATH = ROOT / "experiments/02_stage2_nsga_structure_only/run.py"
ROBUST_PATH = ROOT / "experiments/02_stage2_nsga_structure_only/run_robustness.py"
CONFIG_PATH = ROOT / "configs/experiments/diagnostics/stage2_initialisation_ablation_daytrader.yml"


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


stage2 = _module("stage2_ablation_run", STAGE2_PATH)
robust = _module("stage2_ablation_robust", ROBUST_PATH)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def labels_summary(labels: np.ndarray, context: dict, phase: str, source_categories: list[str]) -> tuple[dict, pd.DataFrame]:
    rows = []
    for index, row in enumerate(np.asarray(labels, dtype=int)):
        canonical = encoding.canonical_relabel(row)
        counts = np.bincount(canonical)
        cluster_by_class = encoding.to_cluster_by_class(canonical, context["class_nodes"])
        coupling, cohesion, imbalance = evaluate_structural_objectives(context["raw_edges"], cluster_by_class, stage2.RAW_WEIGHT_COLUMN)
        violation = admissibility_violation(canonical, len(canonical))
        rows.append({
            "phase": phase, "individual": index,
            "source_category": source_categories[index] if index < len(source_categories) else "random_fill",
            "label_vector": json.dumps(canonical.tolist()),
            "feasible": bool(np.all(violation <= 0)),
            "cluster_count": int(len(counts)), "singleton_count": int(np.sum(counts == 1)),
            "singleton_ratio": float(np.sum(counts == 1) / len(canonical)),
            "max_cluster_size": int(counts.max()), "max_cluster_ratio": float(counts.max() / len(canonical)),
            "imbalance": float(imbalance), "coupling": float(coupling), "cohesion": float(cohesion),
        })
    frame = pd.DataFrame(rows)
    values = frame["imbalance"].to_numpy(float)
    return {
        f"{phase}_population_size": len(frame), f"{phase}_feasible": int(frame["feasible"].sum()),
        f"{phase}_infeasible": int((~frame["feasible"]).sum()),
        f"{phase}_unique_partitions": int(frame["label_vector"].nunique()),
        f"{phase}_unique_partition_ratio": float(frame["label_vector"].nunique() / len(frame)) if len(frame) else 0.0,
        f"{phase}_cluster_count_min": int(frame["cluster_count"].min()), f"{phase}_cluster_count_median": float(frame["cluster_count"].median()), f"{phase}_cluster_count_max": int(frame["cluster_count"].max()),
        f"{phase}_singleton_count_min": int(frame["singleton_count"].min()), f"{phase}_singleton_count_median": float(frame["singleton_count"].median()), f"{phase}_singleton_count_max": int(frame["singleton_count"].max()),
        f"{phase}_imbalance_min": float(values.min()), f"{phase}_imbalance_median": float(np.median(values)), f"{phase}_imbalance_max": float(values.max()),
    }, frame


def run_one(condition: str, seed: int, context: dict, bounds: dict, output: Path) -> dict:
    init_config = context["conditions"][condition]
    seed_records = stage2._seed_initialization_records(context["class_nodes"], context["raw_edges"], context["stage1_raw_baseline"], seed, init_config)
    samples: list[tuple[np.ndarray, np.ndarray]] = []
    initial_pop: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    def observer(raw, repaired): samples.append((raw.copy(), repaired.copy()))
    def callback(algorithm):
        if algorithm.n_gen == 1 and not initial_pop:
            initial_pop.append((np.asarray(algorithm.pop.get("X")).copy(), np.asarray(algorithm.pop.get("F")).copy(), np.asarray(algorithm.pop.get("G")).copy()))
    began = time.perf_counter()
    result = stage2._run_seed(context["class_nodes"], context["raw_edges"], context["stage1_raw_baseline"], init_config, seed, context["population_size"], context["generations"], callback=callback, initialization_observer=observer)
    runtime = time.perf_counter() - began
    if not samples or not initial_pop:
        raise RuntimeError("initial population was not captured")
    raw, repaired = samples[0]
    sources = [str(record["category"]) for record in seed_records] + ["random_fill"] * max(0, len(raw) - len(seed_records))
    pre, pre_frame = labels_summary(raw, context, "before_repair", sources)
    post, post_frame = labels_summary(repaired, context, "after_repair", sources)
    repaired_count = int(sum(stage2._label_key(a) != stage2._label_key(b) for a, b in zip(raw, repaired, strict=True)))
    repair_failures = int((~post_frame["feasible"]).sum())
    initial_actual, _, _ = initial_pop[0]
    actual_summary, actual_frame = labels_summary(initial_actual, context, "initial_algorithm_population", sources[:len(initial_actual)])
    raw_leiden_key = stage2._label_key(context["stage1_raw_baseline"]["cluster_id"].to_numpy(int))
    initial_has_leiden = any(stage2._label_key(row) == raw_leiden_key for row in initial_actual)
    pareto_rows, label_rows, posthoc_rows, _, _ = stage2._materialize_results(context["subject"], context["class_nodes"], context["raw_edges"], [result], context["stage1_raw_baseline"], context["reference_mapping"], np.asarray([1.1, 0.1, 1.1]))
    selected = stage2._select_solution(posthoc_rows, pareto_rows)
    selected_posthoc = next(row for row in posthoc_rows if row["solution_id"] == selected["solution_id"])
    objective = np.asarray([[row["coupling"], row["pymoo_f1_negative_cohesion"], row["imbalance"]] for row in pareto_rows])
    normalized = robust._normalize_checked(objective, bounds, subject="daytrader", seed=seed)
    hypervolume = stage2._hypervolume(normalized, robust.REFERENCE_POINT)
    leiden_f = robust._raw_leiden_objective_vector(context)
    dominates_leiden = int(sum(robust._dominates(row, leiden_f) for row in objective))
    diag = result["front_diagnostics"]
    selected_key = stage2._label_key(np.asarray(json.loads(selected["label_vector"]), int))
    row = {"condition": condition, "seed": seed, "status": "completed", "runtime_sec": runtime,
           "initial_seed_records": len(seed_records), "initial_seed_categories": json.dumps(stage2._category_counts(seed_records), sort_keys=True),
           "repaired_individuals": repaired_count, "repair_failures": repair_failures,
           "exact_leiden_in_initial_population": initial_has_leiden,
           "final_population_size": diag["final_population_size"], "final_feasible_count": diag["feasible_population_size"],
           "pareto_front_size": len(pareto_rows), "unique_final_partitions": diag["n_unique_canonical_partitions"],
           "bound_violations": 0, "fallback_used": diag["used_infeasible_fallback"], "selector_success": True,
           "selected_solution_id": selected["solution_id"], "selected_provenance": selected["injected_seed_category"] or "evolved_or_random",
           "selected_equals_leiden": selected_key == raw_leiden_key, "weighted_modularity": float(selected_posthoc["weighted_modularity"]),
           "coupling": float(selected["coupling"]), "cohesion": float(selected["cohesion"]), "imbalance": float(selected["imbalance"]),
           "cluster_count": int(selected_posthoc["cluster_count"]), "singleton_count": int(round(float(selected_posthoc["singleton_ratio"]) * len(context["class_nodes"]))),
           "singleton_ratio": float(selected_posthoc["singleton_ratio"]), "max_cluster_size": int(selected_posthoc["max_cluster_size"]), "max_cluster_ratio": float(selected_posthoc["max_cluster_ratio"]),
           "hypervolume": float(hypervolume), "front_dominates_paired_leiden": bool(dominates_leiden), "n_front_dominating_leiden": dominates_leiden,
           **pre, **post, **actual_summary}
    output.mkdir(parents=True, exist_ok=True)
    pre_frame.to_csv(output / "initial_population_before_repair.csv", index=False)
    post_frame.to_csv(output / "initial_population_after_repair.csv", index=False)
    actual_frame.to_csv(output / "initial_population_algorithm.csv", index=False)
    pd.DataFrame(pareto_rows).to_csv(output / "pareto_front.csv", index=False)
    pd.DataFrame(label_rows).to_csv(output / "pareto_labels.csv.xz", index=False, compression="xz")
    pd.DataFrame([selected]).to_csv(output / "selected_solution.csv", index=False)
    pd.DataFrame([row]).to_csv(output / "run_metrics.csv", index=False)
    return row


def paired_summary(rows: pd.DataFrame) -> pd.DataFrame:
    specs = [("weighted_modularity", 1), ("coupling", -1), ("cohesion", 1), ("imbalance", -1), ("pareto_front_size", 1), ("unique_final_partitions", 1), ("runtime_sec", -1), ("hypervolume", 1)]
    out = []
    for metric, direction in specs:
        warm = rows[rows.condition == "current_warm_start"].sort_values("seed").set_index("seed")[metric]
        random = rows[rows.condition == "random_only"].sort_values("seed").set_index("seed")[metric]
        delta = warm - random
        signed = delta * direction
        wins, ties, losses = int((signed > 0).sum()), int((signed == 0).sum()), int((signed < 0).sum())
        nonzero = delta[delta != 0]
        p, rbc = np.nan, np.nan
        if len(nonzero):
            from scipy.stats import rankdata, wilcoxon
            p = float(wilcoxon(delta, alternative="two-sided", method="auto").pvalue)
            ranks = rankdata(np.abs(nonzero.to_numpy(float)))
            rbc = float((ranks[nonzero.to_numpy(float) > 0].sum() - ranks[nonzero.to_numpy(float) < 0].sum()) / ranks.sum())
        out.append({"metric": metric, "warm_start_mean": float(warm.mean()), "random_only_mean": float(random.mean()), "warm_wins": wins, "ties": ties, "warm_losses": losses, "paired_median_difference_warm_minus_random": float(delta.median()), "exploratory_wilcoxon_p": p, "rank_biserial_warm_minus_random": rbc, "nonzero_paired_differences": len(nonzero)})
    return pd.DataFrame(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", choices=["current_warm_start", "random_only"])
    parser.add_argument("--seed", type=int)
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(CONFIG_PATH.read_text())
    formal_config = ROOT / config["formal_config"]
    bounds_path = ROOT / config["formal_bounds"]
    context = robust._load_context("daytrader", formal_config)
    context.update({"conditions": config["conditions"], "population_size": int(config["nsga"]["population_size"]), "generations": int(config["nsga"]["generations"])})
    bounds = yaml.safe_load(bounds_path.read_text())["subjects"]["daytrader"]
    robust._validate_bounds_against_context(bounds, context, "formal")
    output_root = ROOT / config["output_root"]
    inventory_paths = [
        formal_config, bounds_path,
        context["extracted_dir"] / "class_nodes.csv",
        context["extracted_dir"] / "structural_dependencies.csv",
        ROOT / "results/daytrader/01_stage1_leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv",
        ROOT / "results/daytrader/03_stage2_nsga/robustness/raw_runs.csv",
        ROOT / "results/daytrader/03_stage2_nsga/robustness/seed_00/selected_solution.csv",
        ROOT / "results/daytrader/03_stage2_nsga/robustness/seed_00/pareto_front.csv",
    ]
    manifest = {"source_branch_commit": stage2._git_state(ROOT)["git_head"], "formal_config": str(formal_config.relative_to(ROOT)), "formal_config_sha256": sha256(formal_config), "diagnostic_config_sha256": sha256(CONFIG_PATH), "bounds_path": str(bounds_path.relative_to(ROOT)), "bounds_sha256": sha256(bounds_path), "input_mode": "referenced_read_only", "input_hashes": robust._input_graph_hashes(context), "leiden_partition_sha256": stage2._frame_sha256(context["stage1_raw_baseline"]), "seeds": config["random_seeds"], "conditions": list(config["conditions"]), "formal_bounds_validated": True,
                "input_inventory": [{"source_path": str(path.relative_to(ROOT)), "destination_path": None, "access": "referenced_read_only", "sha256": sha256(path)} for path in inventory_paths]}
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    conditions = [args.condition] if args.condition else list(config["conditions"])
    seeds = [args.seed] if args.seed is not None else [int(value) for value in config["random_seeds"]]
    if args.seed is not None and args.seed not in config["random_seeds"]:
        raise ValueError("seed must be configured diagnostic seed")
    if not args.summarize_only:
        for condition in conditions:
            for seed in seeds:
                run_one(condition, int(seed), context, bounds, output_root / condition / f"seed_{int(seed):02d}")
    metric_paths = sorted(output_root.glob("*/seed_*/run_metrics.csv"))
    rows = pd.concat([pd.read_csv(path) for path in metric_paths], ignore_index=True)
    rows.to_csv(output_root / "all_run_metrics.csv", index=False)
    initial_columns = [
        "before_repair_feasible", "after_repair_feasible",
        "before_repair_unique_partition_ratio", "after_repair_unique_partition_ratio",
        "before_repair_cluster_count_min", "before_repair_cluster_count_max",
        "after_repair_cluster_count_min", "after_repair_cluster_count_max",
        "before_repair_singleton_count_median", "after_repair_singleton_count_median",
        "before_repair_imbalance_median", "after_repair_imbalance_median",
        "repaired_individuals", "repair_failures",
    ]
    rows.groupby("condition", as_index=False)[initial_columns].mean().to_csv(
        output_root / "initial_population_comparison.csv", index=False
    )
    if set(rows["condition"]) == set(config["conditions"]) and rows.groupby("condition")["seed"].nunique().min() == len(config["random_seeds"]):
        paired_summary(rows).to_csv(output_root / "paired_comparison.csv", index=False)
        front = pd.concat(
            [pd.read_csv(path).assign(condition=path.parents[1].name)
             for path in output_root.glob("*/seed_*/pareto_front.csv")],
            ignore_index=True,
        )
        front.to_csv(output_root / "all_pareto_fronts.csv", index=False)
        summary = front.groupby(["condition", "seed"], as_index=False).agg(
            pareto_solutions=("solution_id", "size"),
            unique_partitions=("label_vector", "nunique"),
            coupling_min=("coupling", "min"), coupling_median=("coupling", "median"), coupling_max=("coupling", "max"),
            cohesion_min=("cohesion", "min"), cohesion_median=("cohesion", "median"), cohesion_max=("cohesion", "max"),
            imbalance_min=("imbalance", "min"), imbalance_median=("imbalance", "median"), imbalance_max=("imbalance", "max"),
        )
        summary.to_csv(output_root / "pareto_front_summary.csv", index=False)
    print(output_root)


if __name__ == "__main__":
    main()
