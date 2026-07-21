"""Record fixed-bounds Hypervolume trajectories for representative Stage 2 seeds.

This is an isolated diagnostic runner. It reuses the formal Stage 2 problem,
operators, initialization, seed handling, and frozen theoretical bounds, but
uses a pymoo callback to calculate Hypervolume after every generation. It
never writes to a formal robustness directory.
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


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _load_robustness_module():
    spec = importlib.util.spec_from_file_location(
        "stage2_robustness_runner",
        SCRIPT_DIR / "run_robustness.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError("Could not load Stage 2 robustness runner module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


robustness = _load_robustness_module()
stage2 = robustness.stage2

DEFAULT_CONFIG = stage2.CONFIG_PATH
DEFAULT_BOUNDS_CONFIG = robustness.DEFAULT_BOUNDS_CONFIG
DEFAULT_SEEDS = [0, 15, 29]


def _parse_seeds(value: str | None) -> list[int]:
    if value is None:
        return list(DEFAULT_SEEDS)
    seeds = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not seeds:
        raise ValueError("--seeds must contain at least one integer seed")
    if len(set(seeds)) != len(seeds):
        raise ValueError("--seeds must not contain duplicates")
    return seeds


def _load_theoretical_bounds(
    subject: str,
    bounds_config: Path,
    config_path: Path,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Load frozen formal bounds without requiring the diagnostic's Git commit.

    The normal formal runner intentionally pins bounds to its generating commit.
    This diagnostic does not write formal data and changes only `save_history`,
    so it instead validates the objective schema, graph hash, class count,
    edge-weight bound, and algorithm configuration hash before reuse.
    """
    document = robustness._normalize_bounds_document(robustness._read_yaml_if_exists(bounds_config))
    bounds = document.get("subjects", {}).get(subject)
    if not isinstance(bounds, dict):
        raise ValueError(f"missing frozen bounds for subject={subject}")
    if bounds.get("bounds_source") != "theoretical" or bounds.get("calibration_status") != "not_required":
        raise ValueError("convergence diagnostics require formal theoretical bounds")
    if list(bounds.get("objective_order", [])) != robustness.OBJECTIVE_ORDER:
        raise ValueError("bounds objective_order does not match the formal runner")
    if list(bounds.get("reference_point", [])) != robustness._float_list(robustness.REFERENCE_POINT):
        raise ValueError("bounds reference_point does not match the formal runner")
    if bounds.get("algorithm_config_sha256") != robustness._file_sha256(config_path):
        raise ValueError("bounds algorithm_config_sha256 does not match the supplied config")
    robustness._validate_theoretical_bounds_schema(bounds)
    robustness._validate_bounds_against_context(bounds, context, "formal")
    return bounds


def _generation_front_objectives(history_entry: Any) -> np.ndarray:
    """Return the feasible nondominated final population in formal minimization space."""
    _, objectives, _, diagnostics = stage2._front_arrays(history_entry)
    if diagnostics["used_infeasible_fallback"]:
        raise RuntimeError("convergence diagnostic encountered an infeasible population fallback")
    return np.asarray(objectives, dtype=float)


class _HypervolumeCallback:
    """Capture each generation without retaining pymoo's full history snapshots."""

    def __init__(self, subject: str, seed: int, bounds: dict[str, Any]) -> None:
        from pymoo.core.callback import Callback

        class CallbackImpl(Callback):
            def __init__(self, outer: _HypervolumeCallback) -> None:
                super().__init__()
                self.outer = outer

            def notify(self, algorithm) -> None:
                objectives = _generation_front_objectives(algorithm)
                normalized = robustness._normalize_checked(
                    objectives,
                    self.outer.bounds,
                    subject=self.outer.subject,
                    seed=self.outer.seed,
                )
                hypervolume = stage2._hypervolume(normalized, robustness.REFERENCE_POINT)
                self.outer.best_so_far = max(self.outer.best_so_far, hypervolume)
                self.outer.rows.append(
                    {
                        "subject": self.outer.subject,
                        "seed": self.outer.seed,
                        "generation": int(algorithm.n_gen),
                        "hypervolume": hypervolume,
                        "best_so_far_hypervolume": self.outer.best_so_far,
                        "front_solution_count": int(len(objectives)),
                    }
                )

        self.subject = subject
        self.seed = int(seed)
        self.bounds = bounds
        self.rows: list[dict[str, Any]] = []
        self.best_so_far = 0.0
        self.callback = CallbackImpl(self)


def _trajectory_for_seed(
    seed: int,
    context: dict[str, Any],
    bounds: dict[str, Any],
) -> pd.DataFrame:
    callback = _HypervolumeCallback(context["subject"], seed, bounds)
    stage2._run_seed(
        class_nodes=context["class_nodes"],
        raw_edges=context["raw_edges"],
        raw_leiden_clusters=context["stage1_raw_baseline"],
        initialization_config=context["initialization_config"],
        seed=seed,
        population_size=context["population_size"],
        generations=context["generations"],
        callback=callback.callback,
    )
    if len(callback.rows) != context["generations"]:
        raise RuntimeError(
            f"expected {context['generations']} callback rows, got {len(callback.rows)}"
        )
    return pd.DataFrame(callback.rows).sort_values("generation").reset_index(drop=True)


