"""Xerces-J budget-chase diagnostic: random+repair versus fresh seeded baseline.

All runs are isolated from the formal result directories.  Random runs reuse
the paired U{0,...,N-1} initialization and existing repair chain from the
previous diagnostic; each requested generation budget is run independently.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SUBJECT = "xerces-j"
SEEDS = list(range(10))
POPULATION_SIZE = 100
RANDOM_BUDGETS = [100, 200, 300, 500]
SEEDED_GENERATIONS = 100
NEAR_MATCH_RATIO = 0.95
OUTPUT_ROOT = ROOT / "results/xerces-j/03_stage2_nsga/diagnostics/random_budget_chase"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


control = _load_module(
    "xerces_random_repair_control",
    ROOT / "experiments/diagnostics/xerces_random_repair_control/run.py",
)
stage2 = _load_module(
    "stage2_seeded_runner_for_budget_chase",
    ROOT / "experiments/02_stage2_nsga_structure_only/run.py",
)


def _seeded_context() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    subject_config = stage2._load_subject_config(ROOT, SUBJECT)
    _, extracted, raw_edges = stage2._raw_graph_inputs(ROOT, SUBJECT, subject_config)
    class_nodes = extracted["class_nodes"]
    raw_leiden = stage2._frozen_raw_leiden_baseline(ROOT, SUBJECT, class_nodes)
    config = stage2.load_yaml(stage2.CONFIG_PATH)
    return class_nodes, raw_edges, raw_leiden, dict(config["initialization"])


class _SeededTrajectoryCallback:
    """Record feasible-front HV from the unmodified seeded Stage 2 runner."""

    def __init__(self, seed: int, bounds: dict[str, Any]) -> None:
        from pymoo.core.callback import Callback

        outer = self

        class CallbackImpl(Callback):
            def notify(self, algorithm) -> None:
                _, objectives, _, diagnostics = stage2._front_arrays(algorithm)
                if diagnostics["used_infeasible_fallback"]:
                    raise RuntimeError("seeded run has no feasible population")
                hv = control._hypervolume(np.asarray(objectives, dtype=float), bounds)
                outer.best_hv = max(outer.best_hv, hv)
                outer.rows.append(
                    {
                        "arm": "leiden_seeded",
                        "seed": int(seed),
                        "generation": int(algorithm.n_gen),
                        "feasible_individual_count": int(diagnostics["feasible_population_size"]),
                        "nondominated_front_size": int(len(objectives)),
                        "hypervolume": hv,
                        "best_so_far_hypervolume": outer.best_hv,
                    }
                )

        self.rows: list[dict[str, Any]] = []
        self.best_hv = 0.0
        self.callback = CallbackImpl()


def _plateau_generation(trajectory: pd.DataFrame) -> int | None:
    best = trajectory["best_so_far_hypervolume"].to_numpy(dtype=float)
    final = float(best[-1])
    if final <= 0.0:
        return None
    return int(trajectory.iloc[int(np.flatnonzero(best >= final * 0.99)[0])]["generation"])


def _run_random(seed: int, generations: int, bounds: dict[str, Any]) -> None:
    # The prior diagnostic's helper uses this module-level budget in its exact
    # existing random+repair execution path.
    control.GENERATIONS = int(generations)
    run_root = OUTPUT_ROOT / f"random_gen_{generations}"
    control._run_arm("random_with_repair", int(seed), run_root, bounds)


def _run_seeded(seed: int, bounds: dict[str, Any]) -> None:
    class_nodes, raw_edges, raw_leiden, initialization = _seeded_context()
    callback = _SeededTrajectoryCallback(seed, bounds)
    result = stage2._run_seed(
        class_nodes=class_nodes,
        raw_edges=raw_edges,
        raw_leiden_clusters=raw_leiden,
        initialization_config=initialization,
        seed=int(seed),
        population_size=POPULATION_SIZE,
        generations=SEEDED_GENERATIONS,
        callback=callback.callback,
    )
    trajectory = pd.DataFrame(callback.rows)
    if len(trajectory) != SEEDED_GENERATIONS:
        raise RuntimeError(f"seeded seed={seed}: expected {SEEDED_GENERATIONS} trajectory rows")
    diagnostics = result["front_diagnostics"]
    summary = {
        "arm": "leiden_seeded",
        "seed": int(seed),
        "class_count": int(len(class_nodes)),
        "population_size": POPULATION_SIZE,
        "generations": SEEDED_GENERATIONS,
        "seed_initialization_count": int(result["seed_initialization_count"]),
        "seed_initialization_categories": json.dumps(result["seed_initialization_categories"], sort_keys=True),
        "final_feasible_individual_count": int(diagnostics["feasible_population_size"]),
        "final_pareto_front_size": int(trajectory.iloc[-1]["nondominated_front_size"]),
        "final_hypervolume": float(trajectory.iloc[-1]["hypervolume"]),
        "best_hypervolume": float(trajectory.iloc[-1]["best_so_far_hypervolume"]),
        "plateau_generation_1pct_best_so_far": _plateau_generation(trajectory),
    }
    seed_dir = OUTPUT_ROOT / "leiden_seeded_gen_100" / f"seed_{seed:02d}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    trajectory.to_csv(seed_dir / "trajectory_by_generation.csv", index=False)
    pd.DataFrame([summary]).to_csv(seed_dir / "summary.csv", index=False)


def _random_summaries() -> pd.DataFrame:
    rows = []
    for generations in RANDOM_BUDGETS:
        for path in sorted((OUTPUT_ROOT / f"random_gen_{generations}").glob("random_with_repair/seed_*/summary.csv")):
            frame = pd.read_csv(path)
            frame["budget_generations"] = generations
            rows.append(frame)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _seeded_summaries() -> pd.DataFrame:
    paths = sorted((OUTPUT_ROOT / "leiden_seeded_gen_100").glob("seed_*/summary.csv"))
    return pd.concat([pd.read_csv(path) for path in paths], ignore_index=True) if paths else pd.DataFrame()


def _summary_table(random: pd.DataFrame, seeded: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for generations, frame in random.groupby("budget_generations", sort=True):
        values = frame["final_hypervolume"].to_numpy(dtype=float)
        rows.append({
            "arm": "random_with_repair",
            "generations": int(generations),
            "seed_count": int(len(values)),
            "hypervolume_mean": float(values.mean()),
            "hypervolume_std": float(values.std(ddof=1)),
            "hypervolume_min": float(values.min()),
            "hypervolume_max": float(values.max()),
            "best_so_far_hypervolume_mean": float(frame["best_hypervolume"].mean()),
            "plateau_generation_mean": float(frame["plateau_generation_1pct_best_so_far"].mean()),
            "plateau_generation_min": int(frame["plateau_generation_1pct_best_so_far"].min()),
            "plateau_generation_max": int(frame["plateau_generation_1pct_best_so_far"].max()),
        })
    seeded_values = seeded["final_hypervolume"].to_numpy(dtype=float)
    rows.append({
        "arm": "leiden_seeded",
        "generations": SEEDED_GENERATIONS,
        "seed_count": int(len(seeded_values)),
        "hypervolume_mean": float(seeded_values.mean()),
        "hypervolume_std": float(seeded_values.std(ddof=1)),
        "hypervolume_min": float(seeded_values.min()),
        "hypervolume_max": float(seeded_values.max()),
        "best_so_far_hypervolume_mean": float(seeded["best_hypervolume"].mean()),
        "plateau_generation_mean": float(seeded["plateau_generation_1pct_best_so_far"].mean()),
        "plateau_generation_min": int(seeded["plateau_generation_1pct_best_so_far"].min()),
        "plateau_generation_max": int(seeded["plateau_generation_1pct_best_so_far"].max()),
    })
    return pd.DataFrame(rows)


def _trajectory_table() -> pd.DataFrame:
    rows = []
    for generations in RANDOM_BUDGETS:
        for path in sorted((OUTPUT_ROOT / f"random_gen_{generations}").glob("random_with_repair/seed_*/trajectory_by_generation.csv")):
            frame = pd.read_csv(path)
            frame["budget_generations"] = generations
            rows.append(frame)
    for path in sorted((OUTPUT_ROOT / "leiden_seeded_gen_100").glob("seed_*/trajectory_by_generation.csv")):
        frame = pd.read_csv(path)
        frame["budget_generations"] = SEEDED_GENERATIONS
        rows.append(frame)
    all_rows = pd.concat(rows, ignore_index=True)
    return all_rows.groupby(["arm", "budget_generations", "generation"], as_index=False).agg(
        seed_count=("seed", "nunique"),
        feasible_individual_count_mean=("feasible_individual_count", "mean"),
        nondominated_front_size_mean=("nondominated_front_size", "mean"),
        hypervolume_mean=("hypervolume", "mean"),
        hypervolume_std=("hypervolume", "std"),
        best_so_far_hypervolume_mean=("best_so_far_hypervolume", "mean"),
    )


def _answers(summary: pd.DataFrame) -> pd.DataFrame:
    seeded_mean = float(summary.loc[summary["arm"] == "leiden_seeded", "hypervolume_mean"].iloc[0])
    random = summary.loc[summary["arm"] == "random_with_repair"].sort_values("generations")
    matches = random.loc[random["hypervolume_mean"] >= seeded_mean * NEAR_MATCH_RATIO]
    final = random.loc[random["generations"] == max(RANDOM_BUDGETS)].iloc[0]
    ratio = seeded_mean / float(final["hypervolume_mean"])
    return pd.DataFrame([
        {
            "question": "a_random_budget_matches_seeded_gen_100",
            "answer": "yes" if len(matches) else "no",
            "definition_of_near_match": f"random mean HV >= {NEAR_MATCH_RATIO:.2f} * seeded mean HV",
            "evidence": "" if not len(matches) else f"first matching budget: gen={int(matches.iloc[0]['generations'])}",
        },
        {
            "question": "b_random_500_plateau",
            "answer": "reported_from_1pct_best_so_far_rule",
            "definition_of_near_match": "plateau is earliest generation within 1% of that seed's final best-so-far HV",
            "evidence": (
                f"gen=500 mean HV={float(final['hypervolume_mean']):.9f}; "
                f"mean plateau generation={float(final['plateau_generation_mean']):.1f} "
                f"(range {int(final['plateau_generation_min'])}-{int(final['plateau_generation_max'])})"
            ),
        },
        {
            "question": "c_random_500_gap_to_seeded_gen_100",
            "answer": "not_applicable" if len(matches) else "reported",
            "definition_of_near_match": "seeded mean HV / random gen=500 mean HV",
            "evidence": f"seeded/random ratio={ratio:.6f}",
        },
    ])


def _write_summary() -> None:
    random = _random_summaries()
    seeded = _seeded_summaries()
    if len(random) != len(RANDOM_BUDGETS) * len(SEEDS) or len(seeded) != len(SEEDS):
        raise RuntimeError("cannot summarize until all 50 random and 10 seeded runs are present")
    summary = _summary_table(random, seeded)
    trajectories = _trajectory_table()
    summary.to_csv(OUTPUT_ROOT / "hypervolume_budget_comparison.csv", index=False)
    trajectories.to_csv(OUTPUT_ROOT / "hypervolume_trajectory_by_budget.csv", index=False)
    _answers(summary).to_csv(OUTPUT_ROOT / "answers.csv", index=False)
    random.to_csv(OUTPUT_ROOT / "random_all_seed_summaries.csv", index=False)
    seeded.to_csv(OUTPUT_ROOT / "seeded_all_seed_summaries.csv", index=False)
    manifest = {
        "subject": SUBJECT,
        "class_count": 814,
        "population_size": POPULATION_SIZE,
        "seeds": SEEDS,
        "random_budgets": RANDOM_BUDGETS,
        "seeded_generations": SEEDED_GENERATIONS,
        "random_initialization": "paired independent uniform labels U{0,...,N-1}, followed by existing repair",
        "seeded_initialization": "existing structure-aware Leiden-seeded Stage 2 configuration",
        "near_match_rule": f"random mean HV >= {NEAR_MATCH_RATIO:.2f} * seeded mean HV",
        "inputs_read_only": [
            "data/extracted/xerces-j/class_nodes.csv",
            "data/extracted/xerces-j/structural_dependencies.csv",
            "results/xerces-j/01_stage1_leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv",
            "configs/experiments/02_stage2_nsga_structure_only.yml",
            "configs/experiments/stage2_robustness_bounds.yml",
        ],
    }
    (OUTPUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["random", "seeded"])
    parser.add_argument("--seed", type=int, choices=SEEDS)
    parser.add_argument("--generations", type=int, choices=RANDOM_BUDGETS)
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    if args.summarize_only:
        _write_summary()
        return
    if args.mode is None or args.seed is None:
        raise ValueError("--mode and --seed are required unless --summarize-only is used")
    bounds = control._bounds()
    if args.mode == "random":
        if args.generations is None:
            raise ValueError("--generations is required for random runs")
        _run_random(args.seed, args.generations, bounds)
    elif args.generations is not None:
        raise ValueError("--generations is not accepted for seeded runs; it is fixed at 100")
    else:
        _run_seeded(args.seed, bounds)


if __name__ == "__main__":
    main()
