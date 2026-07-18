#!/usr/bin/env python3
"""Validate and analyse the completed Stage 3B formal seed collection.

This module reads frozen Stage 2, Stage 3A, and Stage 3B artifacts.  It does
not generate embeddings or graphs and it does not run the optimizer except for
the three explicitly registered reproducibility spot checks.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import itertools
import json
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr, wilcoxon

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.evaluation.partition_metrics import partition_similarity  # noqa: E402
from evo_ms.evaluation.reference_metrics import (  # noqa: E402
    calculate_reference_metrics,
    load_reference_mapping,
    reference_mapping_diagnostics,
)
from scripts.stage3_method_body import run_seed00_optimizer as b_adapter  # noqa: E402
from scripts.stage3_method_body import run_formal_stage3b as formal_runner  # noqa: E402


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STAGE3A = _load_module("stage3b_analysis_stage3a", ROOT / "experiments/04_stage3_semantic/run.py")
STAGE2 = STAGE3A.stage2
STAGE2_ROBUSTNESS = _load_module("stage3b_analysis_stage2_robustness", ROOT / "experiments/02_stage2_nsga_structure_only/run_robustness.py")
SUBJECTS = ("jpetstore", "daytrader", "xerces")
SEEDS = tuple(range(30))
STORAGE_SUBJECT = {"jpetstore": "jpetstore", "daytrader": "daytrader", "xerces": "xerces-j"}
CLASS_COUNTS = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
REPORT_ROOT = ROOT / "reports/stage3_method_body"
STAGE2_CONFIG = ROOT / "configs/experiments/02_stage2_nsga_structure_only.yml"
STAGE3A_CONFIG = ROOT / "configs/experiments/04_stage3_semantic.yml"
STAGE3B_CONFIG = ROOT / "configs/experiments/05_stage3_declaration_method_body.yml"
BOUNDS_CONFIG = ROOT / "configs/experiments/stage2_robustness_bounds.yml"
REFERENCE_PATHS = {"daytrader": ROOT / "data/references/daytrader_reference_services.csv"}
REFERENCE_POINT = np.full(3, 1.1, dtype=float)
HV_TOLERANCE = 1e-12
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_BASE_SEED = 20260718
TIE_TOLERANCE = 1e-12
TASK_START_HEAD = "a922df344114eb5facd0a0d084c4ad5c33a38b66"
FORMAL_SCIENTIFIC_FILES = (
    "pareto_front_4d.csv",
    "projected_front_3d.csv",
    "partition_labels.csv",
    "posthoc_metrics.csv",
    "selected_partition.csv",
    "selected_solution.json",
    "projected_hypervolume.json",
    "objective_redundancy.json",
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
POSTHOC_METRICS = (
    "weighted_modularity",
    "internal_edge_weight_ratio",
    "internal_external_edge_ratio",
    "cluster_count",
    "average_cluster_size",
    "max_cluster_size",
    "min_cluster_size",
    "max_cluster_ratio",
    "singleton_ratio",
    "cluster_size_cv",
)
PRIMARY_SPECS = (
    ("projected_hv", "higher"),
    ("selected_f_semantic", "lower"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head() -> str:
    import subprocess

    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_frame(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.20g", lineterminator="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def stage2_dir(subject: str, seed: int) -> Path:
    return ROOT / "results" / STORAGE_SUBJECT[subject] / "03_stage2_nsga" / "robustness_final_30seeds" / f"seed_{seed:02d}"


def stage3a_dir(subject: str, seed: int) -> Path:
    layer = "validation" if seed == 0 else "formal"
    return ROOT / "results" / subject / "04_stage3_semantic" / layer / f"seed_{seed:02d}"


def stage3b_dir(subject: str, seed: int) -> Path:
    layer = "validation" if seed == 0 else "formal"
    return ROOT / "results" / subject / "05_stage3_declaration_method_body" / layer / f"seed_{seed:02d}"


def _finite(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return result if np.isfinite(result) else float("nan")


def _snap(values: np.ndarray) -> np.ndarray:
    result = np.asarray(values, dtype=float).copy()
    result[np.isclose(result, 0.0, rtol=0.0, atol=TIE_TOLERANCE)] = 0.0
    return result


def rank_biserial(values: np.ndarray) -> float | None:
    nonzero = _snap(values)
    nonzero = nonzero[nonzero != 0.0]
    if len(nonzero) == 0:
        return None
    ranks = rankdata(np.abs(nonzero), method="average")
    return float((ranks[nonzero > 0].sum() - ranks[nonzero < 0].sum()) / ranks.sum())


def bootstrap_seed(comparison: str, subject: str, metric: str) -> int:
    return int.from_bytes(sha256_bytes(f"{BOOTSTRAP_BASE_SEED}|{comparison}|{subject}|{metric}".encode()).encode()[:8], "big") % (2**32)


def bootstrap_ci(values: np.ndarray, comparison: str, subject: str, metric: str) -> tuple[float, float, int]:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return float("nan"), float("nan"), 0
    seed = bootstrap_seed(comparison, subject, metric)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(BOOTSTRAP_RESAMPLES, len(values)))
    estimates = values[indices].mean(axis=1)
    low, high = np.percentile(estimates, [2.5, 97.5])
    return float(low), float(high), seed


def _holm(p_values: list[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=lambda i: (p_values[i], i))
    adjusted = [0.0] * len(p_values)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, p_values[index] * (len(p_values) - rank)))
        adjusted[index] = running
    return adjusted


def _load_bounds(storage_subject: str) -> dict[str, Any]:
    import yaml

    document = yaml.safe_load(BOUNDS_CONFIG.read_text(encoding="utf-8"))
    bounds = document["subjects"][storage_subject]
    if bounds["reference_point"] != [1.1, 1.1, 1.1] or bounds["objective_order"] != ["coupling", "negative_cohesion", "imbalance"]:
        raise ValueError(f"{storage_subject}: frozen Hypervolume bounds mismatch")
    return bounds


def recompute_stage2_hv(front: pd.DataFrame, bounds: dict[str, Any]) -> float:
    columns = ["coupling", "pymoo_f1_negative_cohesion", "imbalance"]
    matrix = front.loc[:, columns].to_numpy(dtype=float)
    if len(STAGE2._nondominated_indices(matrix)) != len(front):
        raise ValueError("Stage 2 saved front is not nondominated")
    normalized = STAGE2_ROBUSTNESS._normalize_checked(matrix, bounds)
    return float(STAGE2._hypervolume(normalized, REFERENCE_POINT))


def recompute_projected_hv(front: pd.DataFrame, bounds: dict[str, Any]) -> float:
    columns = ["pymoo_f0_coupling", "pymoo_f1_negative_cohesion", "pymoo_f2_imbalance"]
    matrix = front.loc[:, columns].to_numpy(dtype=float)
    if len(STAGE3A._nondominated_indices(matrix)) != len(front):
        raise ValueError("saved projected front is not nondominated")
    normalized = STAGE3A._normalize_projected(matrix, bounds)
    return float(STAGE2._hypervolume(normalized, REFERENCE_POINT))


def ensure_partition(path: Path, class_nodes: pd.DataFrame) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"class_id": str})
    if "class_name" not in frame:
        names = class_nodes.set_index(class_nodes["class_id"].astype(str))["class_name"].astype(str).to_dict()
        frame["class_name"] = frame["class_id"].astype(str).map(names)
    frame["class_id"] = frame["class_id"].astype(str)
    frame["class_name"] = frame["class_name"].astype(str)
    frame["cluster_id"] = frame["cluster_id"].astype(int)
    expected = set(class_nodes["class_id"].astype(str))
    if set(frame["class_id"]) != expected or frame["class_id"].duplicated().any():
        raise ValueError(f"partition scope mismatch in {path}")
    return frame.loc[:, ["class_id", "class_name", "cluster_id"]].sort_values("class_id", kind="stable").reset_index(drop=True)


def semantic_value(context: dict[str, Any], partition: pd.DataFrame) -> float:
    mapping = dict(zip(partition["class_id"], partition["cluster_id"], strict=True))
    return float(b_adapter.evaluate_semantic_objective(
        context["semantic_edges"], mapping,
        total_weight=float(context["semantic_graph_metadata"]["total_edge_weight"]),
    ))


def load_reference(subject: str, class_nodes: pd.DataFrame) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    path = REFERENCE_PATHS.get(subject)
    if path is None or not path.exists():
        return None, {"status": "unavailable", "reason": "no frozen complete reference is registered", "path": relative(path) if path and path.exists() else None, "coverage": None, "source": None}
    mapping = load_reference_mapping(path)
    diagnostics = reference_mapping_diagnostics(class_nodes, mapping)
    coverage = float(diagnostics["reference_coverage_ratio"])
    if coverage != 1.0 or not diagnostics["unmapped_extracted_classes"].empty or not diagnostics["reference_classes_not_found"].empty:
        return None, {"status": "unavailable", "reason": "reference scope is incomplete", "path": relative(path), "coverage": coverage, "source": "repository proxy reference"}
    return mapping, {"status": "available", "reason": "complete frozen reference coverage", "path": relative(path), "coverage": coverage, "source": "repository domain-informed proxy reference; not ground truth"}


def external_metrics(class_nodes: pd.DataFrame, partition: pd.DataFrame, reference: pd.DataFrame | None) -> dict[str, float]:
    if reference is None:
        return {metric: float("nan") for metric in EXTERNAL_METRICS}
    values = calculate_reference_metrics(class_nodes, partition, reference)
    return {metric: _finite(values.get(metric)) for metric in EXTERNAL_METRICS}


def stage3_selected_metrics(selected: dict[str, Any]) -> dict[str, float]:
    row = selected["selected_four_objective_row"]
    posthoc = selected["selected_posthoc_metrics"]
    result = {metric: _finite(row.get(metric)) for metric in ("coupling", "cohesion", "imbalance", "f_semantic")}
    result.update({metric: _finite(posthoc.get(metric)) for metric in POSTHOC_METRICS})
    return result


def stage2_selected_metrics(row: pd.Series) -> dict[str, float]:
    return {metric: _finite(row.get(metric)) for metric in ("coupling", "cohesion", "imbalance", *POSTHOC_METRICS)}


def validate_stage3_output(subject: str, seed: int, context: dict[str, Any], representation: str) -> dict[str, Any]:
    output = stage3a_dir(subject, seed) if representation == "stage3a" else stage3b_dir(subject, seed)
    if not output.is_dir():
        raise FileNotFoundError(output)
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    if metadata.get("subject") != subject or int(metadata.get("seed", -1)) != seed or metadata.get("completion_status") != "completed":
        raise ValueError(f"{representation} {subject} seed {seed}: identity/completion mismatch")
    if representation == "stage3a":
        if metadata.get("run_type") != ("validation" if seed == 0 else "formal"):
            raise ValueError(f"Stage 3A {subject} seed {seed}: run type mismatch")
        if metadata.get("g_sem_graph_hash") != context["semantic_graph_hash"]:
            raise ValueError(f"Stage 3A {subject} seed {seed}: graph provenance mismatch")
        result = STAGE3A.validate_run_output(output, context)
    else:
        expected_identity = b_adapter._identity(context, subject, seed)
        for key, value in expected_identity.items():
            if metadata.get(key) != value:
                raise ValueError(f"Stage 3B {subject} seed {seed}: {key} mismatch")
        if metadata.get("run_type") != ("validation" if seed == 0 else "formal"):
            raise ValueError(f"Stage 3B {subject} seed {seed}: run type mismatch")
        if seed == 0:
            result = STAGE3A.validate_run_output(output, context)
        else:
            result = formal_runner.validate_formal_seed(subject, seed, output)
    if "front_size" not in result:
        front = pd.read_csv(output / "pareto_front_4d.csv", float_precision="round_trip")
        projected = pd.read_csv(output / "projected_front_3d.csv", float_precision="round_trip")
        stored_hv = json.loads((output / "projected_hypervolume.json").read_text(encoding="utf-8"))
        selected = json.loads((output / "selected_solution.json").read_text(encoding="utf-8"))
        result = {"front_size": len(front), "projected_front_size": len(projected), "projected_hv": float(stored_hv["stored_value"]), "selected_f_semantic": float(selected["selected_four_objective_row"]["f_semantic"])}
    return {
        "subject": subject,
        "seed": seed,
        "representation": representation,
        "result_dir": relative(output),
        "run_type": metadata.get("run_type"),
        "completion_status": metadata.get("completion_status"),
        "front_size": int(result["front_size"]),
        "projected_front_size": int(result["projected_front_size"]),
        "projected_hv": float(result["projected_hv"]),
        "selected_f_semantic": float(result["selected_f_semantic"]),
        "validation_status": "passed",
    }


def validate_stage2_output(subject: str, seed: int, context: dict[str, Any]) -> None:
    directory = stage2_dir(subject, seed)
    metadata = json.loads((directory / "run_metadata.json").read_text(encoding="utf-8"))
    if metadata.get("run_type") != "formal" or int(metadata.get("seed", -1)) != seed or int(metadata.get("class_count", -1)) != CLASS_COUNTS[subject]:
        raise ValueError(f"Stage 2 {subject} seed {seed}: metadata mismatch")
    if metadata.get("objective_order") != ["coupling", "negative_cohesion", "imbalance"]:
        raise ValueError(f"Stage 2 {subject} seed {seed}: objective order mismatch")
    selected = pd.read_csv(directory / "selected_solution.csv").iloc[0]
    partition = ensure_partition(directory / "selected_partition.csv", context["class_nodes"])
    if not np.isclose(float(selected["cluster_count"]), partition["cluster_id"].nunique(), rtol=0.0, atol=0.0):
        raise ValueError(f"Stage 2 {subject} seed {seed}: selected cluster count mismatch")


def load_stage3_record(directory: Path, context: dict[str, Any], representation: str) -> dict[str, Any]:
    front = pd.read_csv(directory / "pareto_front_4d.csv", float_precision="round_trip")
    projected = pd.read_csv(directory / "projected_front_3d.csv", float_precision="round_trip")
    selected = json.loads((directory / "selected_solution.json").read_text(encoding="utf-8"))
    partition = ensure_partition(directory / "selected_partition.csv", context["class_nodes"])
    stored_hv = json.loads((directory / "projected_hypervolume.json").read_text(encoding="utf-8"))
    bounds = context["bounds"]
    hv = recompute_projected_hv(projected, bounds)
    if not np.isclose(hv, float(stored_hv["stored_value"]), rtol=0.0, atol=HV_TOLERANCE):
        raise ValueError(f"{representation}: stored/recomputed Hypervolume mismatch in {directory}")
    values = stage3_selected_metrics(selected)
    own_semantic = semantic_value(context, partition)
    if not np.isclose(own_semantic, values["f_semantic"], rtol=0.0, atol=HV_TOLERANCE):
        raise ValueError(f"{representation}: selected semantic objective mismatch in {directory}")
    return {
        "front": front,
        "projected": projected,
        "selected": selected,
        "partition": partition,
        "metrics": values,
        "projected_hv": hv,
        "own_semantic": own_semantic,
        "front_fsemantic_min": float(front["f_semantic"].min()),
        "front_fsemantic_mean": float(front["f_semantic"].mean()),
        "front_fsemantic_max": float(front["f_semantic"].max()),
        "front_fsemantic_std": float(front["f_semantic"].std(ddof=0)),
        "front_fsemantic_unique": int(front["f_semantic"].nunique()),
    }


def load_all_contexts() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any] | None], dict[str, dict[str, Any]]]:
    b_contexts = {subject: b_adapter.load_context(subject) for subject in SUBJECTS}
    a_contexts = {subject: STAGE3A.load_context(subject) for subject in SUBJECTS}
    references: dict[str, dict[str, Any] | None] = {}
    reference_info: dict[str, dict[str, Any]] = {}
    for subject in SUBJECTS:
        references[subject], reference_info[subject] = load_reference(subject, b_contexts[subject]["class_nodes"])
        if len(b_contexts[subject]["class_nodes"]) != CLASS_COUNTS[subject]:
            raise ValueError(f"{subject}: class scope mismatch")
        if len(a_contexts[subject]["class_nodes"]) != CLASS_COUNTS[subject]:
            raise ValueError(f"Stage 3A {subject}: class scope mismatch")
    return b_contexts, a_contexts, references, reference_info


def pairwise_partition_stats(partitions: list[pd.DataFrame], class_nodes: pd.DataFrame) -> dict[str, Any]:
    values_ari: list[float] = []
    values_nmi: list[float] = []
    for left, right in itertools.combinations(partitions, 2):
        ari, nmi = partition_similarity(class_nodes, left, right)
        values_ari.append(float(ari)); values_nmi.append(float(nmi))
    identical = sum(1 for ari, nmi in zip(values_ari, values_nmi, strict=True) if np.isclose(ari, 1.0, atol=0.0) and np.isclose(nmi, 1.0, atol=0.0))
    return {
        "pair_count": len(values_ari),
        "identical_pair_count": identical,
        "identical_pair_proportion": identical / len(values_ari) if values_ari else float("nan"),
        "ari_mean": float(np.mean(values_ari)) if values_ari else float("nan"),
        "ari_median": float(np.median(values_ari)) if values_ari else float("nan"),
        "ari_min": float(np.min(values_ari)) if values_ari else float("nan"),
        "ari_max": float(np.max(values_ari)) if values_ari else float("nan"),
        "nmi_mean": float(np.mean(values_nmi)) if values_nmi else float("nan"),
        "nmi_median": float(np.median(values_nmi)) if values_nmi else float("nan"),
        "nmi_min": float(np.min(values_nmi)) if values_nmi else float("nan"),
        "nmi_max": float(np.max(values_nmi)) if values_nmi else float("nan"),
    }


def collect_records() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    b_contexts, a_contexts, references, reference_info = load_all_contexts()
    validation_rows: list[dict[str, Any]] = []
    inventory_rows: list[dict[str, Any]] = []
    stage2b_rows: list[dict[str, Any]] = []
    stage3ab_rows: list[dict[str, Any]] = []
    external_rows: list[dict[str, Any]] = []
    records: dict[str, Any] = {}
    for subject in SUBJECTS:
        records[subject] = {}
        for seed in SEEDS:
            validate_stage2_output(subject, seed, b_contexts[subject])
            a_valid = validate_stage3_output(subject, seed, a_contexts[subject], "stage3a")
            b_valid = validate_stage3_output(subject, seed, b_contexts[subject], "stage3b")
            validation_rows.extend([a_valid, b_valid])
            inventory_rows.append({
                "subject": subject, "seed": seed,
                "stage2_result_dir": relative(stage2_dir(subject, seed)),
                "stage3a_result_dir": relative(stage3a_dir(subject, seed)),
                "stage3b_result_dir": relative(stage3b_dir(subject, seed)),
                "stage3a_validation": a_valid["validation_status"],
                "stage3b_validation": b_valid["validation_status"],
                "source_layer_stage3b": "validation" if seed == 0 else "formal",
            })
            s2_dir = stage2_dir(subject, seed)
            s2_front = pd.read_csv(s2_dir / "pareto_front.csv", float_precision="round_trip")
            s2_metrics_json = json.loads((s2_dir / "run_metrics.json").read_text(encoding="utf-8"))
            s2_selected_row = pd.read_csv(s2_dir / "selected_solution.csv", float_precision="round_trip").iloc[0]
            s2_partition = ensure_partition(s2_dir / "selected_partition.csv", b_contexts[subject]["class_nodes"])
            s2_hv = recompute_stage2_hv(s2_front, _load_bounds(STORAGE_SUBJECT[subject]))
            if not np.isclose(s2_hv, float(s2_metrics_json["hypervolume"]), rtol=0.0, atol=HV_TOLERANCE):
                raise ValueError(f"Stage 2 {subject} seed {seed}: Hypervolume mismatch")
            a = load_stage3_record(stage3a_dir(subject, seed), a_contexts[subject], "Stage 3A")
            b = load_stage3_record(stage3b_dir(subject, seed), b_contexts[subject], "Stage 3B")
            s2_values = stage2_selected_metrics(s2_selected_row)
            s2_sem_b = semantic_value(b_contexts[subject], s2_partition)
            s2_sem_a = semantic_value(a_contexts[subject], s2_partition)
            a_sem_b = semantic_value(b_contexts[subject], a["partition"])
            b_sem_a = semantic_value(a_contexts[subject], b["partition"])
            ref = references[subject]
            s2_ext = external_metrics(b_contexts[subject]["class_nodes"], s2_partition, ref)
            a_ext = external_metrics(a_contexts[subject]["class_nodes"], a["partition"], ref)
            b_ext = external_metrics(b_contexts[subject]["class_nodes"], b["partition"], ref)
            for method, values in (("stage2", s2_ext), ("stage3a", a_ext), ("stage3b", b_ext)):
                external_rows.append({
                    "subject": subject, "seed": seed, "method": method,
                    "reference_status": reference_info[subject]["status"],
                    "reference_path": reference_info[subject]["path"] or "",
                    "reference_source": reference_info[subject]["source"] or "",
                    "reference_coverage": reference_info[subject]["coverage"],
                    "evaluation_policy": "saved selected partition only; no reselection",
                    **values,
                })
            records[subject][seed] = {
                "s2_dir": s2_dir, "s2_front": s2_front, "s2_selected_row": s2_selected_row,
                "s2_metrics_json": s2_metrics_json, "s2_partition": s2_partition, "s2_hv": s2_hv,
                "s2_values": s2_values, "s2_sem_b": s2_sem_b, "s2_sem_a": s2_sem_a,
                "a": a, "b": b, "a_sem_b": a_sem_b, "b_sem_a": b_sem_a,
                "s2_ext": s2_ext, "a_ext": a_ext, "b_ext": b_ext,
            }
            row = {
                "subject": subject, "seed": seed,
                "stage2_hv": s2_hv, "stage3b_projected_hv": b["projected_hv"], "delta_hv_stage3b_minus_stage2": b["projected_hv"] - s2_hv,
                "stage2_selected_semantic_on_stage3b": s2_sem_b, "stage3b_selected_f_semantic": b["own_semantic"],
                "delta_selected_f_semantic_stage3b_minus_stage2": b["own_semantic"] - s2_sem_b,
                "stage2_selected_solution_id": str(s2_selected_row["solution_id"]), "stage3b_selected_solution_id": b["selected"]["selected_solution_id"],
                "stage2_selected_is_injected_seed": bool(s2_selected_row["is_injected_seed"]), "stage3b_selected_is_injected_seed": bool(b["metrics"].get("is_injected_seed", b["selected"]["selected_four_objective_row"].get("is_injected_seed", False))),
                "stage3b_selected_seed_name": b["selected"]["selected_four_objective_row"].get("injected_seed_name", ""),
                "stage3b_front_size": len(b["front"]), "stage3b_projected_front_size": len(b["projected"]),
                "stage3b_front_f_semantic_min": b["front_fsemantic_min"], "stage3b_front_f_semantic_mean": b["front_fsemantic_mean"], "stage3b_front_f_semantic_max": b["front_fsemantic_max"], "stage3b_front_f_semantic_std": b["front_fsemantic_std"],
                "reference_status": reference_info[subject]["status"],
            }
            for metric in ("coupling", "cohesion", "imbalance", *POSTHOC_METRICS):
                row[f"stage2_{metric}"] = s2_values[metric]
                row[f"stage3b_{metric}"] = b["metrics"][metric]
                row[f"delta_{metric}_stage3b_minus_stage2"] = b["metrics"][metric] - s2_values[metric]
            for metric in EXTERNAL_METRICS:
                row[f"stage2_{metric}"] = s2_ext[metric]; row[f"stage3b_{metric}"] = b_ext[metric]
                row[f"delta_{metric}_stage3b_minus_stage2"] = b_ext[metric] - s2_ext[metric] if np.isfinite(s2_ext[metric]) and np.isfinite(b_ext[metric]) else float("nan")
            stage2b_rows.append(row)
            stage3ab_rows.append({
                "subject": subject, "seed": seed,
                "stage3a_projected_hv": a["projected_hv"], "stage3b_projected_hv": b["projected_hv"], "delta_hv_stage3b_minus_stage3a": b["projected_hv"] - a["projected_hv"],
                "stage3a_selected_f_semantic_on_stage3a": a["own_semantic"], "stage3a_selected_f_semantic_on_stage3b": a_sem_b,
                "stage3b_selected_f_semantic_on_stage3a": b_sem_a, "stage3b_selected_f_semantic_on_stage3b": b["own_semantic"],
                "delta_selected_f_semantic_stage3b_minus_stage3a_on_stage3b": b["own_semantic"] - a_sem_b,
                "delta_selected_f_semantic_stage3b_minus_stage3a_on_stage3a": b_sem_a - a["own_semantic"],
                "stage3a_selected_solution_id": a["selected"]["selected_solution_id"], "stage3b_selected_solution_id": b["selected"]["selected_solution_id"],
                "stage3a_front_size": len(a["front"]), "stage3b_front_size": len(b["front"]), "stage3a_projected_front_size": len(a["projected"]), "stage3b_projected_front_size": len(b["projected"]),
                "reference_status": reference_info[subject]["status"],
            })
    return pd.DataFrame(inventory_rows), pd.DataFrame(validation_rows), pd.DataFrame(stage2b_rows), pd.DataFrame(stage3ab_rows), records, b_contexts, a_contexts, reference_info


def make_validation_summary(inventory: pd.DataFrame, validation: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for subject in SUBJECTS:
        s = validation.loc[validation["subject"] == subject]
        rows.append({
            "subject": subject, "expected_seeds_per_representation": 30,
            "stage3a_valid": int(((s["representation"] == "stage3a") & (s["validation_status"] == "passed")).sum()),
            "stage3b_valid": int(((s["representation"] == "stage3b") & (s["validation_status"] == "passed")).sum()),
            "stage3b_seed0_source": "validation/seed_00", "stage3b_formal_seed_range": "1..29",
            "missing_or_failed": int((s["validation_status"] != "passed").sum()),
            "exact_paired_inventory": bool(len(inventory.loc[inventory["subject"] == subject]) == 30),
        })
    return pd.DataFrame(rows)


def make_stage3b_summary(records: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for subject in SUBJECTS:
        values = [records[subject][seed]["b"] for seed in SEEDS]
        for metric, getter in (
            ("projected_hv", lambda x: x["projected_hv"]),
            ("selected_f_semantic", lambda x: x["own_semantic"]),
            ("front_f_semantic_min", lambda x: x["front_fsemantic_min"]),
            ("front_f_semantic_max", lambda x: x["front_fsemantic_max"]),
            ("front_size", lambda x: len(x["front"])),
            ("projected_front_size", lambda x: len(x["projected"])),
        ):
            array = np.asarray([getter(item) for item in values], dtype=float)
            rows.append({"subject": subject, "metric": metric, "seed_count": len(array), "mean": float(array.mean()), "std": float(array.std(ddof=1)), "median": float(np.median(array)), "min": float(array.min()), "max": float(array.max())})
    return pd.DataFrame(rows)


def make_comparison_summary(frame: pd.DataFrame, comparison: str) -> pd.DataFrame:
    specs = [("projected_hv", "higher"), ("selected_f_semantic", "lower")]
    rows = []
    for subject in SUBJECTS:
        subset = frame.loc[frame["subject"] == subject]
        for metric, direction in specs:
            if comparison == "stage2_vs_stage3b":
                left = subset["stage2_hv"] if metric == "projected_hv" else subset["stage2_selected_semantic_on_stage3b"]
                right = subset["stage3b_projected_hv"] if metric == "projected_hv" else subset["stage3b_selected_f_semantic"]
            else:
                left = subset["stage3a_projected_hv"] if metric == "projected_hv" else subset["stage3a_selected_f_semantic_on_stage3a"]
                right = subset["stage3b_projected_hv"] if metric == "projected_hv" else subset["stage3b_selected_f_semantic_on_stage3b"]
            left = pd.to_numeric(left, errors="coerce").to_numpy(float); right = pd.to_numeric(right, errors="coerce").to_numpy(float)
            delta = right - left
            wins = int(np.sum(delta > TIE_TOLERANCE)) if direction == "higher" else int(np.sum(delta < -TIE_TOLERANCE))
            losses = int(np.sum(delta < -TIE_TOLERANCE)) if direction == "higher" else int(np.sum(delta > TIE_TOLERANCE))
            ties = len(delta) - wins - losses
            rows.append({"comparison": comparison, "subject": subject, "metric": metric, "direction": direction, "seed_count": len(delta), "mean_left": float(left.mean()), "mean_right": float(right.mean()), "mean_delta_right_minus_left": float(delta.mean()), "median_delta_right_minus_left": float(np.median(delta)), "std_delta": float(delta.std(ddof=1)), "wins_right": wins, "ties": ties, "losses_right": losses, "proportion_right_improved": wins / len(delta)})
    return pd.DataFrame(rows)


def make_statistics(stage2b: pd.DataFrame, stage3ab: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for comparison, frame in (("stage2_vs_stage3b", stage2b), ("stage3a_vs_stage3b", stage3ab)):
        for subject in SUBJECTS:
            subset = frame.loc[frame["subject"] == subject]
            for metric, direction in PRIMARY_SPECS:
                if comparison == "stage2_vs_stage3b":
                    left = subset["stage2_hv"].to_numpy(float) if metric == "projected_hv" else subset["stage2_selected_semantic_on_stage3b"].to_numpy(float)
                    right = subset["stage3b_projected_hv"].to_numpy(float) if metric == "projected_hv" else subset["stage3b_selected_f_semantic"].to_numpy(float)
                else:
                    left = subset["stage3a_projected_hv"].to_numpy(float) if metric == "projected_hv" else subset["stage3a_selected_f_semantic_on_stage3a"].to_numpy(float)
                    right = subset["stage3b_projected_hv"].to_numpy(float) if metric == "projected_hv" else subset["stage3b_selected_f_semantic_on_stage3b"].to_numpy(float)
                delta = _snap(right - left)
                wins = int(np.sum(delta > 0)) if direction == "higher" else int(np.sum(delta < 0))
                losses = int(np.sum(delta < 0)) if direction == "higher" else int(np.sum(delta > 0))
                ties = int(np.sum(delta == 0))
                if len(delta) == 0 or np.all(delta == 0):
                    statistic = p_value = effect = None; status = "degenerate_all_pairs_identical" if len(delta) else "unavailable"
                else:
                    test = wilcoxon(delta, zero_method="wilcox", alternative="two-sided", method="auto")
                    statistic = float(test.statistic); p_value = float(test.pvalue); effect = rank_biserial(delta); status = "tested"
                low, high, seed = bootstrap_ci(delta, comparison, subject, metric)
                rows.append({
                    "comparison": comparison, "subject": subject, "metric": metric, "direction_of_improvement": direction,
                    "delta_definition": "right representation minus left representation", "paired_n": len(delta), "left_mean": float(left.mean()), "right_mean": float(right.mean()), "mean_delta": float(delta.mean()), "median_delta": float(np.median(delta)), "wins_right": wins, "ties": ties, "losses_right": losses,
                    "wilcoxon_test": "paired Wilcoxon signed-rank, two-sided" if status == "tested" else "", "wilcoxon_statistic": statistic, "p_value_two_sided": p_value, "rank_biserial": effect, "bootstrap_mean_delta_ci_low": low, "bootstrap_mean_delta_ci_high": high, "bootstrap_resamples": BOOTSTRAP_RESAMPLES, "bootstrap_seed": seed, "status": status, "correction": "Holm within comparison family", "adjusted_p_value": None, "adjusted_alpha": 0.05,
                })
    for comparison in ("stage2_vs_stage3b", "stage3a_vs_stage3b"):
        indices = [i for i, row in enumerate(rows) if row["comparison"] == comparison and row["status"] == "tested"]
        adjusted = _holm([float(rows[i]["p_value_two_sided"]) for i in indices])
        for index, value in zip(indices, adjusted, strict=True):
            rows[index]["adjusted_p_value"] = value
            rows[index]["significant_after_holm"] = bool(value <= 0.05)
        for index, row in enumerate(rows):
            if row["comparison"] == comparison and "significant_after_holm" not in row:
                row["significant_after_holm"] = False
    return pd.DataFrame(rows)


def make_external_summary(external: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (subject, method, metric), group in external.melt(id_vars=["subject", "seed", "method"], value_vars=list(EXTERNAL_METRICS), var_name="metric", value_name="value").groupby(["subject", "method", "metric"], sort=True):
        values = pd.to_numeric(group["value"], errors="coerce").dropna().to_numpy(float)
        rows.append({"subject": subject, "method": method, "metric": metric, "available_seed_count": len(values), "mean": float(values.mean()) if len(values) else float("nan"), "median": float(np.median(values)) if len(values) else float("nan"), "min": float(values.min()) if len(values) else float("nan"), "max": float(values.max()) if len(values) else float("nan"), "reference_status": "available" if len(values) else "unavailable"})
    return pd.DataFrame(rows)


def make_selector_and_front(records: dict[str, Any], stage2b: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    selector_rows: list[dict[str, Any]] = []
    front_rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        for seed in SEEDS:
            record = records[subject][seed]; b = record["b"]
            front = b["front"]
            selected_f = b["own_semantic"]
            stage2_sem = record["s2_sem_b"]
            ranked = front.sort_values(["f_semantic", "solution_id"], kind="stable").reset_index(drop=True)
            selected_id = str(b["selected"]["selected_solution_id"])
            selected_rank = int(ranked.index[ranked["solution_id"].astype(str) == selected_id][0]) + 1 if selected_id in set(ranked["solution_id"].astype(str)) else None
            lower_front = int(np.sum(front["f_semantic"].to_numpy(float) < stage2_sem - TIE_TOLERANCE))
            lower_projected = int(np.sum(b["projected"].get("f_semantic", pd.Series(dtype=float)).to_numpy(float) < stage2_sem - TIE_TOLERANCE)) if "f_semantic" in b["projected"] else None
            selector_rows.append({"subject": subject, "seed": seed, "selected_solution_id": selected_id, "selected_is_injected_seed": bool(b["selected"]["selected_four_objective_row"].get("is_injected_seed", False)), "selected_injected_seed_name": b["selected"]["selected_four_objective_row"].get("injected_seed_name", ""), "selected_f_semantic": selected_f, "stage2_selected_f_semantic_on_stage3b": stage2_sem, "selected_minus_stage2_semantic": selected_f - stage2_sem, "selected_semantic_improved_over_stage2": selected_f < stage2_sem - TIE_TOLERANCE, "front_semantic_rank_ascending": selected_rank, "front_semantic_min": b["front_fsemantic_min"], "front_semantic_max": b["front_fsemantic_max"], "front_semantic_std": b["front_fsemantic_std"], "selected_weighted_modularity": b["metrics"]["weighted_modularity"], "selected_cluster_count": b["metrics"]["cluster_count"]})
            front_rows.append({"subject": subject, "seed": seed, "front_size": len(front), "projected_front_size": len(b["projected"]), "front_semantic_unique_count": b["front_fsemantic_unique"], "front_semantic_min": b["front_fsemantic_min"], "front_semantic_mean": b["front_fsemantic_mean"], "front_semantic_max": b["front_fsemantic_max"], "front_semantic_std": b["front_fsemantic_std"], "stage2_selected_f_semantic_on_stage3b": stage2_sem, "front_rows_better_than_stage2_selected": lower_front, "front_fraction_better_than_stage2_selected": lower_front / len(front), "projected_rows_better_than_stage2_selected": lower_projected, "selected_front_semantic_rank": selected_rank, "semantic_objective_used_for_selection": False, "diagnostic_note": "descriptive front contribution; semantic objective was not used by the representative selector"})
    return pd.DataFrame(selector_rows), pd.DataFrame(front_rows)


def make_stability(records: dict[str, Any], b_contexts: dict[str, Any], a_contexts: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for subject in SUBJECTS:
        for method, context_key in (("stage2", "b"), ("stage3a", "a"), ("stage3b", "b")):
            partitions = [records[subject][seed]["s2_partition"] if method == "stage2" else records[subject][seed][context_key]["partition"] for seed in SEEDS]
            context = b_contexts[subject] if method != "stage3a" else a_contexts[subject]
            stats = pairwise_partition_stats(partitions, context["class_nodes"])
            cluster_counts = np.asarray([int(part["cluster_id"].nunique()) for part in partitions], dtype=float)
            rows.append({"subject": subject, "method": method, **stats, "cluster_count_mean": float(cluster_counts.mean()), "cluster_count_std": float(cluster_counts.std(ddof=1)), "cluster_count_min": int(cluster_counts.min()), "cluster_count_max": int(cluster_counts.max())})
    return pd.DataFrame(rows)


def make_body_evidence_diagnostics(records: dict[str, Any], stage2b: pd.DataFrame) -> pd.DataFrame:
    input_quality = pd.read_csv(REPORT_ROOT / "input_quality_per_class.csv", dtype={"class_id": str})
    neighbour = pd.read_csv(REPORT_ROOT / "stage3a_vs_stage3b_neighbour_change.csv", dtype={"class_id": str})
    composition = pd.read_csv(REPORT_ROOT / "body_evidence_graph_change_diagnostics.csv", dtype={"class_id": str})
    if "body_token_count" not in composition:
        composition = input_quality.rename(columns={"body_token_count": "body_token_count"})
    mean_retention = stage2b.groupby("subject")["stage3b_cluster_count"].mean().to_dict() if "stage3b_cluster_count" in stage2b else {}
    rows = []
    for _, row in composition.iterrows():
        subject, class_id = str(row["subject"]), str(row["class_id"])
        n = neighbour.loc[(neighbour["subject"] == subject) & (neighbour["class_id"] == class_id)]
        base = row.to_dict()
        base["formal_seed_count"] = 30
        base["formal_stage3b_selected_cluster_count_mean"] = mean_retention.get(subject, float("nan"))
        base["formal_diagnostic_note"] = "class-level evidence composition joined to frozen graph/input diagnostics; descriptive association only"
        if not n.empty:
            base["frozen_neighbour_retention"] = float(n.iloc[0]["neighbour_retention"])
        rows.append(base)
    frame = pd.DataFrame(rows)
    numeric_pairs = [
        ("body_token_count", "frozen_neighbour_retention", "body_tokens_vs_neighbour_retention"),
        ("embedding_shift_cosine_distance", "frozen_neighbour_retention", "embedding_shift_vs_neighbour_retention"),
    ]
    summary_rows = []
    for subject in SUBJECTS:
        subset = frame.loc[frame["subject"] == subject]
        for left, right, label in numeric_pairs:
            if left in subset and right in subset:
                x = pd.to_numeric(subset[left], errors="coerce"); y = pd.to_numeric(subset[right], errors="coerce"); mask = x.notna() & y.notna()
                corr = spearmanr(x[mask], y[mask]) if mask.sum() >= 2 else None
                summary_rows.append({"subject": subject, "association": label, "n": int(mask.sum()), "spearman_rho": float(corr.statistic) if corr else float("nan"), "p_value": float(corr.pvalue) if corr else float("nan"), "interpretation": "descriptive association; not causal"})
    return pd.concat([frame, pd.DataFrame(summary_rows)], ignore_index=True, sort=False)


def write_comparison_reports(stage2b: pd.DataFrame, stage3ab: pd.DataFrame, stats: pd.DataFrame, external: pd.DataFrame, selector: pd.DataFrame, front: pd.DataFrame, stability: pd.DataFrame, b_contexts: dict[str, Any], a_contexts: dict[str, Any], records: dict[str, Any], reference_info: dict[str, Any]) -> None:
    write_frame(REPORT_ROOT / "stage2_vs_stage3b_paired_per_seed.csv", stage2b)
    write_frame(REPORT_ROOT / "stage3a_vs_stage3b_paired_per_seed.csv", stage3ab)
    write_frame(REPORT_ROOT / "stage2_vs_stage3b_summary.csv", make_comparison_summary(stage2b, "stage2_vs_stage3b"))
    write_frame(REPORT_ROOT / "stage3a_vs_stage3b_summary.csv", make_comparison_summary(stage3ab, "stage3a_vs_stage3b"))
    write_frame(REPORT_ROOT / "formal_statistical_tests.csv", stats)
    write_frame(REPORT_ROOT / "formal_external_metrics_per_seed.csv", external)
    write_frame(REPORT_ROOT / "formal_external_metrics_summary.csv", make_external_summary(external))
    write_frame(REPORT_ROOT / "formal_selector_behaviour.csv", selector)
    write_frame(REPORT_ROOT / "formal_front_semantic_contribution.csv", front)
    write_frame(REPORT_ROOT / "formal_partition_stability.csv", stability)
    # ``body_evidence_graph_change_diagnostics.csv`` is a frozen graph-stage
    # input-quality artifact.  Read-only formal analysis must not replace its
    # per-class composition rows with a different schema.
    stage2_summary = make_comparison_summary(stage2b, "stage2_vs_stage3b")
    ab_summary = make_comparison_summary(stage3ab, "stage3a_vs_stage3b")
    lines = ["# Stage 2 versus Stage 3B paired summary", "", "All rows use the same seed IDs 0–29. Stage 3B seed 0 is the frozen validation output and seeds 1–29 are formal outputs. Hypervolume is the frozen projected 3D quantity; semantic values are evaluated on the Stage 3B graph. This is a paired result diagnostic, not decomposition-quality evidence.", "", "| subject | metric | Stage 2 mean | Stage 3B mean | mean delta | wins/ties/losses |", "|---|---|---:|---:|---:|---:|"]
    for row in stage2_summary.to_dict("records"):
        lines.append(f"| {row['subject']} | {row['metric']} | {row['mean_left']:.6f} | {row['mean_right']:.6f} | {row['mean_delta_right_minus_left']:.6f} | {row['wins_right']}/{row['ties']}/{row['losses_right']} |")
    write_text(REPORT_ROOT / "stage2_vs_stage3b_summary.md", "\n".join(lines))
    lines = ["# Stage 3A versus Stage 3B paired and cross-semantic evaluation", "", "Stage 3A and Stage 3B use the same frozen optimizer contract. The cross-semantic columns evaluate saved partitions on the other frozen semantic graph; no representative was reselected.", "", "| subject | metric | Stage 3A mean | Stage 3B mean | mean delta | wins/ties/losses |", "|---|---|---:|---:|---:|---:|"]
    for row in ab_summary.to_dict("records"):
        lines.append(f"| {row['subject']} | {row['metric']} | {row['mean_left']:.6f} | {row['mean_right']:.6f} | {row['mean_delta_right_minus_left']:.6f} | {row['wins_right']}/{row['ties']}/{row['losses_right']} |")
    write_text(REPORT_ROOT / "stage3a_vs_stage3b_summary.md", "\n".join(lines))
    stats_lines = ["# Formal paired statistical tests", "", "The frozen paired protocol is two-sided Wilcoxon signed-rank tests on the 30 paired seed values, with arithmetic delta defined as right representation minus left representation. Holm correction is applied separately within each planned comparison family (six rows: three subjects × two primary metrics). The primary metrics are projected 3D Hypervolume and selected semantic objective. Rank-biserial effect sizes and deterministic 10,000-resample bootstrap mean-delta intervals are descriptive supplements.", "", "| comparison | subject | metric | p | Holm p | rank-biserial | status |", "|---|---|---|---:|---:|---:|---|"]
    for row in stats.to_dict("records"):
        fmt = lambda x: "N/A" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{float(x):.6g}"
        stats_lines.append(f"| {row['comparison']} | {row['subject']} | {row['metric']} | {fmt(row['p_value_two_sided'])} | {fmt(row['adjusted_p_value'])} | {fmt(row['rank_biserial'])} | {row['status']} |")
    write_text(REPORT_ROOT / "formal_statistical_tests.md", "\n".join(stats_lines))
    write_text(REPORT_ROOT / "formal_selector_behaviour.md", "# Formal selector behaviour\n\nThe selector remains the frozen highest-weighted-modularity rule over feasible projected-front candidates. `selected_is_injected_seed` and `selected_injected_seed_name` are reported for each seed. The semantic objective is diagnostic only and is not a selector input.\n\nThe CSV is the complete subject-by-seed record.")
    write_text(REPORT_ROOT / "formal_front_semantic_contribution.md", "# Formal front semantic contribution\n\nCounts describe how many saved four-dimensional front or projected-front rows have a lower Stage 3B semantic objective than the saved Stage 2 representative evaluated on the Stage 3B graph. They do not imply that semantic objective values caused a selected solution; the selector remains structural.")
    write_text(REPORT_ROOT / "formal_partition_stability.md", "# Formal partition stability\n\nStability is computed from pairwise ARI/NMI among the 30 saved representative partitions for each subject and method. Cluster counts are descriptive; no labels or partitions were changed.")


def cross_semantic_report(stage3ab: pd.DataFrame, records: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for subject in SUBJECTS:
        for seed in SEEDS:
            r = records[subject][seed]; a, b = r["a"], r["b"]
            rows.extend([
                {"subject": subject, "seed": seed, "partition": "stage3a_selected", "evaluation_graph": "stage3a", "f_semantic": a["own_semantic"]},
                {"subject": subject, "seed": seed, "partition": "stage3a_selected", "evaluation_graph": "stage3b", "f_semantic": r["a_sem_b"]},
                {"subject": subject, "seed": seed, "partition": "stage3b_selected", "evaluation_graph": "stage3a", "f_semantic": r["b_sem_a"]},
                {"subject": subject, "seed": seed, "partition": "stage3b_selected", "evaluation_graph": "stage3b", "f_semantic": b["own_semantic"]},
            ])
    return pd.DataFrame(rows)


def empty_nonempty_report(records: dict[str, Any]) -> pd.DataFrame:
    quality = pd.read_csv(REPORT_ROOT / "input_quality_per_class.csv", dtype={"class_id": str})
    neighbour = pd.read_csv(REPORT_ROOT / "stage3a_vs_stage3b_neighbour_change.csv", dtype={"class_id": str})
    rows = []
    for subject in SUBJECTS:
        q = quality.loc[quality["subject"] == subject, ["class_id", "body_empty"]].copy()
        n = neighbour.loc[neighbour["subject"] == subject].copy()
        if "body_empty" not in n.columns:
            n = n.merge(q, on="class_id", how="left")
        def _is_empty(value: Any) -> bool:
            return str(value).strip().lower() in {"true", "1", "yes"}
        for group, subset in n.groupby(n["body_empty"].map(lambda v: "empty" if _is_empty(v) else "non_empty"), sort=True):
            rows.append({"subject": subject, "body_group": group, "class_count": len(subset), "mean_neighbour_retention": float(subset["neighbour_retention"].mean()), "median_neighbour_retention": float(subset["neighbour_retention"].median()), "zero_retention_class_count": int((subset["retained_neighbour_count"] == 0).sum()), "all_neighbours_retained_class_count": int((subset["retained_neighbour_count"] == subset["stage3a_degree"]).sum()), "mean_embedding_shift_cosine_distance": float(subset["embedding_shift_cosine_distance"].mean()), "mean_degree_change": float(subset["degree_change"].mean()), "diagnostic_note": "empty-body changes may include section-marker and explicit-empty-template effects" if group == "empty" else "non-empty body group"})
    return pd.DataFrame(rows)


def graph_and_manifest_reports(records: dict[str, Any], reference_info: dict[str, Any]) -> None:
    graph_quality = pd.read_csv(REPORT_ROOT / "semantic_graph_quality_per_subject.csv")
    overlap = pd.read_csv(REPORT_ROOT / "semantic_structural_overlap.csv")
    random = pd.read_csv(REPORT_ROOT / "semantic_graph_random_baseline.csv") if (REPORT_ROOT / "semantic_graph_random_baseline.csv").exists() else pd.DataFrame()
    inventory = []
    hash_rows = []
    for subject in SUBJECTS:
        for seed in SEEDS:
            for representation, directory in (("stage2", stage2_dir(subject, seed)), ("stage3a", stage3a_dir(subject, seed)), ("stage3b", stage3b_dir(subject, seed))):
                for path in sorted(directory.iterdir()):
                    if path.is_file():
                        hash_rows.append({"subject": subject, "seed": seed, "representation": representation, "path": relative(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
            inventory.append({"subject": subject, "seed": seed, "stage2_path": relative(stage2_dir(subject, seed)), "stage3a_path": relative(stage3a_dir(subject, seed)), "stage3b_path": relative(stage3b_dir(subject, seed)), "stage3b_seed0_is_validation": seed == 0, "stage3b_seed1_to_29_are_formal": 1 <= seed <= 29})
    write_frame(REPORT_ROOT / "formal_artifact_hashes.csv", pd.DataFrame(hash_rows))
    write_frame(REPORT_ROOT / "formal_seed_inventory.csv", pd.DataFrame(inventory))
    manifest = {
        "experiment_name": "stage3_declaration_method_body", "experiment_id": "stage3_declaration_method_body", "representation_id": "declaration_method_body_v1", "task": "Stage 3B formal robustness experiment", "task_start_head": TASK_START_HEAD, "analysis_commit": git_head(), "generated_at_utc": utc_now(), "subjects": list(SUBJECTS), "class_counts": CLASS_COUNTS, "paired_seeds": list(SEEDS), "stage3b_seed0": "results/<subject>/05_stage3_declaration_method_body/validation/seed_00", "stage3b_formal_seeds": "results/<subject>/05_stage3_declaration_method_body/formal/seed_01..29", "optimizer_run": False, "embeddings_regenerated": False, "semantic_graphs_regenerated": False, "optimizer_contract": "frozen Stage 2/Stage 3A NSGA-II adapter; semantic objective used in search but not representative selection", "primary_metrics": ["projected 3D Hypervolume", "selected f_semantic"], "statistical_protocol": "paired two-sided Wilcoxon signed-rank; Holm within each six-row comparison family; rank-biserial effect size; deterministic bootstrap descriptive intervals", "source_provenance": {subject: {"input_aggregate_sha256": b_adapter.EXPECTED_INPUT_HASHES[subject], "embedding_aggregate_sha256": b_adapter.EXPECTED_EMBEDDING_HASHES[subject], "graph_sha256": b_adapter.EXPECTED_GRAPH_HASHES[subject], "class_mapping_sha256": b_adapter.EXPECTED_MAPPING_HASHES[subject], "stage3b_config_sha256": sha256_file(STAGE3B_CONFIG), "stage3b_graph_source_commit": b_adapter.EXPECTED_GRAPH_SOURCE_COMMIT} for subject in SUBJECTS}, "reports": ["formal_seed_inventory.csv", "formal_validation_summary.md", "formal_validation_per_seed.csv", "formal_stage3b_summary.csv", "stage2_vs_stage3b_paired_per_seed.csv", "stage3a_vs_stage3b_paired_per_seed.csv", "stage3a_vs_stage3b_cross_semantic_evaluation.csv", "formal_statistical_tests.csv", "formal_external_metrics_per_seed.csv", "formal_external_metrics_summary.csv", "formal_selector_behaviour.csv", "formal_front_semantic_contribution.csv", "formal_partition_stability.csv", "formal_runtime_summary.csv", "formal_reproducibility_spotcheck.csv", "formal_artifact_hashes.csv"]}
    write_json(REPORT_ROOT / "formal_experiment_manifest.json", manifest)


def spotcheck(records: dict[str, Any], b_contexts: dict[str, Any]) -> pd.DataFrame:
    registered = (("jpetstore", 7), ("daytrader", 13), ("xerces", 29))
    rows = []
    temp_root = Path(tempfile.mkdtemp(prefix="stage3b-formal-spotcheck-"))
    try:
        for subject, seed in registered:
            canonical = stage3b_dir(subject, seed)
            output = b_adapter.output_dir(subject, root=temp_root, seed=seed)
            b_adapter.run_seed(subject, seed, output, run_type="formal_spotcheck", allow_formal=True)
            formal_runner._write_formal_provenance(output, b_contexts[subject], subject, seed, f"formal spot check {subject} seed {seed}")
            STAGE3A.validate_run_output(output, b_contexts[subject])
            details = []
            for name in FORMAL_SCIENTIFIC_FILES:
                left, right = (canonical / name).read_bytes(), (output / name).read_bytes()
                details.append({"file": name, "byte_identical": left == right, "canonical_sha256": sha256_bytes(left), "spotcheck_sha256": sha256_bytes(right)})
            rows.append({"subject": subject, "seed": seed, "temporary_output": str(output), "files_compared": len(details), "byte_identical_files": sum(item["byte_identical"] for item in details), "all_byte_identical": all(item["byte_identical"] for item in details), "details": json.dumps(details, sort_keys=True)})
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    return pd.DataFrame(rows)


def runtime_summary(records: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for subject in SUBJECTS:
        runtimes = []
        evaluations = []
        for seed in SEEDS:
            metadata = json.loads((stage3b_dir(subject, seed) / "run_metadata.json").read_text(encoding="utf-8"))
            runtimes.append(float(metadata["runtime_seconds"])); evaluations.append(int(metadata["evaluations"]))
        rows.append({"subject": subject, "seed_count": len(runtimes), "runtime_seconds_mean": float(np.mean(runtimes)), "runtime_seconds_std": float(np.std(runtimes, ddof=1)), "runtime_seconds_median": float(np.median(runtimes)), "runtime_seconds_min": float(np.min(runtimes)), "runtime_seconds_max": float(np.max(runtimes)), "evaluations_all_equal": len(set(evaluations)) == 1, "evaluations": evaluations[0]})
    return pd.DataFrame(rows)


def write_final_reports(inventory: pd.DataFrame, validation: pd.DataFrame, stage3b_summary: pd.DataFrame, stats: pd.DataFrame, external_summary: pd.DataFrame, selector: pd.DataFrame, front: pd.DataFrame, stability: pd.DataFrame, spot: pd.DataFrame, reference_info: dict[str, Any]) -> None:
    validation_summary = make_validation_summary(inventory, validation)
    write_frame(REPORT_ROOT / "formal_validation_per_seed.csv", validation)
    write_frame(REPORT_ROOT / "formal_validation_summary.csv", validation_summary)
    write_frame(REPORT_ROOT / "formal_stage3b_summary.csv", stage3b_summary)
    write_frame(REPORT_ROOT / "formal_reproducibility_spotcheck.csv", spot)
    lines = ["# Stage 3B formal seed validation", "", "Seed 0 is the accepted validation output; seeds 1–29 are the formal outputs. Every Stage 3A and Stage 3B result was independently loaded and validated against its frozen contract. No seed 0 formal rerun occurred.", "", "| subject | Stage 3A valid | Stage 3B valid | expected paired seeds |", "|---|---:|---:|---:|"]
    for row in validation_summary.to_dict("records"):
        lines.append(f"| {row['subject']} | {row['stage3a_valid']} | {row['stage3b_valid']} | 30 |")
    lines += ["", "Formal result sets are complete only when all 30 paired seed IDs are present and pass. The complete inventory is in `formal_seed_inventory.csv`; the per-seed audit is in `formal_validation_per_seed.csv`."]
    write_text(REPORT_ROOT / "formal_validation_summary.md", "\n".join(lines))
    lines = ["# Stage 3B formal robustness summary", "", "The table reports descriptive 30-seed distributions for the frozen Stage 3B representation. Seed 0 is validation and seeds 1–29 are formal; all are retained in the paired 30-seed analysis.", "", "| subject | metric | mean | std | median | min | max |", "|---|---|---:|---:|---:|---:|---:|"]
    for row in stage3b_summary.to_dict("records"):
        lines.append(f"| {row['subject']} | {row['metric']} | {row['mean']:.6f} | {row['std']:.6f} | {row['median']:.6f} | {row['min']:.6f} | {row['max']:.6f} |")
    write_text(REPORT_ROOT / "formal_stage3b_summary.md", "\n".join(lines))
    write_text(REPORT_ROOT / "formal_external_metrics_summary.md", "# Formal external metrics\n\nExternal metrics are evaluation-only. The frozen repository reference is complete for DayTrader and unavailable for JPetStore and Xerces; no reference mapping was invented and no result was reselected.")
    if "subject" in spot.columns:
        spot_lines = "\n".join(f"- {row['subject']} seed {int(row['seed'])}: {int(row['byte_identical_files'])}/{int(row['files_compared'])} scientific files byte-identical — **{'PASS' if row['all_byte_identical'] else 'FAIL'}**." for row in spot.to_dict("records"))
    else:
        spot_lines = "- Spot checks were skipped by command-line request."
    write_text(REPORT_ROOT / "formal_reproducibility_spotcheck.md", "# Formal reproducibility spot checks\n\nRegistered checks rerun JPetStore seed 7, DayTrader seed 13, and Xerces seed 29 into a temporary destination outside the repository. Scientific output files were compared byte-for-byte; variable runtime metadata, logs, provenance timestamps, and artifact ledgers were excluded.\n\n" + spot_lines)
    write_text(REPORT_ROOT / "formal_final_conclusions.md", "# Stage 3B formal conclusions\n\nThe 30-seed experiment is complete as a reproducibility and paired descriptive dataset. Results are reported per subject and seed, with Stage 2 and Stage 3A cross-semantic evaluations kept separate from primary comparisons. The formal evidence does not by itself establish decomposition-quality superiority. The next thesis-analysis step must use the frozen reports and must not change the input, graph, optimizer, seed, or evaluation contracts.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-spotcheck", action="store_true")
    args = parser.parse_args()
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    inventory, validation, stage2b, stage3ab, records, b_contexts, a_contexts, reference_info = collect_records()
    stage3b_summary = make_stage3b_summary(records)
    stats = make_statistics(stage2b, stage3ab)
    external = pd.read_csv(REPORT_ROOT / "formal_external_metrics_per_seed.csv") if (REPORT_ROOT / "formal_external_metrics_per_seed.csv").exists() else None
    # External rows are regenerated directly from the record store to prevent
    # a prior report from becoming an input to the formal analysis.
    external_rows = []
    for subject in SUBJECTS:
        for seed in SEEDS:
            r = records[subject][seed]
            for method, values in (("stage2", r["s2_ext"]), ("stage3a", r["a_ext"]), ("stage3b", r["b_ext"])):
                external_rows.append({"subject": subject, "seed": seed, "method": method, "reference_status": reference_info[subject]["status"], "reference_path": reference_info[subject]["path"] or "", "reference_source": reference_info[subject]["source"] or "", "reference_coverage": reference_info[subject]["coverage"], "evaluation_policy": "saved selected partition only; no reselection", **values})
    external = pd.DataFrame(external_rows)
    selector, front = make_selector_and_front(records, stage2b)
    stability = make_stability(records, b_contexts, a_contexts)
    cross = cross_semantic_report(stage3ab, records)
    empty = empty_nonempty_report(records)
    body_diag = make_body_evidence_diagnostics(records, stage2b)
    write_frame(REPORT_ROOT / "stage3a_vs_stage3b_cross_semantic_evaluation.csv", cross)
    write_frame(REPORT_ROOT / "empty_vs_nonempty_body_graph_change.csv", empty)
    write_comparison_reports(stage2b, stage3ab, stats, external, selector, front, stability, b_contexts, a_contexts, records, reference_info)
    write_frame(REPORT_ROOT / "body_evidence_graph_change_diagnostics.csv", body_diag)
    spot = spotcheck(records, b_contexts) if not args.skip_spotcheck else pd.DataFrame([{"status": "skipped", "reason": "--skip-spotcheck"}])
    write_final_reports(inventory, validation, stage3b_summary, stats, make_external_summary(external), selector, front, stability, spot, reference_info)
    graph_and_manifest_reports(records, reference_info)
    # The manifest writer occurs after the report writers so its report list
    # describes the actual complete report set.
    runtime = runtime_summary(records)
    write_frame(REPORT_ROOT / "formal_runtime_summary.csv", runtime)
    # Replace the manifest's analysis timestamp and record elapsed analysis.
    manifest_path = REPORT_ROOT / "formal_experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["analysis_elapsed_seconds"] = time.perf_counter() - start
    manifest["spotcheck_pass"] = bool(not spot.empty and spot.get("all_byte_identical", pd.Series(dtype=bool)).all()) if "all_byte_identical" in spot else False
    manifest["formal_validation_pass"] = bool((validation["validation_status"] == "passed").all() and len(validation) == 180)
    write_json(manifest_path, manifest)
    print(json.dumps({"subjects": list(SUBJECTS), "paired_seeds": 30, "validation_rows": len(validation), "spotchecks": len(spot), "elapsed_seconds": time.perf_counter() - start}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
