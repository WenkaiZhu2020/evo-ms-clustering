#!/usr/bin/env python3
"""Select Stage 2 operating solutions from frozen Pareto fronts.

This is a read-only post-hoc analysis of the saved formal Stage 2 fronts.  It
does not invoke NSGA-II, rebuild graphs, or mutate any scientific input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SUBJECTS = ("daytrader", "jpetstore", "xerces-j")
SEEDS = tuple(range(30))
BUDGETS = (0.000, 0.005, 0.010, 0.025, 0.050, 0.100, 0.150, 0.200)
CANONICAL_BUDGET = 0.050
CLASS_COUNTS = {"daytrader": 53, "jpetstore": 24, "xerces-j": 814}
TOL = 1e-12


def source_dir(subject: str, seed: int) -> Path:
    return ROOT / "results" / subject / "03_stage2_nsga" / "robustness_final_30seeds" / f"seed_{seed:02d}"


def select(frame: pd.DataFrame, budget: float) -> tuple[pd.Series, float, int]:
    feasible = frame.loc[frame["feasible"].astype(bool)].copy()
    if feasible.empty:
        feasible = frame.copy()
    q_max = float(feasible["weighted_modularity"].max())
    if abs(q_max) <= TOL:
        feasible["modularity_loss"] = q_max - feasible["weighted_modularity"]
    else:
        feasible["modularity_loss"] = (q_max - feasible["weighted_modularity"]) / abs(q_max)
    eligible = feasible.loc[feasible["modularity_loss"] <= budget + TOL].copy()
    if eligible.empty:
        raise ValueError(f"no candidate in {budget:.3f} modularity band")
    eligible = eligible.sort_values(
        ["imbalance", "weighted_modularity", "coupling", "solution_id"],
        ascending=[True, False, True, True],
        kind="stable",
    )
    return eligible.iloc[0], q_max, int(len(eligible))


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results/cross_subject/03_stage2_nsga/modularity_band",
    )
    args = parser.parse_args()

    profile_rows: list[dict] = []
    source_rows: list[dict] = []
    for subject in SUBJECTS:
        for seed in SEEDS:
            front_path = source_dir(subject, seed) / "pareto_front.csv"
            if not front_path.is_file():
                raise FileNotFoundError(front_path)
            frame = pd.read_csv(front_path)
            required = {"subject", "seed", "solution_id", "feasible", "weighted_modularity", "imbalance", "coupling", "cohesion", "label_vector"}
            missing = required - set(frame.columns)
            if missing:
                raise ValueError(f"{front_path}: missing columns {sorted(missing)}")
            if len(json.loads(frame.iloc[0]["label_vector"])) != CLASS_COUNTS[subject]:
                raise ValueError(f"{front_path}: label vector length mismatch")
            source_rows.append({
                "subject": subject,
                "seed": seed,
                "source_front": str(front_path.relative_to(ROOT)),
                "source_front_sha256": hash_file(front_path),
                "source_front_rows": len(frame),
            })
            for budget in BUDGETS:
                selected, q_max, eligible_count = select(frame, budget)
                profile_rows.append({
                    "subject": subject,
                    "seed": seed,
                    "budget": budget,
                    "selection_rule": "minimum_imbalance_within_relative_modularity_band",
                    "solution_id": selected["solution_id"],
                    "weighted_modularity": float(selected["weighted_modularity"]),
                    "modularity_max_in_feasible_front": q_max,
                    "realised_modularity_loss": float(selected["modularity_loss"]),
                    "eligible_candidate_count": eligible_count,
                    "coupling": float(selected["coupling"]),
                    "cohesion": float(selected["cohesion"]),
                    "imbalance": float(selected["imbalance"]),
                    "cluster_count": int(selected["cluster_count"]),
                    "max_cluster_ratio": float(selected["max_cluster_ratio"]),
                    "singleton_ratio": float(selected["singleton_ratio"]),
                    "label_vector": selected["label_vector"],
                })

    profiles = pd.DataFrame(profile_rows).sort_values(["subject", "seed", "budget"], kind="stable")
    canonical = profiles.loc[profiles["budget"] == CANONICAL_BUDGET].copy()
    canonical.insert(3, "canonical_operating_profile", True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    profiles.to_csv(args.output_dir / "profiles_per_seed.csv", index=False)
    canonical.to_csv(args.output_dir / "canonical_operating_solution_per_seed.csv", index=False)
    profiles.groupby(["subject", "budget"], as_index=False).agg(
        seed_count=("seed", "count"),
        median_realised_modularity_loss=("realised_modularity_loss", "median"),
        mean_realised_modularity_loss=("realised_modularity_loss", "mean"),
        median_imbalance=("imbalance", "median"),
        median_coupling=("coupling", "median"),
        median_cohesion=("cohesion", "median"),
        median_cluster_count=("cluster_count", "median"),
        median_max_cluster_ratio=("max_cluster_ratio", "median"),
        distinct_solution_count=("solution_id", "nunique"),
    ).to_csv(args.output_dir / "profiles_summary.csv", index=False)
    pd.DataFrame(source_rows).to_csv(args.output_dir / "source_front_inventory.csv", index=False)
    (args.output_dir / "analysis_manifest.json").write_text(json.dumps({
        "analysis": "stage2_raw_structure_only_modularity_band",
        "branch": "stage2-nsga",
        "subjects": list(SUBJECTS),
        "seeds": list(SEEDS),
        "budgets": list(BUDGETS),
        "canonical_budget": CANONICAL_BUDGET,
        "band_definition": "relative loss from the maximum weighted modularity among feasible rows in each saved Pareto front",
        "selection_rule": "minimum imbalance, then maximum weighted modularity, then minimum coupling, then solution_id",
        "source_policy": "saved formal Stage 2 robustness Pareto fronts only",
        "no_optimizer_run": True,
        "no_graphs_regenerated": True,
        "no_pareto_fronts_regenerated": True,
        "no_seed_rerun": True,
        "no_reference_mapping_regenerated": True,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
