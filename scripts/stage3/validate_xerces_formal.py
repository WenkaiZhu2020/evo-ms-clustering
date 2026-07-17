#!/usr/bin/env python3
"""Independently validate and inventory the completed Xerces formal seeds.

This module only reloads saved files. It never calls the optimizer, loads a
model, writes experiment outputs, or rebuilds a graph. The command-line entry
point writes the final inventory and reports only after every seed passes.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.optimization.stage3_problem import evaluate_four_objective_values


FORMAL_ROOT = ROOT / "results/xerces/04_stage3_semantic/formal"
SEED_ZERO_ROOT = ROOT / "results/xerces/04_stage3_semantic/validation/seed_00"
CONFIG_PATH = ROOT / "configs/experiments/04_stage3_semantic.yml"
STAGE2_CONFIG_PATH = ROOT / "configs/experiments/02_stage2_nsga_structure_only.yml"
BOUNDS_PATH = ROOT / "configs/experiments/stage2_robustness_bounds.yml"
MANIFEST_PATH = ROOT / "reports/stage3/formal_run_manifest.json"
LAUNCH_PATH = ROOT / "reports/stage3/xerces_formal_launch.json"
INVENTORY_PATH = FORMAL_ROOT / "formal_seed_inventory.csv"
RUN_METADATA_PATH = FORMAL_ROOT / "formal_run_metadata.json"
SUMMARY_MD_PATH = ROOT / "reports/stage3/xerces_formal_validation.md"
SUMMARY_JSON_PATH = ROOT / "reports/stage3/xerces_formal_validation.json"
LAUNCH_REPORT_PATH = ROOT / "reports/stage3/xerces_formal_launch.md"

EXPECTED_CLASS_COUNT = 814
EXPECTED_POPULATION = 100
EXPECTED_GENERATIONS = 100
SUBJECT_CONFIG = {
    "jpetstore": {"storage_subject": "jpetstore", "class_count": 24},
    "daytrader": {"storage_subject": "daytrader", "class_count": 53},
    "xerces": {"storage_subject": "xerces-j", "class_count": 814},
}
REPORT_OBJECTIVES = ["coupling", "cohesion", "imbalance", "f_semantic"]
PYMOO_OBJECTIVES = [
    "pymoo_f0_coupling",
    "pymoo_f1_negative_cohesion",
    "pymoo_f2_imbalance",
    "pymoo_f3_f_semantic",
]
PROJECTED_COLUMNS = [
    "subject",
    "seed",
    "solution_id",
    "original_solution_id",
    "coupling",
    "cohesion",
    "imbalance",
    "original_f_semantic",
    "pymoo_f0_coupling",
    "pymoo_f1_negative_cohesion",
    "pymoo_f2_imbalance",
    "feasible",
    "is_injected_seed",
    "label_vector",
]
REQUIRED_ARTIFACTS = [
    "run_metadata.json",
    "run.log",
    "pareto_front_4d.csv",
    "projected_front_3d.csv",
    "partition_labels.csv",
    "selected_solution.json",
    "projected_hypervolume.json",
    "objective_redundancy.json",
    "selected_partition.csv",
]
ALGORITHM_FILES = [
    "configs/experiments/04_stage3_semantic.yml",
    "configs/experiments/02_stage2_nsga_structure_only.yml",
    "configs/experiments/stage2_robustness_bounds.yml",
    "experiments/04_stage3_semantic/run.py",
    "experiments/02_stage2_nsga_structure_only/run.py",
    "src/evo_ms/optimization/encoding.py",
    "src/evo_ms/optimization/objectives.py",
    "src/evo_ms/optimization/problem.py",
    "src/evo_ms/optimization/semantic_objective.py",
    "src/evo_ms/optimization/stage3_problem.py",
    "src/evo_ms/graph/raw_graph_builder.py",
    "src/evo_ms/extraction/dependency_extractor.py",
    "src/evo_ms/evaluation/partition_metrics.py",
]
SELECTION_SCHEMA = [
    "solution_id",
    "feasible",
    "coupling",
    "cohesion",
    "imbalance",
    "is_injected_seed",
    "label_vector",
]


def _load_stage3_runner():
    path = ROOT / "experiments/04_stage3_semantic/run.py"
    spec = importlib.util.spec_from_file_location("stage3_formal_runner_for_validator", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stage3_runner = _load_stage3_runner()
stage2 = stage3_runner.stage2


class ValidationFailure(ValueError):
    """Raised when saved formal evidence fails an integrity criterion."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_seeds() -> list[int]:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    manifest = load_json(MANIFEST_PATH)
    config_seeds = list(config["seeds"]["formal"])
    manifest_seeds = list(manifest["formal_seeds"])
    if config_seeds != manifest_seeds:
        raise ValidationFailure("config and manifest formal seed lists differ")
    validate_seed_values(config_seeds)
    return [int(seed) for seed in config_seeds]


def validate_seed_values(values: list[int]) -> None:
    if len(values) != 30 or len(set(values)) != 30:
        raise ValidationFailure("formal seed list is not exactly 30 unique seeds")
    if list(values) != list(range(30)):
        raise ValidationFailure(f"unexpected formal seed list: {values}")


