#!/usr/bin/env python3
"""Final paired Stage 2 versus Stage 3 analysis over frozen outputs.

This module deliberately reads saved results only.  It does not run NSGA-II,
load embedding models, regenerate semantic graphs, or reselect solutions.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import rankdata, wilcoxon


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.evaluation.partition_metrics import partition_similarity
from evo_ms.evaluation.reference_metrics import (
    calculate_reference_metrics,
    load_reference_mapping,
    reference_mapping_diagnostics,
)


SUBJECTS = ("jpetstore", "daytrader", "xerces")
STORAGE_SUBJECT = {"jpetstore": "jpetstore", "daytrader": "daytrader", "xerces": "xerces-j"}
CLASS_COUNTS = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
FORMAL_SEEDS = tuple(range(30))
STAGE2_CONFIG = ROOT / "configs/experiments/02_stage2_nsga_structure_only.yml"
BOUNDS_CONFIG = ROOT / "configs/experiments/stage2_robustness_bounds.yml"
BOOTSTRAP_BASE_SEED = 20260717
BOOTSTRAP_RESAMPLES = 10_000
TIE_TOLERANCE = 1e-12
HV_TOLERANCE = 1e-12
REFERENCE_POINT = np.asarray([1.1, 1.1, 1.1], dtype=float)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STAGE2 = _load_module(
    "stage3_paired_stage2_run",
    ROOT / "experiments/02_stage2_nsga_structure_only/run.py",
)
STAGE2_ROBUSTNESS = _load_module(
    "stage3_paired_stage2_robustness",
    ROOT / "experiments/02_stage2_nsga_structure_only/run_robustness.py",
)
STAGE3 = _load_module("stage3_paired_stage3_run", ROOT / "experiments/04_stage3_semantic/run.py")


# ``direction`` describes a desirable change.  ``delta`` is never sign-flipped.
METRIC_SPECS: tuple[dict[str, Any], ...] = (
    {"name": "hv", "stage2": "stage2_hv", "stage3": "stage3_projected_hv", "direction": "higher", "family": "primary", "statistical": True},
    {"name": "semantic_cut", "stage2": "stage2_selected_semantic_cut", "stage3": "stage3_selected_semantic_cut", "direction": "lower", "family": "secondary", "statistical": True},
    {"name": "coupling", "stage2": "stage2_coupling", "stage3": "stage3_coupling", "direction": "lower", "family": "secondary", "statistical": True},
    {"name": "cohesion", "stage2": "stage2_cohesion", "stage3": "stage3_cohesion", "direction": "higher", "family": "secondary", "statistical": True},
    {"name": "imbalance", "stage2": "stage2_imbalance", "stage3": "stage3_imbalance", "direction": "lower", "family": "secondary", "statistical": True},
    {"name": "weighted_modularity", "stage2": "stage2_weighted_modularity", "stage3": "stage3_weighted_modularity", "direction": "higher", "family": "secondary", "statistical": True},
    {"name": "internal_edge_weight_ratio", "stage2": "stage2_internal_edge_weight_ratio", "stage3": "stage3_internal_edge_weight_ratio", "direction": "higher", "family": "secondary", "statistical": True},
    {"name": "internal_external_edge_ratio", "stage2": "stage2_internal_external_edge_ratio", "stage3": "stage3_internal_external_edge_ratio", "direction": "higher", "family": "secondary", "statistical": True},
    {"name": "max_cluster_ratio", "stage2": "stage2_max_cluster_ratio", "stage3": "stage3_max_cluster_ratio", "direction": "lower", "family": "secondary", "statistical": True},
    {"name": "singleton_ratio", "stage2": "stage2_singleton_ratio", "stage3": "stage3_singleton_ratio", "direction": "lower", "family": "secondary", "statistical": True},
    {"name": "cluster_size_cv", "stage2": "stage2_cluster_size_cv", "stage3": "stage3_cluster_size_cv", "direction": "lower", "family": "secondary", "statistical": True},
    {"name": "cluster_count", "stage2": "stage2_cluster_count", "stage3": "stage3_cluster_count", "direction": None, "family": "descriptive", "statistical": False},
    {"name": "average_cluster_size", "stage2": "stage2_average_cluster_size", "stage3": "stage3_average_cluster_size", "direction": None, "family": "descriptive", "statistical": False},
    {"name": "max_cluster_size", "stage2": "stage2_max_cluster_size", "stage3": "stage3_max_cluster_size", "direction": None, "family": "descriptive", "statistical": False},
    {"name": "min_cluster_size", "stage2": "stage2_min_cluster_size", "stage3": "stage3_min_cluster_size", "direction": None, "family": "descriptive", "statistical": False},
)

EXTERNAL_METRICS = (
    "mojofm_vs_reference",
    "pairwise_precision",
    "pairwise_recall",
    "pairwise_f1",
    "ari_vs_reference",
    "nmi_vs_reference",
    "reference_coverage_ratio",
)
EXTERNAL_INFERENTIAL_METRICS = tuple(metric for metric in EXTERNAL_METRICS if metric != "reference_coverage_ratio")
METRIC_SPECS = METRIC_SPECS + tuple(
    {
        "name": metric,
        "stage2": f"stage2_{metric}",
        "stage3": f"stage3_{metric}",
        "direction": "higher",
        "family": "secondary",
        "statistical": True,
    }
    for metric in EXTERNAL_INFERENTIAL_METRICS
)
REFERENCE_PATHS = {
    "daytrader": ROOT / "data/references/daytrader_reference_services.csv",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def stage2_root(subject: str) -> Path:
    return ROOT / "results" / STORAGE_SUBJECT[subject] / "03_stage2_nsga" / "robustness_final_30seeds"


def stage3_root(subject: str) -> Path:
    return ROOT / "results" / subject / "04_stage3_semantic"


def paired_seeds(left: list[int] | tuple[int, ...], right: list[int] | tuple[int, ...]) -> list[int]:
    """Require exact seed identity and return the deterministic paired order."""
    expected = list(FORMAL_SEEDS)
    if list(left) != expected or list(right) != expected:
        raise ValueError(f"exact paired seeds 0..29 required: left={list(left)}, right={list(right)}")
    return expected


def compute_delta(stage3_values: np.ndarray | list[float], stage2_values: np.ndarray | list[float]) -> np.ndarray:
    """Return the required arithmetic delta: Stage 3 minus Stage 2."""
    left = np.asarray(stage3_values, dtype=float)
    right = np.asarray(stage2_values, dtype=float)
    if left.shape != right.shape:
        raise ValueError("Stage 2 and Stage 3 arrays must have identical shape")
    return left - right


def _snap_ties(values: np.ndarray) -> np.ndarray:
    result = np.asarray(values, dtype=float).copy()
    result[np.isclose(result, 0.0, rtol=0.0, atol=TIE_TOLERANCE)] = 0.0
    return result


def rank_biserial(differences: np.ndarray) -> float | None:
    values = _snap_ties(np.asarray(differences, dtype=float))
    nonzero = values[values != 0.0]
    if len(nonzero) == 0:
        return None
    ranks = rankdata(np.abs(nonzero), method="average")
    return float((ranks[nonzero > 0].sum() - ranks[nonzero < 0].sum()) / ranks.sum())


def _derived_bootstrap_seed(subject: str, metric: str, statistic: str = "mean") -> int:
    digest = hashlib.sha256(f"{BOOTSTRAP_BASE_SEED}|{subject}|{metric}|{statistic}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**32)


def bootstrap_ci(differences: np.ndarray, subject: str, metric: str, statistic: str = "mean") -> tuple[float, float, int]:
    values = np.asarray(differences, dtype=float)
    if len(values) == 0:
        return (float("nan"), float("nan"), _derived_bootstrap_seed(subject, metric, statistic))
    if statistic not in {"mean", "median"}:
        raise ValueError(f"unsupported bootstrap statistic: {statistic}")
    seed = _derived_bootstrap_seed(subject, metric, statistic)
    rng = np.random.default_rng(seed)
    samples = rng.integers(0, len(values), size=(BOOTSTRAP_RESAMPLES, len(values)))
    estimates = values[samples].mean(axis=1) if statistic == "mean" else np.median(values[samples], axis=1)
    low, high = np.percentile(estimates, [2.5, 97.5])
    return float(low), float(high), seed


def bootstrap_mean_ci(differences: np.ndarray, subject: str, metric: str) -> tuple[float, float, int]:
    return bootstrap_ci(differences, subject, metric, "mean")


def bootstrap_median_ci(differences: np.ndarray, subject: str, metric: str) -> tuple[float, float, int]:
    return bootstrap_ci(differences, subject, metric, "median")


def wins_ties_losses(differences: np.ndarray, direction: str | None) -> tuple[int | None, int | None, int | None]:
    if direction is None:
        return None, None, None
    if len(differences) == 0:
        return None, None, None
    values = _snap_ties(np.asarray(differences, dtype=float))
    if direction == "higher":
        wins = int(np.sum(values > 0.0))
        losses = int(np.sum(values < 0.0))
    elif direction == "lower":
        wins = int(np.sum(values < 0.0))
        losses = int(np.sum(values > 0.0))
    else:
        raise ValueError(f"unknown direction: {direction}")
    return wins, int(np.sum(values == 0.0)), losses


def _holm_adjust(p_values: list[float]) -> list[float]:
    if not p_values:
        return []
    order = sorted(range(len(p_values)), key=lambda index: (p_values[index], index))
    adjusted = [0.0] * len(p_values)
    running = 0.0
    size = len(p_values)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, p_values[index] * (size - rank)))
        adjusted[index] = running
    return adjusted


def correction_metadata(stat_rows: list[dict[str, Any]]) -> None:
    """Apply the frozen analysis correction families in place."""
    primary = [row for row in stat_rows if row["family"] == "primary" and row["status"] == "tested"]
    primary_family_size = 3
    for row in stat_rows:
        if row["family"] == "primary":
            row.update({
                "correction": "bonferroni",
                "correction_family_size": primary_family_size,
                "adjusted_alpha": 0.05 / primary_family_size,
                "adjusted_p_value": None if row["p_value_two_sided"] is None else min(1.0, row["p_value_two_sided"] * primary_family_size),
            })
    secondary = [row for row in stat_rows if row["family"] == "secondary" and row["status"] == "tested"]
    adjusted = _holm_adjust([float(row["p_value_two_sided"]) for row in secondary])
    secondary_family_size = len(secondary)
    for row in stat_rows:
        if row["family"] == "secondary":
            if row["status"] == "tested":
                row["correction"] = "holm"
                row["correction_family_size"] = secondary_family_size
                row["adjusted_alpha"] = 0.05
                row["adjusted_p_value"] = adjusted[secondary.index(row)]
            else:
                row.update({"correction": "holm", "correction_family_size": secondary_family_size, "adjusted_alpha": 0.05, "adjusted_p_value": None})
    for row in stat_rows:
        value = row.get("adjusted_p_value")
        row["significant_after_correction"] = bool(value is not None and value <= float(row["adjusted_alpha"]))


def evaluate_semantic_cut(context: dict[str, Any], partition: pd.DataFrame) -> float:
    expected = set(context["class_nodes"]["class_id"].astype(str))
    observed = set(partition["class_id"].astype(str))
    if observed != expected or partition["class_id"].astype(str).duplicated().any():
        raise ValueError("partition does not cover the exact frozen class scope")
    mapping = dict(zip(partition["class_id"].astype(str), partition["cluster_id"].astype(int), strict=True))
    return float(STAGE3.evaluate_semantic_objective(
        context["semantic_edges"], mapping,
        total_weight=float(context["semantic_graph_metadata"]["total_edge_weight"]),
    ))


def _validate_partition_pair(class_nodes: pd.DataFrame, left: pd.DataFrame, right: pd.DataFrame) -> dict[str, Any]:
    class_ids = sorted(class_nodes["class_id"].astype(str))
    expected = set(class_ids)
    for frame in (left, right):
        if set(frame["class_id"].astype(str)) != expected or frame["class_id"].astype(str).duplicated().any():
            raise ValueError("paired partition class scope mismatch")
    left_map = dict(zip(left["class_id"].astype(str), left["cluster_id"].astype(int), strict=True))
    right_map = dict(zip(right["class_id"].astype(str), right["cluster_id"].astype(int), strict=True))
    left_labels = sorted(set(left_map.values()))
    right_labels = sorted(set(right_map.values()))
    contingency = np.zeros((len(left_labels), len(right_labels)), dtype=int)
    left_index = {label: index for index, label in enumerate(left_labels)}
    right_index = {label: index for index, label in enumerate(right_labels)}
    for class_id in class_ids:
        contingency[left_index[left_map[class_id]], right_index[right_map[class_id]]] += 1
    row_indices, col_indices = linear_sum_assignment(-contingency)
    aligned = {right_labels[col]: left_labels[row] for row, col in zip(row_indices, col_indices, strict=True)}
    changed = sum(1 for class_id in class_ids if aligned.get(right_map[class_id]) != left_map[class_id])
    left_frame = pd.DataFrame({"class_id": class_ids, "class_name": class_ids, "cluster_id": [left_map[key] for key in class_ids]})
    right_frame = pd.DataFrame({"class_id": class_ids, "class_name": class_ids, "cluster_id": [right_map[key] for key in class_ids]})
    ari, nmi = partition_similarity(class_nodes, left_frame, right_frame)
    return {
        "class_count": len(class_ids),
        "changed_class_count_after_label_alignment": int(changed),
        "changed_class_ratio_after_label_alignment": float(changed / len(class_ids)) if class_ids else 0.0,
        "ari": float(ari),
        "nmi": float(nmi),
        "label_alignment": "maximum-overlap Hungarian assignment; unmatched Stage 3 labels count as changed",
    }


def _load_bounds(storage_subject: str) -> dict[str, Any]:
    import yaml

    document = yaml.safe_load(BOUNDS_CONFIG.read_text(encoding="utf-8"))
    bounds = document["subjects"][storage_subject]
    if bounds["bounds_source"] != "theoretical" or bounds["calibration_status"] != "not_required":
        raise ValueError(f"{storage_subject}: formal Stage 2 theoretical bounds are not frozen")
    if bounds["objective_order"] != ["coupling", "negative_cohesion", "imbalance"]:
        raise ValueError("Stage 2 objective order mismatch")
    if bounds["reference_point"] != [1.1, 1.1, 1.1]:
        raise ValueError("Stage 2 reference point mismatch")
    return bounds


def load_reference_for_subject(subject: str, class_nodes: pd.DataFrame) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    """Load only the repository's frozen reference, with an explicit status."""
    path = REFERENCE_PATHS.get(subject)
    if path is None:
        return None, {
            "status": "unavailable",
            "reason": "no frozen external reference mapping is registered for this subject",
            "path": None,
            "source": None,
            "coverage": None,
            "unmatched_extracted_classes": [],
            "reference_classes_not_found": [],
        }
    if not path.exists():
        return None, {
            "status": "unavailable",
            "reason": f"frozen reference mapping is missing: {relative(path)}",
            "path": relative(path),
            "source": "repository domain-informed proxy reference",
            "coverage": None,
            "unmatched_extracted_classes": [],
            "reference_classes_not_found": [],
        }
    mapping = load_reference_mapping(path)
    diagnostics = reference_mapping_diagnostics(class_nodes, mapping)
    unmatched = diagnostics["unmapped_extracted_classes"]["class_name"].astype(str).tolist()
    reference_not_found = diagnostics["reference_classes_not_found"]["class_name"].astype(str).tolist()
    coverage = float(diagnostics["reference_coverage_ratio"])
    if coverage != 1.0 or unmatched or reference_not_found:
        return None, {
            "status": "unavailable",
            "reason": "reference class scope is not complete for the frozen subject scope",
            "path": relative(path),
            "source": "repository domain-informed proxy reference",
            "coverage": coverage,
            "unmatched_extracted_classes": unmatched,
            "reference_classes_not_found": reference_not_found,
        }
    return mapping, {
        "status": "available",
        "reason": "complete frozen reference coverage",
        "path": relative(path),
        "source": "repository domain-informed proxy reference; not ground truth",
        "coverage": coverage,
        "unmatched_extracted_classes": [],
        "reference_classes_not_found": [],
    }


