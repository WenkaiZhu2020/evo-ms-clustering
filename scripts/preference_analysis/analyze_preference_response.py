#!/usr/bin/env python3
"""Post-hoc preference-response analysis over frozen saved fronts.

This module deliberately reads existing Stage 2, Stage 3A, and Stage 3B
artifacts only.  It never calls an optimizer, writes a scientific result
directory, regenerates an embedding, or rebuilds a semantic graph.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.stats import rankdata, spearmanr, wilcoxon

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.evaluation.partition_metrics import partition_similarity  # noqa: E402
from evo_ms.evaluation.reference_metrics import (  # noqa: E402
    calculate_reference_metrics,
    load_reference_mapping,
    reference_mapping_diagnostics,
)
from scripts.stage3_method_body import analyze_formal_stage3b as frozen  # noqa: E402


SUBJECTS = ("jpetstore", "daytrader", "xerces")
STAGES = ("stage2", "stage3a", "stage3b")
SEEDS = tuple(range(30))
STORAGE_SUBJECT = {"jpetstore": "jpetstore", "daytrader": "daytrader", "xerces": "xerces-j"}
CLASS_COUNTS = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
BUDGETS = (0.000, 0.005, 0.010, 0.025, 0.050, 0.100, 0.150, 0.200)
KEY_BUDGETS = (0.000, 0.010, 0.025, 0.050, 0.100)
TARGETS = (0.05, 0.10, 0.20, 0.30)
TOL = 1e-12
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20260718
REPORT_ROOT = ROOT / "reports/preference_analysis"
STAGE2_CONFIG = ROOT / "configs/experiments/02_stage2_nsga_structure_only.yml"
STAGE3A_CONFIG = ROOT / "configs/experiments/04_stage3_semantic.yml"
STAGE3B_CONFIG = ROOT / "configs/experiments/05_stage3_declaration_method_body.yml"
BOUNDS_CONFIG = ROOT / "configs/experiments/stage2_robustness_bounds.yml"
REFERENCE_PATHS = {"daytrader": ROOT / "data/references/daytrader_reference_services.csv"}

EXPECTED_STAGE3B = {
    "config_hash": "c1af2191baefddee68a7f41c97c29f7799df4bcf5372d9e9cf44a52a3b510286",
    "input_hash": {
        "jpetstore": "2d9007f75a14f4a4ed6152563241b898837b6c12b66a98a2464b4cc3f969a921",
        "daytrader": "da53d434b820e3c25bc69df63ced807cd0113d412fa36acc9694d1a97631d655",
        "xerces": "65488944220cc3a503994d6f2289e0f7bdc06c619351a2e8243bca243538c8a3",
    },
    "embedding_hash": {
        "jpetstore": "e7615e77d4f3258df46e499fd94c2dbb59bee03c0d2f6c3bb822c3aff4577139",
        "daytrader": "db7ef8d78036796c5c5c79cc95f54eb1b9b9974de5e6f035d1929391b415f66c",
        "xerces": "36bdeca0e1ef32f36631c30ebbf86a1875621490e92f9b4a7fd0860755676236",
    },
    "mapping_hash": {
        "jpetstore": "83c4643fdad9661f2e409563f8e496b792575ecc72ac548ba8c2f13fb46e019f",
        "daytrader": "6a995ce5caedd3fa567a09491378a629f7cdef61e41107cf25360bbd75d311d1",
        "xerces": "7e204d1865c1ddb228cc42f6f61519e280076590a92f0965e4f1fc765b77a4ab",
    },
    "graph_hash": {
        "jpetstore": "2dcf34b9e931cfdb0eec205f7da5bd0f24f6956be98d838369e12573026a9214",
        "daytrader": "c7761509fe91acb398ee5bc3a0c71e3a368a34aae316b04c5907d34bced1714d",
        "xerces": "7d5d45f6e7cc46cdb57c57688bc89b5e90e0ecea7390833a7acb2e8887d935a5",
    },
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def write_df(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.17g", lineterminator="\n")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def stage2_dir(subject: str, seed: int) -> Path:
    return ROOT / "results" / STORAGE_SUBJECT[subject] / "03_stage2_nsga" / "robustness_final_30seeds" / f"seed_{seed:02d}"


def stage3_dir(stage: str, subject: str, seed: int) -> Path:
    layer = "validation" if seed == 0 else "formal"
    part = "04_stage3_semantic" if stage == "stage3a" else "05_stage3_declaration_method_body"
    return ROOT / "results" / subject / part / layer / f"seed_{seed:02d}"


def raw_class_nodes_path(subject: str) -> Path:
    return ROOT / "data/extracted" / STORAGE_SUBJECT[subject] / "class_nodes.csv"


def leiden_path(subject: str) -> Path:
    return ROOT / "results" / STORAGE_SUBJECT[subject] / "01_stage1_leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv"


def graph_path(stage: str, subject: str) -> Path:
    if stage == "stage2":
        return ROOT / "data/extracted" / STORAGE_SUBJECT[subject] / "structural_dependencies.csv"
    if stage == "stage3a":
        return ROOT / "results" / subject / "04_stage3_semantic/graph/semantic_edges.csv"
    return ROOT / "data/semantic_graphs/declaration_method_body" / subject / "semantic_edges.csv"


def canonical_partition_key(partition: pd.DataFrame) -> tuple[int, ...]:
    ordered = partition.loc[:, ["class_id", "cluster_id"]].copy()
    ordered["class_id"] = ordered["class_id"].astype(str)
    ordered = ordered.sort_values("class_id", kind="stable")
    remap: dict[Any, int] = {}
    result: list[int] = []
    for value in ordered["cluster_id"].tolist():
        key = int(value)
        if key not in remap:
            remap[key] = len(remap)
        result.append(remap[key])
    return tuple(result)


def vector_partition(class_nodes: pd.DataFrame, vector: str | list[int]) -> pd.DataFrame:
    values = json.loads(vector) if isinstance(vector, str) else vector
    if len(values) != len(class_nodes):
        raise ValueError(f"label vector length {len(values)} != class count {len(class_nodes)}")
    return pd.DataFrame({
        "class_id": class_nodes["class_id"].astype(str).tolist(),
        "class_name": class_nodes["class_name"].astype(str).tolist(),
        "cluster_id": [int(value) for value in values],
    })


def ensure_partition(path: Path, class_nodes: pd.DataFrame) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"class_id": str})
    frame["class_id"] = frame["class_id"].astype(str)
    frame["cluster_id"] = frame["cluster_id"].astype(int)
    expected = set(class_nodes["class_id"].astype(str))
    if set(frame["class_id"]) != expected or frame["class_id"].duplicated().any():
        raise ValueError(f"partition scope mismatch: {path}")
    if "class_name" not in frame:
        names = class_nodes.set_index("class_id")["class_name"].to_dict()
        frame["class_name"] = frame["class_id"].map(names)
    return frame.loc[:, ["class_id", "class_name", "cluster_id"]]


def relative_gain(baseline: float, value: float) -> float:
    if abs(baseline) <= TOL:
        if abs(value - baseline) <= TOL:
            return 0.0
        return float("nan")
    return float((baseline - value) / abs(baseline))


def loss_q(q_leiden: float, q_value: float) -> float:
    if abs(q_leiden) <= TOL:
        raise ValueError("Q_L is zero; frozen relative modularity-loss definition is undefined")
    return float((q_leiden - q_value) / abs(q_leiden))


def metric_row(context: dict[str, Any], partition: pd.DataFrame) -> dict[str, float]:
    mapping = dict(zip(partition["class_id"].astype(str), partition["cluster_id"].astype(int), strict=True))
    labels = np.asarray([mapping[str(value)] for value in context["class_nodes"]["class_id"]], dtype=int)
    fast = context["_fast_raw"]
    same = labels[fast["source"]] == labels[fast["target"]]
    internal = float(fast["weights"][same].sum())
    total = float(fast["total"])
    external = total - internal
    unique, inverse, counts = np.unique(labels, return_inverse=True, return_counts=True)
    internal_by_cluster = np.bincount(inverse[fast["source"]][same], weights=fast["weights"][same], minlength=len(unique))
    cohesion_values = np.divide(2.0 * internal_by_cluster, counts * (counts - 1), out=np.zeros(len(unique), dtype=float), where=counts > 1)
    degrees = fast["degrees"]
    degree_by_cluster = np.bincount(inverse, weights=degrees, minlength=len(unique))
    doubled = 2.0 * total
    modularity = 0.0 if total == 0.0 else float((2.0 * internal - float(np.sum(degree_by_cluster ** 2)) / doubled) / doubled)
    sizes = counts.astype(float)
    mean_size = float(np.mean(sizes)) if len(sizes) else 0.0
    imbalance = 0.0 if mean_size == 0.0 else float(np.std(sizes) / mean_size)
    singleton_count = int(np.sum(counts == 1))
    return {
        "weighted_modularity": modularity,
        "internal_edge_weight_ratio": 0.0 if total == 0.0 else internal / total,
        "internal_external_edge_ratio": internal if external == 0.0 and internal > 0.0 else (0.0 if external == 0.0 else internal / external),
        "cluster_count": int(len(unique)),
        "average_cluster_size": float(np.mean(sizes)) if len(sizes) else 0.0,
        "max_cluster_size": int(np.max(counts)) if len(counts) else 0,
        "min_cluster_size": int(np.min(counts)) if len(counts) else 0,
        "max_cluster_ratio": 0.0 if len(counts) == 0 else float(np.max(counts) / len(labels)),
        "singleton_ratio": 0.0 if len(labels) == 0 else float(singleton_count / len(labels)),
        "cluster_size_cv": imbalance,
        "coupling": 0.0 if total == 0.0 else float(external / total),
        "cohesion": float(np.mean(cohesion_values)) if len(cohesion_values) else 0.0,
        "imbalance": imbalance,
    }


def semantic_value(context: dict[str, Any], partition: pd.DataFrame) -> float:
    mapping = dict(zip(partition["class_id"].astype(str), partition["cluster_id"].astype(int), strict=True))
    labels = np.asarray([mapping[str(value)] for value in context["class_nodes"]["class_id"]], dtype=int)
    fast = context["_fast_semantic"]
    inside = labels[fast["source"]] == labels[fast["target"]]
    return float(1.0 - float(fast["weights"][inside].sum()) / float(fast["total"]))


def prepare_fast_context(context: dict[str, Any]) -> None:
    """Prepare O(E) vector arrays once; preserve the frozen metric formulas."""
    ids = context["class_nodes"]["class_id"].astype(str).tolist()
    index = {value: position for position, value in enumerate(ids)}
    raw = context["raw_edges"]
    source = raw["source"].astype(str).map(index).to_numpy(dtype=int)
    target = raw["target"].astype(str).map(index).to_numpy(dtype=int)
    weights = raw["raw_weight"].to_numpy(dtype=float)
    degrees = np.bincount(np.concatenate([source, target]), weights=np.concatenate([weights, weights]), minlength=len(ids))
    context["_fast_raw"] = {"source": source, "target": target, "weights": weights, "total": float(weights.sum()), "degrees": degrees}
    semantic = context["semantic_edges"]
    s_source = semantic["class_id_a"].astype(str).map(index).to_numpy(dtype=int)
    s_target = semantic["class_id_b"].astype(str).map(index).to_numpy(dtype=int)
    s_weights = semantic["weight"].to_numpy(dtype=float)
    context["_fast_semantic"] = {"source": s_source, "target": s_target, "weights": s_weights, "total": float(s_weights.sum())}


def load_reference(subject: str, class_nodes: pd.DataFrame) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    path = REFERENCE_PATHS.get(subject)
    if path is None or not path.exists():
        return None, {"status": "unavailable", "reason": "no frozen complete reference is registered", "path": None, "coverage": None}
    mapping = load_reference_mapping(path)
    diagnostics = reference_mapping_diagnostics(class_nodes, mapping)
    coverage = float(diagnostics["reference_coverage_ratio"])
    if coverage != 1.0 or not diagnostics["unmapped_extracted_classes"].empty or not diagnostics["reference_classes_not_found"].empty:
        return None, {"status": "unavailable", "reason": "reference scope is incomplete", "path": rel(path), "coverage": coverage}
    return mapping, {"status": "available", "reason": "complete frozen reference coverage", "path": rel(path), "coverage": 1.0}


def external_metrics(class_nodes: pd.DataFrame, partition: pd.DataFrame, reference: pd.DataFrame | None) -> dict[str, float]:
    names = ("mojofm_vs_reference", "pairwise_precision", "pairwise_recall", "pairwise_f1", "ari_vs_reference", "nmi_vs_reference", "reference_coverage_ratio")
    if reference is None:
        return {name: float("nan") for name in names}
    values = calculate_reference_metrics(class_nodes, partition, reference)
    return {name: float(values.get(name, float("nan"))) for name in names}


def bootstrap_ci(values: np.ndarray, key: str) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return float("nan"), float("nan")
    seed = int.from_bytes(hashlib.sha256(f"{BOOTSTRAP_SEED}|{key}".encode()).digest()[:8], "big") % (2**32)
    rng = np.random.default_rng(seed)
    samples = values[rng.integers(0, len(values), size=(BOOTSTRAP_RESAMPLES, len(values)))]
    estimate = samples.mean(axis=1)
    return float(np.percentile(estimate, 2.5)), float(np.percentile(estimate, 97.5))


def rank_biserial(values: np.ndarray) -> float | None:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    values = values[np.abs(values) > TOL]
    if len(values) == 0:
        return None
    ranks = rankdata(np.abs(values), method="average")
    return float((ranks[values > 0].sum() - ranks[values < 0].sum()) / ranks.sum())


def _objective_matrix(frame: pd.DataFrame, stage: str) -> np.ndarray:
    if stage == "stage2":
        return frame[["coupling", "cohesion", "imbalance"]].assign(cohesion=lambda x: -x["cohesion"]).to_numpy(float)
    return frame[["coupling", "cohesion", "imbalance", "f_semantic"]].assign(cohesion=lambda x: -x["cohesion"]).to_numpy(float)


def _dominates(left: np.ndarray, right: np.ndarray) -> bool:
    return bool(np.all(left <= right + TOL) and np.any(left < right - TOL))


def _recompute_front_check(frame: pd.DataFrame, stage: str) -> None:
    matrix = _objective_matrix(frame, stage)
    for i in range(len(matrix)):
        if any(_dominates(matrix[j], matrix[i]) for j in range(len(matrix)) if j != i):
            raise ValueError(f"saved {stage} front has a dominated row: {frame.iloc[i]['solution_id']}")


def _candidate_frame(stage: str, subject: str, seed: int, context: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    class_nodes = context["class_nodes"]
    directory = stage2_dir(subject, seed) if stage == "stage2" else stage3_dir(stage, subject, seed)
    front_name = "pareto_front.csv" if stage == "stage2" else "pareto_front_4d.csv"
    front = pd.read_csv(directory / front_name, float_precision="round_trip")
    if len(front) == 0 or front["solution_id"].duplicated().any():
        raise ValueError(f"{stage} {subject} seed {seed}: invalid front")
    # The repository's accepted retained-front files are the authoritative
    # candidate sets.  They can contain crowding/duplicate rows that are
    # dominated under a strict recheck; post-hoc analysis must not rewrite or
    # silently filter that frozen set.
    projected_ids: set[str] = set()
    selected_id: str
    if stage == "stage2":
        selected = pd.read_csv(directory / "selected_solution.csv").iloc[0]
        selected_id = str(selected["solution_id"])
    else:
        projected = pd.read_csv(directory / "projected_front_3d.csv", float_precision="round_trip")
        projected_ids = set(projected["solution_id"].astype(str))
        selected_json = json.loads((directory / "selected_solution.json").read_text(encoding="utf-8"))
        selected_id = str(selected_json["selected_solution_id"])
        metadata = json.loads((directory / "run_metadata.json").read_text(encoding="utf-8"))
        if stage == "stage3b":
            if metadata.get("representation_id") != "declaration_method_body_v1" or metadata.get("config_hash") != EXPECTED_STAGE3B["config_hash"]:
                raise ValueError(f"Stage 3B {subject} seed {seed}: frozen identity mismatch")
            for key, values in (("input_aggregate_sha256", EXPECTED_STAGE3B["input_hash"]), ("embedding_aggregate_sha256", EXPECTED_STAGE3B["embedding_hash"]), ("class_mapping_sha256", EXPECTED_STAGE3B["mapping_hash"]), ("graph_sha256", EXPECTED_STAGE3B["graph_hash"])):
                if metadata.get(key) != values[subject]:
                    raise ValueError(f"Stage 3B {subject} seed {seed}: {key} mismatch")
    rows: list[dict[str, Any]] = []
    for record in front.to_dict("records"):
        partition = vector_partition(class_nodes, record["label_vector"])
        metrics = metric_row(context, partition)
        for name in ("coupling", "cohesion", "imbalance"):
            if not np.isclose(float(record[name]), metrics[name], rtol=0.0, atol=2e-12):
                raise ValueError(f"{stage} {subject} seed {seed}: {name} changed for {record['solution_id']}")
        row = {
            "subject": subject, "stage": stage, "seed": int(seed),
            "solution_id": str(record["solution_id"]), "label_vector": str(record["label_vector"]),
            "is_injected_seed": bool(record.get("is_injected_seed", False)),
            "injected_seed_name": "" if pd.isna(record.get("injected_seed_name")) else str(record.get("injected_seed_name", "")),
            "injected_seed_category": "" if pd.isna(record.get("injected_seed_category")) else str(record.get("injected_seed_category", "")),
            "projected_membership": stage == "stage2" or str(record["solution_id"]) in projected_ids,
            **metrics,
        }
        if stage != "stage2":
            row["f_semantic"] = float(record["f_semantic"])
            calculated = semantic_value(context, partition)
            if not np.isclose(calculated, row["f_semantic"], rtol=0.0, atol=2e-12):
                raise ValueError(f"{stage} {subject} seed {seed}: semantic objective changed for {record['solution_id']}")
        else:
            row["f_semantic"] = float("nan")
        # The metric helper supplies an internal placeholder solution_id;
        # source-artifact identity must remain the saved front identity.
        row["solution_id"] = str(record["solution_id"])
        row["label_vector"] = str(record["label_vector"])
        row["subject"] = subject
        row["stage"] = stage
        row["seed"] = int(seed)
        rows.append(row)
    candidate = pd.DataFrame(rows)
    if selected_id not in set(candidate["solution_id"]):
        raise ValueError(f"{stage} {subject} seed {seed}: selected solution is not in front")
    return candidate, {"selected_id": selected_id, "front_size": len(candidate), "projected_size": int(candidate["projected_membership"].sum())}


def load_sources() -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    contexts: dict[str, Any] = {}
    references: dict[str, Any] = {}
    inventory: list[dict[str, Any]] = []
    integrity_paths: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        b_context = frozen.b_adapter.load_context(subject)
        a_context = frozen.STAGE3A.load_context(subject)
        if len(b_context["class_nodes"]) != CLASS_COUNTS[subject] or len(a_context["class_nodes"]) != CLASS_COUNTS[subject]:
            raise ValueError(f"{subject}: class scope mismatch")
        prepare_fast_context(b_context)
        prepare_fast_context(a_context)
        contexts[subject] = {"stage2": b_context, "stage3a": a_context, "stage3b": b_context}
        references[subject] = load_reference(subject, b_context["class_nodes"])
        mapping_hash = sha256_file(raw_class_nodes_path(subject))
        for stage in STAGES:
            for seed in SEEDS:
                directory = stage2_dir(subject, seed) if stage == "stage2" else stage3_dir(stage, subject, seed)
                front_path = directory / ("pareto_front.csv" if stage == "stage2" else "pareto_front_4d.csv")
                label_path = directory / ("pareto_labels.csv.xz" if stage == "stage2" else "partition_labels.csv")
                if not front_path.is_file() or not label_path.is_file():
                    raise FileNotFoundError(f"missing {stage} source for {subject} seed {seed}")
                front = pd.read_csv(front_path, nrows=None, float_precision="round_trip")
                if stage == "stage2":
                    labels = pd.read_csv(label_path, compression="xz", nrows=None, dtype={"class_id": str})
                    expected = set(b_context["class_nodes"]["class_id"].astype(str))
                    if set(labels["class_id"].astype(str)) != expected:
                        raise ValueError(f"Stage 2 label scope mismatch: {label_path}")
                else:
                    labels = pd.read_csv(label_path, nrows=None, dtype={"class_id": str})
                    expected = set(b_context["class_nodes"]["class_id"].astype(str))
                    if set(labels["class_id"].astype(str)) != expected:
                        raise ValueError(f"{stage} label scope mismatch: {label_path}")
                inventory.append({
                    "subject": subject, "stage": stage, "seed": seed,
                    "source_kind": "validation" if seed == 0 and stage != "stage2" else "formal",
                    "front_path": rel(front_path), "label_path": rel(label_path),
                    "front_sha256": sha256_file(front_path), "label_sha256": sha256_file(label_path),
                    "front_rows": len(front), "label_rows": len(labels), "class_count": CLASS_COUNTS[subject],
                    "class_mapping_path": rel(raw_class_nodes_path(subject)), "class_mapping_sha256": mapping_hash,
                    "provenance_status": "validated_source_scope",
                })
                integrity_paths.extend([
                    {"artifact_group": f"{stage}_front", "subject": subject, "seed": seed, "path": front_path},
                    {"artifact_group": f"{stage}_labels", "subject": subject, "seed": seed, "path": label_path},
                ])
        integrity_paths.append({"artifact_group": "leiden_baseline", "subject": subject, "seed": "", "path": leiden_path(subject)})
        for stage in ("stage3a", "stage3b"):
            integrity_paths.append({"artifact_group": f"{stage}_semantic_graph", "subject": subject, "seed": "", "path": graph_path(stage, subject)})
        integrity_paths.append({"artifact_group": "raw_structural_graph", "subject": subject, "seed": "", "path": graph_path("stage2", subject)})
    inventory_frame = pd.DataFrame(inventory)
    integrity: list[dict[str, Any]] = []
    for item in integrity_paths:
        path = item["path"]
        if not path.is_file():
            raise FileNotFoundError(path)
        integrity.append({**{key: value for key, value in item.items() if key != "path"}, "path": rel(path), "sha256_before": sha256_file(path), "bytes_before": path.stat().st_size})
    return contexts, inventory_frame, pd.DataFrame(integrity), references


def add_baseline_metrics(context: dict[str, Any]) -> dict[str, Any]:
    partition = context["stage1_raw_baseline"]
    metrics = metric_row(context, partition)
    result = {"partition": partition, "key": canonical_partition_key(partition), "semantic": semantic_value(context, partition), **metrics}
    return result


def select_candidate(frame: pd.DataFrame, rule: str, budget: float | None = None, projected_only: bool = False) -> pd.Series | None:
    eligible = frame
    if budget is not None:
        eligible = eligible.loc[eligible["q_loss"] <= float(budget) + TOL]
    if projected_only:
        eligible = eligible.loc[eligible["projected_membership"]]
    if eligible.empty:
        return None
    if rule == "balance":
        ordered = eligible.sort_values(["imbalance", "weighted_modularity", "solution_id"], ascending=[True, False, True], kind="stable")
    elif rule == "semantic":
        ordered = eligible.sort_values(["f_semantic", "weighted_modularity", "solution_id"], ascending=[True, False, True], kind="stable")
    elif rule == "modularity":
        ordered = eligible.sort_values(["weighted_modularity", "imbalance", "solution_id"], ascending=[False, True, True], kind="stable")
    elif rule == "extreme_balance":
        ordered = eligible.sort_values(["imbalance", "weighted_modularity", "solution_id"], ascending=[True, False, True], kind="stable")
    elif rule == "extreme_semantic":
        ordered = eligible.sort_values(["f_semantic", "weighted_modularity", "solution_id"], ascending=[True, False, True], kind="stable")
    else:
        raise ValueError(rule)
    return ordered.iloc[0]


def profile_record(candidate: pd.Series | None, subject: str, stage: str, seed: int, profile: str, budget: float | None, baseline: dict[str, Any], conservative_key: tuple[int, ...], status: str = "selected") -> dict[str, Any]:
    base = {"subject": subject, "stage": stage, "seed": seed, "profile": profile, "budget": budget, "status": status}
    if candidate is None:
        return {**base, "available_candidate_count": 0}
    record = {**base, "available_candidate_count": int(candidate.get("available_candidate_count", 0))}
    for key in candidate.index:
        if key in {"partition_key"}:
            continue
        value = candidate[key]
        if isinstance(value, (np.generic,)):
            value = value.item()
        record[key] = value
    record.update({
        "realised_modularity_loss": float(candidate["q_loss"]),
        "permitted_modularity_loss": budget,
        "gain_imbalance": float(candidate["gain_imbalance"]),
        "gain_semantic": float(candidate["gain_semantic"]) if stage != "stage2" else float("nan"),
        "equals_leiden": bool(candidate["equals_leiden"]),
        "equals_conservative": bool(candidate["partition_key"] == conservative_key),
        "above_leiden_modularity": bool(candidate["q_loss"] < -TOL),
        "exact_leiden_modularity": bool(abs(candidate["q_loss"]) <= TOL),
        "baseline_weighted_modularity": baseline["weighted_modularity"],
        "baseline_imbalance": baseline["imbalance"],
        "baseline_semantic": baseline["semantic"] if stage != "stage2" else float("nan"),
    })
    return record


def selected_partition(context: dict[str, Any], record: dict[str, Any]) -> pd.DataFrame:
    return vector_partition(context["class_nodes"], record["label_vector"])


def profile_rows_for(candidates: dict[tuple[str, str, int], pd.DataFrame], contexts: dict[str, Any], stages: tuple[str, ...], rule: str, budgets: tuple[float, ...], baselines: dict[tuple[str, str], dict[str, Any]], conservative_keys: dict[tuple[str, str, int], tuple[int, ...]], profile_name: str) -> pd.DataFrame:
    rows = []
    for stage in stages:
        for subject in SUBJECTS:
            for seed in SEEDS:
                frame = candidates[(stage, subject, seed)]
                baseline = baselines[(stage, subject)]
                conservative_key = conservative_keys[(stage, subject, seed)]
                for budget in budgets:
                    eligible = frame.loc[frame["q_loss"] <= budget + TOL]
                    selected = select_candidate(frame, rule, budget)
                    if selected is not None:
                        selected = selected.copy()
                        selected["available_candidate_count"] = len(eligible)
                    rows.append(profile_record(selected, subject, stage, seed, f"{profile_name}_{budget:.3f}", budget, baseline, conservative_key, "selected" if selected is not None else "unavailable"))
    return pd.DataFrame(rows)


def summarize_profiles(frame: pd.DataFrame, gain_column: str, summary_name: str) -> pd.DataFrame:
    rows = []
    for (stage, subject, budget), group in frame.groupby(["stage", "subject", "budget"], dropna=False, sort=True):
        selected = group.loc[group["status"] == "selected"]
        values = selected[gain_column].to_numpy(float) if gain_column in selected else np.asarray([], float)
        values = values[np.isfinite(values)]
        low, high = bootstrap_ci(values, f"{summary_name}|{stage}|{subject}|{budget}")
        rows.append({
            "summary": summary_name, "stage": stage, "subject": subject, "budget": budget,
            "seed_count": 30, "eligible_seed_count": int(len(selected)), "availability_rate": float(len(selected) / 30),
            "unavailable_seed_count": int(30 - len(selected)), "eligible_candidate_count_median": float(selected["available_candidate_count"].median()) if len(selected) else float("nan"),
            "eligible_candidate_count_min": int(selected["available_candidate_count"].min()) if len(selected) else 0,
            "eligible_candidate_count_max": int(selected["available_candidate_count"].max()) if len(selected) else 0,
            "median_gain": float(np.median(values)) if len(values) else float("nan"), "mean_gain": float(np.mean(values)) if len(values) else float("nan"),
            "iqr_gain": float(np.percentile(values, 75) - np.percentile(values, 25)) if len(values) else float("nan"),
            "std_gain": float(np.std(values, ddof=1)) if len(values) > 1 else float("nan"),
            "min_gain": float(np.min(values)) if len(values) else float("nan"), "max_gain": float(np.max(values)) if len(values) else float("nan"),
            "bootstrap_mean_ci_low": low, "bootstrap_mean_ci_high": high,
            "positive_count": int(np.sum(values > TOL)), "at_least_5pct_count": int(np.sum(values >= .05 - TOL)),
            "at_least_10pct_count": int(np.sum(values >= .10 - TOL)), "at_least_20pct_count": int(np.sum(values >= .20 - TOL)),
            "at_least_30pct_count": int(np.sum(values >= .30 - TOL)),
            "median_realised_modularity_loss": float(selected["realised_modularity_loss"].median()) if len(selected) else float("nan"),
            "mean_realised_modularity_loss": float(selected["realised_modularity_loss"].mean()) if len(selected) else float("nan"),
            "max_realised_modularity_loss": float(selected["realised_modularity_loss"].max()) if len(selected) else float("nan"),
            "median_coupling": float(selected["coupling"].median()) if len(selected) else float("nan"),
            "median_cohesion": float(selected["cohesion"].median()) if len(selected) else float("nan"),
            "median_cluster_count": float(selected["cluster_count"].median()) if len(selected) else float("nan"),
            "median_singleton_ratio": float(selected["singleton_ratio"].median()) if len(selected) else float("nan"),
        })
    return pd.DataFrame(rows)


def mechanism_reports(contexts: dict[str, Any], candidates: dict[tuple[str, str, int], pd.DataFrame], selected_ids: dict[tuple[str, str, int], str]) -> None:
    stage2_rows = []
    for subject in SUBJECTS:
        ctx = contexts[subject]["stage2"]
        leiden = add_baseline_metrics(ctx)
        for seed in SEEDS:
            frame = candidates[("stage2", subject, seed)]
            matrix = _objective_matrix(frame, "stage2")
            leiden_vec = np.asarray([leiden["coupling"], -leiden["cohesion"], leiden["imbalance"]], float)
            present = bool(frame["equals_leiden"].any())
            dominators = [str(frame.iloc[i]["solution_id"]) for i in range(len(frame)) if _dominates(matrix[i], leiden_vec)]
            selected_id = selected_ids[("stage2", subject, seed)]
            selected = frame.loc[frame["solution_id"] == selected_id].iloc[0]
            category = "A" if present and bool(selected["equals_leiden"]) else "D" if present else "B" if dominators else "C"
            stage2_rows.append({"subject": subject, "seed": seed, "front_size": len(frame), "leiden_in_retained_front": present, "leiden_dominated": bool(dominators), "leiden_dominator_solution_ids": ";".join(dominators), "selected_solution_id": selected_id, "selected_by_modularity_max": bool(selected["equals_leiden"]), "selected_equals_leiden": bool(selected["equals_leiden"]), "another_retained_higher_modularity": bool((frame["weighted_modularity"] > leiden["weighted_modularity"] + TOL).any()), "population_size_limit_plausible": bool(len(frame) >= 100), "classification": category, "classification_definition": "A=present+selected; B=absent+dominated; C=absent+not dominated; D=present+not selected"})
    stage2_frame = pd.DataFrame(stage2_rows)
    write_df(REPORT_ROOT / "stage2_leiden_front_mechanism_per_seed.csv", stage2_frame)
    expected = {"jpetstore": {"A": 30, "B": 0, "C": 0, "D": 0}, "daytrader": {"A": 1, "B": 24, "C": 5, "D": 0}, "xerces": {"A": 12, "B": 10, "C": 8, "D": 0}}
    actual = stage2_frame.groupby(["subject", "classification"]).size().unstack(fill_value=0).to_dict("index")
    for subject, values in expected.items():
        got = {key: int(actual.get(subject, {}).get(key, 0)) for key in "ABCD"}
        if got != values:
            raise ValueError(f"Stage 2 A/B/C/D mismatch for {subject}: expected {values}, got {got}")
    lines = ["# Stage 2 Leiden/front mechanism", "", "Classification is computed from the retained final feasible front using exact canonical partition equality and the frozen three-objective minimisation orientation.", "", "| subject | A present+selected | B absent+dominated | C absent+not dominated | D present+not selected |", "|---|---:|---:|---:|---:|"]
    for subject in SUBJECTS:
        counts = stage2_frame.loc[stage2_frame.subject == subject, "classification"].value_counts()
        lines.append(f"| {subject} | {int(counts.get('A', 0))} | {int(counts.get('B', 0))} | {int(counts.get('C', 0))} | {int(counts.get('D', 0))} |")
    lines += ["", "Empirically, whenever the exact Leiden partition remained in the retained final feasible front, it was also selected by the modularity-max rule. This is an empirical result, not a theorem; absence from the retained front is not treated as proof of global non-attainability."]
    write_md(REPORT_ROOT / "stage2_leiden_front_mechanism_summary.md", "\n".join(lines))

    stage3_rows = []
    for stage in ("stage3a", "stage3b"):
        for subject in SUBJECTS:
            ctx = contexts[subject][stage]
            leiden = add_baseline_metrics(ctx)
            for seed in SEEDS:
                frame = candidates[(stage, subject, seed)]
                four_matrix = _objective_matrix(frame, stage)
                leiden_vec = np.asarray([leiden["coupling"], -leiden["cohesion"], leiden["imbalance"], leiden["semantic"]], float)
                dominant4 = [str(frame.iloc[i]["solution_id"]) for i in range(len(frame)) if _dominates(four_matrix[i], leiden_vec)]
                projected = frame.loc[frame["projected_membership"]].copy()
                projected_matrix = projected[["coupling", "cohesion", "imbalance"]].assign(cohesion=lambda x: -x["cohesion"]).to_numpy(float)
                leiden3 = leiden_vec[:3]
                dominant3 = [str(projected.iloc[i]["solution_id"]) for i in range(len(projected)) if _dominates(projected_matrix[i], leiden3)]
                selected_id = selected_ids[(stage, subject, seed)]
                selected = frame.loc[frame["solution_id"] == selected_id].iloc[0]
                eligible = projected
                higher = bool((eligible["weighted_modularity"] > leiden["weighted_modularity"] + TOL).any())
                stage3_rows.append({"subject": subject, "stage": stage, "seed": seed, "four_d_front_size": len(frame), "projected_3d_front_size": len(projected), "population_size_limit_plausible": len(frame) >= 100, "leiden_in_four_d_front": bool(frame["equals_leiden"].any()), "leiden_dominated_in_four_d": bool(dominant4), "leiden_four_d_dominator_solution_ids": ";".join(dominant4), "leiden_in_projected_3d_front": bool(projected["equals_leiden"].any()), "leiden_dominated_in_projected_3d": bool(dominant3), "leiden_projected_dominator_solution_ids": ";".join(dominant3), "leiden_eligible_for_projected_selector": bool(projected["equals_leiden"].any()), "another_eligible_solution_higher_modularity": higher, "selected_solution_id": selected_id, "selected_equals_leiden": bool(selected["equals_leiden"]), "selected_weighted_modularity": float(selected["weighted_modularity"]), "four_d_classification": "present" if bool(frame["equals_leiden"].any()) else "absent_dominated" if dominant4 else "absent_not_dominated", "projected_selection_classification": "present_selected" if bool(selected["equals_leiden"]) else "absent_or_not_selected"})
    stage3_frame = pd.DataFrame(stage3_rows)
    write_df(REPORT_ROOT / "stage3_leiden_front_mechanism_per_seed.csv", stage3_frame)
    lines = ["# Stage 3A/Stage 3B Leiden/front mechanism", "", "The search-level four-dimensional retained front and the projected structural three-dimensional selector input are reported separately. Leiden presence, dominance, eligibility, and final modularity-max selection are distinct checks.", "", "| stage | subject | 4D present | 4D dominated | projected present | selected equals Leiden |", "|---|---|---:|---:|---:|---:|"]
    for (stage, subject), group in stage3_frame.groupby(["stage", "subject"], sort=True):
        lines.append(f"| {stage} | {subject} | {int(group.leiden_in_four_d_front.sum())} | {int(group.leiden_dominated_in_four_d.sum())} | {int(group.leiden_in_projected_3d_front.sum())} | {int(group.selected_equals_leiden.sum())} |")
    write_md(REPORT_ROOT / "stage3_leiden_front_mechanism_summary.md", "\n".join(lines))


def baseline_report(contexts: dict[str, Any], references: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    rows = []
    baselines: dict[tuple[str, str], dict[str, Any]] = {}
    for stage in STAGES:
        for subject in SUBJECTS:
            ctx = contexts[subject][stage]
            value = add_baseline_metrics(ctx)
            baselines[(stage, subject)] = value
            ext = external_metrics(ctx["class_nodes"], value["partition"], references[subject][0])
            rows.append({"stage": stage, "subject": subject, "baseline": "raw_leiden", "weighted_modularity": value["weighted_modularity"], "imbalance": value["imbalance"], "coupling": value["coupling"], "cohesion": value["cohesion"], "cluster_count": value["cluster_count"], "max_cluster_ratio": value["max_cluster_ratio"], "singleton_ratio": value["singleton_ratio"], "semantic_objective": value["semantic"] if stage != "stage2" else float("nan"), "relative_modularity_loss_definition": "(Q_L-Q(x))/abs(Q_L), unclamped", "reference_status": references[subject][1]["status"], **ext})
    write_df(REPORT_ROOT / "leiden_baseline_metrics.csv", pd.DataFrame(rows))
    return baselines


def attach_derived(candidates: dict[tuple[str, str, int], pd.DataFrame], baselines: dict[tuple[str, str], dict[str, Any]], conservative_keys: dict[tuple[str, str, int], tuple[int, ...]]) -> None:
    global frozen_context_class_nodes
    for (stage, subject, seed), frame in list(candidates.items()):
        # All subject mappings have the same frozen order for this subject; the
        # temporary global is used only by the compact vector-key helper.
        frozen_context_class_nodes = frozen_contexts[subject][stage]["class_nodes"]
        baseline = baselines[(stage, subject)]
        frame = frame.copy()
        frame["q_loss"] = frame["weighted_modularity"].map(lambda value: loss_q(baseline["weighted_modularity"], float(value)))
        frame["gain_imbalance"] = frame["imbalance"].map(lambda value: relative_gain(baseline["imbalance"], float(value)))
        frame["gain_semantic"] = frame["f_semantic"].map(lambda value: relative_gain(baseline["semantic"], float(value)) if stage != "stage2" else float("nan"))
        frame["partition_key"] = [canonical_partition_key(vector_partition(frozen_context_class_nodes, value)) for value in frame["label_vector"]]
        frame["equals_leiden"] = frame["partition_key"].map(lambda value: value == baseline["key"])
        frame["equals_conservative"] = frame["partition_key"].map(lambda value: value == conservative_keys[(stage, subject, seed)])
        candidates[(stage, subject, seed)] = frame


def source_selected_ids(candidates: dict[tuple[str, str, int], pd.DataFrame], contexts: dict[str, Any]) -> tuple[dict[tuple[str, str, int], str], dict[tuple[str, str, int], tuple[int, ...]]]:
    selected_ids: dict[tuple[str, str, int], str] = {}
    keys: dict[tuple[str, str, int], tuple[int, ...]] = {}
    for stage in STAGES:
        for subject in SUBJECTS:
            for seed in SEEDS:
                directory = stage2_dir(subject, seed) if stage == "stage2" else stage3_dir(stage, subject, seed)
                if stage == "stage2":
                    selected_ids[(stage, subject, seed)] = str(pd.read_csv(directory / "selected_solution.csv").iloc[0]["solution_id"])
                else:
                    selected_ids[(stage, subject, seed)] = str(json.loads((directory / "selected_solution.json").read_text())["selected_solution_id"])
            for seed in SEEDS:
                frame = candidates[(stage, subject, seed)]
                selected = frame.loc[frame["solution_id"] == selected_ids[(stage, subject, seed)]].iloc[0]
                keys[(stage, subject, seed)] = canonical_partition_key(vector_partition(contexts[subject][stage]["class_nodes"], selected["label_vector"]))
    return selected_ids, keys


def summary_md(title: str, frame: pd.DataFrame, gain_name: str) -> str:
    lines = [f"# {title}", "", "Values are computed from the frozen retained candidate set. A profile is unavailable when no retained candidate meets the stated budget; it is not silently replaced by the conservative profile.", "", "| stage | subject | budget | availability | median gain | IQR | median realised Q loss | ≥5% | ≥10% | ≥20% |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in frame.loc[frame["budget"].isin(KEY_BUDGETS)].sort_values(["stage", "subject", "budget"]).to_dict("records"):
        lines.append(f"| {row['stage']} | {row['subject']} | {float(row['budget']):.1%} | {row['availability_rate']:.3f} | {row['median_gain']:.4f} | {row['iqr_gain']:.4f} | {row['median_realised_modularity_loss']:.4f} | {int(row['at_least_5pct_count'])} | {int(row['at_least_10pct_count'])} | {int(row['at_least_20pct_count'])} |")
    lines += ["", f"The gain column is `{gain_name}`. The budget is a maximum permitted relative modularity loss, not a claim that the selected profile realises the full budget."]
    return "\n".join(lines)


def realised_loss_report(frames: list[tuple[str, pd.DataFrame]]) -> None:
    rows = []
    for name, frame in frames:
        for (stage, subject, budget), group in frame.groupby(["stage", "subject", "budget"], sort=True):
            selected = group.loc[group.status == "selected", "realised_modularity_loss"].to_numpy(float)
            selected = selected[np.isfinite(selected)]
            rows.append({"profile_family": name, "stage": stage, "subject": subject, "budget": budget, "permitted_loss": budget, "selected_count": len(selected), "median_realised_loss": float(np.median(selected)) if len(selected) else float("nan"), "mean_realised_loss": float(np.mean(selected)) if len(selected) else float("nan"), "iqr_realised_loss": float(np.percentile(selected, 75)-np.percentile(selected,25)) if len(selected) else float("nan"), "maximum_realised_loss": float(np.max(selected)) if len(selected) else float("nan"), "solutions_above_leiden": int(np.sum(selected < -TOL)), "solutions_equal_leiden_within_tolerance": int(np.sum(np.abs(selected) <= TOL))})
    write_df(REPORT_ROOT / "realised_modularity_loss.csv", pd.DataFrame(rows))


def secondary_cost_reports(profile_frames: list[tuple[str, pd.DataFrame]], baseline: dict[tuple[str, str], dict[str, Any]], conservative: dict[tuple[str, str, int], pd.Series]) -> None:
    rows = []
    for family, frame in profile_frames:
        group = frame.loc[(frame["budget"] == 0.050) & (frame["status"] == "selected")].copy()
        for record in group.to_dict("records"):
            b = baseline[(record["stage"], record["subject"])]
            c = conservative[(record["stage"], record["subject"], int(record["seed"]))]
            item = {"profile_family": family, **{key: record.get(key) for key in ("stage", "subject", "seed", "budget", "solution_id")}, "status": record["status"]}
            for metric in ("coupling", "cohesion", "imbalance", "weighted_modularity", "cluster_count", "max_cluster_ratio", "singleton_ratio"):
                item[f"{metric}_change_vs_leiden"] = float(record[metric]) - float(b[metric])
                item[f"{metric}_change_vs_conservative"] = float(record[metric]) - float(c[metric])
            rows.append(item)
    per = pd.DataFrame(rows)
    write_df(REPORT_ROOT / "preference_secondary_costs_per_seed.csv", per)
    summary = []
    for keys, group in per.groupby(["profile_family", "stage", "subject"], sort=True):
        for metric in ("coupling", "cohesion", "imbalance", "weighted_modularity", "cluster_count", "max_cluster_ratio", "singleton_ratio"):
            for reference in ("leiden", "conservative"):
                values = group[f"{metric}_change_vs_{reference}"].to_numpy(float)
                summary.append({"profile_family": keys[0], "stage": keys[1], "subject": keys[2], "metric": metric, "reference": reference, "n": len(values), "median_change": float(np.median(values)), "mean_change": float(np.mean(values)), "iqr_change": float(np.percentile(values,75)-np.percentile(values,25)), "std_change": float(np.std(values,ddof=1)) if len(values)>1 else float("nan")})
    write_df(REPORT_ROOT / "preference_secondary_costs_summary.csv", pd.DataFrame(summary))


def cross_semantic_report(semantic_profiles: pd.DataFrame, contexts: dict[str, Any], baselines: dict[tuple[str, str], dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in semantic_profiles.loc[semantic_profiles.status == "selected"].to_dict("records"):
        subject, seed, source_stage = record["subject"], int(record["seed"]), record["stage"]
        partition = selected_partition(contexts[subject][source_stage], record)
        for eval_stage in ("stage3a", "stage3b"):
            value = semantic_value(contexts[subject][eval_stage], partition)
            rows.append({"subject": subject, "seed": seed, "budget": record["budget"], "source_stage": source_stage, "evaluation_graph": eval_stage, "solution_id": record["solution_id"], "f_semantic": value, "semantic_improvement_vs_same_graph_leiden": relative_gain(baselines[(eval_stage, subject)]["semantic"], value), "evaluation_policy": "post-hoc matched partition; no reselection"})
    return pd.DataFrame(rows)


def reverse_reports(candidates: dict[tuple[str, str, int], pd.DataFrame], contexts: dict[str, Any], baselines: dict[tuple[str, str], dict[str, Any]], conservative_keys: dict[tuple[str, str, int], tuple[int, ...]], references: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    balance_rows = []
    semantic_rows = []
    for stage in STAGES:
        for subject in SUBJECTS:
            baseline = baselines[(stage, subject)]
            for seed in SEEDS:
                frame = candidates[(stage, subject, seed)]
                for target in TARGETS:
                    eligible = frame.loc[frame["gain_imbalance"] >= target - TOL]
                    chosen = select_candidate(eligible, "modularity") if len(eligible) else None
                    if chosen is None:
                        balance_rows.append({"stage": stage, "subject": subject, "seed": seed, "target_improvement": target, "status": "unavailable", "required_modularity_loss": float("nan")})
                    else:
                        row = profile_record(chosen, subject, stage, seed, f"reverse_balance_{target:.2f}", None, baseline, conservative_keys[(stage, subject, seed)])
                        balance_rows.append({**row, "target_improvement": target, "required_modularity_loss": row["realised_modularity_loss"], "status": "achieved"})
                if stage != "stage2":
                    for target in TARGETS:
                        eligible = frame.loc[frame["gain_semantic"] >= target - TOL]
                        chosen = select_candidate(eligible, "modularity") if len(eligible) else None
                        if chosen is None:
                            semantic_rows.append({"stage": stage, "subject": subject, "seed": seed, "target_improvement": target, "status": "unavailable", "required_modularity_loss": float("nan")})
                        else:
                            row = profile_record(chosen, subject, stage, seed, f"reverse_semantic_{target:.2f}", None, baseline, conservative_keys[(stage, subject, seed)])
                            semantic_rows.append({**row, "target_improvement": target, "required_modularity_loss": row["realised_modularity_loss"], "status": "achieved"})
    balance = pd.DataFrame(balance_rows)
    semantic = pd.DataFrame(semantic_rows)
    write_df(REPORT_ROOT / "reverse_balance_target_per_seed.csv", balance)
    write_df(REPORT_ROOT / "reverse_semantic_target_per_seed.csv", semantic)
    def reverse_summary(frame: pd.DataFrame, name: str) -> pd.DataFrame:
        rows = []
        if frame.empty:
            return pd.DataFrame()
        for keys, group in frame.groupby(["stage", "subject", "target_improvement"], sort=True):
            values = group.loc[group.status.isin(["achieved", "selected"]), "required_modularity_loss"].to_numpy(float)
            values = values[np.isfinite(values)]
            rows.append({"analysis": name, "stage": keys[0], "subject": keys[1], "target_improvement": keys[2], "achieved_seed_count": len(values), "availability_rate": len(values)/30, "median_required_modularity_loss": float(np.median(values)) if len(values) else float("nan"), "iqr_required_modularity_loss": float(np.percentile(values,75)-np.percentile(values,25)) if len(values) else float("nan"), "maximum_required_modularity_loss": float(np.max(values)) if len(values) else float("nan")})
        return pd.DataFrame(rows)
    bsum = reverse_summary(balance, "balance")
    ssum = reverse_summary(semantic, "semantic")
    write_df(REPORT_ROOT / "reverse_balance_target_summary.csv", bsum)
    write_df(REPORT_ROOT / "reverse_semantic_target_summary.csv", ssum)
    write_md(REPORT_ROOT / "reverse_balance_target_summary.md", "# Reverse balance targets\n\nA target is achieved only when a saved retained-front candidate reaches the requested relative imbalance improvement. The chosen candidate maximises weighted modularity within that target.\n\n" + bsum.to_csv(index=False) if not bsum.empty else "# Reverse balance targets\n\nNo rows.")
    return balance, semantic


def profile_comparison(candidates: dict[tuple[str, str, int], pd.DataFrame], contexts: dict[str, Any], baselines: dict[tuple[str, str], dict[str, Any]], conservative_keys: dict[tuple[str, str, int], tuple[int, ...]], selected_ids: dict[tuple[str, str, int], str]) -> pd.DataFrame:
    rows = []
    for stage in STAGES:
        for subject in SUBJECTS:
            for seed in SEEDS:
                frame = candidates[(stage, subject, seed)]
                baseline = baselines[(stage, subject)]
                key = conservative_keys[(stage, subject, seed)]
                selections: list[tuple[str, pd.Series | None]] = []
                selected_id = selected_ids[(stage, subject, seed)]
                selections.append(("conservative", frame.loc[frame.solution_id == selected_id].iloc[0]))
                for budget in (0.010, 0.025, 0.050, 0.100):
                    selections.append((f"budgeted_balance_{budget:.3f}", select_candidate(frame, "balance", budget)))
                if stage != "stage2":
                    selections.append(("budgeted_semantic_0.050", select_candidate(frame, "semantic", .05)))
                # Frozen secondary knee: min-max normalisation, distance to
                # ideal zero, then highest Q and lexicographic solution ID.
                obj_cols = ["coupling", "cohesion", "imbalance"] + ([] if stage == "stage2" else ["f_semantic"])
                matrix = frame[obj_cols].to_numpy(float).copy()
                matrix[:, 1] *= -1
                low, high = matrix.min(axis=0), matrix.max(axis=0)
                denom = high - low
                norm = np.divide(matrix - low, denom, out=np.zeros_like(matrix), where=denom > TOL)
                dist = np.sqrt(np.sum(norm * norm, axis=1))
                knee_frame = frame.copy(); knee_frame["_knee_distance"] = dist
                knee = knee_frame.sort_values(["_knee_distance", "weighted_modularity", "solution_id"], ascending=[True, False, True], kind="stable").iloc[0]
                selections.append(("knee_native", knee))
                if stage != "stage2":
                    projected = frame.loc[frame.projected_membership].copy()
                    pm = projected[["coupling", "cohesion", "imbalance"]].to_numpy(float); pm[:,1]*=-1
                    pl, ph = pm.min(axis=0), pm.max(axis=0); pdn=ph-pl
                    pn=np.divide(pm-pl,pdn,out=np.zeros_like(pm),where=pdn>TOL); projected=projected.copy(); projected["_knee_distance"]=np.sqrt(np.sum(pn*pn,axis=1))
                    selections.append(("knee_projected_structural", projected.sort_values(["_knee_distance","weighted_modularity","solution_id"],ascending=[True,False,True],kind="stable").iloc[0]))
                selections.append(("extreme_balance", select_candidate(frame, "extreme_balance")))
                if stage != "stage2":
                    selections.append(("extreme_semantic", select_candidate(frame, "extreme_semantic")))
                for profile, selection in selections:
                    record = profile_record(selection, subject, stage, seed, profile, None, baseline, key, "selected" if selection is not None else "unavailable")
                    rows.append(record)
    result = pd.DataFrame(rows)
    write_df(REPORT_ROOT / "profile_comparison_per_seed.csv", result)
    summary_rows=[]
    for keys, group in result.groupby(["stage","subject","profile"],sort=True):
        selected=group.loc[group.status=="selected"]
        summary_rows.append({"stage":keys[0],"subject":keys[1],"profile":keys[2],"availability_rate":len(selected)/30,"median_q_loss":float(selected.realised_modularity_loss.median()) if len(selected) else float("nan"),"median_imbalance_gain":float(selected.gain_imbalance.median()) if len(selected) else float("nan"),"median_semantic_gain":float(selected.gain_semantic.median()) if len(selected) else float("nan"),"median_coupling":float(selected.coupling.median()) if len(selected) else float("nan"),"median_cohesion":float(selected.cohesion.median()) if len(selected) else float("nan"),"median_cluster_count":float(selected.cluster_count.median()) if len(selected) else float("nan"),"median_singleton_ratio":float(selected.singleton_ratio.median()) if len(selected) else float("nan")})
    summary=pd.DataFrame(summary_rows); write_df(REPORT_ROOT / "profile_comparison_summary.csv",summary)
    write_md(REPORT_ROOT / "profile_comparison_summary.md", "# Conservative, budgeted, knee, and extreme profiles\n\nThe conservative profile is the existing frozen modularity-max result. Knee profiles are secondary sensitivity analyses. Extreme profiles are retained-front capability bounds, not deployment recommendations.\n\n" + summary.to_csv(index=False))
    return result


def external_report(profile_result: pd.DataFrame, contexts: dict[str, Any], references: dict[str, Any], baselines: dict[tuple[str, str], dict[str, Any]]) -> None:
    rows=[]
    keep_profiles={"conservative","budgeted_balance_0.050","budgeted_semantic_0.050","knee_native","extreme_balance","extreme_semantic"}
    metric_names=("mojofm_vs_reference","pairwise_precision","pairwise_recall","pairwise_f1","ari_vs_reference","nmi_vs_reference","reference_coverage_ratio")
    for record in profile_result.loc[profile_result.profile.isin(keep_profiles)].to_dict("records"):
        ref, info=references[record["subject"]]
        if record["status"] == "selected":
            part=selected_partition(contexts[record["subject"]][record["stage"]],record)
            values=external_metrics(contexts[record["subject"]][record["stage"]]["class_nodes"],part,ref)
        else:
            values={name:float("nan") for name in metric_names}
        baseline_part=baselines[(record["stage"],record["subject"])] ["partition"]
        baseline_values=external_metrics(contexts[record["subject"]][record["stage"]]["class_nodes"],baseline_part,ref)
        conservative_rows=profile_result.loc[(profile_result.stage==record["stage"])&(profile_result.subject==record["subject"])&(profile_result.seed==record["seed"])&(profile_result.profile=="conservative")]
        conservative_values={name:float("nan") for name in metric_names}
        if len(conservative_rows) and conservative_rows.iloc[0]["status"] == "selected":
            conservative_values=external_metrics(contexts[record["subject"]][record["stage"]]["class_nodes"],selected_partition(contexts[record["subject"]][record["stage"]],conservative_rows.iloc[0].to_dict()),ref)
        deltas={}
        for name in metric_names:
            deltas[f"{name}_delta_vs_leiden"]=values[name]-baseline_values[name] if np.isfinite(values[name]) and np.isfinite(baseline_values[name]) else float("nan")
            deltas[f"{name}_delta_vs_conservative"]=values[name]-conservative_values[name] if np.isfinite(values[name]) and np.isfinite(conservative_values[name]) else float("nan")
        rows.append({**{key:record.get(key) for key in ("stage","subject","seed","profile","status","realised_modularity_loss","gain_imbalance","gain_semantic","cluster_count")},"reference_status":info["status"],"reference_path":info["path"],"evaluation_policy":"post-hoc only; external metrics did not influence selection",**values,**deltas})
    per=pd.DataFrame(rows); write_df(REPORT_ROOT / "preference_external_metrics_per_seed.csv",per)
    rows=[]
    for keys,group in per.groupby(["stage","subject","profile"],sort=True):
        for metric in metric_names:
            values=group[metric].to_numpy(float); values=values[np.isfinite(values)]
            delta_leiden=group[f"{metric}_delta_vs_leiden"].to_numpy(float); delta_leiden=delta_leiden[np.isfinite(delta_leiden)]
            delta_conservative=group[f"{metric}_delta_vs_conservative"].to_numpy(float); delta_conservative=delta_conservative[np.isfinite(delta_conservative)]
            row={"stage":keys[0],"subject":keys[1],"profile":keys[2],"metric":metric,"reference_status":group.reference_status.iloc[0],"available_n":len(values),"median":float(np.median(values)) if len(values) else float("nan"),"mean":float(np.mean(values)) if len(values) else float("nan"),"iqr":float(np.percentile(values,75)-np.percentile(values,25)) if len(values) else float("nan"),"median_delta_vs_leiden":float(np.median(delta_leiden)) if len(delta_leiden) else float("nan"),"mean_delta_vs_leiden":float(np.mean(delta_leiden)) if len(delta_leiden) else float("nan"),"median_delta_vs_conservative":float(np.median(delta_conservative)) if len(delta_conservative) else float("nan"),"mean_delta_vs_conservative":float(np.mean(delta_conservative)) if len(delta_conservative) else float("nan")}
            for reference_stage in ("stage2","stage3a","stage3b"):
                ref_rows=per.loc[(per.subject==keys[1])&(per.stage==reference_stage)&(per.profile=="conservative"),metric].to_numpy(float); ref_rows=ref_rows[np.isfinite(ref_rows)]
                row[f"mean_delta_vs_{reference_stage}_conservative"]=float(np.mean(values)-np.mean(ref_rows)) if len(values) and len(ref_rows) else float("nan")
            rows.append(row)
    write_df(REPORT_ROOT / "preference_external_metrics_summary.csv",pd.DataFrame(rows))


def stability_report(profile_result: pd.DataFrame, contexts: dict[str, Any]) -> None:
    main={"conservative","budgeted_balance_0.010","budgeted_balance_0.025","budgeted_balance_0.050","budgeted_balance_0.100","budgeted_semantic_0.050","knee_native","extreme_balance","extreme_semantic"}
    rows=[]
    for (stage,subject,profile),group in profile_result.loc[profile_result.profile.isin(main)].groupby(["stage","subject","profile"],sort=True):
        group=group.loc[group.status=="selected"].sort_values("seed")
        pairs=[]; aris=[]; nmis=[]
        for i in range(len(group)):
            left=selected_partition(contexts[subject][stage],group.iloc[i])
            for j in range(i+1,len(group)):
                right=selected_partition(contexts[subject][stage],group.iloc[j])
                ari,nmi=partition_similarity(contexts[subject][stage]["class_nodes"],left,right); aris.append(float(ari)); nmis.append(float(nmi)); pairs.append(bool(np.isclose(ari,1.0,rtol=0,atol=0) and np.isclose(nmi,1.0,rtol=0,atol=0)))
        rows.append({"stage":stage,"subject":subject,"profile":profile,"available_seed_count":len(group),"pair_count":len(aris),"availability_rate":len(group)/30,"ari_mean":float(np.mean(aris)) if aris else float("nan"),"ari_median":float(np.median(aris)) if aris else float("nan"),"ari_iqr":float(np.percentile(aris,75)-np.percentile(aris,25)) if aris else float("nan"),"nmi_mean":float(np.mean(nmis)) if nmis else float("nan"),"nmi_median":float(np.median(nmis)) if nmis else float("nan"),"identical_partition_count":int(sum(pairs)),"identical_partition_rate":float(np.mean(pairs)) if pairs else float("nan"),"cluster_count_mean":float(group.cluster_count.mean()) if len(group) else float("nan"),"cluster_count_std":float(group.cluster_count.std(ddof=1)) if len(group)>1 else float("nan")})
    frame=pd.DataFrame(rows); write_df(REPORT_ROOT / "preference_partition_stability.csv",frame)
    write_md(REPORT_ROOT / "preference_partition_stability_summary.md", "# Preference-selected partition stability\n\nStability is pairwise across the 30 saved seeds. Profiles with missing eligible seeds are marked through their availability rate; no fallback selection is applied.\n\n" + frame.to_csv(index=False))


def marginal_report(balance_summaries: list[tuple[str,pd.DataFrame]], semantic_summary: pd.DataFrame) -> None:
    rows=[]; intervals=list(zip(BUDGETS[:-1],BUDGETS[1:],strict=True))
    all_summaries=[*balance_summaries,("semantic",semantic_summary)]
    for family,summary in all_summaries:
        if summary.empty: continue
        for (stage,subject),group in summary.groupby(["stage","subject"],sort=True):
            group=group.set_index("budget")
            for left,right in intervals:
                if left not in group.index or right not in group.index: continue
                dg=float(group.loc[right,"median_gain"]-group.loc[left,"median_gain"])
                db=float(right-left); dl=float(group.loc[right,"median_realised_modularity_loss"]-group.loc[left,"median_realised_modularity_loss"])
                rows.append({"family":family,"stage":stage,"subject":subject,"interval_start":left,"interval_end":right,"response_metric":"gain","budget_based_exchange_rate":dg/db,"realised_loss_based_exchange_rate":dg/dl if abs(dl)>TOL else float("nan"),"realised_loss_denominator":dl,"stability":"stable" if abs(dl)>TOL else "undefined_near_zero_realised_loss","interpretation": "descriptive interval response; no sweet spot selected"})
    frame=pd.DataFrame(rows); write_df(REPORT_ROOT / "marginal_exchange_rates.csv",frame)
    write_md(REPORT_ROOT / "marginal_exchange_rates_summary.md", "# Marginal exchange rates\n\nRates are interval-level changes in median attainable improvement. Near-zero realised-loss denominators are reported as undefined rather than infinite. The complete curve is retained; no sweet spot is selected from inspection.\n\n" + frame.to_csv(index=False))


def five_percent_report(profile_result: pd.DataFrame, baseline: dict[tuple[str,str],dict[str,Any]], references: dict[str,Any], contexts: dict[str,Any]) -> None:
    rows=[]
    for record in profile_result.loc[profile_result.profile.isin({"budgeted_balance_0.050","budgeted_semantic_0.050"})].to_dict("records"):
        if record["status"] != "selected": continue
        rows.append({"stage":record["stage"],"subject":record["subject"],"seed":record["seed"],"profile":record["profile"],"availability":"selected","realised_modularity_loss":record["realised_modularity_loss"],"imbalance_improvement":record["gain_imbalance"],"semantic_improvement":record["gain_semantic"],"coupling_change":record["coupling"]-baseline[(record["stage"],record["subject"])] ["coupling"],"cohesion_change":record["cohesion"]-baseline[(record["stage"],record["subject"])] ["cohesion"],"cluster_count_change":record["cluster_count"]-baseline[(record["stage"],record["subject"])] ["cluster_count"],"singleton_ratio_change":record["singleton_ratio"]-baseline[(record["stage"],record["subject"])] ["singleton_ratio"],"equals_leiden":record["equals_leiden"],"equals_conservative":record["equals_conservative"],"statement":"Under a maximum 5% modularity-loss budget; realised loss may be lower than 5%."})
    frame=pd.DataFrame(rows); write_df(REPORT_ROOT / "five_percent_operating_profile.csv",frame)
    summary=frame.groupby(["stage","subject","profile"],sort=True).agg(eligible_seed_count=("seed","count"),median_realised_loss=("realised_modularity_loss","median"),median_imbalance_improvement=("imbalance_improvement","median"),median_semantic_improvement=("semantic_improvement","median"),median_coupling_change=("coupling_change","median"),median_cohesion_change=("cohesion_change","median"),median_cluster_count_change=("cluster_count_change","median"),median_singleton_ratio_change=("singleton_ratio_change","median"),equals_leiden_rate=("equals_leiden","mean"),equals_conservative_rate=("equals_conservative","mean")).reset_index()
    summary["availability_rate"] = summary["eligible_seed_count"] / 30.0
    summary["unavailable_seed_count"] = 30 - summary["eligible_seed_count"]
    write_md(REPORT_ROOT / "five_percent_operating_profile_summary.md", "# Five-percent operating profile\n\nUnder a maximum 5% modularity-loss budget, the following post-hoc profiles are available within the saved retained fronts. The 5% figure is a permitted maximum, not necessarily the realised loss.\n\n" + summary.to_csv(index=False))


def statistical_reports(profile_frames: list[tuple[str,pd.DataFrame]]) -> None:
    rows=[]
    for family,frame in profile_frames:
        target=frame.loc[(frame["budget"]==.05)&(frame.status=="selected")].sort_values(["stage","subject","seed"])
        for (stage,subject),group in target.groupby(["stage","subject"],sort=True):
            conservative=global_profile_result.loc[(global_profile_result.stage==stage)&(global_profile_result.subject==subject)&(global_profile_result.profile=="conservative")].sort_values("seed")
            if len(group)!=len(conservative): continue
            for metric in ("coupling","cohesion","cluster_count","singleton_ratio"):
                diffs=group[metric].to_numpy(float)-conservative[metric].to_numpy(float)
                try:
                    test=wilcoxon(diffs,zero_method="wilcox",alternative="two-sided",method="auto")
                    p=float(test.pvalue); status="tested"
                except ValueError:
                    p=float("nan"); status="no_nonzero_pairs"
                rows.append({"family":"secondary_costs","profile_family":family,"stage":stage,"subject":subject,"metric":metric,"n":len(diffs),"p_value_two_sided":p,"rank_biserial":rank_biserial(diffs),"wins":int(np.sum(diffs>0)),"ties":int(np.sum(np.abs(diffs)<=TOL)),"losses":int(np.sum(diffs<0)),"status":status,"correction":"holm"})
    frame=pd.DataFrame(rows)
    if not frame.empty:
        valid=frame.loc[frame.status=="tested","p_value_two_sided"].to_numpy(float)
        order=np.argsort(valid); adj=np.empty(len(valid)); running=0.0
        for rank,index in enumerate(order): running=max(running,min(1.0,valid[index]*(len(valid)-rank))); adj[index]=running
        frame.loc[frame.status=="tested","adjusted_p_value"]=adj
    write_df(REPORT_ROOT / "preference_statistical_tests.csv",frame)
    write_md(REPORT_ROOT / "preference_statistical_summary.md", "# Preference-response statistical protocol\n\nPrimary balance and semantic claims are descriptive attainable-front summaries with availability, IQR, and bootstrap intervals. Paired Wilcoxon tests are secondary consequence checks only, with rank-biserial effects and Holm correction across this planned secondary family.\n\n" + frame.to_csv(index=False))


def figure_reports(balance_summaries: list[tuple[str,pd.DataFrame]], semantic_summary: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_data = REPORT_ROOT / "figure_data"; fig_dir = REPORT_ROOT / "figures"; fig_data.mkdir(parents=True, exist_ok=True); fig_dir.mkdir(parents=True, exist_ok=True)
    for family,summary in [*balance_summaries,("semantic",semantic_summary)]:
        write_df(fig_data / f"{family}_response.csv",summary)
    colors={"jpetstore":"#1f77b4","daytrader":"#ff7f0e","xerces":"#2ca02c"}
    def plot_family(family:str,summary:pd.DataFrame,stage:str|None,path_stem:str,allow_png:bool=False):
        fig,ax=plt.subplots(figsize=(8,5),dpi=160)
        subset=summary if stage is None else summary.loc[summary.stage==stage]
        for subject,group in subset.groupby("subject",sort=True):
            group=group.sort_values("budget"); x=group.budget.to_numpy(float)*100; y=group.median_gain.to_numpy(float); lo=(y-group.iqr_gain.to_numpy(float)/2); hi=(y+group.iqr_gain.to_numpy(float)/2)
            ax.plot(x,y,marker="o",label=subject,color=colors[subject]); ax.fill_between(x,lo,hi,color=colors[subject],alpha=.14)
        ax.set_xlabel("Allowed modularity loss (%)"); ax.set_ylabel("Median relative improvement"); ax.set_xlim(0,20); ax.grid(alpha=.25); ax.legend(); ax.set_title(f"{family} preference response" + (f" — {stage}" if stage else "")); fig.tight_layout()
        metadata = {"Creator": "scripts/preference_analysis/analyze_preference_response.py", "Title": path_stem, "CreationDate": None, "ModDate": None}
        fig.savefig(fig_dir/f"{path_stem}.pdf", metadata=metadata)
        if allow_png: fig.savefig(fig_dir/f"{path_stem}.png", metadata={"Software": "preference-analysis"})
        plt.close(fig)
    for name,summary in balance_summaries:
        plot_family("balance",summary,name,f"{name}_balance_preference_response",allow_png=name=="stage2")
    plot_family("balance",pd.concat([s.assign(method=name) for name,s in balance_summaries],ignore_index=True),None,"stage2_stage3_balance_comparison")
    for name in ("stage3a","stage3b"):
        plot_family("semantic",semantic_summary, name, f"{name}_semantic_preference_response")


def final_conclusions(baselines: dict[tuple[str,str],dict[str,Any]], balance_summaries: list[tuple[str,pd.DataFrame]], semantic_summary: pd.DataFrame, external_summary: pd.DataFrame, stability: pd.DataFrame) -> None:
    lines=["# Preference-response analysis conclusions", "", "This is a post-hoc analysis of the saved retained final feasible fronts for 30 paired seeds. It does not replace the frozen conservative selector, rerun an optimizer, or establish a global Pareto frontier. Reported capability is attainable within the saved retained candidate set, which is limited by population size, crowding truncation, duplicate handling, evolutionary trajectory, and finite generations.", "", "## Conservative-profile result", "", "The existing selected solution remains the highest-weighted-modularity feasible solution under the frozen selection rule. No selected result was changed.", "", "## Retained-front capability and preference sensitivity", ""]
    for name,summary in balance_summaries:
        rows=summary.loc[summary.budget.isin([.01,.05,.10])]
        lines.append(f"- {name}: balance capability is reported with availability and realised modularity loss for all subjects; the complete eight-budget curve is in the CSV and figure data.")
    lines += ["", "Stage 3A and Stage 3B semantic profiles are evaluated on their native semantic graphs. Cross-graph values are kept separate and are descriptive matched-partition checks, not direct comparisons of raw objective values.", "", "## Structural costs, external quality, and stability", "", "Secondary changes in coupling, cohesion, cluster count, and singleton ratio are reported per seed. DayTrader is the only subject with a complete frozen external reference; JPetStore and Xerces-J are marked unavailable rather than assigned invented references. External metrics are post-hoc and did not influence selection.", "", "Cross-seed ARI/NMI stability is reported for conservative, budgeted, knee, and extreme retained-front profiles. Extreme profiles are capability bounds, not deployment recommendations.", "", "## Subject dependence", "", "JPetStore, DayTrader, and Xerces-J are reported separately. The analysis does not force a universal positive conclusion across subjects or preference families."]
    write_md(REPORT_ROOT / "preference_final_conclusions.md", "\n".join(lines))


def integrity_after(before: pd.DataFrame) -> pd.DataFrame:
    frame=before.copy(); after=[]; unchanged=[]
    for path in frame.path:
        p=ROOT/path; current=sha256_file(p) if p.is_file() else ""; after.append(current)
    frame["sha256_after"]=after; frame["unchanged"]=frame.sha256_before==frame.sha256_after; frame["status"]=np.where(frame.unchanged,"PASS","FAIL")
    write_df(REPORT_ROOT / "scientific_artifact_integrity.csv",frame)
    if not bool(frame.unchanged.all()): raise RuntimeError("accepted scientific artifact changed during analysis")
    return frame


def manifest(inventory: pd.DataFrame, integrity: pd.DataFrame, references: dict[str,Any], contexts: dict[str,Any]) -> None:
    value={"task":"Stage 2/Stage 3A/Stage 3B post-hoc preference-response analysis","branch":subprocess.check_output(["git","branch","--show-current"],cwd=ROOT,text=True).strip(),"starting_head":START_HEAD,"analysis_head":git_head(),"generated_at_utc":utc_now(),"subjects":list(SUBJECTS),"seeds":list(SEEDS),"class_counts":CLASS_COUNTS,"budgets":list(BUDGETS),"targets":list(TARGETS),"source_policy":"saved retained final feasible fronts and saved labels only; no optimizer, embedding, graph, or scientific result regeneration","objective_orientations":{"stage2":["coupling_min","cohesion_max","imbalance_min"],"stage3a":["coupling_min","cohesion_max","imbalance_min","f_semantic_min"],"stage3b":["coupling_min","cohesion_max","imbalance_min","f_semantic_min"]},"selection_rule_unchanged":"highest weighted modularity among eligible feasible candidates; budgeted analyses are post-hoc profiles and do not replace frozen selection","baseline":"one frozen raw Leiden partition per subject","reference_status":{s:references[s][1] for s in SUBJECTS},"source_inventory_path":"reports/preference_analysis/source_artifact_inventory.csv","scientific_artifact_integrity_path":"reports/preference_analysis/scientific_artifact_integrity.csv","integrity_pass":bool(integrity.unchanged.all()),"no_optimizer_run":True,"no_new_seed":True,"no_embeddings_regenerated":True,"no_graphs_regenerated":True,"no_scientific_artifact_modified":bool(integrity.unchanged.all()),"limitations":"retained-front capability is not global capability; finite population and evolution constrain the saved candidate set"}
    write_json(REPORT_ROOT / "preference_analysis_manifest.json",value)


def run() -> None:
    global frozen_contexts, global_profile_result, START_HEAD
    prior_manifest = REPORT_ROOT / "preference_analysis_manifest.json"
    prior_start = None
    if prior_manifest.is_file():
        try:
            prior_start = json.loads(prior_manifest.read_text(encoding="utf-8")).get("starting_head")
        except (OSError, json.JSONDecodeError):
            prior_start = None
    START_HEAD = str(prior_start or git_head())
    frozen_contexts, inventory, integrity_before, references=load_sources()
    REPORT_ROOT.mkdir(parents=True,exist_ok=True)
    write_df(REPORT_ROOT / "source_artifact_inventory.csv",inventory)
    baselines=baseline_report(frozen_contexts,references)
    candidates={}; selected_ids={}
    for stage in STAGES:
        for subject in SUBJECTS:
            for seed in SEEDS:
                frame,meta=_candidate_frame(stage,subject,seed,frozen_contexts[subject][stage]); candidates[(stage,subject,seed)]=frame; selected_ids[(stage,subject,seed)]=meta["selected_id"]
    selected_ids, conservative_keys=source_selected_ids(candidates,frozen_contexts)
    attach_derived(candidates,baselines,conservative_keys)
    mechanism_reports(frozen_contexts,candidates,selected_ids)
    s2_balance=profile_rows_for(candidates,frozen_contexts,("stage2",),"balance",BUDGETS,baselines,conservative_keys,"budgeted_balance")
    s3_balance=profile_rows_for(candidates,frozen_contexts,("stage3a","stage3b"),"balance",BUDGETS,baselines,conservative_keys,"budgeted_balance")
    s3_sem=profile_rows_for(candidates,frozen_contexts,("stage3a","stage3b"),"semantic",BUDGETS,baselines,conservative_keys,"budgeted_semantic")
    write_df(REPORT_ROOT/"stage2_budgeted_balance_per_seed.csv",s2_balance); s2_sum=summarize_profiles(s2_balance,"gain_imbalance","stage2_balance"); write_df(REPORT_ROOT/"stage2_budgeted_balance_summary.csv",s2_sum); write_md(REPORT_ROOT/"stage2_budgeted_balance_summary.md",summary_md("Stage 2 budgeted balance",s2_sum,"gain_imbalance"))
    write_df(REPORT_ROOT/"stage3_budgeted_balance_per_seed.csv",s3_balance); s3b_sum=summarize_profiles(s3_balance,"gain_imbalance","stage3_balance"); write_df(REPORT_ROOT/"stage3_budgeted_balance_summary.csv",s3b_sum); write_md(REPORT_ROOT/"stage3_budgeted_balance_summary.md",summary_md("Stage 3A/Stage 3B budgeted balance",s3b_sum,"gain_imbalance"))
    write_df(REPORT_ROOT/"stage3_budgeted_semantic_per_seed.csv",s3_sem); s3s_sum=summarize_profiles(s3_sem,"gain_semantic","stage3_semantic"); write_df(REPORT_ROOT/"stage3_budgeted_semantic_summary.csv",s3s_sum); write_md(REPORT_ROOT/"stage3_budgeted_semantic_summary.md",summary_md("Stage 3A/Stage 3B budgeted semantic",s3s_sum,"gain_semantic"))
    cross=cross_semantic_report(s3_sem,frozen_contexts,baselines); write_df(REPORT_ROOT/"stage3_budgeted_semantic_cross_evaluation.csv",cross)
    availability=[]
    for name,frame in (("stage2_balance",s2_balance),("stage3_balance",s3_balance),("stage3_semantic",s3_sem)):
        availability.append(summarize_profiles(frame,"gain_imbalance" if "balance" in name else "gain_semantic",name))
    write_df(REPORT_ROOT/"preference_availability.csv",pd.concat(availability,ignore_index=True))
    realised_loss_report([("stage2_balance",s2_balance),("stage3_balance",s3_balance),("stage3_semantic",s3_sem)])
    conservative={}
    for stage in STAGES:
        for subject in SUBJECTS:
            for seed in SEEDS:
                conservative[(stage,subject,seed)]=candidates[(stage,subject,seed)].loc[candidates[(stage,subject,seed)].solution_id==selected_ids[(stage,subject,seed)]].iloc[0]
    secondary_cost_reports([("stage2_balance",s2_balance),("stage3_balance",s3_balance),("stage3_semantic",s3_sem)],baselines,conservative)
    reverse_reports(candidates,frozen_contexts,baselines,conservative_keys,references)
    global_profile_result=profile_comparison(candidates,frozen_contexts,baselines,conservative_keys,selected_ids)
    external_report(global_profile_result,frozen_contexts,references,baselines)
    stability_report(global_profile_result,frozen_contexts)
    marginal_report([("stage2_balance",s2_sum),("stage3_balance",s3b_sum)],s3s_sum)
    five_percent_report(global_profile_result,baselines,references,frozen_contexts)
    statistical_reports([("stage2_balance",s2_balance),("stage3_balance",s3_balance),("stage3_semantic",s3_sem)])
    figure_reports([("stage2",s2_sum),("stage3a",s3b_sum.loc[s3b_sum.stage=="stage3a"]),("stage3b",s3b_sum.loc[s3b_sum.stage=="stage3b"])],s3s_sum)
    integrity=integrity_after(integrity_before)
    manifest(inventory,integrity,references,frozen_contexts)
    final_conclusions(baselines,[ ("stage2_balance",s2_sum),("stage3_balance",s3b_sum)],s3s_sum,pd.read_csv(REPORT_ROOT/"preference_external_metrics_summary.csv"),pd.read_csv(REPORT_ROOT/"preference_partition_stability.csv"))
    print(json.dumps({"status":"PASS","starting_head":START_HEAD,"subjects":list(SUBJECTS),"seeds":30,"artifact_integrity":bool(integrity.unchanged.all()),"reports":str(REPORT_ROOT)},indent=2))


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.parse_args(); run(); return 0


if __name__ == "__main__":
    raise SystemExit(main())
