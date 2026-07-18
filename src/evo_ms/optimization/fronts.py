"""Reusable Pareto-front and Hypervolume operations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


def population_arrays(
    population: Any,
    objective_count: int | None = None,
    constraint_count: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract X/F/G arrays without depending on an experiment runner."""
    if population is None or len(population) == 0:
        objective_width = 0 if objective_count is None else objective_count
        constraint_width = 0 if constraint_count is None else constraint_count
        return (
            np.empty((0, 0), dtype=int),
            np.empty((0, objective_width), dtype=float),
            np.empty((0, constraint_width), dtype=float),
        )
    labels = np.atleast_2d(np.asarray(population.get("X"), dtype=int))
    objectives = np.atleast_2d(np.asarray(population.get("F"), dtype=float))
    constraints = population.get("G")
    if constraints is None:
        width = 0 if constraint_count is None else constraint_count
        constraints = np.zeros((len(labels), width), dtype=float)
    constraints = np.atleast_2d(np.asarray(constraints, dtype=float))
    return labels, objectives, constraints


def feasible_mask(constraints: np.ndarray, size: int) -> np.ndarray:
    if size == 0:
        return np.asarray([], dtype=bool)
    if constraints.size == 0:
        return np.ones(size, dtype=bool)
    return np.all(np.atleast_2d(constraints) <= 0.0, axis=1)


def nondominated_indices(objectives: np.ndarray) -> np.ndarray:
    if len(objectives) == 0:
        return np.asarray([], dtype=int)
    from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

    indices = NonDominatedSorting().do(
        np.asarray(objectives, dtype=float),
        only_non_dominated_front=True,
    )
    return np.asarray(sorted(indices.tolist()), dtype=int)


def validated_front(
    result: Any,
    objective_count: int,
    constraint_count: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    """Recompute the feasible nondominated front from a pymoo result."""
    pop_x, pop_f, pop_g = population_arrays(result.pop, objective_count, constraint_count)
    opt_x, opt_f, opt_g = population_arrays(result.opt, objective_count, constraint_count)
    final_population_size = len(pop_x)
    result_opt_size = len(opt_x)
    feasible = feasible_mask(pop_g, final_population_size)
    feasible_population_size = int(np.sum(feasible))
    violating = int(final_population_size - feasible_population_size)
    if final_population_size == 0:
        labels, objectives, constraints = opt_x, opt_f, opt_g
        recomputed_size = 0
        source = "result.opt" if result_opt_size else "result.pop_fallback"
        used_infeasible_fallback = False
    else:
        pool_mask = feasible if feasible_population_size else np.ones(final_population_size, dtype=bool)
        pool_indices = np.flatnonzero(pool_mask)
        front_local = nondominated_indices(pop_f[pool_indices])
        front_indices = pool_indices[front_local]
        labels = pop_x[front_indices]
        objectives = pop_f[front_indices]
        constraints = pop_g[front_indices]
        recomputed_size = len(front_indices)
        source = "recomputed_nondominated_front"
        used_infeasible_fallback = feasible_population_size == 0
    return labels, objectives, constraints, {
        "front_source": source,
        "final_population_size": int(final_population_size),
        "result_opt_size": int(result_opt_size),
        "feasible_population_size": feasible_population_size,
        "constraint_violating_population_size": violating,
        "recomputed_nondominated_size": int(recomputed_size),
        "front_validation_passed": bool(len(labels) == recomputed_size),
        "has_feasible_solution": bool(feasible_population_size > 0),
        "used_infeasible_fallback": bool(used_infeasible_fallback),
    }


def hypervolume_reference(
    seed_results: Sequence[Mapping[str, object]],
) -> tuple[np.ndarray, str]:
    objective_rows = [
        np.asarray(solution["F"], dtype=float)
        for seed_result in seed_results
        for solution in seed_result["solutions"]
    ]
    if not objective_rows:
        return np.asarray([1.1, 0.1, 1.1], dtype=float), "fallback_reference_for_empty_front"
    matrix = np.vstack(objective_rows)
    ideal = np.min(matrix, axis=0)
    nadir = np.max(matrix, axis=0)
    span = np.maximum(nadir - ideal, 1e-6)
    reference = nadir + np.maximum(0.1 * span, 1e-6)
    return reference.astype(float), "nadir_plus_10_percent_observed_span"


def calculate_hypervolume(objectives: np.ndarray, reference: np.ndarray) -> float:
    if np.asarray(objectives).size == 0:
        return 0.0
    from pymoo.indicators.hv import HV

    return float(HV(ref_point=np.asarray(reference, dtype=float))(np.asarray(objectives, dtype=float)))


def summarize_hypervolume(
    subject: str,
    rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    values = np.asarray([row["hypervolume"] for row in rows], dtype=float)
    return {
        "subject": subject,
        "seed_count": int(len(values)),
        "hypervolume_mean": float(np.mean(values)) if len(values) else 0.0,
        "hypervolume_std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        "hypervolume_min": float(np.min(values)) if len(values) else 0.0,
        "hypervolume_max": float(np.max(values)) if len(values) else 0.0,
    }