def resolve_seed_sources(seeds: list[int]) -> dict[int, Path]:
    """Resolve seed 0 without copying it and reject unexpected formal dirs."""
    if not SEED_ZERO_ROOT.is_dir():
        raise ValidationFailure(f"missing seed-0 source: {SEED_ZERO_ROOT}")
    formal_dirs = {
        path.name
        for path in FORMAL_ROOT.iterdir()
        if path.is_dir() and path.name.startswith("seed_")
    }
    expected_formal_dirs = {f"seed_{seed:02d}" for seed in seeds if seed != 0}
    extra = sorted(formal_dirs - expected_formal_dirs)
    missing = sorted(expected_formal_dirs - formal_dirs)
    if extra or missing:
        raise ValidationFailure(f"formal seed directories extra={extra} missing={missing}")
    sources = {0: SEED_ZERO_ROOT}
    sources.update({seed: FORMAL_ROOT / f"seed_{seed:02d}" for seed in seeds if seed != 0})
    for seed, path in sources.items():
        if not path.is_dir():
            raise ValidationFailure(f"missing seed {seed} source directory: {path}")
    return sources


def validate_run_log(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "completed runtime_seconds=" not in text:
        raise ValidationFailure(f"run log has no completion record: {path}")
    for forbidden in ("Traceback", "KeyboardInterrupt", "fatal error", "ERROR"):
        if forbidden.lower() in text.lower():
            raise ValidationFailure(f"run log contains {forbidden}: {path}")


def canonical_seed_artifact_hash(source: Path) -> str:
    rows = []
    for name in sorted(REQUIRED_ARTIFACTS):
        path = source / name
        if not path.is_file():
            raise ValidationFailure(f"missing required artifact: {path}")
        rows.append(f"{name}\t{aggregate_artifact_hash(name, path)}\n")
    return sha256_bytes("".join(rows).encode("utf-8"))


def _without_timestamps(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_timestamps(item)
            for key, item in value.items()
            if not key.endswith("_timestamp_utc") and key not in {"creation_timestamp_utc", "completed_at_utc"}
        }
    if isinstance(value, list):
        return [_without_timestamps(item) for item in value]
    return value


def aggregate_artifact_hash(name: str, path: Path) -> str:
    """Hash one artifact for the seed aggregate, excluding metadata timestamps."""
    if name == "run_metadata.json":
        canonical = json.dumps(
            _without_timestamps(load_json(path)),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256_bytes(canonical)
    return sha256_file(path)


def canonical_formal_hash(seed_hashes: dict[int, str]) -> str:
    payload = "".join(
        f"{seed}\t{seed_hashes[seed]}\n" for seed in sorted(seed_hashes)
    ).encode("utf-8")
    return sha256_bytes(payload)


def _git_file_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def algorithm_fingerprint(commit: str) -> dict[str, Any]:
    file_hashes = {
        path: sha256_bytes(_git_file_bytes(commit, path))
        for path in sorted(ALGORITHM_FILES)
    }
    payload = "".join(f"{path}\t{file_hashes[path]}\n" for path in sorted(file_hashes)).encode("utf-8")
    return {"sha256": sha256_bytes(payload), "files": file_hashes}


def current_frozen_hashes(context: dict[str, Any]) -> dict[str, str]:
    manifest = load_json(MANIFEST_PATH)
    input_paths = {
        "jpetstore": ROOT / "data/semantic_inputs/jpetstore_class_declarations.csv",
        "daytrader": ROOT / "data/semantic_inputs/daytrader_class_declarations.csv",
        "xerces": ROOT / "data/semantic_inputs/xerces-j_class_declarations.csv",
    }
    input_hashes = {}
    for subject, path in input_paths.items():
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        payload = "".join(
            f"{row['class_id']}\t{row['input_hash']}\n"
            for row in sorted(rows, key=lambda row: row["class_id"])
        ).encode("utf-8")
        input_hashes[subject] = sha256_bytes(payload)
        if input_hashes[subject] != manifest["input_hashes"][subject]["aggregate_sha256"]:
            raise ValidationFailure(f"input hash changed for {subject}")
    embedding_loader_path = ROOT / "scripts/stage3/build_semantic_graphs.py"
    if str(ROOT / "scripts/stage3") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts/stage3"))
    embedding_spec = importlib.util.spec_from_file_location("stage3_graph_builder_for_validator", embedding_loader_path)
    if embedding_spec is None or embedding_spec.loader is None:
        raise ValidationFailure("cannot load saved-embedding integrity loader")
    embedding_module = importlib.util.module_from_spec(embedding_spec)
    embedding_spec.loader.exec_module(embedding_module)
    _, _, embedding_source = embedding_module.load_embedding_inputs("xerces", ROOT / "results", manifest)
    if embedding_source["source_embedding_aggregate_sha256"] != manifest["embedding_hashes"]["xerces"]["aggregate_sha256"]:
        raise ValidationFailure("Xerces embedding aggregate hash changed")
    actual_graph_hash = stage3_runner.canonical_graph_hash_file(
        ROOT / "results/xerces/04_stage3_semantic/graph/semantic_edges.csv"
    )
    if actual_graph_hash != manifest["semantic_graph_hashes"]["xerces"]["aggregate_sha256"]:
        raise ValidationFailure("Xerces semantic graph hash changed")
    return {
        "jpetstore_input": input_hashes["jpetstore"],
        "daytrader_input": input_hashes["daytrader"],
        "xerces_input": input_hashes["xerces"],
        "xerces_semantic_graph": actual_graph_hash,
        "xerces_embedding": embedding_source["source_embedding_aggregate_sha256"],
    }


def _assert_scope(
    group: pd.DataFrame,
    expected_class_ids: set[str],
    label: str,
    expected_class_count: int = EXPECTED_CLASS_COUNT,
) -> dict[str, int]:
    class_ids = group["class_id"].astype(str)
    if len(class_ids) != expected_class_count or class_ids.duplicated().any() or set(class_ids) != expected_class_ids:
        raise ValidationFailure(f"class scope mismatch for {label}")
    return dict(zip(class_ids, group["cluster_id"].astype(int), strict=True))


def _recompute_projected_hv(projected: pd.DataFrame, bounds: dict[str, Any]) -> tuple[float, int]:
    matrix = projected.loc[:, [
        "pymoo_f0_coupling",
        "pymoo_f1_negative_cohesion",
        "pymoo_f2_imbalance",
    ]].to_numpy(dtype=float)
    nd = stage3_runner._nondominated_indices(matrix)
    if len(nd) != len(projected):
        raise ValidationFailure("dominated projected row remains")
    if len({tuple(float(value) for value in row) for row in matrix}) != len(matrix):
        raise ValidationFailure("duplicate projected objective vector remains")
    normalized = stage3_runner._normalize_projected(matrix[nd], bounds)
    return stage2._hypervolume(normalized, stage3_runner.REFERENCE_POINT), len(nd)


def validate_four_dimensional_front(front: pd.DataFrame, seed: int) -> None:
    if front.empty:
        raise ValidationFailure(f"seed {seed}: empty four-dimensional front")
    for column in REPORT_OBJECTIVES + PYMOO_OBJECTIVES:
        if column not in front.columns:
            raise ValidationFailure(f"seed {seed}: missing front column {column}")
    objective_values = front.loc[:, REPORT_OBJECTIVES + PYMOO_OBJECTIVES].to_numpy(dtype=float)
    if not np.isfinite(objective_values).all():
        raise ValidationFailure(f"seed {seed}: non-finite objective")
    if not ((front["f_semantic"] >= 0.0) & (front["f_semantic"] <= 1.0)).all():
        raise ValidationFailure(f"seed {seed}: f_semantic outside [0,1]")
    if float(front["f_semantic"].max() - front["f_semantic"].min()) <= 0.0:
        raise ValidationFailure(f"seed {seed}: f_semantic has no variation")
    if not front["solution_id"].is_unique:
        raise ValidationFailure(f"seed {seed}: duplicate four-dimensional solution_id")
    nd4 = stage3_runner._nondominated_indices(front.loc[:, PYMOO_OBJECTIVES].to_numpy(dtype=float))
    if len(nd4) != len(front):
        raise ValidationFailure(f"seed {seed}: dominated four-dimensional row remains")


def validate_projected_front(projected: pd.DataFrame, front: pd.DataFrame, seed: int, bounds: dict[str, Any]) -> float:
    if projected.empty:
        raise ValidationFailure(f"seed {seed}: empty projected front")
    if list(projected.columns) != PROJECTED_COLUMNS:
        raise ValidationFailure(f"seed {seed}: projected schema mismatch")
    numeric_columns = [
        "coupling", "cohesion", "imbalance", "original_f_semantic",
        "pymoo_f0_coupling", "pymoo_f1_negative_cohesion", "pymoo_f2_imbalance",
    ]
    if not np.isfinite(projected.loc[:, numeric_columns].to_numpy(dtype=float)).all():
        raise ValidationFailure(f"seed {seed}: non-finite projected objective")
    if not projected["solution_id"].is_unique:
        raise ValidationFailure(f"seed {seed}: duplicate projected solution_id")
    if not set(projected["solution_id"]).issubset(set(front["solution_id"])):
        raise ValidationFailure(f"seed {seed}: projected solution is not in four-dimensional front")
    recomputed_hv, projected_nd = _recompute_projected_hv(projected, bounds)
    if projected_nd != len(projected):
        raise ValidationFailure(f"seed {seed}: projected non-dominance size mismatch")
    front_matrix_3d = front.loc[:, PYMOO_OBJECTIVES[:3]].to_numpy(dtype=float)
    front_nd3 = stage3_runner._nondominated_indices(front_matrix_3d)
    candidate_rows = [front.iloc[int(index)].to_dict() for index in front_nd3]
    candidate_rows.sort(key=lambda row: (row["solution_id"], tuple(float(row[column]) for column in PYMOO_OBJECTIVES[:3])))
    expected_projected_ids = []
    seen_projected = set()
    for row in candidate_rows:
        key = tuple(float(row[column]) for column in PYMOO_OBJECTIVES[:3])
        if key not in seen_projected:
            seen_projected.add(key)
            expected_projected_ids.append(row["solution_id"])
    if list(projected["solution_id"]) != expected_projected_ids:
        raise ValidationFailure(f"seed {seed}: projected stable-survivor rule mismatch")
    front_by_id = {row["solution_id"]: row for row in front.to_dict("records")}
    for row in projected.to_dict("records"):
        if row["original_solution_id"] != row["solution_id"]:
            raise ValidationFailure(f"seed {seed}: projected original_solution_id mismatch")
        if not np.isclose(float(row["original_f_semantic"]), float(front_by_id[row["solution_id"]]["f_semantic"]), rtol=0.0, atol=1e-12):
            raise ValidationFailure(f"seed {seed}: projected semantic mapping mismatch")
    return recomputed_hv


def _validate_metadata(
    metadata: dict[str, Any],
    seed: int,
    expected_config_sha: str,
    expected_graph_sha: str,
    expected_raw_edge_hash: str,
    subject: str = "xerces",
    storage_subject: str = "xerces-j",
) -> None:
    if metadata.get("subject") != subject:
        raise ValidationFailure(f"seed {seed}: subject is not {subject}")
    if int(metadata.get("seed", -1)) != seed:
        raise ValidationFailure(f"seed {seed}: metadata seed mismatch")
    expected_run_type = "validation" if seed == 0 else "formal"
    if metadata.get("run_type") != expected_run_type:
        raise ValidationFailure(f"seed {seed}: run_type mismatch")
    if metadata.get("completion_status") != "completed":
        raise ValidationFailure(f"seed {seed}: incomplete completion status")
    if metadata.get("config_sha256") != expected_config_sha:
        raise ValidationFailure(f"seed {seed}: config hash mismatch")
    if metadata.get("g_sem_graph_hash") != expected_graph_sha:
        raise ValidationFailure(f"seed {seed}: semantic graph hash mismatch")
    if metadata.get("report_objective_order") != ["coupling", "cohesion", "imbalance", "f_semantic"]:
        raise ValidationFailure(f"seed {seed}: report objective order mismatch")
    if metadata.get("population_size") != EXPECTED_POPULATION or metadata.get("generations") != EXPECTED_GENERATIONS:
        raise ValidationFailure(f"seed {seed}: population/generation mismatch")
    if metadata.get("objective_order") != ["coupling", "negative_cohesion", "imbalance", "f_semantic"]:
        raise ValidationFailure(f"seed {seed}: objective order mismatch")
    provenance = metadata.get("g_raw_provenance", {})
    if provenance.get("loader") != "experiments/02_stage2_nsga_structure_only/run.py:_raw_graph_inputs":
        raise ValidationFailure(f"seed {seed}: G_raw loader mismatch")
    if provenance.get("builder") != "src/evo_ms/graph/raw_graph_builder.py":
        raise ValidationFailure(f"seed {seed}: G_raw builder mismatch")
    if provenance.get("class_nodes_path") != f"data/extracted/{storage_subject}/class_nodes.csv" or provenance.get("structural_dependencies_path") != f"data/extracted/{storage_subject}/structural_dependencies.csv":
        raise ValidationFailure(f"seed {seed}: G_raw source paths mismatch")
    if provenance.get("raw_edge_hash") != expected_raw_edge_hash:
        raise ValidationFailure(f"seed {seed}: G_raw hash mismatch")


def validate_seed(
    seed: int,
    source: Path,
    context: dict[str, Any],
    expected_config_sha: str,
    expected_graph_sha: str,
    expected_raw_edge_hash: str,
    subject: str = "xerces",
    storage_subject: str = "xerces-j",
    expected_class_count: int = EXPECTED_CLASS_COUNT,
) -> dict[str, Any]:
    failures: list[str] = []
    for name in REQUIRED_ARTIFACTS:
        if not (source / name).is_file():
            failures.append(f"missing artifact: {name}")
    if failures:
        raise ValidationFailure(f"seed {seed}: " + "; ".join(failures))

    metadata = load_json(source / "run_metadata.json")
    _validate_metadata(
        metadata,
        seed,
        expected_config_sha,
        expected_graph_sha,
        expected_raw_edge_hash,
        subject=subject,
        storage_subject=storage_subject,
    )
    validate_run_log(source / "run.log")

    front = pd.read_csv(source / "pareto_front_4d.csv")
    validate_four_dimensional_front(front, seed)
    if set(front["subject"]) != {subject} or set(front["seed"].astype(int)) != {seed}:
        raise ValidationFailure(f"seed {seed}: four-dimensional subject/seed columns mismatch")
    nd4 = stage3_runner._nondominated_indices(front.loc[:, PYMOO_OBJECTIVES].to_numpy(dtype=float))
    if len(nd4) != len(front):
        raise ValidationFailure(f"seed {seed}: dominated four-dimensional row remains")

    projected = pd.read_csv(source / "projected_front_3d.csv")
    recomputed_hv = validate_projected_front(projected, front, seed, context["bounds"])
    if set(projected["subject"]) != {subject} or set(projected["seed"].astype(int)) != {seed}:
        raise ValidationFailure(f"seed {seed}: projected subject/seed columns mismatch")
    stored_hv = load_json(source / "projected_hypervolume.json")
    if not np.isclose(recomputed_hv, float(stored_hv["stored_value"]), rtol=0.0, atol=1e-12):
        raise ValidationFailure(f"seed {seed}: projected Hypervolume mismatch")

    labels = pd.read_csv(source / "partition_labels.csv")
    expected_class_ids = set(context["class_nodes"]["class_id"].astype(str))
    if set(labels["solution_id"]) != set(front["solution_id"]):
        raise ValidationFailure(f"seed {seed}: partition solution IDs mismatch")
    label_groups = {}
    for solution_id, group in labels.groupby("solution_id", sort=False):
        label_groups[solution_id] = _assert_scope(
            group,
            expected_class_ids,
            f"seed {seed}/{solution_id}",
            expected_class_count=expected_class_count,
        )

    # Recompute every saved 4D row from its reloaded partition.
    for row in front.to_dict("records"):
        computed = evaluate_four_objective_values(
            context["raw_edges"], context["semantic_edges"], label_groups[row["solution_id"]],
            "raw_weight", float(context["semantic_graph_metadata"]["total_edge_weight"]),
        )
        expected = tuple(float(row[column]) for column in REPORT_OBJECTIVES)
        if not np.allclose(computed, expected, rtol=0.0, atol=1e-12):
            raise ValidationFailure(f"seed {seed}: objective recomputation mismatch for {row['solution_id']}")

    selected = load_json(source / "selected_solution.json")
    selected_id = selected.get("selected_solution_id")
    if selected_id not in set(projected["solution_id"]):
        raise ValidationFailure(f"seed {seed}: selected solution is not projected")
    if selected.get("selection_input_schema") != SELECTION_SCHEMA:
        raise ValidationFailure(f"seed {seed}: selection schema mismatch")
    if selected.get("semantic_objective_used_for_selection") is not False:
        raise ValidationFailure(f"seed {seed}: semantic objective influenced selection")
    selected_front = front.loc[front["solution_id"] == selected_id].iloc[0].to_dict()
    if selected.get("selected_four_objective_row", {}).get("solution_id") != selected_id:
        raise ValidationFailure(f"seed {seed}: selected 4D mapping mismatch")

    # Re-run only the exact Stage 2 representative selection on reloaded
    # projected rows and G_raw-derived posthoc metrics.
    projected_records = projected.to_dict("records")
    posthoc_rows = []
    for row in projected_records:
        group = labels.loc[labels["solution_id"] == row["solution_id"]]
        clusters = group.loc[:, ["class_id", "class_name", "cluster_id"]]
        posthoc_rows.append(stage2._partition_metrics_row(
            subject=subject, seed=seed, solution_id=row["solution_id"],
            class_nodes=context["class_nodes"], clusters=clusters,
            raw_edges=context["raw_edges"],
            cluster_by_class=label_groups[row["solution_id"]], reference_mapping=None,
        ))
    selection_inputs = [
        {key: row[key] for key in SELECTION_SCHEMA}
        for row in projected_records
    ]
    independently_selected = stage2._select_solution(posthoc_rows, selection_inputs)
    if independently_selected["solution_id"] != selected_id:
        raise ValidationFailure(f"seed {seed}: independent representative selection mismatch")

    selected_partition = pd.read_csv(source / "selected_partition.csv")
    selected_mapping = _assert_scope(
        selected_partition,
        expected_class_ids,
        f"seed {seed}/selected_partition",
        expected_class_count=expected_class_count,
    )
    if selected_mapping != label_groups[selected_id]:
        raise ValidationFailure(f"seed {seed}: selected partition mapping mismatch")
    selected_values = evaluate_four_objective_values(
        context["raw_edges"], context["semantic_edges"], selected_mapping,
        "raw_weight", float(context["semantic_graph_metadata"]["total_edge_weight"]),
    )
    selected_expected = tuple(float(selected_front[column]) for column in REPORT_OBJECTIVES)
    if not np.allclose(selected_values, selected_expected, rtol=0.0, atol=1e-12):
        raise ValidationFailure(f"seed {seed}: selected partition objective mismatch")

    redundancy = load_json(source / "objective_redundancy.json")
    if redundancy.get("semantic_objective") != "f_semantic" or redundancy.get("structural_objective") != "coupling" or redundancy.get("structural_objective_index") != 0 or redundancy.get("method") != "spearman":
        raise ValidationFailure(f"seed {seed}: redundancy diagnostic contract mismatch")
    if redundancy.get("source") is not None and redundancy.get("source") != "final_stage3_4d_pareto_front":
        raise ValidationFailure(f"seed {seed}: redundancy source mismatch")
    from scipy.stats import spearmanr
    correlation = spearmanr(front["f_semantic"].to_numpy(dtype=float), front["coupling"].to_numpy(dtype=float))
    if redundancy.get("rho") is None or not np.isclose(float(redundancy["rho"]), float(correlation.statistic), rtol=0.0, atol=1e-12):
        raise ValidationFailure(f"seed {seed}: redundancy rho mismatch")

    artifact_hashes = {name: sha256_file(source / name) for name in REQUIRED_ARTIFACTS}
    seed_hash = canonical_seed_artifact_hash(source)
    selected_posthoc = selected.get("selected_posthoc_metrics", {})
    return {
        "seed": seed,
        "source_directory": relative(source),
        "status": "valid",
        "implementation_commit": metadata["implementation_commit"],
        "execution_head": metadata["execution_head"],
        "config_sha256": metadata["config_sha256"],
        "semantic_graph_sha256": metadata["g_sem_graph_hash"],
        "runtime_seconds": float(metadata["runtime_seconds"]),
        "population_size": int(metadata["population_size"]),
        "generations": int(metadata["generations"]),
        "front_4d_size": int(len(front)),
        "projected_front_size": int(len(projected)),
        "projected_hv": float(stored_hv["stored_value"]),
        "selected_solution_id": selected_id,
        "selected_cluster_count": int(selected_posthoc["cluster_count"]),
        "selected_f_semantic": float(selected_front["f_semantic"]),
        "f_semantic_min": float(front["f_semantic"].min()),
        "f_semantic_mean": float(front["f_semantic"].mean()),
        "f_semantic_max": float(front["f_semantic"].max()),
        "f_semantic_std": float(front["f_semantic"].std(ddof=0)),
        "redundancy_spearman_rho": float(redundancy["rho"]),
        "validation_pass": True,
        "seed_artifact_aggregate_sha256": seed_hash,
        "aggregate_timestamp_policy": "run_metadata.json timestamps removed before seed aggregate hashing; all other required artifacts use raw UTF-8 bytes",
        "artifact_hashes": artifact_hashes,
    }


def write_inventory(records: list[dict[str, Any]]) -> None:
    fields = [
        "seed", "source_directory", "status", "implementation_commit", "execution_head",
        "config_sha256", "semantic_graph_sha256", "runtime_seconds", "population_size",
        "generations", "front_4d_size", "projected_front_size", "projected_hv",
        "selected_solution_id", "selected_cluster_count", "selected_f_semantic",
        "f_semantic_min", "f_semantic_mean", "f_semantic_max", "f_semantic_std",
        "redundancy_spearman_rho", "validation_pass", "seed_artifact_aggregate_sha256",
        "run_metadata_sha256", "run_log_sha256", "pareto_front_4d_sha256",
        "projected_front_3d_sha256", "partition_labels_sha256", "selected_solution_artifact_sha256",
        "projected_hv_artifact_sha256", "redundancy_artifact_sha256",
    ]
    INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with INVENTORY_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in sorted(records, key=lambda row: row["seed"]):
            hashes = record["artifact_hashes"]
            row = {key: record.get(key) for key in fields}
            row.update({
                "run_metadata_sha256": hashes["run_metadata.json"],
                "run_log_sha256": hashes["run.log"],
                "pareto_front_4d_sha256": hashes["pareto_front_4d.csv"],
                "projected_front_3d_sha256": hashes["projected_front_3d.csv"],
                "partition_labels_sha256": hashes["partition_labels.csv"],
                "selected_solution_artifact_sha256": hashes["selected_solution.json"],
                "projected_hv_artifact_sha256": hashes["projected_hypervolume.json"],
                "redundancy_artifact_sha256": hashes["objective_redundancy.json"],
            })
            writer.writerow(row)


def build_summary(records: list[dict[str, Any]], aggregate_hash: str, algorithm: dict[str, Any], seed0_compatibility: dict[str, Any]) -> dict[str, Any]:
    ordered = sorted(records, key=lambda row: row["seed"])
    all_front_f = []
    for record in ordered:
        front = pd.read_csv(ROOT / record["source_directory"] / "pareto_front_4d.csv")
        all_front_f.extend(front["f_semantic"].astype(float).tolist())
    runtimes = [row["runtime_seconds"] for row in ordered]
    front_sizes = [row["front_4d_size"] for row in ordered]
    projected_sizes = [row["projected_front_size"] for row in ordered]
    hvs = [row["projected_hv"] for row in ordered]
    rhos = [row["redundancy_spearman_rho"] for row in ordered]
    cluster_counts: dict[str, int] = {}
    for row in ordered:
        key = str(row["selected_cluster_count"])
        cluster_counts[key] = cluster_counts.get(key, 0) + 1
    return {
        "schema_version": 1,
        "subject": "xerces",
        "seed_count": len(ordered),
        "seed_list": [row["seed"] for row in ordered],
        "algorithm_fingerprint": algorithm,
        "seed_0_compatibility": seed0_compatibility,
        "runtime_seconds": {"min": min(runtimes), "mean": mean(runtimes), "median": median(runtimes), "max": max(runtimes)},
        "front_4d_size": {"min": min(front_sizes), "mean": mean(front_sizes), "median": median(front_sizes), "max": max(front_sizes)},
        "projected_front_size": {"min": min(projected_sizes), "mean": mean(projected_sizes), "median": median(projected_sizes), "max": max(projected_sizes)},
        "projected_hypervolume": {"min": min(hvs), "mean": mean(hvs), "median": median(hvs), "max": max(hvs), "std_population": pstdev(hvs)},
        "f_semantic_across_all_4d_rows": {"min": min(all_front_f), "mean": mean(all_front_f), "max": max(all_front_f)},
        "selected_cluster_count_distribution": dict(sorted(cluster_counts.items(), key=lambda item: int(item[0]))),
        "redundancy_rho": {"min": min(rhos), "mean": mean(rhos), "median": median(rhos), "max": max(rhos)},
        "independent_validation_pass_count": sum(bool(row["validation_pass"]) for row in ordered),
        "all_seeds_valid": all(bool(row["validation_pass"]) for row in ordered),
        "aggregate_formal_run_sha256": aggregate_hash,
        "per_seed": ordered,
        "no_final_effectiveness_claim": True,
    }


def write_summary(summary: dict[str, Any]) -> None:
    SUMMARY_JSON_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Xerces Stage 3 formal validation",
        "",
        "This report validates saved formal artifacts only. It makes no Stage 2",
        "versus Stage 3 effectiveness or statistical claim.",
        "",
        f"- Seeds: {summary['independent_validation_pass_count']}/{summary['seed_count']} passed.",
        f"- Algorithm fingerprint: `{summary['algorithm_fingerprint']['sha256']}`.",
        f"- Aggregate formal-run SHA-256: `{summary['aggregate_formal_run_sha256']}`.",
        f"- Seed-0 compatibility: {summary['seed_0_compatibility']['conclusion']}.",
        "",
        "## Distribution summary",
        "",
        f"- Runtime seconds min/mean/median/max: {summary['runtime_seconds']['min']:.6f} / {summary['runtime_seconds']['mean']:.6f} / {summary['runtime_seconds']['median']:.6f} / {summary['runtime_seconds']['max']:.6f}",
        f"- 4D front size min/mean/median/max: {summary['front_4d_size']['min']} / {summary['front_4d_size']['mean']:.3f} / {summary['front_4d_size']['median']:.3f} / {summary['front_4d_size']['max']}",
        f"- Projected front size min/mean/median/max: {summary['projected_front_size']['min']} / {summary['projected_front_size']['mean']:.3f} / {summary['projected_front_size']['median']:.3f} / {summary['projected_front_size']['max']}",
        f"- Projected HV min/mean/median/max/std: {summary['projected_hypervolume']['min']:.12f} / {summary['projected_hypervolume']['mean']:.12f} / {summary['projected_hypervolume']['median']:.12f} / {summary['projected_hypervolume']['max']:.12f} / {summary['projected_hypervolume']['std_population']:.12f}",
        f"- f_semantic across all 4D rows min/mean/max: {summary['f_semantic_across_all_4d_rows']['min']:.12f} / {summary['f_semantic_across_all_4d_rows']['mean']:.12f} / {summary['f_semantic_across_all_4d_rows']['max']:.12f}",
        f"- Selected cluster-count distribution: `{json.dumps(summary['selected_cluster_count_distribution'], sort_keys=True)}`.",
        f"- Redundancy rho min/mean/median/max: {summary['redundancy_rho']['min']:.12f} / {summary['redundancy_rho']['mean']:.12f} / {summary['redundancy_rho']['median']:.12f} / {summary['redundancy_rho']['max']:.12f}",
        "",
        "## Per-seed results",
        "",
        "| seed | runtime (s) | 4D front | projected front | projected HV | selected solution | clusters | selected f_semantic | rho | status |",
        "|---:|---:|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for row in summary["per_seed"]:
        lines.append(
            f"| {row['seed']} | {row['runtime_seconds']:.6f} | {row['front_4d_size']} | {row['projected_front_size']} | {row['projected_hv']:.12f} | `{row['selected_solution_id']}` | {row['selected_cluster_count']} | {row['selected_f_semantic']:.12f} | {row['redundancy_spearman_rho']:.12f} | PASS |"
        )
    lines.extend([
        "",
        "## Integrity scope",
        "",
        "Every 4D front, projected front, Hypervolume, representative selection,",
        "partition scope, objective recomputation, redundancy diagnostic, and",
        "per-artifact hash was independently checked from disk. No Wilcoxon test,",
        "Bonferroni correction, or cross-stage effectiveness conclusion was run.",
        "",
        "The launcher lock was removed only after OS process checks confirmed that",
        "no launcher or Xerces runner remained active.",
    ])
    SUMMARY_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_launch_record(aggregate_hash: str, summary: dict[str, Any], completed_at: str) -> None:
    launch = load_json(LAUNCH_PATH)
    launch.update({
        "status": "completed",
        "completion_timestamp_utc": completed_at,
        "completed_seeds": list(range(30)),
        "failed_seeds": [],
        "formal_run_aggregate_sha256": aggregate_hash,
        "validation_report_path": relative(SUMMARY_MD_PATH),
        "validation_json_path": relative(SUMMARY_JSON_PATH),
        "formal_run_metadata_path": relative(RUN_METADATA_PATH),
        "inventory_path": relative(INVENTORY_PATH),
        "launcher_process_active": False,
        "child_process_active": False,
        "lock_removed_after_process_check": True,
        "completion_evidence": "No matching launcher or Xerces runner process; seed_29 metadata and all saved artifacts independently validated.",
    })
    LAUNCH_PATH.write_text(json.dumps(launch, indent=2) + "\n", encoding="utf-8")
    LAUNCH_REPORT_PATH.write_text(
        "\n".join([
            "# Xerces formal launcher completion",
            "",
            "- Status: `completed`",
            f"- Completed at UTC: `{completed_at}`",
            "- Seeds: `0..29`",
            "- Failed seeds: none",
            f"- Aggregate formal-run SHA-256: `{aggregate_hash}`",
            f"- Validation report: `{relative(SUMMARY_MD_PATH)}`",
            "- Launcher and child process checks: no matching process remained.",
            "- Lock: removed after nonblocking lock acquisition confirmed it was not held.",
            "",
            "Seed 0 remains at its original validation source directory and was not",
            "copied into the formal output root.",
        ]) + "\n",
        encoding="utf-8",
    )


def matching_processes() -> list[str]:
    output = subprocess.check_output(["ps", "-axo", "pid=,command="], text=True)
    current_pid = str(__import__("os").getpid())
    matches = []
    for line in output.splitlines():
        if current_pid in line.split(maxsplit=1)[0:1]:
            continue
        if "launch_xerces_formal.py" in line or ("experiments/04_stage3_semantic/run.py" in line and "--subject xerces" in line):
            matches.append(line.strip())
    return matches


def remove_lock_after_process_check(lock_path: Path) -> None:
    if matching_processes():
        raise ValidationFailure("cannot remove launcher lock while a matching process is active")
    if not lock_path.exists():
        return
    import fcntl
    with lock_path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValidationFailure("launcher lock is still held") from exc
    lock_path.unlink()


def run_validation() -> dict[str, Any]:
    if matching_processes():
        raise ValidationFailure("launcher or Xerces runner is still active")
    seeds = expected_seeds()
    sources = resolve_seed_sources(seeds)
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    manifest = load_json(MANIFEST_PATH)
    context = stage3_runner.load_context("xerces")
    expected_config_sha = sha256_file(CONFIG_PATH)
    expected_graph_sha = manifest["semantic_graph_hashes"]["xerces"]["aggregate_sha256"]
    expected_raw_edge_hash = stage2._frame_sha256(context["raw_edges"])
    frozen_before = current_frozen_hashes(context)

    records = []
    failures = {}
    for seed in seeds:
        try:
            records.append(validate_seed(seed, sources[seed], context, expected_config_sha, expected_graph_sha, expected_raw_edge_hash))
        except Exception as exc:  # report every seed failure without partial aggregation
            failures[str(seed)] = str(exc)
    if failures:
        raise ValidationFailure(json.dumps({"seed_failures": failures}, indent=2))
    if len(records) != 30:
        raise ValidationFailure("not all 30 seeds produced validation records")

    commits = sorted({record["implementation_commit"] for record in records})
    fingerprints = {commit: algorithm_fingerprint(commit) for commit in commits}
    fingerprint_values = {value["sha256"] for value in fingerprints.values()}
    if len(fingerprint_values) != 1:
        raise ValidationFailure(f"algorithm fingerprints differ: {fingerprints}")
    current_fingerprint = algorithm_fingerprint(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())
    if current_fingerprint["sha256"] != next(iter(fingerprint_values)):
        raise ValidationFailure("current algorithm fingerprint differs from completed seeds")
    seed0_commit = load_json(sources[0] / "run_metadata.json")["implementation_commit"]
    seed0_compatibility = {
        "seed_0_source": relative(sources[0]),
        "seed_0_implementation_commit": seed0_commit,
        "seed_0_execution_head": load_json(sources[0] / "run_metadata.json")["execution_head"],
        "other_implementation_commits": commits,
        "launch_record_commit": "f47a2d34a3e63dd4a4f6320ed6186080e27c3f21",
        "current_head_before_final_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "algorithm_fingerprints_equal": True,
        "conclusion": "accepted; commit differences are reporting, validation, and launch-record changes only",
    }
    algorithm = {
        "sha256": next(iter(fingerprint_values)),
        "files": current_fingerprint["files"],
        "historical_by_implementation_commit": fingerprints,
    }
    seed_hashes = {record["seed"]: record["seed_artifact_aggregate_sha256"] for record in records}
    aggregate_hash = canonical_formal_hash(seed_hashes)
    write_inventory(records)
    summary = build_summary(records, aggregate_hash, algorithm, seed0_compatibility)
    write_summary(summary)
    completed_at = utc_now()
    RUN_METADATA_PATH.write_text(json.dumps({
        "schema_version": 1,
        "subject": "xerces",
        "seed_count": 30,
        "ordered_seed_list": seeds,
        "seed_0_source": relative(sources[0]),
        "seed_0_compatibility": seed0_compatibility,
        "algorithm_fingerprint": algorithm,
        "population_size": EXPECTED_POPULATION,
        "generations": EXPECTED_GENERATIONS,
        "objective_order": ["coupling", "negative_cohesion", "imbalance", "f_semantic"],
        "g_raw_provenance": {
            "loader": "experiments/02_stage2_nsga_structure_only/run.py:_raw_graph_inputs",
            "builder": "src/evo_ms/graph/raw_graph_builder.py",
            "class_nodes_path": "data/extracted/xerces-j/class_nodes.csv",
            "structural_dependencies_path": "data/extracted/xerces-j/structural_dependencies.csv",
            "raw_edge_hash": expected_raw_edge_hash,
        },
        "g_semantic_hash": expected_graph_sha,
        "config_sha256": expected_config_sha,
        "validation_script": relative(Path(__file__)),
        "completed_at_utc": completed_at,
        "per_seed_inventory_path": relative(INVENTORY_PATH),
        "aggregate_formal_run_sha256": aggregate_hash,
        "aggregate_canonicalization": "seed<TAB>seed_artifact_aggregate_sha256<LF>, numeric seed order; per-seed payload is sorted relative_artifact_path<TAB>artifact_sha256<LF>; run_metadata.json timestamps are removed before its aggregate artifact hash",
        "launcher_start_timestamp_utc": load_json(LAUNCH_PATH)["start_timestamp_utc"],
        "launcher_completion_evidence": "No matching launcher or Xerces runner process; all 30 saved seed artifacts independently validated.",
        "all_seeds_valid": True,
        "frozen_integrity_before_validation": frozen_before,
        "frozen_integrity_after_validation": current_frozen_hashes(context),
        "no_model_weights_loaded": True,
        "no_embeddings_regenerated": True,
        "no_semantic_graph_rebuilt": True,
        "no_ssa_used": True,
        "no_cross_stage_effectiveness_claim": True,
    }, indent=2) + "\n", encoding="utf-8")
    remove_lock_after_process_check(ROOT / "reports/stage3/xerces_formal_seed_launcher.lock")
    update_launch_record(aggregate_hash, summary, completed_at)
    return {
        "aggregate_hash": aggregate_hash,
        "records": records,
        "summary": summary,
        "algorithm": algorithm,
        "seed0_compatibility": seed0_compatibility,
    }


def main() -> int:
    try:
        result = run_validation()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "completed",
        "seed_count": len(result["records"]),
        "aggregate_formal_run_sha256": result["aggregate_hash"],
        "inventory": relative(INVENTORY_PATH),
        "summary": relative(SUMMARY_MD_PATH),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