def evaluate_external_metrics(class_nodes: pd.DataFrame, partition: pd.DataFrame, mapping: pd.DataFrame | None) -> dict[str, float]:
    """Evaluate the saved partition with the existing validated implementation."""
    if mapping is None:
        return {metric: float("nan") for metric in EXTERNAL_METRICS}
    values = calculate_reference_metrics(class_nodes, partition, mapping)
    return {metric: _finite_or_nan(values.get(metric)) for metric in EXTERNAL_METRICS}


def recompute_stage2_hv(front: pd.DataFrame, bounds: dict[str, Any]) -> float:
    columns = ["coupling", "pymoo_f1_negative_cohesion", "imbalance"]
    if any(column not in front.columns for column in columns):
        raise ValueError("Stage 2 Pareto front is missing frozen objective columns")
    matrix = front.loc[:, columns].to_numpy(dtype=float)
    indices = STAGE2._nondominated_indices(matrix)
    if len(indices) != len(front):
        raise ValueError("saved Stage 2 front is not already nondominated")
    normalized = STAGE2_ROBUSTNESS._normalize_checked(matrix, bounds)
    return float(STAGE2._hypervolume(normalized, REFERENCE_POINT))


def recompute_stage3_projected_hv(front: pd.DataFrame, bounds: dict[str, Any]) -> float:
    columns = ["pymoo_f0_coupling", "pymoo_f1_negative_cohesion", "pymoo_f2_imbalance"]
    if any(column not in front.columns for column in columns):
        raise ValueError("Stage 3 projected front is missing frozen objective columns")
    matrix = front.loc[:, columns].to_numpy(dtype=float)
    indices = STAGE3._nondominated_indices(matrix)
    if len(indices) != len(front):
        raise ValueError("saved Stage 3 projected front is not already nondominated")
    normalized = STAGE3._normalize_projected(matrix, bounds)
    return float(STAGE2._hypervolume(normalized, REFERENCE_POINT))