def _formal_final_hypervolume(subject: str, seed: int) -> float:
    path = ROOT / "results" / subject / "03_stage2_nsga" / "robustness_final_30seeds" / "raw_runs.csv"
    rows = pd.read_csv(path)
    matched = rows.loc[rows["seed"] == seed, "hypervolume"]
    if len(matched) != 1:
        raise ValueError(f"expected one formal hypervolume for subject={subject} seed={seed}")
    return float(matched.iloc[0])


def _summary_row(trajectory: pd.DataFrame) -> dict[str, Any]:
    ordered = trajectory.sort_values("generation")
    best = ordered["best_so_far_hypervolume"].to_numpy(dtype=float)
    final_best = float(best[-1])
    denominator = max(abs(final_best), np.finfo(float).eps)
    remaining = (final_best - best) / denominator
    plateau_generation = int(ordered.iloc[int(np.flatnonzero(remaining <= 0.01)[0])]["generation"])
    last_window_start = max(0, len(best) - 20)
    last_20_relative_gain = float((final_best - best[last_window_start]) / denominator)
    return {
        "subject": str(ordered.iloc[0]["subject"]),
        "seed": int(ordered.iloc[0]["seed"]),
        "final_hypervolume": float(ordered.iloc[-1]["hypervolume"]),
        "best_hypervolume": final_best,
        "plateau_generation_1pct_best_so_far": plateau_generation,
        "last_20_relative_best_hv_gain": last_20_relative_gain,
    }


def _plot_trajectory(trajectory: pd.DataFrame, output_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(8, 4.5))
    for seed, rows in trajectory.groupby("seed", sort=True):
        ordered = rows.sort_values("generation")
        axis.plot(
            ordered["generation"],
            ordered["best_so_far_hypervolume"],
            label=f"seed {int(seed)}",
        )
    axis.set_xlabel("Generation")
    axis.set_ylabel("Best-so-far hypervolume")
    axis.set_title(f"Stage 2 convergence diagnostic: {trajectory.iloc[0]['subject']}")
    axis.set_xlim(1, int(trajectory["generation"].max()))
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_dir / "hypervolume_by_generation.png", dpi=180)
    figure.savefig(output_dir / "hypervolume_by_generation.pdf")
    plt.close(figure)


def run_diagnostic(
    subject: str,
    seeds: list[int],
    output_dir: Path,
    bounds_config: Path,
    config_path: Path,
) -> pd.DataFrame:
    context = robustness._load_context(subject, config_path)
    bounds = _load_theoretical_bounds(subject, bounds_config, config_path, context)
    output_dir.mkdir(parents=True, exist_ok=True)

    trajectories = [_trajectory_for_seed(seed, context, bounds) for seed in seeds]
    trajectory = pd.concat(trajectories, ignore_index=True)
    summaries = pd.DataFrame([_summary_row(rows) for _, rows in trajectory.groupby("seed", sort=True)])
    formal_hv = {
        seed: _formal_final_hypervolume(subject, seed)
        for seed in seeds
    }
    summaries["formal_final_hypervolume"] = summaries["seed"].map(formal_hv)
    summaries["final_hv_abs_difference"] = (
        summaries["final_hypervolume"] - summaries["formal_final_hypervolume"]
    ).abs()
    summaries["final_hv_matches_formal"] = np.isclose(
        summaries["final_hypervolume"],
        summaries["formal_final_hypervolume"],
        rtol=1e-12,
        atol=1e-12,
    )
    if not bool(summaries["final_hv_matches_formal"].all()):
        mismatches = summaries.loc[
            ~summaries["final_hv_matches_formal"],
            ["seed", "final_hypervolume", "formal_final_hypervolume", "final_hv_abs_difference"],
        ]
        raise RuntimeError("final Hypervolume does not match formal output:\n" + mismatches.to_string(index=False))

    trajectory.to_csv(output_dir / "hypervolume_by_generation.csv", index=False)
    summaries.to_csv(output_dir / "convergence_summary.csv", index=False)
    _plot_trajectory(trajectory, output_dir)
    metadata = {
        "subject": subject,
        "seeds": [int(seed) for seed in seeds],
        "population_size": context["population_size"],
        "generations": context["generations"],
        "objective_order": robustness.OBJECTIVE_ORDER,
        "normalization_bounds": {
            "lower_bounds": bounds["lower_bounds"],
            "upper_bounds": bounds["upper_bounds"],
        },
        "reference_point": robustness._float_list(robustness.REFERENCE_POINT),
        "bounds_source": bounds["bounds_source"],
        "calibration_status": bounds["calibration_status"],
        "plateau_rule": "earliest generation whose best-so-far HV is within 1% of the final best-so-far HV",
    }
    (output_dir / "convergence_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description="Run isolated Stage 2 convergence diagnostics.")
    parser.add_argument("--subject", required=True, choices=robustness.SUBJECTS)
    parser.add_argument("--seeds", default=None, help="Comma-separated representative seeds; default: 0,15,29")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--bounds-config", type=Path, default=DEFAULT_BOUNDS_CONFIG)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    output_dir = args.output_dir or (
        ROOT / "results" / args.subject / "03_stage2_nsga" / "convergence_diagnostic"
    )
    summaries = run_diagnostic(
        subject=args.subject,
        seeds=_parse_seeds(args.seeds),
        output_dir=output_dir,
        bounds_config=args.bounds_config,
        config_path=args.config,
    )
    print(summaries.to_string(index=False))
    print(f"Convergence diagnostic output: {output_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
