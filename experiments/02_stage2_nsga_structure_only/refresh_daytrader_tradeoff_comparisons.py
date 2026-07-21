#!/usr/bin/env python3
"""Refresh selected-dependent DayTrader Stage 2 comparison tables."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata, wilcoxon


ROOT = Path(__file__).resolve().parents[2]
SELECTOR_CONTRACT_ID = "stage2-raw-structure-only-modularity-band-v1"
SELECTOR_CONTRACT = (
    "feasible retained Pareto candidates; fallback to all retained candidates "
    "only when feasible is empty; 5% relative weighted-modularity-loss band "
    "with 1e-12 tolerance; minimum imbalance; maximum weighted modularity; "
    "minimum coupling; solution_id; canonical label tuple"
)
METRICS = ("weighted_modularity", "coupling", "cohesion")
CALIPERS = (0.01, 0.025, 0.05, 0.1)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _match_row(stage2: pd.Series, candidates: pd.DataFrame, scope: str) -> dict:
    if scope == "same_seed":
        candidates = candidates.loc[candidates["seed"] == int(stage2["seed"])]
    elif scope == "same_seed_cluster_count_delta_le_1":
        candidates = candidates.loc[
            (candidates["seed"] == int(stage2["seed"]))
            & (candidates["cluster_count"] - float(stage2["cluster_count"])).abs().le(1)
        ]
    elif scope != "pooled":
        raise ValueError(f"unknown matching scope: {scope}")
    candidates = candidates.copy()
    if candidates.empty:
        return {
            "stage2_seed": int(stage2["seed"]),
            "matching_scope": scope,
            "match_found": False,
        }
    candidates["imbalance_gap"] = (
        candidates["imbalance"] - float(stage2["imbalance"])
    ).abs()
    chosen = candidates.sort_values(
        ["imbalance_gap", "seed", "resolution"],
        ascending=[True, True, True],
        kind="stable",
    ).iloc[0]
    return {
        "stage2_seed": int(stage2["seed"]),
        "matching_scope": scope,
        "match_found": True,
        "stage2_solution_id": stage2["solution_id"],
        "stage2_imbalance": float(stage2["imbalance"]),
        "stage2_weighted_modularity": float(stage2["weighted_modularity"]),
        "stage2_coupling": float(stage2["coupling"]),
        "stage2_cohesion": float(stage2["cohesion"]),
        "stage2_cluster_count": int(stage2["cluster_count"]),
        "leiden_seed": int(chosen["seed"]),
        "leiden_resolution": float(chosen["resolution"]),
        "leiden_imbalance": float(chosen["imbalance"]),
        "leiden_weighted_modularity": float(chosen["weighted_modularity"]),
        "leiden_coupling": float(chosen["coupling"]),
        "leiden_cohesion": float(chosen["cohesion"]),
        "leiden_cluster_count": int(chosen["cluster_count"]),
        "imbalance_gap": float(chosen["imbalance_gap"]),
        "cluster_count_difference": float(
            float(stage2["cluster_count"]) - float(chosen["cluster_count"])
        ),
        "stage2_minus_leiden_modularity": float(
            stage2["weighted_modularity"] - chosen["weighted_modularity"]
        ),
        "stage2_minus_leiden_coupling": float(
            stage2["coupling"] - chosen["coupling"]
        ),
        "stage2_minus_leiden_cohesion": float(
            stage2["cohesion"] - chosen["cohesion"]
        ),
    }


def _oriented_delta(row: pd.Series, metric: str) -> float:
    raw = float(row[f"stage2_{metric}"] - row[f"leiden_{metric}"])
    return -raw if metric == "coupling" else raw


def _rank_biserial(values: np.ndarray) -> float:
    nonzero = values[~np.isclose(values, 0.0)]
    if len(nonzero) == 0:
        return float("nan")
    ranks = rankdata(np.abs(nonzero))
    return float((ranks[nonzero > 0].sum() - ranks[nonzero < 0].sum()) / ranks.sum())


def _pairwise_rows(matches: pd.DataFrame, scope: str, caliper: float) -> list[dict]:
    usable = matches.loc[
        matches["match_found"].astype(bool)
        & matches["imbalance_gap"].le(caliper + 1e-12)
    ].copy()
    rows = []
    for metric in METRICS:
        raw = usable[f"stage2_{metric}"] - usable[f"leiden_{metric}"]
        oriented = np.asarray([_oriented_delta(row, metric) for _, row in usable.iterrows()])
        ties = np.isclose(oriented, 0.0)
        nonzero = np.where(ties, 0.0, oriented)
        n_nonzero = int(np.count_nonzero(nonzero))
        if n_nonzero <= 1:
            statistic = p_value = float("nan")
        else:
            result = wilcoxon(nonzero, alternative="two-sided", method="auto")
            statistic, p_value = float(result.statistic), float(result.pvalue)
        rows.append({
            "matching_scope": scope,
            "caliper": caliper,
            "metric": metric,
            "n_pairs": int(len(usable)),
            "stage2_wins": int(np.sum(nonzero > 0)),
            "ties": int(np.sum(ties)),
            "stage2_losses": int(np.sum(nonzero < 0)),
            "mean_stage2_minus_leiden_raw": float(raw.mean()) if len(raw) else float("nan"),
            "median_stage2_minus_leiden_raw": float(raw.median()) if len(raw) else float("nan"),
            "wilcoxon_statistic": statistic,
            "wilcoxon_p_two_sided": p_value,
            "rank_biserial": _rank_biserial(nonzero),
            "n_nonzero_pairs": n_nonzero,
        })
    return rows


def refresh(output_dir: Path, selected_profile: Path) -> None:
    selected = pd.read_csv(selected_profile)
    selected = selected.loc[selected["subject"] == "daytrader"].sort_values("seed")
    leiden = pd.read_csv(output_dir / "leiden_candidate_metrics.csv")
    leiden = leiden.loc[leiden["stage2_feasible"].astype(bool)].copy()
    provenance = {
        "selector_contract_id": SELECTOR_CONTRACT_ID,
        "selector_contract": SELECTOR_CONTRACT,
        "selected_profile_source": _display_path(selected_profile),
        "selected_profile_sha256": _sha256(selected_profile),
        "posthoc_status": "recomputed_from_frozen_front_and_labels",
    }

    scopes = ("same_seed", "pooled", "same_seed_cluster_count_delta_le_1")
    for scope in scopes:
        rows = [_match_row(row, leiden, scope) for _, row in selected.iterrows()]
        matches = pd.DataFrame(rows)
        for key, value in provenance.items():
            matches[key] = value
        filename = {
            "same_seed": "matched_imbalance_same_seed.csv",
            "pooled": "matched_imbalance_pooled.csv",
            "same_seed_cluster_count_delta_le_1": "matched_imbalance_same_seed_cluster_count_delta_le_1.csv",
        }[scope]
        matches.to_csv(output_dir / filename, index=False)

    summaries = []
    pairwise = []
    for scope in scopes:
        filename = {
            "same_seed": "matched_imbalance_same_seed.csv",
            "pooled": "matched_imbalance_pooled.csv",
            "same_seed_cluster_count_delta_le_1": "matched_imbalance_same_seed_cluster_count_delta_le_1.csv",
        }[scope]
        matches = pd.read_csv(output_dir / filename)
        for caliper in CALIPERS:
            usable = matches.loc[
                matches["match_found"].astype(bool)
                & matches["imbalance_gap"].le(caliper + 1e-12)
            ]
            summaries.append({
                "matching_scope": scope,
                "caliper": caliper,
                "usable_pairs": int(len(usable)),
                "mean_imbalance_gap": float(usable["imbalance_gap"].mean()) if len(usable) else float("nan"),
                "median_imbalance_gap": float(usable["imbalance_gap"].median()) if len(usable) else float("nan"),
                **provenance,
            })
            pairwise.extend(_pairwise_rows(matches, scope, caliper))
    pd.DataFrame(summaries).to_csv(output_dir / "matched_imbalance_caliper_summary.csv", index=False)
    pairwise_frame = pd.DataFrame(pairwise)
    for key, value in provenance.items():
        pairwise_frame[key] = value
    pairwise_frame.to_csv(output_dir / "matched_imbalance_pairwise_statistics.csv", index=False)

    structural_path = output_dir / "structural_sensitivity_per_seed.csv"
    structural = pd.read_csv(structural_path)
    selected_ids = selected.set_index("seed")["solution_id"].astype(str)
    structural["same_as_selected"] = structural.apply(
        lambda row: (
            bool(row["has_candidate"])
            and str(row["solution_id"]) == str(selected_ids.get(int(row["seed"]), ""))
        ),
        axis=1,
    )
    for key, value in provenance.items():
        structural[key] = value
    structural.to_csv(structural_path, index=False)

    try:
        candidate_source = str(
            (output_dir / "leiden_candidate_metrics.csv").relative_to(ROOT)
        )
    except ValueError:
        candidate_source = str(output_dir / "leiden_candidate_metrics.csv")
    refresh_manifest = {
        "analysis": "stage2_daytrader_tradeoff_comparison_refresh",
        **provenance,
        "source_leiden_candidate_metrics": candidate_source,
        "source_leiden_candidate_metrics_sha256": _sha256(output_dir / "leiden_candidate_metrics.csv"),
        "no_optimizer_run": True,
        "no_seed_rerun": True,
        "no_pareto_fronts_regenerated": True,
    }
    (output_dir / "canonical_profile_refresh_manifest.json").write_text(
        json.dumps(refresh_manifest, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--selected-profile",
        type=Path,
        default=ROOT / "results/cross_subject/03_stage2_nsga/modularity_band/"
        "canonical_operating_profile_metrics_per_seed.csv",
    )
    args = parser.parse_args()
    refresh(args.output_dir.resolve(), args.selected_profile.resolve())
    print(json.dumps({"output_dir": str(args.output_dir.resolve()), "status": "refreshed"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
