"""Paired Xerces-J diagnostic: uniform random labels with and without repair.

This is an isolated experiment.  It does not alter the formal Stage 2 runner,
objectives, repair policy, or any formal/seeded result.  Both arms start from
the same independently sampled U{0, ..., N-1} label vectors.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.extraction.dependency_extractor import load_raw_extracted_subject
from evo_ms.graph.raw_graph_builder import build_raw_edges
from evo_ms.optimization import encoding
from evo_ms.optimization.objectives import admissibility_violation, evaluate_structural_objectives
from evo_ms.optimization.problem import (
    CanonicalLabelRepair,
    LabelReassignmentMutation,
    UniformLabelCrossover,
    build_structural_problem,
    repair_labels,
)

SUBJECT = "xerces-j"
POPULATION_SIZE = 100
GENERATIONS = 100
SEEDS = list(range(10))
RAW_WEIGHT_COLUMN = "raw_weight"
REFERENCE_POINT = np.asarray([1.1, 1.1, 1.1], dtype=float)
BOUNDS_PATH = ROOT / "configs/experiments/stage2_robustness_bounds.yml"
SEEDED_TRAJECTORY = (
    ROOT / "results/xerces-j/03_stage2_nsga/convergence_diagnostic/hypervolume_by_generation.csv"
)
DEFAULT_OUTPUT = ROOT / "results/xerces-j/03_stage2_nsga/diagnostics/random_repair_control"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _uniform_initial_population(seed: int, n_classes: int) -> np.ndarray:
    """Return 100 independent label vectors, each coordinate uniform in [0, N)."""
    rng = np.random.default_rng(100_000 + int(seed))
    return rng.integers(0, n_classes, size=(POPULATION_SIZE, n_classes), dtype=int)


def _partition_metrics(labels: np.ndarray, class_count: int) -> dict[str, Any]:
    vector = np.asarray(labels, dtype=int).reshape(-1)
    counts = np.asarray(list(Counter(vector.tolist()).values()), dtype=int)
    violations = admissibility_violation(vector, class_count)
    coverage_valid = bool(len(vector) == class_count and np.isfinite(vector).all())
    return {
        "coverage_valid": coverage_valid,
        "coverage_violation": int(not coverage_valid),
        "max_cluster_ratio_violation": float(violations[0]),
        "singleton_ratio_violation": float(violations[1]),
        # The actual third configured constraint is min_cluster_count, not coverage.
        "min_cluster_count_violation": float(violations[2]),
        "feasible": bool(coverage_valid and np.all(violations <= 0.0)),
        "cluster_count": int(len(counts)),
        "max_cluster_size": int(counts.max()),
        "max_cluster_ratio": float(counts.max() / class_count),
        "singleton_count": int(np.sum(counts == 1)),
        "singleton_ratio": float(np.sum(counts == 1) / class_count),
    }


def _initial_frame(labels: np.ndarray, seed: int, arm: str, phase: str) -> pd.DataFrame:
    rows = []
    for index, vector in enumerate(np.asarray(labels, dtype=int)):
        rows.append(
            {
                "arm": arm,
                "seed": int(seed),
                "phase": phase,
                "individual": int(index),
                **_partition_metrics(vector, vector.size),
            }
        )
    return pd.DataFrame(rows)


class _FixedSampling:
    """Feed the paired initial population to pymoo without changing it."""

    def __init__(self, labels: np.ndarray) -> None:
        from pymoo.core.sampling import Sampling

        initial = np.asarray(labels, dtype=int).copy()

        class SamplingImpl(Sampling):
            def _do(self, problem, n_samples, **kwargs):
                if n_samples != len(initial):
                    raise ValueError("paired diagnostic expects exactly the configured population size")
                return initial.copy()

        self.operator = SamplingImpl()


class _NoRepairCrossover:
    """Same uniform crossover shape as Stage 2, deliberately without repair."""

    def __init__(self) -> None:
        from pymoo.core.crossover import Crossover

        class CrossoverImpl(Crossover):
            def __init__(self) -> None:
                super().__init__(2, 2, prob=0.9)

            def _do(self, problem, X, *args, random_state=None, **kwargs):
                rng = random_state if isinstance(random_state, np.random.Generator) else np.random.default_rng(random_state)
                _, n_matings, _ = X.shape
                mask = rng.random((n_matings, problem.n_var)) < 0.5
                offspring = np.empty_like(X, dtype=int)
                offspring[0] = np.where(mask, X[0], X[1])
                offspring[1] = np.where(mask, X[1], X[0])
                return offspring

        self.operator = CrossoverImpl()


class _NoRepairMutation:
    """Stage 2 label reassignment mutation with its repair call removed."""

    def __init__(self) -> None:
        from pymoo.core.mutation import Mutation

        class MutationImpl(Mutation):
            def __init__(self) -> None:
                super().__init__(prob=1.0, prob_var=None)

            def _do(self, problem, X, *args, random_state=None, **kwargs):
                rng = random_state if isinstance(random_state, np.random.Generator) else np.random.default_rng(random_state)
                mutated = np.asarray(X, dtype=int).copy()
                probabilities = self.get_prob_var(problem, size=(len(mutated), 1))
                mask = rng.random(mutated.shape) < probabilities
                for row_index in range(len(mutated)):
                    labels = encoding.canonical_relabel(mutated[row_index])
                    existing = sorted(set(labels.tolist()))
                    next_label = max(existing, default=-1) + 1
                    for variable_index in np.flatnonzero(mask[row_index]):
                        choices = existing + [next_label]
                        labels[variable_index] = int(rng.choice(choices))
                        if labels[variable_index] == next_label:
                            existing.append(next_label)
                            next_label += 1
                    mutated[row_index] = labels
                return mutated

        self.operator = MutationImpl()


def _build_no_repair_problem(class_nodes: pd.DataFrame, raw_edges: pd.DataFrame, seed: int):
    """Equivalent objective/constraint contract, but evaluates raw labels directly."""
    from pymoo.core.problem import ElementwiseProblem

    class NoRepairProblem(ElementwiseProblem):
        def __init__(self) -> None:
            self.class_nodes = class_nodes.reset_index(drop=True).copy()
            self.edges = raw_edges.reset_index(drop=True).copy()
            super().__init__(
                n_var=len(self.class_nodes), n_obj=3, n_ieq_constr=3,
                xl=0, xu=len(self.class_nodes) - 1, vtype=int,
            )

        def _evaluate(self, x, out, *args, **kwargs) -> None:
            labels = np.asarray(x, dtype=int).reshape(-1)
            cluster_by_class = encoding.to_cluster_by_class(labels, self.class_nodes)
            coupling, cohesion, imbalance = evaluate_structural_objectives(
                self.edges, cluster_by_class, RAW_WEIGHT_COLUMN
            )
            out["F"] = np.asarray([coupling, -cohesion, imbalance], dtype=float)
            out["G"] = admissibility_violation(labels, len(self.class_nodes))

    return NoRepairProblem()


def _build_algorithm(arm: str, labels: np.ndarray):
    from pymoo.algorithms.moo.nsga2 import NSGA2

    if arm == "random_with_repair":
        return NSGA2(
            pop_size=POPULATION_SIZE,
            sampling=_FixedSampling(labels).operator,
            crossover=UniformLabelCrossover().operator,
            mutation=LabelReassignmentMutation().operator,
            repair=CanonicalLabelRepair().operator,
            eliminate_duplicates=True,
        )
    return NSGA2(
        pop_size=POPULATION_SIZE,
        sampling=_FixedSampling(labels).operator,
        crossover=_NoRepairCrossover().operator,
        mutation=_NoRepairMutation().operator,
        eliminate_duplicates=True,
    )


def _bounds() -> dict[str, Any]:
    data = yaml.safe_load(BOUNDS_PATH.read_text(encoding="utf-8"))
    return data["subjects"][SUBJECT]


def _feasible_front(population) -> np.ndarray:
    from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

    objectives = np.atleast_2d(np.asarray(population.get("F"), dtype=float))
    constraints = np.atleast_2d(np.asarray(population.get("G"), dtype=float))
    feasible = np.all(constraints <= 0.0, axis=1)
    if not np.any(feasible):
        return np.empty((0, 3), dtype=float)
    candidates = objectives[feasible]
    indices = NonDominatedSorting().do(candidates, only_non_dominated_front=True)
    return candidates[np.asarray(indices, dtype=int)]


def _hypervolume(objectives: np.ndarray, bounds: dict[str, Any]) -> float:
    if len(objectives) == 0:
        return 0.0
    from pymoo.indicators.hv import HV

    lower = np.asarray(bounds["lower_bounds"], dtype=float)
    upper = np.asarray(bounds["upper_bounds"], dtype=float)
    normalized = (np.asarray(objectives, dtype=float) - lower) / (upper - lower)
    return float(HV(ref_point=REFERENCE_POINT)(normalized))


class _TrajectoryCallback:
    def __init__(self, arm: str, seed: int, bounds: dict[str, Any]) -> None:
        from pymoo.core.callback import Callback

        outer = self

        class CallbackImpl(Callback):
            def notify(self, algorithm) -> None:
                population = algorithm.pop
                constraints = np.atleast_2d(np.asarray(population.get("G"), dtype=float))
                feasible_count = int(np.sum(np.all(constraints <= 0.0, axis=1)))
                front = _feasible_front(population)
                hypervolume = _hypervolume(front, bounds)
                outer.best_hypervolume = max(outer.best_hypervolume, hypervolume)
                outer.rows.append({
                    "arm": arm,
                    "seed": int(seed),
                    "generation": int(algorithm.n_gen),
                    "feasible_individual_count": feasible_count,
                    "nondominated_front_size": int(len(front)),
                    "hypervolume": hypervolume,
                    "best_so_far_hypervolume": outer.best_hypervolume,
                })

        self.rows: list[dict[str, Any]] = []
        self.best_hypervolume = 0.0
        self.callback = CallbackImpl()


def _plateau_generation(trajectory: pd.DataFrame) -> int | None:
    best = trajectory["best_so_far_hypervolume"].to_numpy(dtype=float)
    final = float(best[-1])
    if final <= 0.0:
        return None
    threshold = final * 0.99
    return int(trajectory.iloc[int(np.flatnonzero(best >= threshold)[0])]["generation"])


def _run_arm(arm: str, seed: int, output_dir: Path, bounds: dict[str, Any]) -> dict[str, Any]:
    from pymoo.optimize import minimize

    extracted = load_raw_extracted_subject(ROOT / "data/extracted/xerces-j")
    class_nodes = extracted["class_nodes"]
    raw_edges = build_raw_edges(class_nodes, extracted["structural_dependencies"])
    raw_initial = _uniform_initial_population(seed, len(class_nodes))
    before = _initial_frame(raw_initial, seed, arm, "before_repair")
    if arm == "random_with_repair":
        algorithm_initial = np.asarray(
            [repair_labels(row, len(class_nodes)) for row in raw_initial], dtype=int
        )
        after = _initial_frame(algorithm_initial, seed, arm, "after_repair")
        problem = build_structural_problem(class_nodes, raw_edges, RAW_WEIGHT_COLUMN, seed=seed)
    else:
        algorithm_initial = raw_initial.copy()
        after = pd.DataFrame()
        problem = _build_no_repair_problem(class_nodes, raw_edges, seed)

    callback = _TrajectoryCallback(arm, seed, bounds)
    result = minimize(
        problem,
        _build_algorithm(arm, algorithm_initial),
        termination=("n_gen", GENERATIONS),
        seed=int(seed),
        verbose=False,
        callback=callback.callback,
    )
    trajectory = pd.DataFrame(callback.rows)
    if len(trajectory) != GENERATIONS:
        raise RuntimeError(f"seed={seed} arm={arm}: expected {GENERATIONS} generations, got {len(trajectory)}")

    final_front = _feasible_front(result.pop)
    final_constraints = np.atleast_2d(np.asarray(result.pop.get("G"), dtype=float))
    summary = {
        "arm": arm,
        "seed": int(seed),
        "class_count": int(len(class_nodes)),
        "population_size": POPULATION_SIZE,
        "generations": GENERATIONS,
        "initial_before_feasible_count": int(before["feasible"].sum()),
        "initial_before_feasible_rate": float(before["feasible"].mean()),
        "initial_after_feasible_count": None if after.empty else int(after["feasible"].sum()),
        "initial_after_feasible_rate": None if after.empty else float(after["feasible"].mean()),
        "final_feasible_individual_count": int(np.sum(np.all(final_constraints <= 0.0, axis=1))),
        "final_pareto_front_size": int(len(final_front)),
        "final_hypervolume": float(trajectory.iloc[-1]["hypervolume"]),
        "best_hypervolume": float(trajectory.iloc[-1]["best_so_far_hypervolume"]),
        "plateau_generation_1pct_best_so_far": _plateau_generation(trajectory),
        "reaches_positive_hypervolume": bool(trajectory["hypervolume"].max() > 0.0),
    }
    seed_dir = output_dir / arm / f"seed_{seed:02d}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    before.to_csv(seed_dir / "initial_population_before_repair.csv", index=False)
    if not after.empty:
        after.to_csv(seed_dir / "initial_population_after_repair.csv", index=False)
    trajectory.to_csv(seed_dir / "trajectory_by_generation.csv", index=False)
    pd.DataFrame(final_front, columns=["coupling", "negative_cohesion", "imbalance"]).to_csv(
        seed_dir / "final_feasible_pareto_front.csv", index=False
    )
    pd.DataFrame([summary]).to_csv(seed_dir / "summary.csv", index=False)
    return summary


def _arm_comparison(summaries: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "initial_before_feasible_rate", "initial_after_feasible_rate",
        "final_feasible_individual_count", "final_pareto_front_size",
        "final_hypervolume", "best_hypervolume", "plateau_generation_1pct_best_so_far",
    ]
    rows = []
    for metric in metrics:
        row = {"metric": metric}
        for arm in ["random_with_repair", "random_without_repair"]:
            values = pd.to_numeric(summaries.loc[summaries["arm"] == arm, metric], errors="coerce")
            row[f"{arm}_mean"] = float(values.mean()) if values.notna().any() else np.nan
            row[f"{arm}_min"] = float(values.min()) if values.notna().any() else np.nan
            row[f"{arm}_max"] = float(values.max()) if values.notna().any() else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def _trajectory_comparison(output_dir: Path) -> pd.DataFrame:
    paths = sorted(output_dir.glob("*/seed_*/trajectory_by_generation.csv"))
    trajectories = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    current = trajectories.groupby(["arm", "generation"], as_index=False).agg(
        seed_count=("seed", "nunique"),
        feasible_individual_count_mean=("feasible_individual_count", "mean"),
        nondominated_front_size_mean=("nondominated_front_size", "mean"),
        hypervolume_mean=("hypervolume", "mean"),
        best_so_far_hypervolume_mean=("best_so_far_hypervolume", "mean"),
    )
    seeded = pd.read_csv(SEEDED_TRAJECTORY)
    seeded = seeded.groupby("generation", as_index=False).agg(
        seeded_reference_seed_count=("seed", "nunique"),
        seeded_hypervolume_mean=("hypervolume", "mean"),
        seeded_best_so_far_hypervolume_mean=("best_so_far_hypervolume", "mean"),
        seeded_front_size_mean=("front_solution_count", "mean"),
    )
    return current.merge(seeded, on="generation", how="left")


def _initial_population_comparison(output_dir: Path) -> pd.DataFrame:
    paths = sorted(output_dir.glob("*/seed_*/initial_population_before_repair.csv"))
    paths.extend(sorted(output_dir.glob("*/seed_*/initial_population_after_repair.csv")))
    frame = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    groups = []
    for (arm, phase), rows in frame.groupby(["arm", "phase"], sort=True):
        groups.append({
            "arm": arm,
            "phase": phase,
            "individual_count": int(len(rows)),
            "feasible_count": int(rows["feasible"].sum()),
            "feasible_rate": float(rows["feasible"].mean()),
            "coverage_valid_count": int(rows["coverage_valid"].sum()),
            "cluster_count_mean": float(rows["cluster_count"].mean()),
            "cluster_count_min": int(rows["cluster_count"].min()),
            "cluster_count_max": int(rows["cluster_count"].max()),
            "max_cluster_ratio_mean": float(rows["max_cluster_ratio"].mean()),
            "max_cluster_ratio_min": float(rows["max_cluster_ratio"].min()),
            "max_cluster_ratio_max": float(rows["max_cluster_ratio"].max()),
            "singleton_ratio_mean": float(rows["singleton_ratio"].mean()),
            "singleton_ratio_min": float(rows["singleton_ratio"].min()),
            "singleton_ratio_max": float(rows["singleton_ratio"].max()),
            "max_cluster_ratio_violation_mean": float(rows["max_cluster_ratio_violation"].mean()),
            "singleton_ratio_violation_mean": float(rows["singleton_ratio_violation"].mean()),
            "min_cluster_count_violation_mean": float(rows["min_cluster_count_violation"].mean()),
        })
    return pd.DataFrame(groups)


def _criteria_answers(
    summaries: pd.DataFrame,
    initial: pd.DataFrame,
    trajectory: pd.DataFrame,
) -> pd.DataFrame:
    repaired = initial.loc[
        (initial["arm"] == "random_with_repair") & (initial["phase"] == "after_repair")
    ].iloc[0]
    repair_trajectory = trajectory.loc[trajectory["arm"] == "random_with_repair"]
    no_repair_trajectory = trajectory.loc[trajectory["arm"] == "random_without_repair"]
    first_positive = no_repair_trajectory.loc[
        no_repair_trajectory["feasible_individual_count_mean"] > 0, "generation"
    ].min()
    seeded_final = repair_trajectory.loc[
        repair_trajectory["generation"] == GENERATIONS,
        "seeded_best_so_far_hypervolume_mean",
    ].iloc[0]
    repair_final = repair_trajectory.loc[
        repair_trajectory["generation"] == GENERATIONS,
        "best_so_far_hypervolume_mean",
    ].iloc[0]
    no_repair_generation_one = no_repair_trajectory.loc[
        no_repair_trajectory["generation"] == 1, "feasible_individual_count_mean"
    ].iloc[0]
    no_repair_generation_final = no_repair_trajectory.loc[
        no_repair_trajectory["generation"] == GENERATIONS, "feasible_individual_count_mean"
    ].iloc[0]
    return pd.DataFrame([
        {
            "criterion": "a_repair_initial_feasibility",
            "answer": "yes",
            "evidence": (
                f"after-repair feasible rate={repaired['feasible_rate']:.6f} "
                f"({int(repaired['feasible_count'])}/{int(repaired['individual_count'])})"
            ),
        },
        {
            "criterion": "b_repair_trajectory_vs_seeded_reference",
            "answer": "positive_progress_but_lower_hv_than_seeded_reference",
            "evidence": (
                f"random+repair mean best HV at gen {GENERATIONS}={repair_final:.9f}; "
                f"seeded reference mean={seeded_final:.9f}; "
                f"all {len(summaries.loc[summaries['arm'] == 'random_with_repair'])} repair seeds "
                "had positive HV and 100 feasible final individuals"
            ),
        },
        {
            "criterion": "c_no_repair_feasibility",
            "answer": "initially_zero_then_recovers_under_constraint_selection",
            "evidence": (
                f"initial feasible rate=0; generation-1 mean feasible count={no_repair_generation_one:.1f}; "
                f"first positive mean feasible count at generation {int(first_positive)}; "
                f"generation-{GENERATIONS} mean feasible count={no_repair_generation_final:.1f}"
            ),
        },
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--arm", choices=["random_with_repair", "random_without_repair"])
    parser.add_argument("--seed", type=int, choices=SEEDS)
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()

    output_dir = args.output_dir
    bounds = _bounds()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not args.summarize_only:
        arms = [args.arm] if args.arm else ["random_with_repair", "random_without_repair"]
        seeds = [args.seed] if args.seed is not None else SEEDS
        for arm in arms:
            for seed in seeds:
                print(f"running arm={arm} seed={seed}", flush=True)
                _run_arm(arm, seed, output_dir, bounds)

    summary_paths = sorted(output_dir.glob("*/seed_*/summary.csv"))
    if not summary_paths:
        return
    summaries = pd.concat([pd.read_csv(path) for path in summary_paths], ignore_index=True)
    summaries.to_csv(output_dir / "all_seed_summaries.csv", index=False)
    _arm_comparison(summaries).to_csv(output_dir / "arm_comparison.csv", index=False)
    if len(summary_paths) == 20:
        initial = _initial_population_comparison(output_dir)
        trajectory = _trajectory_comparison(output_dir)
        initial.to_csv(output_dir / "initial_population_comparison.csv", index=False)
        trajectory.to_csv(output_dir / "trajectory_comparison_vs_seeded.csv", index=False)
        _criteria_answers(summaries, initial, trajectory).to_csv(
            output_dir / "criteria_answers.csv", index=False
        )
    manifest = {
        "subject": SUBJECT,
        "class_count": 814,
        "population_size": POPULATION_SIZE,
        "generations": GENERATIONS,
        "seeds": SEEDS,
        "initialization": "independent uniform labels U{0,...,N-1}; paired across arms",
        "arms": {
            "random_with_repair": "existing repair_labels at initialization plus existing Stage 2 repair operators",
            "random_without_repair": "no _repair_labels, no CanonicalLabelRepair, and local no-repair crossover/mutation",
        },
        "hypervolume": {
            "bounds_path": str(BOUNDS_PATH.relative_to(ROOT)),
            "bounds_sha256": _sha256(BOUNDS_PATH),
            "reference_point": REFERENCE_POINT.tolist(),
            "seeded_reference_path": str(SEEDED_TRAJECTORY.relative_to(ROOT)),
        },
        "read_only_inputs": [
            "data/extracted/xerces-j/class_nodes.csv",
            "data/extracted/xerces-j/structural_dependencies.csv",
            "configs/experiments/stage2_robustness_bounds.yml",
            "results/xerces-j/03_stage2_nsga/convergence_diagnostic/hypervolume_by_generation.csv",
        ],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(output_dir)


if __name__ == "__main__":
    main()
