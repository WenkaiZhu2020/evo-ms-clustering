"""Wrap the Stage 2 structural clustering problem as a pymoo Problem.

Design decisions:
- NSGA-II uses pymoo. The project must not hand-write the NSGA-II core.
- Individuals are integer label vectors, as described in `encoding.py`.
- The optimization contract has three objectives, as described in
  `objectives.py`.
- pymoo minimizes by default, so `_evaluate` must emit
  `F = [coupling, -cohesion, imbalance]`.
- Anti-degeneration checks are pymoo constraints or repair logic, using the
  thresholds in `objectives.py`.

pymoo imports stay lazy so this module can still be imported in lightweight
contexts before the optional optimization dependency is installed.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

from evo_ms.optimization import encoding
from evo_ms.optimization.objectives import (
    MIN_CLUSTER_COUNT,
    admissibility_violation,
    evaluate_structural_objectives,
)


CONSTRAINT_COUNT = 2
DEFAULT_MAX_CLUSTER_RATIO = 0.4


def validate_max_cluster_ratio(value: float) -> float:
    """Validate the shared max-cluster threshold used by repair and constraints."""
    ratio = float(value)
    if not 0.0 < ratio < 1.0:
        raise ValueError("max_cluster_ratio must be greater than 0 and less than 1")
    return ratio


class LabelVectorSampling:
    """pymoo sampling operator for variable-k integer label vectors.

    Optional seed label vectors are inserted first, then the remaining initial
    population is filled with random label vectors. This keeps seeded
    metaheuristic probes explicit while preserving the random-initialization
    default used by existing runs.
    """

    def __init__(
        self,
        max_clusters: int | None = None,
        seed_labels: list[np.ndarray] | None = None,
        max_cluster_ratio: float = DEFAULT_MAX_CLUSTER_RATIO,
    ) -> None:
        from pymoo.core.sampling import Sampling

        prepared_seed_labels = [
            np.asarray(labels, dtype=int).reshape(-1)
            for labels in (seed_labels or [])
        ]
        configured_max_cluster_ratio = validate_max_cluster_ratio(max_cluster_ratio)

        class _Sampling(Sampling):
            def _do(self, problem, n_samples, *args, random_state=None, **kwargs):
                rng = _rng(random_state)
                rows = []
                for labels in prepared_seed_labels[:n_samples]:
                    if len(labels) != problem.n_var:
                        raise ValueError(
                            "seed label vector length does not match problem.n_var"
                        )
                    rows.append(
                        _repair_labels(labels, problem.n_var, configured_max_cluster_ratio)
                    )

                rows.extend(
                    _repair_labels(
                        encoding.random_individual(
                            problem.n_var,
                            rng,
                            max_clusters=max_clusters,
                        ),
                        problem.n_var,
                        configured_max_cluster_ratio,
                    )
                    for _ in range(n_samples - len(rows))
                )
                return np.asarray(rows, dtype=int)

        self.operator = _Sampling()

    def do(self, *args, **kwargs):
        return self.operator.do(*args, **kwargs)


class UniformLabelCrossover:
    """Uniform crossover followed by canonical relabeling."""

    def __init__(
        self,
        probability: float = 0.9,
        max_cluster_ratio: float = DEFAULT_MAX_CLUSTER_RATIO,
    ) -> None:
        from pymoo.core.crossover import Crossover
        configured_max_cluster_ratio = validate_max_cluster_ratio(max_cluster_ratio)

        class _Crossover(Crossover):
            def __init__(self) -> None:
                super().__init__(2, 2, prob=probability)

            def _do(self, problem, X, *args, random_state=None, **kwargs):
                rng = _rng(random_state)
                _, n_matings, n_var = X.shape
                offspring = np.empty((2, n_matings, n_var), dtype=int)
                mask = rng.random((n_matings, n_var)) < 0.5
                offspring[0] = np.where(mask, X[0], X[1])
                offspring[1] = np.where(mask, X[1], X[0])
                for child_index in range(2):
                    for mating_index in range(n_matings):
                        offspring[child_index, mating_index] = _repair_labels(
                            offspring[child_index, mating_index],
                            problem.n_var,
                            configured_max_cluster_ratio,
                        )
                return offspring

        self.operator = _Crossover()

    def do(self, *args, **kwargs):
        return self.operator.do(*args, **kwargs)


class LabelReassignmentMutation:
    """Reassign selected classes to existing clusters or one new cluster."""

    def __init__(
        self,
        probability: float = 1.0,
        variable_probability: float | None = None,
        max_cluster_ratio: float = DEFAULT_MAX_CLUSTER_RATIO,
    ) -> None:
        from pymoo.core.mutation import Mutation
        configured_max_cluster_ratio = validate_max_cluster_ratio(max_cluster_ratio)

        class _Mutation(Mutation):
            def __init__(self) -> None:
                super().__init__(prob=probability, prob_var=variable_probability)

            def _do(self, problem, X, *args, random_state=None, **kwargs):
                rng = _rng(random_state)
                Xp = np.asarray(X, dtype=int).copy()
                probability_by_var = self.get_prob_var(problem, size=(len(Xp), 1))
                mutation_mask = rng.random(Xp.shape) < probability_by_var
                for row_index in range(len(Xp)):
                    labels = encoding.canonical_relabel(Xp[row_index])
                    existing = sorted(set(labels.tolist()))
                    next_label = max(existing, default=-1) + 1
                    for var_index in np.flatnonzero(mutation_mask[row_index]):
                        choices = existing + [next_label]
                        labels[var_index] = int(rng.choice(choices))
                        if labels[var_index] == next_label:
                            existing.append(next_label)
                            next_label += 1
                    Xp[row_index] = _repair_labels(
                        labels,
                        problem.n_var,
                        configured_max_cluster_ratio,
                    )
                return Xp

        self.operator = _Mutation()

    def do(self, *args, **kwargs):
        return self.operator.do(*args, **kwargs)


class CanonicalLabelRepair:
    """Canonicalize labels and repair the configured hard constraints."""

    def __init__(self, max_cluster_ratio: float = DEFAULT_MAX_CLUSTER_RATIO) -> None:
        from pymoo.core.repair import Repair
        configured_max_cluster_ratio = validate_max_cluster_ratio(max_cluster_ratio)

        class _Repair(Repair):
            def _do(self, problem, X, **kwargs):
                rows = [
                    _repair_labels(row, problem.n_var, configured_max_cluster_ratio)
                    for row in np.asarray(X, dtype=int)
                ]
                return np.asarray(rows, dtype=int)

        self.operator = _Repair()

    def do(self, *args, **kwargs):
        return self.operator.do(*args, **kwargs)


def build_nsga2_algorithm(
    population_size: int,
    max_clusters: int | None = None,
    seed_labels: list[np.ndarray] | None = None,
    max_cluster_ratio: float = DEFAULT_MAX_CLUSTER_RATIO,
):
    """Build pymoo NSGA2 with label-vector operators."""
    from pymoo.algorithms.moo.nsga2 import NSGA2

    return NSGA2(
        pop_size=int(population_size),
        sampling=LabelVectorSampling(
            max_clusters=max_clusters,
            seed_labels=seed_labels,
            max_cluster_ratio=max_cluster_ratio,
        ).operator,
        crossover=UniformLabelCrossover(max_cluster_ratio=max_cluster_ratio).operator,
        mutation=LabelReassignmentMutation(max_cluster_ratio=max_cluster_ratio).operator,
        repair=CanonicalLabelRepair(max_cluster_ratio=max_cluster_ratio).operator,
        eliminate_duplicates=True,
    )


def repair_labels(
    labels: np.ndarray,
    class_count: int,
    max_cluster_ratio: float = DEFAULT_MAX_CLUSTER_RATIO,
) -> np.ndarray:
    """Canonicalize labels and apply the Stage 2 admissibility repair policy."""
    return _repair_labels(labels, class_count, validate_max_cluster_ratio(max_cluster_ratio))


def build_structural_problem(
    class_nodes: pd.DataFrame,
    edges: pd.DataFrame,
    weight_column: str,
    seed: int = 42,
    max_cluster_ratio: float = DEFAULT_MAX_CLUSTER_RATIO,
):
    """Build and return a pymoo Problem for the raw structural graph.

    The caller supplies fixed `G_raw` edges and the `raw_weight` column. The
    returned instance keeps the edge table and weight column so evaluation does
    not rebuild graph inputs.
    """
    from pymoo.core.problem import ElementwiseProblem

    _validate_class_nodes(class_nodes)
    _validate_edges(edges, weight_column)
    configured_max_cluster_ratio = validate_max_cluster_ratio(max_cluster_ratio)

    class StructuralClusteringProblem(ElementwiseProblem):
        def __init__(self) -> None:
            self.class_nodes = class_nodes.reset_index(drop=True).copy()
            self.edges = edges.reset_index(drop=True).copy()
            self.weight_column = weight_column
            self.seed = int(seed)
            self.max_cluster_ratio = configured_max_cluster_ratio
            super().__init__(
                n_var=len(self.class_nodes),
                n_obj=3,
                n_ieq_constr=CONSTRAINT_COUNT,
                xl=0,
                xu=max(len(self.class_nodes) - 1, 0),
                vtype=int,
            )

        def _evaluate(self, x, out, *args, **kwargs) -> None:
            labels = _repair_labels(
                np.asarray(x, dtype=int),
                len(self.class_nodes),
                self.max_cluster_ratio,
            )
            cluster_by_class = encoding.to_cluster_by_class(labels, self.class_nodes)
            coupling, cohesion, imbalance = evaluate_structural_objectives(
                self.edges,
                cluster_by_class,
                self.weight_column,
            )
            out["F"] = np.asarray([coupling, -cohesion, imbalance], dtype=float)
            out["G"] = admissibility_violation(
                labels,
                len(self.class_nodes),
                self.max_cluster_ratio,
            )

    return StructuralClusteringProblem()


def _repair_labels(
    labels: np.ndarray,
    class_count: int,
    max_cluster_ratio: float,
) -> np.ndarray:
    labels = encoding.canonical_relabel(labels)
    if class_count <= 1:
        return labels

    labels = _ensure_min_cluster_count(labels)
    labels = _split_oversized_clusters(labels, class_count, max_cluster_ratio)
    labels = _ensure_min_cluster_count(labels)
    return encoding.canonical_relabel(labels)


def _ensure_min_cluster_count(labels: np.ndarray) -> np.ndarray:
    labels = labels.copy()
    while len(set(labels.tolist())) < min(MIN_CLUSTER_COUNT, len(labels)):
        counts = Counter(labels.tolist())
        largest_label, _ = max(counts.items(), key=lambda item: (item[1], -item[0]))
        member_indices = np.flatnonzero(labels == largest_label)
        if len(member_indices) <= 1:
            break
        labels[member_indices[-1]] = max(counts) + 1
        labels = encoding.canonical_relabel(labels)
    return labels


def _split_oversized_clusters(
    labels: np.ndarray,
    class_count: int,
    max_cluster_ratio: float,
) -> np.ndarray:
    labels = labels.copy()
    max_size = max(1, int(np.floor(max_cluster_ratio * class_count)))
    for _ in range(class_count):
        counts = Counter(labels.tolist())
        largest_label, largest_size = max(counts.items(), key=lambda item: item[1])
        if largest_size <= max_size:
            break
        member_indices = np.flatnonzero(labels == largest_label)
        overflow = member_indices[max_size:]
        next_label = max(counts) + 1
        for start in range(0, len(overflow), max_size):
            labels[overflow[start : start + max_size]] = next_label
            next_label += 1
        labels = encoding.canonical_relabel(labels)
    return labels


def _rng(random_state) -> np.random.Generator:
    if isinstance(random_state, np.random.Generator):
        return random_state
    if random_state is None:
        return np.random.default_rng()
    return np.random.default_rng(random_state)


def _validate_class_nodes(class_nodes: pd.DataFrame) -> None:
    missing = [
        column
        for column in ["class_id", "class_name"]
        if column not in class_nodes.columns
    ]
    if missing:
        raise ValueError(f"class_nodes is missing required columns: {', '.join(missing)}")
    if class_nodes["class_id"].astype(str).duplicated().any():
        raise ValueError("class_nodes contains duplicate class_id values")


def _validate_edges(edges: pd.DataFrame, weight_column: str) -> None:
    missing = [
        column
        for column in ["source", "target", weight_column]
        if column not in edges.columns
    ]
    if missing:
        raise ValueError(f"edges is missing required columns: {', '.join(missing)}")
    weights = pd.to_numeric(edges[weight_column], errors="coerce")
    if weights.isna().any():
        raise ValueError(f"edges contains non-numeric {weight_column} values")
    if (weights < 0).any():
        raise ValueError(f"edges contains negative {weight_column} values")
