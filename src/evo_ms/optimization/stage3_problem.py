"""Four-objective Stage 3 problem using separate G_raw and G_sem evidence."""

from __future__ import annotations

import numpy as np
import pandas as pd

from evo_ms.optimization import encoding
from evo_ms.optimization.objectives import evaluate_structural_objectives
from evo_ms.optimization.problem import (
    CONSTRAINT_COUNT,
    DEFAULT_MAX_CLUSTER_RATIO,
    _repair_labels,
    _validate_class_nodes,
    _validate_edges,
    admissibility_violation,
    validate_max_cluster_ratio,
)
from evo_ms.optimization.semantic_objective import semantic_total_weight, validate_semantic_edges


STAGE3_OBJECTIVE_ORDER = ["coupling", "negative_cohesion", "imbalance", "f_semantic"]
STAGE3_REPORT_COLUMNS = ["coupling", "cohesion", "imbalance", "f_semantic"]


def evaluate_four_objective_values(
    raw_edges: pd.DataFrame,
    semantic_edges: pd.DataFrame,
    cluster_by_class: dict[str, int],
    raw_weight_column: str,
    total_semantic_weight: float,
) -> tuple[float, float, float, float]:
    """Evaluate the frozen Stage 3 objectives for one fixed partition.

    The first three values deliberately call the Stage 2 structural evaluator
    unchanged.  This small seam is also used by output validation to
    independently recompute saved objective values.
    """
    from evo_ms.optimization.semantic_objective import evaluate_semantic_objective

    coupling, cohesion, imbalance = evaluate_structural_objectives(
        raw_edges,
        cluster_by_class,
        raw_weight_column,
    )
    f_semantic = evaluate_semantic_objective(
        semantic_edges,
        cluster_by_class,
        total_weight=total_semantic_weight,
    )
    return float(coupling), float(cohesion), float(imbalance), float(f_semantic)


def build_four_objective_problem(
    class_nodes: pd.DataFrame,
    raw_edges: pd.DataFrame,
    semantic_edges: pd.DataFrame,
    raw_weight_column: str,
    seed: int = 42,
    max_cluster_ratio: float = DEFAULT_MAX_CLUSTER_RATIO,
):
    """Build Stage 3's four-objective problem with unchanged Stage 2 operators."""
    from pymoo.core.problem import ElementwiseProblem

    _validate_class_nodes(class_nodes)
    _validate_edges(raw_edges, raw_weight_column)
    class_ids = set(class_nodes["class_id"].astype(str))
    validate_semantic_edges(semantic_edges, expected_class_ids=class_ids)
    if semantic_edges.empty:
        raise ValueError("formal semantic graph is empty")
    total_semantic_weight = semantic_total_weight(semantic_edges)
    configured_max_cluster_ratio = validate_max_cluster_ratio(max_cluster_ratio)

    class Stage3SemanticProblem(ElementwiseProblem):
        def __init__(self) -> None:
            self.class_nodes = class_nodes.reset_index(drop=True).copy()
            self.raw_edges = raw_edges.reset_index(drop=True).copy()
            self.semantic_edges = semantic_edges.reset_index(drop=True).copy()
            self.raw_weight_column = raw_weight_column
            self.semantic_total_weight = float(total_semantic_weight)
            self.seed = int(seed)
            self.max_cluster_ratio = configured_max_cluster_ratio
            super().__init__(
                n_var=len(self.class_nodes),
                n_obj=4,
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
            coupling, cohesion, imbalance, f_semantic = evaluate_four_objective_values(
                self.raw_edges,
                self.semantic_edges,
                cluster_by_class,
                self.raw_weight_column,
                self.semantic_total_weight,
            )
            out["F"] = np.asarray([coupling, -cohesion, imbalance, f_semantic], dtype=float)
            out["G"] = admissibility_violation(
                labels,
                len(self.class_nodes),
                self.max_cluster_ratio,
            )

    return Stage3SemanticProblem()