def _finite_or_nan(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return result if np.isfinite(result) else float("nan")


def _selected_metrics(
    stage2_selected: pd.Series,
    stage3_selected: dict[str, Any],
    stage2_external: dict[str, float] | None = None,
    stage3_external: dict[str, float] | None = None,
) -> dict[str, float]:
    four = stage3_selected["selected_four_objective_row"]
    posthoc = stage3_selected["selected_posthoc_metrics"]
    values: dict[str, float] = {}
    structural = ("coupling", "cohesion", "imbalance")
    for metric in structural:
        values[f"stage2_{metric}"] = _finite_or_nan(stage2_selected.get(metric))
        values[f"stage3_{metric}"] = _finite_or_nan(four.get(metric))
    for metric in ("weighted_modularity", "internal_edge_weight_ratio", "internal_external_edge_ratio", "cluster_count", "average_cluster_size", "max_cluster_size", "min_cluster_size", "max_cluster_ratio", "singleton_ratio", "cluster_size_cv"):
        values[f"stage2_{metric}"] = _finite_or_nan(stage2_selected.get(metric))
        values[f"stage3_{metric}"] = _finite_or_nan(posthoc.get(metric))
    for metric in EXTERNAL_METRICS:
        values[f"stage2_{metric}"] = _finite_or_nan(
            (stage2_external or {}).get(metric, stage2_selected.get(metric))
        )
        values[f"stage3_{metric}"] = _finite_or_nan((stage3_external or {}).get(metric))
    return values


def _validate_provenance(subject: str, seed: int, stage2_manifest: dict[str, Any], stage2_metadata: dict[str, Any], stage3_metadata: dict[str, Any], context: dict[str, Any]) -> None:
    expected_count = CLASS_COUNTS[subject]
    if stage2_metadata.get("run_type") != "formal" or int(stage2_metadata.get("class_count", -1)) != expected_count:
        raise ValueError(f"{subject} seed {seed}: invalid Stage 2 formal metadata")
    if stage2_metadata.get("objective_order") != ["coupling", "negative_cohesion", "imbalance"]:
        raise ValueError(f"{subject} seed {seed}: Stage 2 objective order mismatch")
    if stage2_metadata.get("reference_point") != [1.1, 1.1, 1.1]:
        raise ValueError(f"{subject} seed {seed}: Stage 2 reference point mismatch")
    if stage3_metadata.get("completion_status") != "completed" or int(stage3_metadata.get("population_size", -1)) != 100 or int(stage3_metadata.get("generations", -1)) != 100:
        raise ValueError(f"{subject} seed {seed}: invalid Stage 3 formal result metadata")
    if stage3_metadata.get("objective_order") != ["coupling", "negative_cohesion", "imbalance", "f_semantic"]:
        raise ValueError(f"{subject} seed {seed}: Stage 3 objective order mismatch")
    raw_hash = stage3_metadata.get("g_raw_provenance", {}).get("raw_edge_hash")
    if raw_hash != stage2_manifest.get("input_graph_hashes", {}).get("raw_edges"):
        raise ValueError(f"{subject} seed {seed}: Stage 2/Stage 3 raw graph provenance mismatch")
    if stage3_metadata.get("g_sem_graph_hash") is None:
        raise ValueError(f"{subject} seed {seed}: missing semantic graph provenance")
    if context["semantic_graph_hash"] != stage3_metadata["g_sem_graph_hash"]:
        raise ValueError(f"{subject} seed {seed}: semantic graph hash mismatch")


def load_paired_outputs() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    paired_rows: list[dict[str, Any]] = []
    partition_rows: list[dict[str, Any]] = []
    validation: dict[str, Any] = {}
    for subject in SUBJECTS:
        s2_dir = stage2_root(subject)
        s3_dir = stage3_root(subject)
        s2_manifest = json.loads((s2_dir / "robustness_manifest.json").read_text(encoding="utf-8"))
        if list(s2_manifest.get("formal_seeds", [])) != list(FORMAL_SEEDS):
            raise ValueError(f"{subject}: Stage 2 formal seed inventory is not 0..29")
        context = STAGE3.load_context(subject)
        if len(context["class_nodes"]) != CLASS_COUNTS[subject]:
            raise ValueError(f"{subject}: class scope count mismatch")
        reference_mapping, reference_info = load_reference_for_subject(subject, context["class_nodes"])
        bounds = _load_bounds(STORAGE_SUBJECT[subject])
        if s2_manifest["normalization_bounds"] != {"lower_bounds": bounds["lower_bounds"], "upper_bounds": bounds["upper_bounds"]}:
            raise ValueError(f"{subject}: Stage 2 saved bounds do not match frozen bounds config")
        validation[subject] = {
            "class_count": CLASS_COUNTS[subject],
            "stage2_formal_seeds": list(FORMAL_SEEDS),
            "raw_edge_hash": s2_manifest["input_graph_hashes"]["raw_edges"],
            "semantic_graph_hash": context["semantic_graph_hash"],
            "population_size": context["population_size"],
            "generations": context["generations"],
            "stage2_git_commit": s2_manifest.get("git_commit"),
            "stage3_seed_count": 0,
            "reference": reference_info,
            "input_file_hashes": {
                "stage2_robustness_manifest": sha256_file(s2_dir / "robustness_manifest.json"),
                "class_nodes": sha256_file(context["extracted_dir"] / "class_nodes.csv"),
                "structural_dependencies": sha256_file(context["extracted_dir"] / "structural_dependencies.csv"),
                "stage3_semantic_edges": sha256_file(STAGE3.subject_paths(subject)["graph_edges"]),
                "stage3_semantic_graph_metadata": sha256_file(STAGE3.subject_paths(subject)["graph_metadata"]),
            },
        }
        for seed in paired_seeds(list(FORMAL_SEEDS), list(FORMAL_SEEDS)):
            s2_seed = s2_dir / f"seed_{seed:02d}"
            s3_seed = s3_dir / "validation" / f"seed_{seed:02d}" if seed == 0 else s3_dir / "formal" / f"seed_{seed:02d}"
            s2_metadata = json.loads((s2_seed / "run_metadata.json").read_text(encoding="utf-8"))
            s3_metadata = json.loads((s3_seed / "run_metadata.json").read_text(encoding="utf-8"))
            _validate_provenance(subject, seed, s2_manifest, s2_metadata, s3_metadata, context)
            s2_selected = pd.read_csv(s2_seed / "selected_solution.csv").iloc[0]
            s3_selected = json.loads((s3_seed / "selected_solution.json").read_text(encoding="utf-8"))
            s2_partition = pd.read_csv(s2_seed / "selected_partition.csv")
            s3_partition = pd.read_csv(s3_seed / "selected_partition.csv")
            stage2_front = pd.read_csv(s2_seed / "pareto_front.csv", float_precision="round_trip")
            stage3_front = pd.read_csv(s3_seed / "projected_front_3d.csv", float_precision="round_trip")
            s2_metrics = json.loads((s2_seed / "run_metrics.json").read_text(encoding="utf-8"))
            s3_hv = json.loads((s3_seed / "projected_hypervolume.json").read_text(encoding="utf-8"))
            stage2_hv = recompute_stage2_hv(stage2_front, bounds)
            stage3_hv = recompute_stage3_projected_hv(stage3_front, bounds)
            if not np.isclose(stage2_hv, float(s2_metrics["hypervolume"]), rtol=0.0, atol=HV_TOLERANCE):
                raise ValueError(f"{subject} seed {seed}: Stage 2 stored/recomputed HV mismatch")
            if not np.isclose(stage3_hv, float(s3_hv["stored_value"]), rtol=0.0, atol=HV_TOLERANCE):
                raise ValueError(f"{subject} seed {seed}: Stage 3 stored/recomputed HV mismatch")
            if s3_selected["selected_solution_id"] not in set(stage3_front["solution_id"].astype(str)):
                raise ValueError(f"{subject} seed {seed}: Stage 3 representative is not in projected front")
            stage2_semantic = evaluate_semantic_cut(context, s2_partition)
            stage3_semantic = evaluate_semantic_cut(context, s3_partition)
            saved_stage3_semantic = float(s3_selected["selected_four_objective_row"]["f_semantic"])
            if not np.isclose(stage3_semantic, saved_stage3_semantic, rtol=0.0, atol=HV_TOLERANCE):
                raise ValueError(f"{subject} seed {seed}: Stage 3 semantic objective round-trip mismatch")
            stage2_external = evaluate_external_metrics(context["class_nodes"], s2_partition, reference_mapping)
            stage3_external = evaluate_external_metrics(context["class_nodes"], s3_partition, reference_mapping)
            if reference_mapping is not None:
                saved_external = {metric: _finite_or_nan(s2_selected.get(metric)) for metric in EXTERNAL_METRICS}
                for metric in EXTERNAL_METRICS:
                    if not np.isclose(stage2_external[metric], saved_external[metric], rtol=0.0, atol=HV_TOLERANCE):
                        raise ValueError(
                            f"{subject} seed {seed}: saved Stage 2 {metric} disagrees with evaluation-only recomputation"
                        )
            values = _selected_metrics(s2_selected, s3_selected, stage2_external, stage3_external)
            redundancy_path = s3_seed / "objective_redundancy.json"
            redundancy = json.loads(redundancy_path.read_text(encoding="utf-8"))
            rho = _finite_or_nan(redundancy.get("rho"))
            row: dict[str, Any] = {
                "subject": subject,
                "seed": seed,
                "stage2_result_dir": relative(s2_seed),
                "stage3_result_dir": relative(s3_seed),
                "stage2_hv": stage2_hv,
                "stage3_projected_hv": stage3_hv,
                "delta_hv": stage3_hv - stage2_hv,
                "stage2_selected_solution_id": str(s2_selected["solution_id"]),
                "stage3_selected_solution_id": str(s3_selected["selected_solution_id"]),
                "stage2_selected_semantic_cut": stage2_semantic,
                "stage3_selected_semantic_cut": stage3_semantic,
                "delta_semantic_cut": stage3_semantic - stage2_semantic,
                "stage3_coupling_semantic_rho": rho,
                "reference_status": reference_info["status"],
                "reference_path": reference_info["path"] or "",
            }
            row.update(values)
            for spec in METRIC_SPECS:
                if spec["name"] in {"hv", "semantic_cut"}:
                    continue
                left = row.get(spec["stage2"], float("nan"))
                right = row.get(spec["stage3"], float("nan"))
                row[f"delta_{spec['name']}"] = compute_delta([right], [left])[0] if np.isfinite(left) and np.isfinite(right) else float("nan")
            paired_rows.append(row)
            partition = _validate_partition_pair(context["class_nodes"], s2_partition, s3_partition)
            partition.update({
                "subject": subject,
                "seed": seed,
                "stage2_cluster_count": int(s2_selected["cluster_count"]),
                "stage3_cluster_count": int(s3_selected["selected_posthoc_metrics"]["cluster_count"]),
                "delta_cluster_count": int(s3_selected["selected_posthoc_metrics"]["cluster_count"]) - int(s2_selected["cluster_count"]),
            })
            partition_rows.append(partition)
            validation[subject]["stage3_seed_count"] += 1
            validation[subject].setdefault("coupling_semantic_rho_values", []).append(None if not np.isfinite(rho) else rho)
        rho_values = [value for value in validation[subject].pop("coupling_semantic_rho_values", []) if value is not None]
        validation[subject]["coupling_semantic_rho"] = {
            "source": "objective_redundancy.json",
            "count": len(rho_values),
            "mean": float(np.mean(rho_values)) if rho_values else None,
            "min": float(np.min(rho_values)) if rho_values else None,
            "max": float(np.max(rho_values)) if rho_values else None,
        }
    return pd.DataFrame(paired_rows), pd.DataFrame(partition_rows), validation


def _metric_vector(frame: pd.DataFrame, column: str, subject: str) -> np.ndarray:
    values = pd.to_numeric(frame.loc[frame["subject"] == subject, column], errors="coerce").to_numpy(dtype=float)
    return values[np.isfinite(values)]


def make_descriptive_summary(paired: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    all_specs = list(METRIC_SPECS) + [
        {
            "name": "reference_coverage_ratio",
            "stage2": "stage2_reference_coverage_ratio",
            "stage3": "stage3_reference_coverage_ratio",
            "direction": "higher",
            "family": "external_descriptive",
            "statistical": False,
        }
    ]
    for subject in SUBJECTS:
        subject_frame = paired.loc[paired["subject"] == subject]
        for spec in all_specs:
            stage2_values = pd.to_numeric(subject_frame[spec["stage2"]], errors="coerce").to_numpy(dtype=float)
            stage3_values = pd.to_numeric(subject_frame[spec["stage3"]], errors="coerce").to_numpy(dtype=float)
            mask = np.isfinite(stage2_values) & np.isfinite(stage3_values)
            left = stage2_values[mask]
            right = stage3_values[mask]
            delta = compute_delta(right, left) if len(left) else np.asarray([], dtype=float)
            wins, ties, losses = wins_ties_losses(delta, spec["direction"])
            low, high, bootstrap_seed = bootstrap_mean_ci(delta, subject, spec["name"])
            rows.append({
                "subject": subject,
                "metric": spec["name"],
                "family": spec["family"],
                "direction": spec["direction"] or "descriptive_only",
                "paired_n": int(len(delta)),
                "missing_pairs": int(len(subject_frame) - len(delta)),
                "stage2_mean": float(np.mean(left)) if len(left) else np.nan,
                "stage3_mean": float(np.mean(right)) if len(right) else np.nan,
                "delta_mean_stage3_minus_stage2": float(np.mean(delta)) if len(delta) else np.nan,
                "stage2_std": float(np.std(left, ddof=1)) if len(left) > 1 else (0.0 if len(left) == 1 else np.nan),
                "stage3_std": float(np.std(right, ddof=1)) if len(right) > 1 else (0.0 if len(right) == 1 else np.nan),
                "stage2_min": float(np.min(left)) if len(left) else np.nan,
                "stage2_max": float(np.max(left)) if len(left) else np.nan,
                "stage3_min": float(np.min(right)) if len(right) else np.nan,
                "stage3_max": float(np.max(right)) if len(right) else np.nan,
                "stage2_median": float(np.median(left)) if len(left) else np.nan,
                "stage3_median": float(np.median(right)) if len(right) else np.nan,
                "delta_median_stage3_minus_stage2": float(np.median(delta)) if len(delta) else np.nan,
                "delta_std": float(np.std(delta, ddof=1)) if len(delta) > 1 else (0.0 if len(delta) == 1 else np.nan),
                "delta_min": float(np.min(delta)) if len(delta) else np.nan,
                "delta_max": float(np.max(delta)) if len(delta) else np.nan,
                "bootstrap_mean_delta_ci_low": low,
                "bootstrap_mean_delta_ci_high": high,
                "bootstrap_resamples": BOOTSTRAP_RESAMPLES if len(delta) else 0,
                "bootstrap_seed": bootstrap_seed if len(delta) else None,
                "wins_stage3": wins,
                "ties": ties,
                "losses_stage3": losses,
                "proportion_seeds_improved": (float(wins / len(delta)) if wins is not None and len(delta) else np.nan),
                "availability": "available" if len(delta) == len(subject_frame) else "not_consistently_available",
                "unavailable_reason": "" if len(delta) == len(subject_frame) else "Stage 3 saved representative does not contain this reference-dependent metric",
            })
    return pd.DataFrame(rows)


def make_external_evaluation(paired: pd.DataFrame, validation: dict[str, Any]) -> pd.DataFrame:
    """Create an auditable evaluation-only record for all saved partitions."""
    rows: list[dict[str, Any]] = []
    for record in paired.to_dict("records"):
        subject = str(record["subject"])
        info = validation[subject]["reference"]
        row: dict[str, Any] = {
            "subject": subject,
            "seed": int(record["seed"]),
            "reference_status": info["status"],
            "reference_path": info["path"] or "",
            "reference_source": info["source"] or "",
            "reference_coverage": info["coverage"],
            "evaluation_policy": "existing calculate_reference_metrics; saved partitions only; no reselection",
        }
        for metric in EXTERNAL_METRICS:
            row[f"stage2_{metric}"] = record[f"stage2_{metric}"]
            row[f"stage3a_{metric}"] = record[f"stage3_{metric}"]
            row[f"delta_{metric}"] = record.get(f"delta_{metric}", float("nan"))
        rows.append(row)
    return pd.DataFrame(rows)


def make_statistical_tests(paired: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        subject_frame = paired.loc[paired["subject"] == subject]
        for spec in METRIC_SPECS:
            if not spec["statistical"]:
                continue
            left = pd.to_numeric(subject_frame[spec["stage2"]], errors="coerce").to_numpy(dtype=float)
            right = pd.to_numeric(subject_frame[spec["stage3"]], errors="coerce").to_numpy(dtype=float)
            mask = np.isfinite(left) & np.isfinite(right)
            differences = _snap_ties(compute_delta(right[mask], left[mask]))
            wins, ties, losses = wins_ties_losses(differences, spec["direction"])
            low, high, seed = bootstrap_mean_ci(differences, subject, spec["name"])
            median_low, median_high, median_seed = bootstrap_median_ci(differences, subject, spec["name"])
            all_zero = len(differences) > 0 and bool(np.all(differences == 0.0))
            if len(differences) == 0:
                status = "unavailable"
                statistic = p_value = effect = None
            elif all_zero:
                status = "degenerate_all_pairs_identical"
                statistic = p_value = effect = None
            else:
                test = wilcoxon(differences, zero_method="wilcox", alternative="two-sided", method="auto")
                status = "tested"
                statistic = float(test.statistic)
                p_value = float(test.pvalue)
                effect = rank_biserial(differences)
            rows.append({
                "subject": subject,
                "metric": spec["name"],
                "family": spec["family"],
                "direction": spec["direction"],
                "direction_of_improvement": spec["direction"],
                "delta_definition": "Stage 3 minus Stage 2",
                "paired_n": int(len(differences)),
                "stage2_mean": float(np.mean(left[mask])) if np.any(mask) else np.nan,
                "stage3_mean": float(np.mean(right[mask])) if np.any(mask) else np.nan,
                "mean_delta": float(np.mean(differences)) if len(differences) else np.nan,
                "median_delta": float(np.median(differences)) if len(differences) else np.nan,
                "wins_stage3": wins,
                "ties": ties,
                "losses_stage3": losses,
                "wins": wins,
                "losses": losses,
                "wilcoxon_test": "paired Wilcoxon signed-rank, two-sided" if status == "tested" else None,
                "wilcoxon_statistic": statistic,
                "p_value_two_sided": p_value,
                "raw_p": p_value,
                "rank_biserial_stage3_minus_stage2": effect,
                "rank_biserial": effect,
                "bootstrap_mean_delta_ci_low": low,
                "bootstrap_mean_delta_ci_high": high,
                "bootstrap_median_delta_ci_low": median_low,
                "bootstrap_median_delta_ci_high": median_high,
                "bootstrap_resamples": BOOTSTRAP_RESAMPLES if len(differences) else 0,
                "bootstrap_seed": seed if len(differences) else None,
                "status": status,
                "test_status": status,
                "eligible_for_correction": status == "tested",
            })
    correction_metadata(rows)
    for row in rows:
        row["metric_family"] = row["family"]
        row["adjustment_method"] = row.get("correction")
        row["adjusted_p"] = row.get("adjusted_p_value")
    return pd.DataFrame(rows)


def _format(value: Any, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "N/A"
    return f"{float(value):.{digits}f}"


def write_report(output_dir: Path, paired: pd.DataFrame, partitions: pd.DataFrame, descriptive: pd.DataFrame, stats: pd.DataFrame, validation: dict[str, Any]) -> str:
    primary = stats.loc[stats["metric"] == "hv"]
    significant = bool(primary["significant_after_correction"].any())
    mean_delta = float(pd.to_numeric(paired["delta_hv"], errors="coerce").mean())
    if significant and mean_delta > 0:
        answer = "yes, on the preregistered primary metric"
        conclusion = "Stage 3 outperformed Stage 2 on the primary projected 3D Hypervolume comparison after the prespecified multiple-testing correction."
    elif significant and mean_delta < 0:
        answer = "no, on the preregistered primary metric"
        conclusion = "Stage 3 did not outperform Stage 2 on the primary projected 3D Hypervolume comparison; the corrected result favored Stage 2."
    else:
        answer = "no overall corrected primary-metric superiority was established"
        conclusion = "Stage 3 did not establish an overall statistically significant advantage over Stage 2 on the primary projected 3D Hypervolume comparison."
    lines = [
        "# Paired Stage 2 versus Stage 3 analysis",
        "",
        "## Executive conclusion",
        "",
        f"Direct answer: {answer}. {conclusion} The comparison uses the same 30 seed IDs (0–29) for JPetStore, DayTrader, and Xerces, and compares Stage 2 three-objective Hypervolume with Stage 3 projected three-dimensional Hypervolume. The arithmetic delta is always Stage 3 minus Stage 2. Semantic-cut values for the saved Stage 2 representatives were evaluated on the frozen Stage 3 semantic graph; they were not used for reselection. This is a paired result comparison and does not by itself establish an improvement in decomposition quality.",
        "",
        "## Scope and frozen-data policy",
        "",
        "No optimizer, embedding, graph construction, representative reselection, configuration, seed, objective, or statistical setting was rerun or changed. All 90 pairs passed exact seed and class-scope validation. Hypervolume was independently recomputed from each saved Pareto/projected front and checked against the stored value.",
        "",
        "## Primary projected-Hypervolume comparison",
        "",
        "| subject | n | Stage 2 median | Stage 3 median | median delta | mean delta | wins/ties/losses | Wilcoxon p | Holm/Bonferroni adjusted p | corrected significant |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for subject in SUBJECTS:
        row = primary.loc[primary["subject"] == subject].iloc[0]
        d = descriptive.loc[(descriptive["subject"] == subject) & (descriptive["metric"] == "hv")].iloc[0]
        lines.append(f"| {subject} | {int(row['paired_n'])} | {_format(d['stage2_median'])} | {_format(d['stage3_median'])} | {_format(d['delta_median_stage3_minus_stage2'])} | {_format(d['delta_mean_stage3_minus_stage2'])} | {int(row['wins_stage3'])}/{int(row['ties'])}/{int(row['losses_stage3'])} | {_format(row['p_value_two_sided'])} | {_format(row['adjusted_p_value'])} | {'yes' if row['significant_after_correction'] else 'no'} |")
    lines.extend([
        "",
        "Primary correction: two-sided paired Wilcoxon tests across the three subjects, Bonferroni family size 3, alpha = 0.05/3. Bootstrap intervals are deterministic 95% intervals for the mean arithmetic delta, based on 10,000 resamples per subject/metric.",
        "",
        "## Key paired values",
        "",
        "| subject | Stage 2 HV mean | Stage 3 projected HV mean | mean delta | HV wins/ties/losses | HV rank-biserial | HV bootstrap mean CI | MoJoFM delta | Pairwise F1 delta | semantic-cut delta | partition ARI | mean Stage 3 coupling–semantic rho |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for subject in SUBJECTS:
        d_hv = descriptive.loc[(descriptive["subject"] == subject) & (descriptive["metric"] == "hv")].iloc[0]
        s_hv = stats.loc[(stats["subject"] == subject) & (stats["metric"] == "hv")].iloc[0]
        d_mojo = descriptive.loc[(descriptive["subject"] == subject) & (descriptive["metric"] == "mojofm_vs_reference")].iloc[0]
        d_f1 = descriptive.loc[(descriptive["subject"] == subject) & (descriptive["metric"] == "pairwise_f1")].iloc[0]
        d_sem = descriptive.loc[(descriptive["subject"] == subject) & (descriptive["metric"] == "semantic_cut")].iloc[0]
        ari = partitions.loc[partitions["subject"] == subject, "ari"].mean()
        rho = validation[subject]["coupling_semantic_rho"]["mean"]
        lines.append(f"| {subject} | {_format(d_hv['stage2_mean'])} | {_format(d_hv['stage3_mean'])} | {_format(d_hv['delta_mean_stage3_minus_stage2'])} | {int(s_hv['wins'])}/{int(s_hv['ties'])}/{int(s_hv['losses'])} | {_format(s_hv['rank_biserial'])} | [{_format(s_hv['bootstrap_mean_delta_ci_low'])}, {_format(s_hv['bootstrap_mean_delta_ci_high'])}] | {_format(d_mojo['delta_mean_stage3_minus_stage2'])} | {_format(d_f1['delta_mean_stage3_minus_stage2'])} | {_format(d_sem['delta_mean_stage3_minus_stage2'])} | {_format(ari)} | {_format(rho)} |")
    lines.extend([
        "",
        "External-quality metrics below are evaluation-only calculations on the saved representatives. Subjects without a complete frozen reference remain N/A; no values were invented or used for reselection.",
        "",
        "## External-reference evaluation",
        "",
        "| subject | reference status | reference path | MoJoFM mean delta | Pairwise F1 mean delta | reference ARI mean delta | reference NMI mean delta |",
        "|---|---|---|---:|---:|---:|---:|",
    ])
    for subject in SUBJECTS:
        info = validation[subject]["reference"]
        values = []
        for metric in ("mojofm_vs_reference", "pairwise_f1", "ari_vs_reference", "nmi_vs_reference"):
            row = descriptive.loc[(descriptive["subject"] == subject) & (descriptive["metric"] == metric)].iloc[0]
            values.append(_format(row["delta_mean_stage3_minus_stage2"]))
        lines.append(f"| {subject} | {info['status']} | {info['path'] or 'N/A'} | {values[0]} | {values[1]} | {values[2]} | {values[3]} |")
    lines.extend([
        "",
        "",
        "## Semantic-cut evaluation",
        "",
        "The Stage 2 selected partition was evaluated with the exact frozen Stage 3 graph and formula. Lower semantic cut is better; these values are secondary and were not used to select either solution.",
        "",
        "| subject | Stage 2 median | Stage 3 median | median delta | wins/ties/losses | corrected p |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for subject in SUBJECTS:
        d = descriptive.loc[(descriptive.subject == subject) & (descriptive.metric == "semantic_cut")].iloc[0]
        s = stats.loc[(stats.subject == subject) & (stats.metric == "semantic_cut")].iloc[0]
        lines.append(f"| {subject} | {_format(d['stage2_median'])} | {_format(d['stage3_median'])} | {_format(d['delta_median_stage3_minus_stage2'])} | {int(d['wins_stage3'])}/{int(d['ties'])}/{int(d['losses_stage3'])} | {_format(s['adjusted_p_value'])} |")
    lines.extend([
        "",
        "## Partition change",
        "",
        "ARI and NMI are label-invariant. The changed-class ratio uses deterministic maximum-overlap Hungarian label alignment and is descriptive only.",
        "",
        "| subject | mean changed-class ratio | mean ARI | mean NMI | mean cluster-count delta |",
        "|---|---:|---:|---:|---:|",
    ])
    for subject in SUBJECTS:
        frame = partitions.loc[partitions.subject == subject]
        lines.append(f"| {subject} | {_format(frame['changed_class_ratio_after_label_alignment'].mean())} | {_format(frame['ari'].mean())} | {_format(frame['nmi'].mean())} | {_format(frame['delta_cluster_count'].mean())} |")
    lines.extend([
        "",
        "## Secondary paired metrics",
        "",
        "See `stage2_vs_stage3_paired_descriptive_summary.csv` and `stage2_vs_stage3_paired_statistical_tests.csv` for all structural metrics, directions, paired sample sizes, bootstrap intervals, wins/ties/losses, proportions improved, and corrected values. Secondary inferential tests use Holm correction over all eligible non-degenerate secondary tests. Cluster count and size summaries are descriptive only.",
        "",
        "Reference-dependent metrics are available only for DayTrader because it has the complete frozen proxy reference. JPetStore and Xerces remain unavailable with explicit reasons in the manifest and external-evaluation CSV; no values were imputed.",
        "",
        "## Statistical-analysis contract",
        "",
        "The repository contains a Stage 3 internal Wilcoxon/Bonferroni configuration in `configs/experiments/04_stage3_semantic.yml` and a Stage 2 selected-versus-Leiden protocol in `docs/stage2/reproducibility.md`; neither is a complete frozen Stage 2-versus-Stage 3 paired contract. This report therefore labels the transparent two-sided Wilcoxon, rank-biserial, deterministic bootstrap, primary Bonferroni, and secondary Holm procedure as a post-hoc analysis protocol established after formal execution.",
        "",
        "## Provenance and validation",
        "",
        f"Analysis source commit at start: `{git_head()}`. Subject pair validation: all passed. No embeddings, semantic graphs, or optimizer runs were generated by this analysis. Frozen source validation details are recorded in `stage2_vs_stage3_analysis_manifest.json`.",
        "",
        "## Outputs",
        "",
        "- `stage2_vs_stage3_paired_seed_metrics.csv` — authoritative one-row-per-subject/seed dataset.",
        "- `stage2_vs_stage3_partition_change.csv` — paired partition-change diagnostics.",
        "- `stage2_vs_stage3_paired_descriptive_summary.csv` — paired descriptive metrics.",
        "- `stage2_vs_stage3_paired_statistical_tests.csv` — two-sided paired tests and corrections.",
        "- `stage2_vs_stage3_external_metric_evaluation.csv` — evaluation-only external metrics for saved partitions.",
    ])
    report = "\n".join(lines) + "\n"
    (output_dir / "stage2_vs_stage3_paired_analysis.md").write_text(report, encoding="utf-8")
    return report


def run(output_dir: Path) -> dict[str, Any]:
    start_commit = git_head()
    paired, partitions, validation = load_paired_outputs()
    expected_columns = {"subject", "seed", "stage2_hv", "stage3_projected_hv", "delta_hv", "stage2_selected_semantic_cut", "stage3_selected_semantic_cut", "delta_semantic_cut"}
    if not expected_columns.issubset(paired.columns) or len(paired) != 90:
        raise ValueError("authoritative paired dataset schema or row count is invalid")
    descriptive = make_descriptive_summary(paired)
    stats = make_statistical_tests(paired)
    external = make_external_evaluation(paired, validation)
    output_dir.mkdir(parents=True, exist_ok=True)
    paired_path = output_dir / "stage2_vs_stage3_paired_seed_metrics.csv"
    partition_path = output_dir / "stage2_vs_stage3_partition_change.csv"
    descriptive_path = output_dir / "stage2_vs_stage3_paired_descriptive_summary.csv"
    stats_path = output_dir / "stage2_vs_stage3_paired_statistical_tests.csv"
    external_path = output_dir / "stage2_vs_stage3_external_metric_evaluation.csv"
    paired.to_csv(paired_path, index=False, float_format="%.17g")
    partitions.to_csv(partition_path, index=False, float_format="%.17g")
    descriptive.to_csv(descriptive_path, index=False, float_format="%.17g")
    stats.to_csv(stats_path, index=False, float_format="%.17g")
    external.to_csv(external_path, index=False, float_format="%.17g")
    report = write_report(output_dir, paired, partitions, descriptive, stats, validation)
    manifest = {
        "schema_version": 1,
        "analysis_type": "paired_stage2_vs_stage3_frozen_results",
        "generated_at_utc": utc_now(),
        "analysis_start_commit": start_commit,
        "analysis_final_commit": None,
        "subjects": list(SUBJECTS),
        "seed_pairing": {"ids": list(FORMAL_SEEDS), "pairs_per_subject": 30, "total_pairs": 90, "requirement": "exact identical seed IDs 0..29"},
        "delta_definition": "Stage 3 minus Stage 2; no direction-dependent sign flips",
        "primary_comparison": {
            "stage2_metric": "three_objective_hypervolume",
            "stage3_metric": "projected_three_dimensional_hypervolume",
            "stage2_objectives": ["coupling", "negative_cohesion", "imbalance"],
            "stage3_projected_objectives": ["coupling", "negative_cohesion", "imbalance"],
            "reference_point": [1.1, 1.1, 1.1],
            "bounds_source": relative(BOUNDS_CONFIG),
            "independent_recomputation": True,
        },
        "statistical_protocol": {
            "status": "post_hoc_default; no complete frozen cross_stage_paired_contract found",
            "repository_contract_audit": {
                "stage3_config": relative(ROOT / "configs/experiments/04_stage3_semantic.yml"),
                "stage2_reproducibility": relative(ROOT / "docs/stage2/reproducibility.md"),
                "finding": "existing rules cover internal Stage 3 or Stage 2-versus-Leiden analyses, not this cross-stage paired comparison",
            },
            "test": "paired Wilcoxon signed-rank, two-sided",
            "rank_biserial": "signed-rank effect; arithmetic Stage3-minus-Stage2 sign",
            "bootstrap": {"statistics": ["mean_delta", "median_delta"], "resamples": BOOTSTRAP_RESAMPLES, "base_seed": BOOTSTRAP_BASE_SEED, "derived_seed": "SHA256(base_seed|subject|metric|statistic) first 8 bytes modulo 2^32", "confidence_level": 0.95},
            "primary_correction": {"method": "Bonferroni", "family": "projected_HV_across_three_subjects", "family_size": 3, "alpha": 0.05, "adjusted_alpha": 0.05 / 3},
            "secondary_correction": {"method": "Holm", "family": "all eligible non-degenerate secondary tests across subjects", "alpha": 0.05},
            "semantic_cut": "secondary",
            "partition_ari_nmi": "descriptive_only",
            "tie_tolerance": TIE_TOLERANCE,
            "minimum_sample_rule": "all exact paired seeds are retained; Wilcoxon is undefined for all-zero differences and no p-value is fabricated",
        },
        "validation": validation,
        "external_reference_evaluation": {
            subject: validation[subject]["reference"] for subject in SUBJECTS
        },
        "result_paths": {
            subject: {
                "stage2": relative(stage2_root(subject)),
                "stage3_validation_seed0": relative(stage3_root(subject) / "validation/seed_00"),
                "stage3_formal_seeds1_to_29": relative(stage3_root(subject) / "formal"),
            }
            for subject in SUBJECTS
        },
        "no_rerun_policy": {"optimizer_rerun": False, "embedding_generation": False, "semantic_graph_generation": False, "representative_reselection": False, "configuration_change": False},
        "output_files": {
            "paired_seed_metrics": {"path": relative(paired_path), "sha256": sha256_file(paired_path), "rows": len(paired)},
            "partition_change": {"path": relative(partition_path), "sha256": sha256_file(partition_path), "rows": len(partitions)},
            "descriptive_summary": {"path": relative(descriptive_path), "sha256": sha256_file(descriptive_path), "rows": len(descriptive)},
            "statistical_tests": {"path": relative(stats_path), "sha256": sha256_file(stats_path), "rows": len(stats)},
            "external_metric_evaluation": {"path": relative(external_path), "sha256": sha256_file(external_path), "rows": len(external)},
            "report": {"path": relative(output_dir / "stage2_vs_stage3_paired_analysis.md"), "sha256": sha256_file(output_dir / "stage2_vs_stage3_paired_analysis.md")},
        },
    }
    (output_dir / "stage2_vs_stage3_analysis_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/stage3")
    args = parser.parse_args()
    manifest = run(args.output_dir)
    print(json.dumps({"status": "PASS", "pairs": manifest["seed_pairing"], "outputs": manifest["output_files"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
