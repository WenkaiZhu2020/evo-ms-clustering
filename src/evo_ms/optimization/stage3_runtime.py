#!/usr/bin/env python3
"""Run the final four-objective Stage 3 Declaration + Method Body pipeline.

The Stage 2 runner supplies the raw-graph loader, initialization, operators,
repair, termination, and selection implementation. This module only adds the
fourth objective and the frozen projected-evaluation boundary.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.optimization import encoding
from evo_ms.optimization.semantic_objective import evaluate_semantic_objective, load_semantic_edges
from evo_ms.optimization.stage3_problem import (
    STAGE3_OBJECTIVE_ORDER,
    build_four_objective_problem,
    evaluate_four_objective_values,
)


def _load_stage2_runner():
    path = ROOT / "experiments/02_stage2_nsga_structure_only/run.py"
    spec = importlib.util.spec_from_file_location("stage2_structure_only_run_for_stage3", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load Stage 2 runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stage2 = _load_stage2_runner()

CONFIG_PATH = ROOT / "configs/experiments/05_stage3_declaration_method_body.yml"
STAGE2_CONFIG_PATH = ROOT / "configs/experiments/02_stage2_nsga_structure_only.yml"
BOUNDS_PATH = ROOT / "configs/experiments/stage2_robustness_bounds.yml"
MANIFEST_PATH = ROOT / "reports/stage3/provenance/semantic_graph_generation_manifest.json"
SEMANTIC_SUBJECTS = ("jpetstore", "daytrader", "xerces")
STORAGE_SUBJECT = {"jpetstore": "jpetstore", "daytrader": "daytrader", "xerces": "xerces-j"}
FORMAL_SEEDS = list(range(30))
REFERENCE_POINT = np.full(3, 1.1, dtype=float)
HV_TOLERANCE = 1e-12


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def load_stage3_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def subject_paths(subject: str) -> dict[str, Path]:
    storage = STORAGE_SUBJECT[subject]
    graph = ROOT / "data/semantic_graphs/declaration_method_body" / subject
    return {
        "graph_edges": graph / "semantic_edges.csv",
        "graph_metadata": graph / "graph_metadata.json",
        "raw_class_nodes": ROOT / "data/extracted" / storage / "class_nodes.csv",
        "raw_structural_dependencies": ROOT / "data/extracted" / storage / "structural_dependencies.csv",
        "stage1_clusters": ROOT / "results" / storage / "01_stage1_leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv",
        "stage2_robustness_manifest": ROOT / "results" / storage / "03_stage2_nsga/robustness/robustness_manifest.json",
        "stage2_seed_metrics": ROOT / "results" / storage / "03_stage2_nsga/robustness/seed_00/run_metrics.json",
        "stage2_seed_metadata": ROOT / "results" / storage / "03_stage2_nsga/robustness/seed_00/run_metadata.json",
        "stage2_raw_hv": ROOT / "results" / storage / "03_stage2_nsga/raw/hypervolume_by_seed.csv",
    }


def canonical_graph_hash(edges: pd.DataFrame) -> str:
    payload = "".join(
        f"{row['class_id_a']}\t{row['class_id_b']}\t{format(float(row['weight']), '.17g') if float(row['weight']) != 0.0 else '0'}\n"
        for row in edges.to_dict("records")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_graph_hash_file(path: Path) -> str:
    """Hash the exact persisted canonical weight tokens in a graph CSV.

    The graph builder records its hash before pandas or another CSV reader can
    round-trip a decimal token. The formal runner therefore validates the
    decoded numeric table separately, then hashes the persisted tokens exactly
    as written so provenance checks do not introduce a float reserialization
    change.
    """
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    payload = "".join(
        f"{row['class_id_a']}\t{row['class_id_b']}\t{row['weight']}\n"
        for row in rows
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_stage2_bounds(subject: str) -> dict[str, Any]:
    bounds_document = yaml.safe_load(BOUNDS_PATH.read_text(encoding="utf-8"))
    bounds = bounds_document["subjects"][STORAGE_SUBJECT[subject]]
    if bounds.get("bounds_source") != "theoretical" or bounds.get("calibration_status") != "not_required":
        raise ValueError(f"{subject}: Stage 2 bounds are not frozen theoretical bounds")
    if bounds.get("objective_order") != ["coupling", "negative_cohesion", "imbalance"]:
        raise ValueError(f"{subject}: Stage 2 bounds objective order mismatch")
    if bounds.get("reference_point") != [1.1, 1.1, 1.1]:
        raise ValueError(f"{subject}: Stage 2 reference point mismatch")
    return bounds


def load_context(subject: str) -> dict[str, Any]:
    if subject not in SEMANTIC_SUBJECTS:
        raise ValueError(f"subject must be one of {SEMANTIC_SUBJECTS}")
    config = yaml.safe_load(STAGE2_CONFIG_PATH.read_text(encoding="utf-8"))
    stage2._reject_obsolete_config(config)
    storage_subject = STORAGE_SUBJECT[subject]
    subject_config = stage2._load_subject_config(ROOT, storage_subject)
    extracted_dir, extracted, raw_edges = stage2._raw_graph_inputs(ROOT, storage_subject, subject_config)
    class_nodes = extracted["class_nodes"]
    class_ids = set(class_nodes["class_id"].astype(str))
    paths = subject_paths(subject)
    graph_metadata = json.loads(paths["graph_metadata"].read_text(encoding="utf-8"))
    graph_manifest = {"aggregate_sha256": graph_metadata["semantic_graph_sha256"], "source": "final_graph_metadata"}
    semantic_edges = load_semantic_edges(paths["graph_edges"], expected_class_ids=class_ids)
    actual_graph_hash = canonical_graph_hash_file(paths["graph_edges"])
    if actual_graph_hash != graph_metadata["semantic_graph_sha256"]:
        raise ValueError(f"{subject}: semantic graph metadata hash mismatch")
    if actual_graph_hash != graph_manifest["aggregate_sha256"]:
        raise ValueError(f"{subject}: semantic graph manifest hash mismatch")
    if graph_metadata["total_edge_weight"] <= 0 or graph_metadata["negative_edge_count"] != 0:
        raise ValueError(f"{subject}: semantic graph violates non-negative positive-weight contract")
    stage1 = stage2._frozen_raw_leiden_baseline(ROOT, storage_subject, class_nodes)
    bounds = load_stage2_bounds(subject)
    return {
        "subject": subject,
        "storage_subject": storage_subject,
        "stage2_config": config,
        "stage2_config_path": STAGE2_CONFIG_PATH,
        "config": load_stage3_config(),
        "config_path": CONFIG_PATH,
        "subject_config": subject_config,
        "extracted_dir": extracted_dir,
        "class_nodes": class_nodes,
        "raw_edges": raw_edges,
        "stage1_raw_baseline": stage1,
        "semantic_edges": semantic_edges,
        "semantic_graph_metadata": graph_metadata,
        "semantic_graph_hash": actual_graph_hash,
        "graph_manifest_entry": graph_manifest,
        "bounds": bounds,
        "population_size": int(config["nsga"]["population_size"]),
        "generations": int(config["nsga"]["generations"]),
        "initialization_config": config["initialization"],
        "max_cluster_ratio": stage2.resolve_max_cluster_ratio(config),
        "stage2_hv": stage2_hypervolume_lookup(subject),
    }


def stage2_hypervolume_lookup(subject: str) -> dict[str, Any]:
    paths = subject_paths(subject)
    checked = [paths["stage2_seed_metrics"], paths["stage2_raw_hv"]]
    metrics_path = paths["stage2_seed_metrics"]
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        manifest = json.loads(paths["stage2_robustness_manifest"].read_text(encoding="utf-8"))
        return {
            "value": float(metrics["hypervolume"]),
            "source_path": relative(metrics_path),
            "checked_paths": [relative(path) for path in checked],
            "stage2_git_commit": manifest.get("git_commit"),
            "bounds_path": relative(BOUNDS_PATH),
        }
    return {"value": None, "source_path": None, "checked_paths": [relative(path) for path in checked], "stage2_git_commit": None, "bounds_path": relative(BOUNDS_PATH)}


def structural_invariance_checks(context: dict[str, Any]) -> dict[str, Any]:
    class_nodes = context["class_nodes"]
    partitions = {
        "fixed_leiden": context["stage1_raw_baseline"]["cluster_id"].to_numpy(dtype=int),
        "all_one": np.zeros(len(class_nodes), dtype=int),
        "deterministic_two_cluster": np.asarray([index % 2 for index in range(len(class_nodes))], dtype=int),
    }
    rows = {}
    for name, labels in partitions.items():
        labels = encoding.canonical_relabel(labels)
        mapping = encoding.to_cluster_by_class(labels, class_nodes)
        stage2_values = stage2.evaluate_structural_objectives(context["raw_edges"], mapping, "raw_weight")
        stage3_values = evaluate_four_objective_values(
            context["raw_edges"],
            context["semantic_edges"],
            mapping,
            "raw_weight",
            float(context["semantic_graph_metadata"]["total_edge_weight"]),
        )[:3]
        rows[name] = {
            "stage2": list(map(float, stage2_values)),
            "stage3_first_three": list(map(float, stage3_values)),
            "pass": bool(np.array_equal(np.asarray(stage2_values), np.asarray(stage3_values))),
        }
    return {"checks": rows, "pass": all(value["pass"] for value in rows.values())}


def _population_arrays(population) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if population is None or len(population) == 0:
        return np.empty((0, 0), dtype=int), np.empty((0, 4), dtype=float), np.empty((0, 2), dtype=float)
    labels = np.atleast_2d(np.asarray(population.get("X"), dtype=int))
    objectives = np.atleast_2d(np.asarray(population.get("F"), dtype=float))
    constraints = population.get("G")
    if constraints is None:
        constraints = np.zeros((len(labels), 2), dtype=float)
    return labels, objectives, np.atleast_2d(np.asarray(constraints, dtype=float))


def _nondominated_indices(objectives: np.ndarray) -> np.ndarray:
    return stage2._nondominated_indices(np.asarray(objectives, dtype=float))


def _write_stage3_csv(frame: pd.DataFrame, path: Path) -> None:
    """Persist numeric objectives losslessly enough for later dominance checks."""
    frame.to_csv(path, index=False, float_format="%.20g")


def _read_stage3_csv(path: Path) -> pd.DataFrame:
    """Reload saved objective values with round-trip float parsing."""
    return pd.read_csv(path, float_precision="round_trip")


def _front_arrays(result) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    pop_x, pop_f, pop_g = _population_arrays(result.pop)
    if len(pop_x) == 0:
        pop_x, pop_f, pop_g = _population_arrays(result.opt)
    feasible = np.all(pop_g <= 0.0, axis=1) if len(pop_g) else np.asarray([], dtype=bool)
    pool = np.flatnonzero(feasible) if feasible.any() else np.arange(len(pop_x))
    nd_local = _nondominated_indices(pop_f[pool])
    indices = pool[nd_local]
    return pop_x[indices], pop_f[indices], pop_g[indices], {
        "final_population_size": int(len(pop_x)),
        "feasible_population_size": int(feasible.sum()),
        "constraint_violating_population_size": int(len(pop_x) - feasible.sum()),
        "recomputed_nondominated_size": int(len(indices)),
        "front_source": "recomputed_nondominated_front",
        "front_validation_passed": True,
    }


def _label_key(labels: np.ndarray) -> tuple[int, ...]:
    return tuple(int(value) for value in encoding.canonical_relabel(labels).tolist())


def _solution_rows(context: dict[str, Any], seed: int, labels: np.ndarray, f_values: np.ndarray, constraints: np.ndarray, seed_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    seed_by_key = {_label_key(np.asarray(record["labels"], dtype=int)): record for record in seed_records}
    unique: dict[tuple[int, ...], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for label, f_value, constraint in zip(labels, f_values, constraints, strict=True):
        canonical = encoding.canonical_relabel(label)
        unique.setdefault(_label_key(canonical), (canonical, np.asarray(f_value, dtype=float), np.asarray(constraint, dtype=float)))
    ordered = sorted(unique.values(), key=lambda value: (tuple(float(item) for item in value[1]), _label_key(value[0])))
    pareto_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    posthoc_rows: list[dict[str, Any]] = []
    for index, (canonical, _pymoo_f, constraint) in enumerate(ordered):
        solution_id = f"seed{seed}_solution{index:03d}"
        mapping = encoding.to_cluster_by_class(canonical, context["class_nodes"])
        coupling, cohesion, imbalance = stage2.evaluate_structural_objectives(context["raw_edges"], mapping, "raw_weight")
        f_semantic = evaluate_semantic_objective(
            context["semantic_edges"], mapping, total_weight=float(context["semantic_graph_metadata"]["total_edge_weight"])
        )
        record = seed_by_key.get(_label_key(canonical))
        row = {
            "subject": context["subject"], "seed": seed, "solution_id": solution_id,
            "coupling": float(coupling), "cohesion": float(cohesion), "imbalance": float(imbalance),
            "f_semantic": float(f_semantic),
            "pymoo_f0_coupling": float(coupling), "pymoo_f1_negative_cohesion": float(-cohesion),
            "pymoo_f2_imbalance": float(imbalance), "pymoo_f3_f_semantic": float(f_semantic),
            "feasible": bool(np.all(constraint <= 0.0)),
            "is_injected_seed": bool(record is not None),
            "injected_seed_name": "" if record is None else str(record["name"]),
            "injected_seed_category": "" if record is None else str(record["category"]),
            "label_vector": json.dumps(canonical.astype(int).tolist()),
        }
        pareto_rows.append(row)
        clusters = encoding.to_clusters_frame(canonical, context["class_nodes"])
        label_rows.extend({"subject": context["subject"], "seed": seed, "solution_id": solution_id, **item} for item in clusters.to_dict("records"))
        posthoc_rows.append(stage2._partition_metrics_row(
            subject=context["subject"], seed=seed, solution_id=solution_id,
            class_nodes=context["class_nodes"], clusters=clusters, raw_edges=context["raw_edges"],
            cluster_by_class=mapping, reference_mapping=None,
        ))
    return pareto_rows, label_rows, posthoc_rows


def _project_front(pareto_rows: list[dict[str, Any]], posthoc_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not pareto_rows:
        raise ValueError("Stage 3 four-dimensional Pareto front is empty")
    matrix = np.asarray([[row["pymoo_f0_coupling"], row["pymoo_f1_negative_cohesion"], row["pymoo_f2_imbalance"]] for row in pareto_rows], dtype=float)
    indices = _nondominated_indices(matrix)
    candidates = [pareto_rows[int(index)] for index in indices]
    candidates.sort(key=lambda row: (row["solution_id"], tuple(float(row[key]) for key in ("pymoo_f0_coupling", "pymoo_f1_negative_cohesion", "pymoo_f2_imbalance"))))
    seen: set[tuple[float, float, float]] = set()
    projected: list[dict[str, Any]] = []
    for row in candidates:
        key = tuple(float(row[key]) for key in ("pymoo_f0_coupling", "pymoo_f1_negative_cohesion", "pymoo_f2_imbalance"))
        if key in seen:
            continue
        seen.add(key)
        projected.append({
            "subject": row["subject"], "seed": row["seed"], "solution_id": row["solution_id"],
            "original_solution_id": row["solution_id"], "coupling": row["coupling"], "cohesion": row["cohesion"],
            "imbalance": row["imbalance"], "original_f_semantic": row["f_semantic"],
            "pymoo_f0_coupling": row["pymoo_f0_coupling"], "pymoo_f1_negative_cohesion": row["pymoo_f1_negative_cohesion"],
            "pymoo_f2_imbalance": row["pymoo_f2_imbalance"], "feasible": row["feasible"],
            "is_injected_seed": row["is_injected_seed"], "label_vector": row["label_vector"],
        })
    posthoc_by_id = {row["solution_id"]: row for row in posthoc_rows}
    selection_inputs = [{**row, "feasible": bool(row["feasible"])} for row in projected]
    selection_posthoc = [posthoc_by_id[row["solution_id"]] for row in projected]
    return projected, [stage2._select_solution(selection_posthoc, selection_inputs)]


def _normalize_projected(matrix: np.ndarray, bounds: dict[str, Any]) -> np.ndarray:
    lower = np.asarray(bounds["lower_bounds"], dtype=float)
    upper = np.asarray(bounds["upper_bounds"], dtype=float)
    values = np.asarray(matrix, dtype=float)
    tolerance = float(bounds.get("bound_tolerance", 1e-12))
    if np.any(values < lower - tolerance) or np.any(values > upper + tolerance):
        raise ValueError("projected Stage 3 objective lies outside frozen Stage 2 bounds")
    return (values - lower) / (upper - lower)


def _independent_projected_hv(path: Path, bounds: dict[str, Any]) -> tuple[float, int]:
    frame = _read_stage3_csv(path)
    objective_columns = ["pymoo_f0_coupling", "pymoo_f1_negative_cohesion", "pymoo_f2_imbalance"]
    matrix = frame.loc[:, objective_columns].to_numpy(dtype=float)
    indices = _nondominated_indices(matrix)
    if len(indices) != len(frame):
        raise ValueError("saved projected front contains dominated rows")
    normalized = _normalize_projected(matrix[indices], bounds)
    return stage2._hypervolume(normalized, REFERENCE_POINT), len(indices)


def _redundancy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from scipy.stats import spearmanr

    semantic = np.asarray([row["f_semantic"] for row in rows], dtype=float)
    coupling = np.asarray([row["coupling"] for row in rows], dtype=float)
    result = {
        "method": "spearman", "semantic_objective": "f_semantic", "structural_objective": "coupling",
        "structural_objective_index": 0, "pareto_solution_count": len(rows),
        "constant_input": bool(len(set(semantic.tolist())) <= 1 or len(set(coupling.tolist())) <= 1),
        "rho": None, "p_value": None, "undefined_reason": None,
    }
    if len(rows) < 2:
        result["undefined_reason"] = "fewer_than_two_pareto_solutions"
        return result
    if result["constant_input"]:
        result["undefined_reason"] = "constant_input"
        return result
    correlation = spearmanr(semantic, coupling)
    result["rho"] = float(correlation.statistic)
    result["p_value"] = float(correlation.pvalue)
    return result


def validate_run_output(output_dir: Path, context: dict[str, Any]) -> dict[str, Any]:
    front = _read_stage3_csv(output_dir / "pareto_front_4d.csv")
    projected = _read_stage3_csv(output_dir / "projected_front_3d.csv")
    if front.empty or projected.empty:
        raise ValueError("formal Stage 3 front is empty")
    required = ["coupling", "cohesion", "imbalance", "f_semantic", "pymoo_f0_coupling", "pymoo_f1_negative_cohesion", "pymoo_f2_imbalance", "pymoo_f3_f_semantic"]
    if any(column not in front.columns for column in required):
        raise ValueError("four-dimensional front schema is incomplete")
    values = front[required].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("four-dimensional front contains non-finite values")
    if not np.all((front["f_semantic"] >= 0.0) & (front["f_semantic"] <= 1.0)):
        raise ValueError("f_semantic lies outside [0,1]")
    if float(front["f_semantic"].max() - front["f_semantic"].min()) <= 0.0:
        raise ValueError("f_semantic has no variation across the final front")
    nd = _nondominated_indices(front[["pymoo_f0_coupling", "pymoo_f1_negative_cohesion", "pymoo_f2_imbalance", "pymoo_f3_f_semantic"]].to_numpy(dtype=float))
    if len(nd) != len(front):
        raise ValueError("four-dimensional front contains dominated rows")
    stored_hv = json.loads((output_dir / "projected_hypervolume.json").read_text(encoding="utf-8"))
    recomputed, projected_nd = _independent_projected_hv(output_dir / "projected_front_3d.csv", context["bounds"])
    if projected_nd != len(projected):
        raise ValueError("projected front was not independently re-filtered")
    if not np.isclose(recomputed, float(stored_hv["stored_value"]), rtol=0.0, atol=HV_TOLERANCE):
        raise ValueError("stored and independently recomputed projected Hypervolume differ")
    selected = json.loads((output_dir / "selected_solution.json").read_text(encoding="utf-8"))
    if selected["selected_solution_id"] not in set(projected["solution_id"]):
        raise ValueError("selected solution is not in projected front")
    labels = _read_stage3_csv(output_dir / "partition_labels.csv")
    expected_class_ids = set(context["class_nodes"]["class_id"].astype(str))
    for solution_id, group in labels.groupby("solution_id", sort=False):
        observed_class_ids = set(group["class_id"].astype(str))
        if observed_class_ids != expected_class_ids or group["class_id"].astype(str).duplicated().any():
            raise ValueError(f"partition labels do not cover the formal scope exactly: {solution_id}")
    if labels["solution_id"].nunique() != len(front):
        raise ValueError("partition labels do not cover every four-dimensional front solution")

    # Recompute every saved four-objective row from its saved partition. This
    # keeps the objective/selection boundary auditable and catches accidental
    # reporting-only transformations.
    expected_by_solution = {
        row["solution_id"]: row
        for row in front.to_dict("records")
    }
    for solution_id, group in labels.groupby("solution_id", sort=False):
        if solution_id not in expected_by_solution:
            raise ValueError(f"partition labels contain unknown solution_id: {solution_id}")
        mapping = dict(zip(group["class_id"].astype(str), group["cluster_id"].astype(int), strict=True))
        computed = evaluate_four_objective_values(
            context["raw_edges"],
            context["semantic_edges"],
            mapping,
            "raw_weight",
            float(context["semantic_graph_metadata"]["total_edge_weight"]),
        )
        row = expected_by_solution[solution_id]
        expected = (row["coupling"], row["cohesion"], row["imbalance"], row["f_semantic"])
        if not np.allclose(computed, expected, rtol=0.0, atol=1e-12):
            raise ValueError(f"saved objective row does not match its partition: {solution_id}")

    selection_schema = selected.get("selection_input_schema") if isinstance(selected, dict) else None
    if selection_schema != ["solution_id", "feasible", "coupling", "cohesion", "imbalance", "is_injected_seed", "label_vector"]:
        raise ValueError("representative selection schema is not the frozen Stage 2 schema")
    selected_group = labels.loc[labels["solution_id"] == selected["selected_solution_id"]]
    selected_mapping = dict(zip(selected_group["class_id"].astype(str), selected_group["cluster_id"].astype(int), strict=True))
    selected_computed = evaluate_four_objective_values(
        context["raw_edges"],
        context["semantic_edges"],
        selected_mapping,
        "raw_weight",
        float(context["semantic_graph_metadata"]["total_edge_weight"]),
    )
    selected_row = selected["selected_four_objective_row"]
    if not np.allclose(selected_computed, (selected_row["coupling"], selected_row["cohesion"], selected_row["imbalance"], selected_row["f_semantic"]), rtol=0.0, atol=1e-12):
        raise ValueError("selected solution objective values do not match its saved partition")
    return {
        "front_size": len(front), "f_semantic_min": float(front["f_semantic"].min()),
        "f_semantic_mean": float(front["f_semantic"].mean()), "f_semantic_max": float(front["f_semantic"].max()),
        "f_semantic_std": float(front["f_semantic"].std(ddof=0)), "projected_front_size": len(projected),
        "projected_hv": float(stored_hv["stored_value"]), "recomputed_projected_hv": recomputed,
        "hv_abs_difference": abs(float(stored_hv["stored_value"]) - recomputed),
        "selected_solution_id": selected["selected_solution_id"],
        "selected_f_semantic": float(selected["selected_four_objective_row"]["f_semantic"]),
        "validation_pass": True,
    }


def run_seed(subject: str, seed: int, output_dir: Path, run_type: str = "validation") -> Path:
    context = load_context(subject)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite existing Stage 3 output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    implementation_commit = git_head()
    start_timestamp = utc_now()
    started = time.perf_counter()
    logs = [f"start subject={subject} seed={seed} run_type={run_type}", f"implementation_commit={implementation_commit}"]
    seed_records = stage2._seed_initialization_records(
        class_nodes=context["class_nodes"], raw_edges=context["raw_edges"],
        raw_leiden_clusters=context["stage1_raw_baseline"], seed=seed,
        config=context["initialization_config"], max_cluster_ratio=context["max_cluster_ratio"],
    )
    problem = build_four_objective_problem(
        context["class_nodes"], context["raw_edges"], context["semantic_edges"], "raw_weight",
        seed=seed, max_cluster_ratio=context["max_cluster_ratio"],
    )
    algorithm = stage2.build_nsga2_algorithm(
        population_size=context["population_size"],
        seed_labels=[record["labels"] for record in seed_records],
        max_cluster_ratio=context["max_cluster_ratio"],
    )
    from pymoo.optimize import minimize

    result = minimize(problem, algorithm, termination=("n_gen", context["generations"]), seed=int(seed), verbose=False, save_history=False)
    labels, f_values, constraints, front_diagnostics = _front_arrays(result)
    pareto_rows, label_rows, posthoc_rows = _solution_rows(context, seed, labels, f_values, constraints, seed_records)
    if not pareto_rows:
        raise ValueError("formal Stage 3 produced an empty four-dimensional front")
    projected_rows, selected_list = _project_front(pareto_rows, posthoc_rows)
    selected = selected_list[0]
    selected_original = next(row for row in pareto_rows if row["solution_id"] == selected["solution_id"])
    selected_posthoc = next(row for row in posthoc_rows if row["solution_id"] == selected["solution_id"])
    projected_path = output_dir / "projected_front_3d.csv"
    _write_stage3_csv(pd.DataFrame(projected_rows), projected_path)
    matrix = pd.DataFrame(projected_rows)[["pymoo_f0_coupling", "pymoo_f1_negative_cohesion", "pymoo_f2_imbalance"]].to_numpy(dtype=float)
    normalized = _normalize_projected(matrix, context["bounds"])
    stored_hv = stage2._hypervolume(normalized, REFERENCE_POINT)
    recomputed_hv, _ = _independent_projected_hv(projected_path, context["bounds"])
    _write_stage3_csv(pd.DataFrame(pareto_rows), output_dir / "pareto_front_4d.csv")
    _write_stage3_csv(pd.DataFrame(label_rows), output_dir / "partition_labels.csv")
    selected_partition = pd.DataFrame([
        {"class_id": row["class_id"], "class_name": row["class_name"], "cluster_id": row["cluster_id"]}
        for row in label_rows if row["solution_id"] == selected["solution_id"]
    ])
    selected_json = {
        "selected_solution_id": selected["solution_id"],
        "selected_projected_row": selected,
        "selected_four_objective_row": selected_original,
        "selected_posthoc_metrics": selected_posthoc,
        "selected_partition": selected_partition.to_dict("records"),
        "selection_input_schema": ["solution_id", "feasible", "coupling", "cohesion", "imbalance", "is_injected_seed", "label_vector"],
        "selection_implementation": "experiments/02_stage2_nsga_structure_only/run.py:_select_solution",
        "semantic_objective_used_for_selection": False,
    }
    (output_dir / "selected_solution.json").write_text(json.dumps(selected_json, indent=2) + "\n", encoding="utf-8")
    (output_dir / "projected_hypervolume.json").write_text(json.dumps({
        "implementation": "experiments/02_stage2_nsga_structure_only/run.py:_hypervolume",
        "bounds_source": relative(BOUNDS_PATH), "reference_point": [1.1, 1.1, 1.1],
        "stored_value": stored_hv, "recomputed_value": recomputed_hv,
        "absolute_difference": abs(stored_hv - recomputed_hv), "tolerance": HV_TOLERANCE,
        "pass": bool(np.isclose(stored_hv, recomputed_hv, rtol=0.0, atol=HV_TOLERANCE)),
    }, indent=2) + "\n", encoding="utf-8")
    (output_dir / "objective_redundancy.json").write_text(json.dumps(_redundancy(pareto_rows), indent=2) + "\n", encoding="utf-8")
    _write_stage3_csv(selected_partition, output_dir / "selected_partition.csv")
    elapsed = time.perf_counter() - started
    validation = validate_run_output(output_dir, context)
    metadata = {
        "schema_version": 1, "subject": subject, "storage_subject": context["storage_subject"], "seed": seed,
        "run_type": run_type, "implementation_commit": implementation_commit, "execution_head": implementation_commit,
        "results_commit": None, "reporting_commit": None, "config_path": relative(CONFIG_PATH),
        "config_sha256": sha256_file(CONFIG_PATH), "stage2_config_path": relative(STAGE2_CONFIG_PATH),
        "g_raw_provenance": {
            "loader": "experiments/02_stage2_nsga_structure_only/run.py:_raw_graph_inputs",
            "builder": "src/evo_ms/graph/raw_graph_builder.py",
            "class_nodes_path": relative(context["extracted_dir"] / "class_nodes.csv"),
            "structural_dependencies_path": relative(context["extracted_dir"] / "structural_dependencies.csv"),
            "raw_edge_hash": stage2._frame_sha256(context["raw_edges"]),
        },
        "g_sem_graph_hash": context["semantic_graph_hash"], "g_sem_metadata_path": relative(subject_paths(subject)["graph_metadata"]),
        "objective_order": STAGE3_OBJECTIVE_ORDER,
        "report_objective_order": ["coupling", "cohesion", "imbalance", "f_semantic"],
        "coupling_objective": {"name": "coupling", "index": 0},
        "population_size": context["population_size"], "generations": context["generations"],
        "warm_start_source": "experiments/02_stage2_nsga_structure_only/run.py:_seed_initialization_records",
        "projected_front_rule": "final 4D front -> exact 3D nondominance -> exact projected objective tuple deduplication; stable solution_id survivor",
        "projected_hv_implementation": "experiments/02_stage2_nsga_structure_only/run.py:_hypervolume",
        "projected_hv_bounds_source": relative(BOUNDS_PATH), "projected_hv_reference_point": [1.1, 1.1, 1.1],
        "representative_selection_implementation": "experiments/02_stage2_nsga_structure_only/run.py:_select_solution",
        "start_timestamp_utc": start_timestamp, "end_timestamp_utc": utc_now(), "runtime_seconds": elapsed,
        "completion_status": "completed", "validation": validation,
        "stage2_same_seed_hypervolume": context["stage2_hv"],
        "structural_objective_invariance": structural_invariance_checks(context),
        "no_model_inference": True, "no_graph_fusion": True, "semantic_input_source": "semantic_edges.csv only",
    }
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    logs.extend([f"completed runtime_seconds={elapsed:.6f}", f"four_objective_front_size={len(pareto_rows)}", f"projected_front_size={len(projected_rows)}"])
    (output_dir / "run.log").write_text("\n".join(logs) + "\n", encoding="utf-8")
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True, choices=SEMANTIC_SUBJECTS)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-type", default="validation", choices=["validation", "formal"])
    args = parser.parse_args()
    output = run_seed(args.subject, args.seed, args.output_dir, args.run_type)
    print(f"Stage 3 output: {relative(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
