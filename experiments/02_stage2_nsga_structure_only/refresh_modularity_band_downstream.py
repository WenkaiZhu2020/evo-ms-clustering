#!/usr/bin/env python3
"""Refresh Stage 2 downstream tables from the frozen modularity-band profile.

This command performs post-hoc evaluation only.  It reads the saved final
Pareto fronts and long-form label mappings, plus the existing raw Stage 2
inputs and frozen Stage 1 baseline.  It never calls the optimizer and never
writes into a seed directory.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.repository_layout import stage2_subject_root

SUBJECTS = ("jpetstore", "daytrader", "xerces-j")
SEEDS = tuple(range(30))
CANONICAL_SOURCE = Path(
    "results/stage2/cross_subject/operating_profile/"
    "canonical_operating_solution_per_seed.csv"
)
SELECTOR_CONTRACT_ID = "stage2-raw-structure-only-modularity-band-v1"
SELECTOR_CONTRACT = (
    "feasible retained Pareto candidates; fallback to all retained candidates "
    "only when feasible is empty; 5% relative weighted-modularity-loss band "
    "with 1e-12 tolerance; minimum imbalance; maximum weighted modularity; "
    "minimum coupling; solution_id; canonical label tuple"
)


def _load_robustness_module():
    path = ROOT / "experiments/02_stage2_nsga_structure_only/run_robustness.py"
    spec = importlib.util.spec_from_file_location("stage2_refresh_robustness", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_row(canonical: pd.DataFrame, subject: str, seed: int) -> dict[str, Any]:
    rows = canonical.loc[(canonical["subject"] == subject) & (canonical["seed"] == seed)]
    if len(rows) != 1:
        raise ValueError(f"expected one canonical row for {subject}/{seed}, got {len(rows)}")
    return rows.iloc[0].to_dict()


def _selected_clusters(stage2, context: dict[str, Any], labels_path: Path, solution_id: str) -> pd.DataFrame:
    labels = pd.read_csv(labels_path, compression="xz")
    selected = labels.loc[labels["solution_id"].astype(str) == solution_id].copy()
    if selected.empty:
        raise ValueError(f"missing frozen labels for {labels_path}: {solution_id}")
    return stage2._align_clusters(context["class_nodes"], selected)


def _posthoc_profile(
    robustness,
    context: dict[str, Any],
    subject: str,
    seed: int,
    front_row: dict[str, Any],
    clusters: pd.DataFrame,
) -> dict[str, Any]:
    cluster_by_class = robustness.encoding.to_cluster_by_class(
        clusters["cluster_id"].to_numpy(dtype=int), context["class_nodes"]
    )
    metrics = robustness.stage2._partition_metrics_row(
        subject=subject,
        seed=seed,
        solution_id=str(front_row["solution_id"]),
        class_nodes=context["class_nodes"],
        clusters=clusters,
        raw_edges=context["raw_edges"],
        cluster_by_class=cluster_by_class,
        reference_mapping=context["reference_mapping"],
    )
    coupling, cohesion, imbalance = robustness.stage2.evaluate_structural_objectives(
        context["raw_edges"], cluster_by_class, robustness.stage2.RAW_WEIGHT_COLUMN
    )
    metrics.update({
        "coupling": float(coupling),
        "cohesion": float(cohesion),
        "imbalance": float(imbalance),
        "feasible": bool(front_row["feasible"]),
        "is_injected_seed": bool(front_row.get("is_injected_seed", False)),
        "injected_seed_name": str(front_row.get("injected_seed_name", "")),
        "injected_seed_category": str(front_row.get("injected_seed_category", "")),
    })
    return metrics


def _refresh_raw_run(
    base: dict[str, Any],
    profile: dict[str, Any],
    front_row: dict[str, Any],
    provenance: dict[str, str],
    used_infeasible_fallback: bool,
    selected_equals_leiden: bool,
) -> dict[str, Any]:
    row = dict(base)
    replacements = {
        "solution_id": profile["solution_id"],
        "coupling": profile["coupling"],
        "cohesion": profile["cohesion"],
        "imbalance": profile["imbalance"],
        "weighted_modularity": profile["weighted_modularity"],
        "internal_edge_weight_ratio": profile["internal_edge_weight_ratio"],
        "internal_external_edge_ratio": profile["internal_external_edge_ratio"],
        "cluster_count": profile["cluster_count"],
        "average_cluster_size": profile["average_cluster_size"],
        "maximum_cluster_size": profile["max_cluster_size"],
        "minimum_cluster_size": profile["min_cluster_size"],
        "max_cluster_ratio": profile["max_cluster_ratio"],
        "singleton_ratio": profile["singleton_ratio"],
        "selected_equals_leiden": selected_equals_leiden,
        "selected_is_injected_seed": bool(front_row.get("is_injected_seed", False)),
        "selected_seed_name": str(front_row.get("injected_seed_name", "")),
        "used_infeasible_fallback": used_infeasible_fallback,
    }
    for key in (
        "mojofm_vs_reference",
        "pairwise_precision",
        "pairwise_recall",
        "pairwise_f1",
        "ari_vs_reference",
        "nmi_vs_reference",
        "reference_coverage_ratio",
    ):
        if key in profile:
            replacements[key] = profile[key]
    row.update(replacements)
    row.update(provenance)
    return row


def _profile_provenance(
    canonical_path: Path,
    front_path: Path,
    labels_path: Path,
    command: str,
) -> dict[str, str]:
    return {
        "selector_contract_id": SELECTOR_CONTRACT_ID,
        "selector_contract": SELECTOR_CONTRACT,
        "canonical_source_path": str(CANONICAL_SOURCE),
        "canonical_source_sha256": _sha256(canonical_path),
        "source_front_path": str(front_path.relative_to(ROOT)),
        "source_front_sha256": _sha256(front_path),
        "source_candidate_label_path": str(labels_path.relative_to(ROOT)),
        "source_candidate_label_sha256": _sha256(labels_path),
        "refresh_command": command,
        "posthoc_status": "recomputed_from_frozen_front_and_labels",
    }


def refresh(output_root: Path, command: str) -> dict[str, Any]:
    robustness = _load_robustness_module()
    canonical_path = ROOT / CANONICAL_SOURCE
    canonical = pd.read_csv(canonical_path)
    expected = {(subject, seed) for subject in SUBJECTS for seed in SEEDS}
    observed = set(zip(canonical["subject"], canonical["seed"], strict=False))
    if observed != expected:
        raise ValueError("canonical profile does not contain exactly the 90 subject/seed rows")

    all_profiles: list[dict[str, Any]] = []
    raw_rows: dict[str, list[dict[str, Any]]] = {subject: [] for subject in SUBJECTS}
    stage1_rows: dict[str, dict[str, Any]] = {}
    manifest_rows: list[dict[str, Any]] = []
    config_path = ROOT / "configs/experiments/02_stage2_nsga_structure_only.yml"

    for subject in SUBJECTS:
        context = robustness._load_context(subject, config_path)
        final_dir = stage2_subject_root(subject, ROOT) / "robustness_final_30seeds"
        existing_raw = pd.read_csv(final_dir / "raw_runs.csv").set_index("seed")
        baseline = context["stage1_raw_baseline"]
        baseline_key = robustness.stage2._label_key(
            baseline["cluster_id"].to_numpy(dtype=int)
        )
        for seed in SEEDS:
            canonical_row = _canonical_row(canonical, subject, seed)
            seed_dir = final_dir / f"seed_{seed:02d}"
            front_path = seed_dir / "pareto_front.csv"
            labels_path = seed_dir / "pareto_labels.csv.xz"
            front = pd.read_csv(front_path)
            front_match = front.loc[
                front["solution_id"].astype(str) == str(canonical_row["solution_id"])
            ]
            if len(front_match) != 1:
                raise ValueError(f"canonical ID is not unique in {front_path}")
            front_row = front_match.iloc[0].to_dict()
            clusters = _selected_clusters(
                robustness.stage2, context, labels_path, str(canonical_row["solution_id"])
            )
            profile = _posthoc_profile(
                robustness, context, subject, seed, front_row, clusters
            )
            if abs(float(profile["weighted_modularity"]) - float(canonical_row["weighted_modularity"])) > 1e-12:
                raise ValueError(f"weighted modularity mismatch for {subject}/{seed}")
            profile.update({
                "subject": subject,
                "seed": seed,
                "budget": float(canonical_row["budget"]),
                "canonical_operating_profile": True,
                "selection_rule": canonical_row["selection_rule"],
                "modularity_max_in_feasible_front": canonical_row["modularity_max_in_feasible_front"],
                "realised_modularity_loss": canonical_row["realised_modularity_loss"],
                "eligible_candidate_count": int(canonical_row["eligible_candidate_count"]),
                "label_vector": canonical_row["label_vector"],
            })
            provenance = _profile_provenance(canonical_path, front_path, labels_path, command)
            profile.update(provenance)
            all_profiles.append(profile)

            selected_key = robustness.stage2._label_key(
                clusters["cluster_id"].to_numpy(dtype=int)
            )
            selected_equals_leiden = selected_key == baseline_key
            if seed not in existing_raw.index:
                raise ValueError(f"missing raw_runs row for {subject}/{seed}")
            refreshed_raw = _refresh_raw_run(
                existing_raw.loc[seed].to_dict(),
                profile,
                front_row,
                provenance,
                used_infeasible_fallback=not bool(front["feasible"].astype(bool).any()),
                selected_equals_leiden=selected_equals_leiden,
            )
            refreshed_raw.update({"subject": subject, "seed": seed})
            raw_rows[subject].append(refreshed_raw)

            if seed == 0:
                selected_solution = {
                    **front_row,
                    "selection_rule": "minimum_imbalance_within_5_percent_relative_modularity_band",
                }
                stage1_rows[subject] = robustness.stage2._stage1_vs_stage2_summary(
                    subject=subject,
                    class_nodes=context["class_nodes"],
                    raw_edges=context["raw_edges"],
                    stage1_raw_baseline=baseline,
                    selected_clusters=clusters,
                    selected_solution=selected_solution,
                    pareto_front_size=len(front),
                    population_size=100,
                    generations=100,
                )
                stage1_rows[subject].update(provenance)

            manifest_rows.append({
                "subject": subject,
                "seed": seed,
                "canonical_solution_id": canonical_row["solution_id"],
                "source_front_path": str(front_path.relative_to(ROOT)),
                "source_front_sha256": _sha256(front_path),
                "source_candidate_label_path": str(labels_path.relative_to(ROOT)),
                "source_candidate_label_sha256": _sha256(labels_path),
            })

    output_modularity = output_root / "results/stage2/cross_subject/operating_profile"
    output_modularity.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_profiles).sort_values(["subject", "seed"]).to_csv(
        output_modularity / "canonical_operating_profile_metrics_per_seed.csv", index=False
    )
    for subject in SUBJECTS:
        out_final = stage2_subject_root(subject, output_root) / "robustness_final_30seeds"
        out_final.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(raw_rows[subject]).sort_values("seed").to_csv(
            out_final / "raw_runs.csv", index=False
        )
        out_raw = stage2_subject_root(subject, output_root) / "raw"
        out_raw.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([stage1_rows[subject]]).to_csv(
            out_raw / "stage1_vs_stage2.csv", index=False
        )

    manifest = {
        "analysis": "stage2_modularity_band_downstream_refresh",
        "selector_contract_id": SELECTOR_CONTRACT_ID,
        "selector_contract": SELECTOR_CONTRACT,
        "canonical_source_path": str(CANONICAL_SOURCE),
        "canonical_source_sha256": _sha256(canonical_path),
        "subjects": list(SUBJECTS),
        "seeds": list(SEEDS),
        "posthoc_status": "recomputed_from_frozen_front_and_labels",
        "no_optimizer_run": True,
        "no_seed_rerun": True,
        "no_graph_files_regenerated": True,
        "no_pareto_fronts_regenerated": True,
        "no_reference_mapping_regenerated": True,
        "source_inventory": manifest_rows,
    }
    (output_modularity / "downstream_refresh_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT,
        help="write refreshed derived outputs below this root (use /tmp first)",
    )
    args = parser.parse_args()
    command = "python experiments/02_stage2_nsga_structure_only/refresh_modularity_band_downstream.py"
    manifest = refresh(args.output_root.resolve(), command)
    print(json.dumps({
        "output_root": str(args.output_root.resolve()),
        "profiles": 90,
        "subjects": manifest["subjects"],
        "no_optimizer_run": manifest["no_optimizer_run"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
