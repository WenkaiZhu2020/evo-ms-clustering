#!/usr/bin/env python3
"""Build descriptive operating-preference validation for supplementary subjects.

This is deterministic post-processing over frozen EasyMock and JFreeChart
Stage 2 fronts and Stage 3 projected fronts. It never pairs the unequal
cross-stage seed sets and never performs an inferential test.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
for candidate in (SRC, SCRIPT_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import build_operating_preference_analysis as primary
from evo_ms.evaluation.partition_ops import partition_metrics_row
from evo_ms.graph.raw_graph_builder import build_raw_edges
from evo_ms.optimization.semantic_objective import (
    evaluate_semantic_objective,
    load_semantic_edges,
    semantic_total_weight,
)


SUBJECTS = ("easymock", "jfreechart")
DISPLAY = {"easymock": "EasyMock", "jfreechart": "JFreeChart"}
CLASS_COUNTS = {"easymock": 105, "jfreechart": 635}
STAGE_SEEDS = {"stage2": tuple(range(10)), "stage3": tuple(range(1, 11))}
OUTPUT_RELATIVE = primary.OUTPUT_RELATIVE / "supplementary"
SCRIPT_RELATIVE = Path(
    "experiments/05_stage3_declaration_method_body/"
    "build_supplementary_operating_preference_analysis.py"
)
ANALYSIS_VERSION = "supplementary-operating-preference-analysis-v1"


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_csv(path, float_precision="round_trip")


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n", float_format="%.17g").encode()


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _inputs(subject: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, float, Path, Path, Path]:
    class_path = ROOT / "data/extracted" / subject / "class_nodes.csv"
    dependency_path = ROOT / "data/extracted" / subject / "structural_dependencies.csv"
    semantic_path = ROOT / "data/semantic_graphs/declaration_method_body" / subject / "semantic_edges.csv"
    nodes = _read_csv(class_path)
    dependencies = _read_csv(dependency_path)
    if len(nodes) != CLASS_COUNTS[subject] or nodes["class_id"].astype(str).duplicated().any():
        raise ValueError(f"{subject}: retained class universe mismatch")
    raw_edges = build_raw_edges(nodes, dependencies)
    semantic = load_semantic_edges(semantic_path, expected_class_ids=set(nodes["class_id"].astype(str)))
    return nodes, raw_edges, semantic, semantic_total_weight(semantic), class_path, dependency_path, semantic_path


def _stage2_candidates(source_paths: set[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    validation: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        nodes, _raw, semantic, total, class_path, dependency_path, semantic_path = _inputs(subject)
        source_paths.update({class_path, dependency_path, semantic_path})
        class_order = nodes["class_id"].astype(str).tolist()
        for seed in STAGE_SEEDS["stage2"]:
            run = ROOT / "results" / subject / "03_stage2_nsga/robustness" / f"seed_{seed:02d}"
            front_path, labels_path, metrics_path = run / "pareto_front.csv", run / "pareto_labels.csv.xz", run / "run_metrics.json"
            source_paths.update({front_path, labels_path, metrics_path})
            front, labels = _read_csv(front_path), _read_csv(labels_path)
            if len(front) != 100 or front["solution_id"].astype(str).duplicated().any():
                raise ValueError(f"{subject}/stage2/{seed}: invalid saved front")
            mappings: dict[str, dict[str, int]] = {}
            for solution_id, group in labels.groupby("solution_id", sort=False):
                mapping = dict(zip(group["class_id"].astype(str), group["cluster_id"].astype(int), strict=True))
                if len(group) != len(nodes) or set(mapping) != set(class_order):
                    raise ValueError(f"{subject}/stage2/{seed}/{solution_id}: label scope mismatch")
                mappings[str(solution_id)] = mapping
            if set(mappings) != set(front["solution_id"].astype(str)):
                raise ValueError(f"{subject}/stage2/{seed}: front/labels mismatch")
            for index, record in enumerate(front.to_dict("records")):
                solution_id = str(record["solution_id"])
                vector = primary._labels(record["label_vector"])
                if vector != [mappings[solution_id][item] for item in class_order]:
                    raise ValueError(f"{subject}/stage2/{seed}/{solution_id}: vector mismatch")
                rows.append({
                    "subject": subject, "seed": seed, "stage": "stage2", "solution_id": solution_id,
                    "source_solution_id": solution_id, "source_front_row_index_zero_based": index,
                    "stage3_original_four_objective_row_index_zero_based": np.nan,
                    "weighted_modularity": float(record["weighted_modularity"]), "coupling": float(record["coupling"]),
                    "cohesion": float(record["cohesion"]), "imbalance": float(record["imbalance"]),
                    "f_semantic": float(evaluate_semantic_objective(semantic, mappings[solution_id], total_weight=total)),
                    "cluster_count": int(record["cluster_count"]), "max_cluster_ratio": float(record["max_cluster_ratio"]),
                    "singleton_ratio": float(record["singleton_ratio"]), "feasible": primary._as_bool(record["feasible"]),
                    "label_vector": json.dumps(vector, separators=(",", ":")),
                    "canonical_partition_sha256": primary._partition_hash(nodes, vector),
                    "source_front": _relative(front_path), "source_front_sha256": _sha256(front_path),
                    "source_labels": _relative(labels_path), "source_labels_sha256": _sha256(labels_path),
                    "semantic_graph": _relative(semantic_path), "semantic_graph_sha256": _sha256(semantic_path),
                    "semantic_total_weight": total,
                })
            retained = json.loads(metrics_path.read_text())
            match = next(row for row in rows if row["subject"] == subject and row["seed"] == seed and row["stage"] == "stage2" and row["solution_id"] == str(retained["solution_id"]))
            errors = [abs(float(match[key]) - float(retained[key])) for key in ("weighted_modularity", "coupling", "cohesion", "imbalance", "max_cluster_ratio", "singleton_ratio")]
            if max(errors) > primary.TOL or int(match["cluster_count"]) != int(retained["cluster_count"]):
                raise ValueError(f"{subject}/stage2/{seed}: retained structural cross-check failed")
            validation.append({
                "subject": subject, "seed": seed, "candidate_count": len(front),
                "status": "NEWLY_COMPUTED_FROM_FROZEN_PARTITIONS", "retained_fsemantic_reference_available": False,
                "retained_structural_reference_solution_id": retained["solution_id"],
                "retained_structural_crosscheck_max_abs_error": max(errors), "passed": True,
            })
    return pd.DataFrame(rows), pd.DataFrame(validation)


def _stage3_candidates(source_paths: set[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    validation: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        nodes, raw_edges, _semantic, _total, class_path, dependency_path, semantic_path = _inputs(subject)
        source_paths.update({class_path, dependency_path, semantic_path})
        class_order = nodes["class_id"].astype(str).tolist()
        for seed in STAGE_SEEDS["stage3"]:
            run = ROOT / "results/stage3/subjects" / subject / "declaration_method_body/formal" / f"seed_{seed:02d}"
            projected_path, four_path = run / "projected_front_3d.csv", run / "pareto_front_4d.csv"
            labels_path, historical_path = run / "partition_labels.csv", run / "selected_solution.json"
            source_paths.update({projected_path, four_path, labels_path, historical_path})
            projected, four, labels = _read_csv(projected_path), _read_csv(four_path), _read_csv(labels_path)
            if projected["solution_id"].astype(str).duplicated().any():
                raise ValueError(f"{subject}/stage3/{seed}: duplicate projected solution")
            four_by_id = {str(row["solution_id"]): row for row in four.to_dict("records")}
            labels_by_id = {str(key): group for key, group in labels.groupby("solution_id", sort=False)}
            for index, record in enumerate(projected.to_dict("records")):
                solution_id, original_id = str(record["solution_id"]), str(record["original_solution_id"])
                if original_id not in four_by_id or solution_id not in labels_by_id:
                    raise ValueError(f"{subject}/stage3/{seed}/{solution_id}: projected mapping missing")
                group = labels_by_id[solution_id]
                mapping = dict(zip(group["class_id"].astype(str), group["cluster_id"].astype(int), strict=True))
                if len(group) != len(nodes) or set(mapping) != set(class_order):
                    raise ValueError(f"{subject}/stage3/{seed}/{solution_id}: label scope mismatch")
                vector = primary._labels(record["label_vector"])
                if vector != [mapping[item] for item in class_order]:
                    raise ValueError(f"{subject}/stage3/{seed}/{solution_id}: vector mismatch")
                clusters = pd.DataFrame({"class_id": class_order, "class_name": nodes["class_name"].astype(str), "cluster_id": vector})
                posthoc = partition_metrics_row(subject, seed, solution_id, nodes, clusters, raw_edges, mapping)
                semantic = float(record["original_f_semantic"])
                if abs(semantic - float(four_by_id[original_id]["f_semantic"])) > primary.TOL:
                    raise ValueError(f"{subject}/stage3/{seed}/{solution_id}: semantic mismatch")
                rows.append({
                    "subject": subject, "seed": seed, "stage": "stage3", "solution_id": solution_id,
                    "source_solution_id": original_id, "source_front_row_index_zero_based": index,
                    "stage3_original_four_objective_row_index_zero_based": list(four["solution_id"].astype(str)).index(original_id),
                    "weighted_modularity": float(posthoc["weighted_modularity"]), "coupling": float(record["coupling"]),
                    "cohesion": float(record["cohesion"]), "imbalance": float(record["imbalance"]), "f_semantic": semantic,
                    "cluster_count": int(posthoc["cluster_count"]), "max_cluster_ratio": float(posthoc["max_cluster_ratio"]),
                    "singleton_ratio": float(posthoc["singleton_ratio"]), "feasible": primary._as_bool(record["feasible"]),
                    "label_vector": json.dumps(vector, separators=(",", ":")),
                    "canonical_partition_sha256": primary._partition_hash(nodes, vector),
                    "source_front": _relative(projected_path), "source_front_sha256": _sha256(projected_path),
                    "source_labels": _relative(labels_path), "source_labels_sha256": _sha256(labels_path),
                    "semantic_graph": _relative(semantic_path), "semantic_graph_sha256": _sha256(semantic_path),
                    "semantic_total_weight": np.nan,
                })
            retained = json.loads(historical_path.read_text())["selected_posthoc_metrics"]
            match = next(row for row in rows if row["subject"] == subject and row["seed"] == seed and row["stage"] == "stage3" and row["solution_id"] == str(retained["solution_id"]))
            keys = ("weighted_modularity", "max_cluster_ratio", "singleton_ratio")
            errors = [abs(float(match[key]) - float(retained[key])) for key in keys]
            if max(errors) > primary.TOL or int(match["cluster_count"]) != int(retained["cluster_count"]):
                raise ValueError(f"{subject}/stage3/{seed}: retained posthoc cross-check failed")
            validation.append({"subject": subject, "seed": seed, "projected_candidate_count": len(projected), "retained_posthoc_solution_id": retained["solution_id"], "max_abs_error": max(errors), "passed": True})
    return pd.DataFrame(rows), pd.DataFrame(validation)


def _materialise(candidates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_rows: list[dict[str, Any]] = []
    bands: list[dict[str, Any]] = []
    for (subject, stage, seed), group in candidates.groupby(["subject", "stage", "seed"], sort=False):
        feasible = group.loc[group["feasible"].map(primary._as_bool)].copy()
        q_best = float(feasible["weighted_modularity"].max())
        feasible["relative_modularity_loss"] = (q_best - feasible["weighted_modularity"].astype(float)) / abs(q_best)
        band = feasible.loc[feasible["relative_modularity_loss"] <= 0.05 + primary.TOL].copy()
        if q_best <= 0 or band.empty:
            raise ValueError(f"{subject}/{stage}/{seed}: invalid 5% band")
        chosen: dict[str, Mapping[str, Any]] = {}
        for profile in primary.PROFILES:
            pool = feasible.to_dict("records") if profile == "MODULARITY_ANCHOR" else band.to_dict("records")
            first = min(pool, key=lambda row: primary._ordering(profile, row))
            second = min(pool, key=lambda row: primary._ordering(profile, row))
            if first["solution_id"] != second["solution_id"]:
                raise ValueError("selector is not deterministic")
            chosen[profile] = first
        hashes = {profile: str(row["canonical_partition_sha256"]) for profile, row in chosen.items()}
        for profile, row in chosen.items():
            loss = (q_best - float(row["weighted_modularity"])) / abs(q_best)
            selected_rows.append({
                "subject": subject, "stage": stage, "seed": int(seed), "profile": profile,
                "profile_id": primary.SELECTOR_DEFINITIONS[profile]["profile_id"],
                "selected_solution_id": row["solution_id"], "source_front": row["source_front"], "Q_best": q_best,
                "weighted_modularity": float(row["weighted_modularity"]), "relative_modularity_loss": loss,
                "band_size": len(band), "band_size_is_one": len(band) == 1,
                "coupling": float(row["coupling"]), "cohesion": float(row["cohesion"]), "imbalance": float(row["imbalance"]),
                "f_semantic": float(row["f_semantic"]), "cluster_count": int(row["cluster_count"]),
                "max_cluster_ratio": float(row["max_cluster_ratio"]), "singleton_ratio": float(row["singleton_ratio"]),
                "feasible": primary._as_bool(row["feasible"]), "partition_hash": row["canonical_partition_sha256"],
                "canonical_partition_sha256": row["canonical_partition_sha256"],
                "balance_equals_semantic": hashes["BALANCE"] == hashes["SEMANTIC"],
                "balance_equals_coupling": hashes["BALANCE"] == hashes["COUPLING"],
                "balance_equals_cohesion": hashes["BALANCE"] == hashes["COHESION"],
                "label_vector": row["label_vector"],
            })
        bands.extend(band.to_dict("records"))
    selected = pd.DataFrame(selected_rows).sort_values(["subject", "stage", "seed", "profile_id"], kind="stable").reset_index(drop=True)
    if len(selected) != 200:
        raise ValueError(f"expected 200 supplementary profile rows, got {len(selected)}")
    return selected, pd.DataFrame(bands)


def _quantiles(values: pd.Series) -> tuple[float, float, float, float]:
    array = values.to_numpy(dtype=float)
    q1, q3 = np.quantile(array, [0.25, 0.75])
    return float(np.median(array)), float(q1), float(q3), float(q3 - q1)


def _profile_summary(selected: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metrics = ("weighted_modularity", "relative_modularity_loss", "coupling", "cohesion", "imbalance", "f_semantic", "cluster_count", "band_size")
    for (subject, stage, profile), group in selected.groupby(["subject", "stage", "profile"], sort=False):
        row: dict[str, Any] = {"subject": subject, "stage": stage, "profile": profile, "profile_id": primary.SELECTOR_DEFINITIONS[profile]["profile_id"], "n_runs": len(group)}
        for metric in metrics:
            row[f"median_{metric}"] = float(np.median(group[metric].to_numpy(dtype=float)))
        for metric in ("cohesion", "imbalance", "f_semantic", "band_size"):
            _median, q1, q3, iqr = _quantiles(group[metric]); row[f"q1_{metric}"] = q1; row[f"q3_{metric}"] = q3; row[f"iqr_{metric}"] = iqr
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["subject", "stage", "profile_id"]).reset_index(drop=True)


def _preference_deltas(selected: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for subject in SUBJECTS:
        for stage in ("stage2", "stage3"):
            base = selected.loc[(selected.subject == subject) & (selected.stage == stage) & (selected.profile == "BALANCE")].set_index("seed")
            for alternative in ("MODULARITY_ANCHOR", "COUPLING", "COHESION", "SEMANTIC"):
                other = selected.loc[(selected.subject == subject) & (selected.stage == stage) & (selected.profile == alternative)].set_index("seed")
                similarities = [
                    primary._similarity(
                        primary._labels(base.loc[seed, "label_vector"]),
                        primary._labels(other.loc[seed, "label_vector"]),
                    )
                    for seed in STAGE_SEEDS[stage]
                ]
                same_count = int(sum(item[0] for item in similarities))
                row: dict[str, Any] = {
                    "subject": subject,
                    "stage": stage,
                    "baseline_profile": "BALANCE",
                    "alternative_profile": alternative,
                    "n_within_stage_pairs": 10,
                    "same_partition_count": same_count,
                    "different_partition_count": 10 - same_count,
                    "median_ari": float(np.median([item[1] for item in similarities])),
                    "median_nmi": float(np.median([item[2] for item in similarities])),
                    "delta_definition": "alternative minus BALANCE",
                    "analysis_status": "SUPPLEMENTARY_DESCRIPTIVE",
                }
                for metric in primary.METRICS + ("relative_modularity_loss",):
                    row[f"balance_median_{metric}"] = float(np.median(base[metric]))
                    row[f"alternative_median_{metric}"] = float(np.median(other[metric]))
                    row[f"median_delta_{metric}"] = float(np.median([primary._snapped_delta(base.loc[seed], other.loc[seed], metric)[1] for seed in STAGE_SEEDS[stage]]))
                rows.append(row)
    return pd.DataFrame(rows)


def _balance_semantic(selected: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for subject in SUBJECTS:
        for stage in ("stage2", "stage3"):
            balance = selected.loc[(selected.subject == subject) & (selected.stage == stage) & (selected.profile == "BALANCE")].set_index("seed")
            semantic = selected.loc[(selected.subject == subject) & (selected.stage == stage) & (selected.profile == "SEMANTIC")].set_index("seed")
            sims = [primary._similarity(primary._labels(balance.loc[seed, "label_vector"]), primary._labels(semantic.loc[seed, "label_vector"])) for seed in STAGE_SEEDS[stage]]
            row: dict[str, Any] = {"subject": subject, "stage": stage, "n_within_stage_pairs": 10, "same_partition_count": int(sum(item[0] for item in sims)), "different_partition_count": int(10 - sum(item[0] for item in sims)), "median_ari": float(np.median([item[1] for item in sims])), "median_nmi": float(np.median([item[2] for item in sims]))}
            for metric in primary.METRICS + ("relative_modularity_loss",):
                row[f"balance_median_{metric}"] = float(np.median(balance[metric])); row[f"semantic_median_{metric}"] = float(np.median(semantic[metric])); row[f"median_delta_{metric}_semantic_minus_balance"] = float(np.median([primary._snapped_delta(balance.loc[seed], semantic.loc[seed], metric)[1] for seed in STAGE_SEEDS[stage]]))
            rows.append(row)
    return pd.DataFrame(rows)


def _band_summary(selected: pd.DataFrame) -> pd.DataFrame:
    balance = selected.loc[selected.profile == "BALANCE"]
    rows = []
    for (subject, stage), group in balance.groupby(["subject", "stage"], sort=False):
        median, q1, q3, iqr = _quantiles(group.band_size)
        rows.append({"subject": subject, "stage": stage, "n_runs": 10, "median_band_size": median, "q1_band_size": q1, "q3_band_size": q3, "iqr_band_size": iqr, "min_band_size": int(group.band_size.min()), "max_band_size": int(group.band_size.max()), "band_size_one_count": int((group.band_size == 1).sum())})
    return pd.DataFrame(rows)


def _five_subject_band(supplementary: pd.DataFrame) -> pd.DataFrame:
    primary_rows = _read_csv(ROOT / primary.OUTPUT_RELATIVE / "04_selected_profiles_per_seed.csv")
    primary_rows = primary_rows.loc[primary_rows.profile == "BALANCE"].copy()
    mapping = {"jpetstore": ("JPetStore", 24), "daytrader": ("DayTrader", 53), "xerces": ("Xerces-J", 814)}
    rows: dict[str, dict[str, Any]] = {}
    for subject, (display, classes) in mapping.items():
        rows[subject] = {"Subject": display, "Classes": classes, "Role": "Primary"}
        for stage in ("stage2", "stage3"):
            median, _q1, _q3, iqr = _quantiles(primary_rows.loc[(primary_rows.subject == subject) & (primary_rows.stage == stage), "band_size"])
            rows[subject][f"{stage}_median_band_size"] = median; rows[subject][f"{stage}_band_iqr"] = iqr
    for subject in SUBJECTS:
        rows[subject] = {"Subject": DISPLAY[subject], "Classes": CLASS_COUNTS[subject], "Role": "Supplementary"}
        for stage in ("stage2", "stage3"):
            item = supplementary.loc[(supplementary.subject == subject) & (supplementary.stage == stage)].iloc[0]
            rows[subject][f"{stage}_median_band_size"] = item.median_band_size; rows[subject][f"{stage}_band_iqr"] = item.iqr_band_size
    return pd.DataFrame([rows[key] for key in ("jpetstore", "daytrader", "easymock", "jfreechart", "xerces")])


def _mechanism(summary: pd.DataFrame, band: pd.DataFrame, comparison: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for subject in SUBJECTS:
        for stage in ("stage2", "stage3"):
            b = summary.loc[(summary.subject == subject) & (summary.stage == stage) & (summary.profile == "BALANCE")].iloc[0]
            s = summary.loc[(summary.subject == subject) & (summary.stage == stage) & (summary.profile == "SEMANTIC")].iloc[0]
            c = comparison.loc[(comparison.subject == subject) & (comparison.stage == stage)].iloc[0]
            bands = band.loc[(band.subject == subject) & (band.stage == stage)].iloc[0]
            rows.append({"Subject": DISPLAY[subject], "Stage": stage, "Median band size": bands.median_band_size, "BALANCE f_semantic": b.median_f_semantic, "SEMANTIC f_semantic": s.median_f_semantic, "SEMANTIC-minus-BALANCE f_semantic": c.median_delta_f_semantic_semantic_minus_balance, "BALANCE cohesion": b.median_cohesion, "SEMANTIC cohesion": s.median_cohesion, "BALANCE-minus-SEMANTIC cohesion": b.median_cohesion - s.median_cohesion, "same BALANCE/SEMANTIC partition count": c.same_partition_count, "median modularity loss under BALANCE": b.median_relative_modularity_loss, "median modularity loss under SEMANTIC": s.median_relative_modularity_loss})
    return pd.DataFrame(rows)


def build_outputs() -> tuple[dict[Path, bytes], dict[str, Any]]:
    source_paths: set[Path] = set()
    stage2, fsem_validation = _stage2_candidates(source_paths)
    stage3, stage3_validation = _stage3_candidates(source_paths)
    candidates = pd.concat([stage2, stage3], ignore_index=True)
    selected, _bands = _materialise(candidates)
    summary = _profile_summary(selected); deltas = _preference_deltas(selected); balance_semantic = _balance_semantic(selected); band = _band_summary(selected)
    five = _five_subject_band(band); mechanism = _mechanism(summary, band, balance_semantic)
    selected_export = selected.drop(columns=["label_vector", "canonical_partition_sha256"])
    validation_export = fsem_validation.merge(stage3_validation.groupby("subject").agg(stage3_posthoc_crosschecks=("passed", "size"), stage3_posthoc_max_abs_error=("max_abs_error", "max")).reset_index(), on="subject", how="left")
    outputs: dict[Path, bytes] = {
        OUTPUT_RELATIVE / "01_supplementary_selected_profiles_per_run.csv": _csv_bytes(selected_export),
        OUTPUT_RELATIVE / "02_supplementary_profile_summary.csv": _csv_bytes(summary),
        OUTPUT_RELATIVE / "03_supplementary_preference_deltas.csv": _csv_bytes(deltas),
        OUTPUT_RELATIVE / "04_supplementary_band_summary.csv": _csv_bytes(band),
        OUTPUT_RELATIVE / "05_five_subject_band_summary.csv": _csv_bytes(five),
        OUTPUT_RELATIVE / "06_supplementary_mechanism_summary.csv": _csv_bytes(mechanism),
        OUTPUT_RELATIVE / "07_stage2_front_fsemantic_validation.csv": _csv_bytes(validation_export),
    }
    report = "\n".join(["# Supplementary operating-preference validation", "", "Status: **SUPPLEMENTARY DESCRIPTIVE VALIDATION ONLY**.", "", "EasyMock uses Stage 2 seeds 0-9 and Stage 3 seeds 1-10. JFreeChart uses the same stage-specific ranges. No cross-stage pairing, inferential test, correction family, size-effect test, optimiser rerun, embedding regeneration, semantic-graph regeneration, or front regeneration was performed.", "", "## Band size", "", primary.stage3_reporting.markdown_table(band), "", "## BALANCE versus SEMANTIC within each stage", "", primary.stage3_reporting.markdown_table(balance_semantic), "", "## Mechanism summary", "", primary.stage3_reporting.markdown_table(mechanism), "", "Stage 2 front-level f_semantic was newly evaluated from frozen partitions and frozen semantic graphs. No retained Stage 2 f_semantic reference values exist for these subjects; all 20 retained selected structural records were cross-checked instead. Stage 3 post-hoc metrics were evaluated in memory from frozen projected partitions and cross-checked against all 20 retained runtime selected-solution records.", ""])
    outputs[OUTPUT_RELATIVE / "08_validation_report.md"] = report.encode()
    selected_keys = set(selected_export[["subject", "stage", "seed", "selected_solution_id"]].itertuples(index=False, name=None))
    candidate_keys = set(candidates[["subject", "stage", "seed", "solution_id"]].itertuples(index=False, name=None))
    gates = {
        "profile_rows_200": len(selected) == 200,
        "easy_mock_rows_100": int((selected.subject == "easymock").sum()) == 100,
        "jfreechart_rows_100": int((selected.subject == "jfreechart").sum()) == 100,
        "all_selected_in_source_front": selected_keys <= candidate_keys,
        "p1_p4_inside_5pct_band": bool((selected.loc[selected.profile != "MODULARITY_ANCHOR", "relative_modularity_loss"] <= 0.05 + primary.TOL).all()),
        "all_selected_feasible": bool(selected.feasible.all()),
        "stage2_structural_crosschecks_20": len(fsem_validation) == 20 and bool(fsem_validation.passed.all()),
        "stage3_posthoc_crosschecks_20": len(stage3_validation) == 20 and bool(stage3_validation.passed.all()),
        "stage2_stage3_seed_sets_not_paired": STAGE_SEEDS["stage2"] != STAGE_SEEDS["stage3"],
        "no_inferential_outputs": True, "selectors_deterministic": True,
    }
    if not all(gates.values()):
        raise ValueError("supplementary validation gates failed: " + ", ".join(key for key, value in gates.items() if not value))
    manifest = {"analysis": "supplementary_stage2_stage3_operating_preference_validation", "analysis_version": ANALYSIS_VERSION, "status": "SUPPLEMENTARY_DESCRIPTIVE_ONLY", "source_branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(), "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "analysis_script": SCRIPT_RELATIVE.as_posix(), "analysis_script_sha256": _sha256(ROOT / SCRIPT_RELATIVE), "primary_selector_script": primary.SCRIPT_RELATIVE.as_posix(), "primary_selector_script_sha256": _sha256(ROOT / primary.SCRIPT_RELATIVE), "subjects": list(SUBJECTS), "class_counts": CLASS_COUNTS, "stage_seeds": {key: list(value) for key, value in STAGE_SEEDS.items()}, "profiles": list(primary.PROFILES), "profile_row_count": len(selected), "validation_gates": gates, "source_artifacts": [{"path": _relative(path), "sha256": _sha256(path), "size_bytes": path.stat().st_size} for path in sorted(source_paths, key=_relative)], "safety": {"optimizer_rerun": False, "embedding_regenerated": False, "semantic_graph_regenerated": False, "pareto_front_regenerated": False, "projected_front_regenerated": False, "runtime_selection_modified": False, "cross_stage_pairing": False, "inferential_tests": False, "writes_confined_to": OUTPUT_RELATIVE.as_posix()}, "output_files": [{"path": path.as_posix(), "sha256": sha256(content).hexdigest(), "size_bytes": len(content)} for path, content in sorted(outputs.items())]}
    outputs[OUTPUT_RELATIVE / "manifest.json"] = _json_bytes(manifest)
    return outputs, manifest


def _write(outputs: Mapping[Path, bytes]) -> None:
    root = ROOT / OUTPUT_RELATIVE
    root.mkdir(parents=True, exist_ok=True)
    for relative, content in outputs.items():
        target = ROOT / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)


def _check(outputs: Mapping[Path, bytes]) -> None:
    stale: list[str] = []
    for path, content in outputs.items():
        retained = ROOT / path
        if not retained.is_file():
            stale.append(path.as_posix())
            continue
        retained_content = retained.read_bytes()
        if path.name == "manifest.json":
            retained_manifest = json.loads(retained_content)
            generated_manifest = json.loads(content)
            for manifest in (retained_manifest, generated_manifest):
                manifest.pop("source_branch", None)
                manifest.pop("source_head", None)
            matches = retained_manifest == generated_manifest
        else:
            matches = retained_content == content
        if not matches:
            stale.append(path.as_posix())
    if stale:
        raise ValueError("supplementary bundle is stale: " + ", ".join(stale))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true"); mode.add_argument("--check", action="store_true")
    args = parser.parse_args(); outputs, manifest = build_outputs()
    _write(outputs) if args.write else _check(outputs)
    print(json.dumps({"status": "PASS", "mode": "write" if args.write else "check", "profile_rows": manifest["profile_row_count"], "output_root": OUTPUT_RELATIVE.as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
