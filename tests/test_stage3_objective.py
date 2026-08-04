from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evo_ms.optimization.stage3_problem import build_four_objective_problem


def test_final_problem_has_four_frozen_objectives() -> None:
    class_nodes = pd.DataFrame({"class_id": ["a", "b"], "class_name": ["A", "B"]})
    raw_edges = pd.DataFrame({"source": ["a"], "target": ["b"], "weight": [1.0]})
    semantic_edges = pd.DataFrame({"class_id_a": ["a"], "class_id_b": ["b"], "weight": [0.5]})
    problem = build_four_objective_problem(class_nodes, raw_edges, semantic_edges, "weight")
    assert problem.n_obj == 4
    assert problem.n_ieq_constr > 0
    out: dict[str, np.ndarray] = {}
    problem._evaluate(np.asarray([0, 0]), out)
    assert out["F"].shape == (4,)
