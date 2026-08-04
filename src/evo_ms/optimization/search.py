"""Small reusable optimizer execution seam."""

from __future__ import annotations

from typing import Any


def run_nsga2(
    problem: Any,
    algorithm: Any,
    *,
    seed: int,
    generations: int,
    save_history: bool = False,
    callback: Any | None = None,
) -> Any:
    """Run one already-constructed pymoo problem and algorithm."""
    from pymoo.optimize import minimize

    kwargs: dict[str, Any] = {
        "seed": int(seed),
        "verbose": False,
        "save_history": bool(save_history),
    }
    if callback is not None:
        kwargs["callback"] = callback
    return minimize(problem, algorithm, termination=("n_gen", int(generations)), **kwargs)
