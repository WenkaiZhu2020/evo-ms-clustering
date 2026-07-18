#!/usr/bin/env python3
"""Run the isolated Stage 3B seed-0 optimizer validation.

The optimizer contract uses the frozen Stage 2 runner and the final Stage 3
Declaration + Method Body graph. Structural objectives, initialization,
operators, projection, Hypervolume, and selection remain unchanged.
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

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.optimization import encoding  # noqa: E402
from evo_ms.optimization.semantic_objective import (  # noqa: E402
    evaluate_semantic_objective,
    load_semantic_edges,
    semantic_total_weight,
)
from evo_ms.optimization.stage3_problem import (  # noqa: E402
    STAGE3_OBJECTIVE_ORDER,
    build_four_objective_problem,
)
from scripts.stage3 import final_build_semantic_graphs as build_semantic_graphs  # noqa: E402
from scripts.stage3.final_paths import (  # noqa: E402
    EXPERIMENT_ID,
    REPRESENTATION_ID,
    STAGE3_CONFIG,
    STAGE3_REPORT_ROOT,
    STAGE3_RESULT_PART,
    assert_stage3_write_path,
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = _load_module(
    "stage3_final_optimizer_runtime",
    ROOT / "experiments/05_stage3_declaration_method_body/run.py",
)
stage2 = runtime.stage2

SUBJECTS = ("jpetstore", "daytrader", "xerces")
STORAGE_SUBJECT = {"jpetstore": "jpetstore", "daytrader": "daytrader", "xerces": "xerces-j"}
EXPECTED_COUNTS = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
EXPECTED_GRAPH_HASHES = {
    "jpetstore": "2dcf34b9e931cfdb0eec205f7da5bd0f24f6956be98d838369e12573026a9214",
    "daytrader": "c7761509fe91acb398ee5bc3a0c71e3a368a34aae316b04c5907d34bced1714d",
    "xerces": "7d5d45f6e7cc46cdb57c57688bc89b5e90e0ecea7390833a7acb2e8887d935a5",
}
EXPECTED_INPUT_HASHES = {
    "jpetstore": "2d9007f75a14f4a4ed6152563241b898837b6c12b66a98a2464b4cc3f969a921",
    "daytrader": "da53d434b820e3c25bc69df63ced807cd0113d412fa36acc9694d1a97631d655",
    "xerces": "65488944220cc3a503994d6f2289e0f7bdc06c619351a2e8243bca243538c8a3",
}
EXPECTED_EMBEDDING_HASHES = {
    "jpetstore": "e7615e77d4f3258df46e499fd94c2dbb59bee03c0d2f6c3bb822c3aff4577139",
    "daytrader": "db7ef8d78036796c5c5c79cc95f54eb1b9b9974de5e6f035d1929391b415f66c",
    "xerces": "36bdeca0e1ef32f36631c30ebbf86a1875621490e92f9b4a7fd0860755676236",
}
EXPECTED_MAPPING_HASHES = {
    "jpetstore": "83c4643fdad9661f2e409563f8e496b792575ecc72ac548ba8c2f13fb46e019f",
    "daytrader": "6a995ce5caedd3fa567a09491378a629f7cdef61e41107cf25360bbd75d311d1",
    "xerces": "7e204d1865c1ddb228cc42f6f61519e280076590a92f0965e4f1fc765b77a4ab",
}
EXPECTED_GRAPH_CONFIG_HASH = "eddbb3674dacabfac2925f4ef6887bb86c9030f629a231230d6a889e1c28cc27"
EXPECTED_GRAPH_SOURCE_COMMIT = "6f595208e1bde1702b7a99f00410b35a225777c8"
EXPECTED_EMBEDDING_SOURCE_COMMIT = "33074fe5a2479b9d76605cd6a507c8a66c523a19"
GRAPH_ROOT = ROOT / "data/semantic_graphs/declaration_method_body"
STAGE2_CONFIG_PATH = ROOT / "configs/experiments/02_stage2_nsga_structure_only.yml"
BOUNDS_PATH = ROOT / "configs/experiments/stage2_robustness_bounds.yml"
REFERENCE_POINT = np.full(3, 1.1, dtype=float)
HV_TOLERANCE = 1e-12


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def output_dir(subject: str, root: Path = ROOT, seed: int = 0) -> Path:
    if subject not in SUBJECTS:
        raise ValueError(f"unknown subject: {subject}")
    if not 0 <= int(seed) <= 29:
        raise ValueError("Stage 3B formal seed must be in the range 0..29")
    run_layer = "validation" if int(seed) == 0 else "formal"
    path = root / "results" / subject / STAGE3_RESULT_PART / run_layer / f"seed_{int(seed):02d}"
    if root.resolve() == ROOT.resolve():
        assert_stage3_write_path(path, kind="optimizer result")
    elif path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("reproduction output must be outside the repository")
    return path


def validate_seed(seed: int, *, allow_formal: bool = False) -> None:
    seed = int(seed)
    if not 0 <= seed <= 29:
        raise ValueError("Stage 3B seed must be in the range 0..29")
    if allow_formal and seed == 0:
        raise ValueError("formal runner refuses to rerun authoritative validation seed 0")
    if not allow_formal and seed != 0:
        raise ValueError("this adapter is restricted to validation seed 0")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _graph_paths(subject: str) -> dict[str, Path]:
    directory = GRAPH_ROOT / subject
    return {
        "directory": directory,
        "edges": directory / "semantic_edges.csv",
        "metadata": directory / "graph_metadata.json",
        "mapping": directory / "class_mapping.csv",
        "directed": directory / "directed_topk_neighbours.csv",
    }


def _canonical_graph_hash_file(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    payload = "".join(
        f"{row['class_id_a']}\t{row['class_id_b']}\t{row['weight']}\n" for row in rows
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _mapping_hash(path: Path) -> str:
    return sha256_file(path)


def _load_stage3_config() -> dict[str, Any]:
    config = yaml.safe_load(STAGE3_CONFIG.read_text(encoding="utf-8"))
    if config.get("experiment_name") != EXPERIMENT_ID:
        raise ValueError("Stage 3B experiment identity mismatch")
    if config.get("representation_id") != REPRESENTATION_ID:
        raise ValueError("Stage 3B representation identity mismatch")
    roots = config.get("outputs", {}).get("result_roots", {})
    for subject in SUBJECTS:
        expected = f"results/{subject}/{STAGE3_RESULT_PART}"
        if roots.get(subject) != expected:
            raise ValueError(f"{subject}: Stage 3B result root mismatch")
    return config


def _load_stage3_graph(subject: str, class_nodes: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    paths = _graph_paths(subject)
    for key, path in paths.items():
        if key != "directory" and not path.is_file():
            raise FileNotFoundError(path)
    metadata = _read_json(paths["metadata"])
    if metadata.get("experiment_name") != EXPERIMENT_ID:
        raise ValueError(f"{subject}: graph experiment identity mismatch")
    if metadata.get("representation_id") != REPRESENTATION_ID:
        raise ValueError(f"{subject}: graph representation identity mismatch")
    if metadata.get("subject") != subject or metadata.get("node_count") != EXPECTED_COUNTS[subject]:
        raise ValueError(f"{subject}: graph subject/count provenance mismatch")
    if metadata.get("top_k") != 3 or metadata.get("similarity") != "true_cosine":
        raise ValueError(f"{subject}: graph top-k/similarity differs from frozen Stage 3A contract")
    if metadata.get("semantic_graph_sha256") != EXPECTED_GRAPH_HASHES[subject]:
        raise ValueError(f"{subject}: graph hash differs from frozen Stage 3B graph")
    actual_hash = _canonical_graph_hash_file(paths["edges"])
    if actual_hash != metadata.get("semantic_graph_sha256"):
        raise ValueError(f"{subject}: persisted graph hash mismatch")
    if metadata.get("graph_config_sha256") != EXPECTED_GRAPH_CONFIG_HASH:
        raise ValueError(f"{subject}: graph configuration hash mismatch")
    if metadata.get("source_commit") != EXPECTED_GRAPH_SOURCE_COMMIT:
        raise ValueError(f"{subject}: graph source commit mismatch")
    if metadata.get("input_aggregate_sha256") != EXPECTED_INPUT_HASHES[subject]:
        raise ValueError(f"{subject}: graph input aggregate mismatch")
    if metadata.get("embedding_aggregate_sha256") != EXPECTED_EMBEDDING_HASHES[subject]:
        raise ValueError(f"{subject}: graph embedding aggregate mismatch")
    if metadata.get("class_mapping_sha256") != EXPECTED_MAPPING_HASHES[subject]:
        raise ValueError(f"{subject}: graph class mapping hash mismatch")
    if metadata.get("class_mapping_file_sha256") != _mapping_hash(paths["mapping"]):
        raise ValueError(f"{subject}: graph class mapping file hash mismatch")
    expected_ids = class_nodes["class_id"].astype(str).tolist()
    mapping = pd.read_csv(paths["mapping"], dtype=str)
    if mapping["class_id"].astype(str).tolist() != expected_ids:
        raise ValueError(f"{subject}: graph mapping does not match raw class scope/order")
    if mapping["class_id"].duplicated().any():
        raise ValueError(f"{subject}: graph mapping has duplicate class IDs")
    edges = load_semantic_edges(paths["edges"], expected_class_ids=set(expected_ids))
    if float(edges["weight"].sum()) <= 0.0:
        raise ValueError(f"{subject}: semantic graph has no positive total weight")
    vectors, embedding_mapping, embedding_source = build_semantic_graphs.load_stage3_inputs(subject)
    if [row["class_id"] for row in embedding_mapping] != expected_ids:
        raise ValueError(f"{subject}: embedding mapping differs from raw class scope/order")
    for key, expected in {
        "input_aggregate_sha256": EXPECTED_INPUT_HASHES[subject],
        "embedding_aggregate_sha256": EXPECTED_EMBEDDING_HASHES[subject],
        "class_mapping_sha256": EXPECTED_MAPPING_HASHES[subject],
    }.items():
        if metadata.get(key) != expected or embedding_source.get(key) != expected:
            raise ValueError(f"{subject}: graph/embedding {key} provenance mismatch")
    enriched = dict(metadata)
    enriched["total_edge_weight"] = semantic_total_weight(edges)
    enriched["actual_embedding_dimension"] = int(vectors.shape[1])
    enriched["embedding_file_sha256"] = embedding_source["embedding_sha256"]
    return edges, enriched, {
        "paths": paths,
        "embedding_source": embedding_source,
        "mapping_file_sha256": _mapping_hash(paths["mapping"]),
        "graph_hash": actual_hash,
    }


def load_context(subject: str) -> dict[str, Any]:
    _load_stage3_config()
    if subject not in SUBJECTS:
        raise ValueError(f"unknown subject: {subject}")
    stage2_config = yaml.safe_load(STAGE2_CONFIG_PATH.read_text(encoding="utf-8"))
    stage2._reject_obsolete_config(stage2_config)
    storage_subject = STORAGE_SUBJECT[subject]
    subject_config = stage2._load_subject_config(ROOT, storage_subject)
    extracted_dir, extracted, raw_edges = stage2._raw_graph_inputs(ROOT, storage_subject, subject_config)
    class_nodes = extracted["class_nodes"]
    if len(class_nodes) != EXPECTED_COUNTS[subject]:
        raise ValueError(f"{subject}: raw class scope count mismatch")
    semantic_edges, semantic_metadata, provenance = _load_stage3_graph(subject, class_nodes)
    stage1 = stage2._frozen_raw_leiden_baseline(ROOT, storage_subject, class_nodes)
    bounds = runtime.load_stage2_bounds(subject)
    return {
        "subject": subject,
        "storage_subject": storage_subject,
        "stage2_config": stage2_config,
        "stage2_config_path": STAGE2_CONFIG_PATH,
        "config": yaml.safe_load(STAGE3_CONFIG.read_text(encoding="utf-8")),
        "config_path": STAGE3_CONFIG,
        "stage3_config": yaml.safe_load(STAGE3_CONFIG.read_text(encoding="utf-8")),
        "stage3_config_path": STAGE3_CONFIG,
        "subject_config": subject_config,
        "extracted_dir": extracted_dir,
        "class_nodes": class_nodes,
        "raw_edges": raw_edges,
        "stage1_raw_baseline": stage1,
        "semantic_edges": semantic_edges,
        "semantic_graph_metadata": semantic_metadata,
        "semantic_graph_hash": provenance["graph_hash"],
        "graph_provenance": provenance,
        "bounds": bounds,
        "population_size": int(stage2_config["nsga"]["population_size"]),
        "generations": int(stage2_config["nsga"]["generations"]),
        "initialization_config": stage2_config["initialization"],
        "max_cluster_ratio": stage2.resolve_max_cluster_ratio(stage2_config),
        "stage2_hv": runtime.stage2_hypervolume_lookup(subject),
    }


def structural_invariance_checks(context: dict[str, Any]) -> dict[str, Any]:
    class_nodes = context["class_nodes"]
    partitions = {
        "fixed_leiden": context["stage1_raw_baseline"]["cluster_id"].to_numpy(dtype=int),
        "all_one": np.zeros(len(class_nodes), dtype=int),
        "deterministic_two_cluster": np.asarray([index % 2 for index in range(len(class_nodes))], dtype=int),
    }
    rows: dict[str, Any] = {}
    for name, labels in partitions.items():
        labels = encoding.canonical_relabel(labels)
        mapping = encoding.to_cluster_by_class(labels, class_nodes)
        stage2_values = stage2.evaluate_structural_objectives(context["raw_edges"], mapping, "raw_weight")
        stage3_values = runtime.evaluate_four_objective_values(
            context["raw_edges"], context["semantic_edges"], mapping, "raw_weight",
            float(context["semantic_graph_metadata"]["total_edge_weight"]),
        )[:3]
        exact = np.array_equal(np.asarray(stage2_values), np.asarray(stage3_values))
        rows[name] = {
            "stage2_coupling": float(stage2_values[0]), "stage2_cohesion": float(stage2_values[1]),
            "stage2_imbalance": float(stage2_values[2]), "stage3_coupling": float(stage3_values[0]),
            "stage3_cohesion": float(stage3_values[1]), "stage3_imbalance": float(stage3_values[2]),
            "pass": bool(exact),
        }
    return {"checks": rows, "pass": all(value["pass"] for value in rows.values())}


def _identity(context: dict[str, Any], subject: str, seed: int) -> dict[str, Any]:
    source = context["graph_provenance"]["embedding_source"]
    return {
        "experiment_id": EXPERIMENT_ID, "experiment_name": EXPERIMENT_ID,
        "representation_id": REPRESENTATION_ID, "subject": subject, "seed": int(seed),
        "input_hash": context["semantic_graph_metadata"]["input_aggregate_sha256"],
        "input_aggregate_sha256": context["semantic_graph_metadata"]["input_aggregate_sha256"],
        "embedding_aggregate_sha256": source["embedding_aggregate_sha256"],
        "embedding_file_sha256": source["embedding_sha256"],
        "class_mapping_sha256": context["semantic_graph_metadata"]["class_mapping_sha256"],
        "graph_sha256": context["semantic_graph_hash"],
        "config_hash": sha256_file(STAGE3_CONFIG),
    }


def _add_identity(rows: list[dict[str, Any]], identity: dict[str, Any]) -> list[dict[str, Any]]:
    return [{**identity, **row} for row in rows]


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.20g", lineterminator="\n")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _artifact_hashes(output: Path, identity: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name == "artifact_hashes.csv":
            continue
        rows.append({**identity, "path": str(path.relative_to(output)), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return pd.DataFrame(rows)


def run_seed(
    subject: str,
    seed: int,
    destination: Path,
    run_type: str = "validation",
    *,
    allow_formal: bool = False,
) -> Path:
    validate_seed(seed, allow_formal=allow_formal)
    context = load_context(subject)
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"refusing to overwrite existing Stage 3B output: {destination}")
    if destination.resolve().is_relative_to(ROOT.resolve()):
        assert_stage3_write_path(destination, kind="optimizer result")
    destination.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    started = time.perf_counter()
    implementation_commit = git_head()
    identity = _identity(context, subject, seed)
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
    labels, f_values, constraints, front_diagnostics = runtime._front_arrays(result)
    pareto_rows, label_rows, posthoc_rows = runtime._solution_rows(context, seed, labels, f_values, constraints, seed_records)
    if not pareto_rows:
        raise ValueError(f"{subject}: seed {seed} produced an empty four-objective front")
    projected_rows, selected_list = runtime._project_front(pareto_rows, posthoc_rows)
    selected = selected_list[0]
    selected_original = next(row for row in pareto_rows if row["solution_id"] == selected["solution_id"])
    selected_posthoc = next(row for row in posthoc_rows if row["solution_id"] == selected["solution_id"])
    pareto_rows = _add_identity(pareto_rows, identity)
    projected_rows = _add_identity(projected_rows, identity)
    label_rows = _add_identity(label_rows, identity)
    posthoc_rows = _add_identity(posthoc_rows, identity)
    selected = {**identity, **selected}
    selected_original = {**identity, **selected_original}
    selected_posthoc = {**identity, **selected_posthoc}
    _write_csv(pd.DataFrame(pareto_rows), destination / "pareto_front_4d.csv")
    _write_csv(pd.DataFrame(projected_rows), destination / "projected_front_3d.csv")
    _write_csv(pd.DataFrame(label_rows), destination / "partition_labels.csv")
    _write_csv(pd.DataFrame(posthoc_rows), destination / "posthoc_metrics.csv")
    selected_partition = pd.DataFrame([
        {**identity, "class_id": row["class_id"], "class_name": row["class_name"], "cluster_id": row["cluster_id"]}
        for row in label_rows if row["solution_id"] == selected["solution_id"]
    ])
    selected_json = {
        **identity, "selected_solution_id": selected["solution_id"], "selected_projected_row": selected,
        "selected_four_objective_row": selected_original, "selected_posthoc_metrics": selected_posthoc,
        "selected_partition": selected_partition.to_dict("records"),
        "selection_input_schema": ["solution_id", "feasible", "coupling", "cohesion", "imbalance", "is_injected_seed", "label_vector"],
        "selection_implementation": "experiments/02_stage2_nsga_structure_only/run.py:_select_solution",
        "semantic_objective_used_for_selection": False,
    }
    _write_json(destination / "selected_solution.json", selected_json)
    projected_path = destination / "projected_front_3d.csv"
    matrix = pd.DataFrame(projected_rows)[["pymoo_f0_coupling", "pymoo_f1_negative_cohesion", "pymoo_f2_imbalance"]].to_numpy(dtype=float)
    normalized = runtime._normalize_projected(matrix, context["bounds"])
    stored_hv = stage2._hypervolume(normalized, REFERENCE_POINT)
    recomputed_hv, projected_nd = runtime._independent_projected_hv(projected_path, context["bounds"])
    _write_json(destination / "projected_hypervolume.json", {
        **identity, "implementation": "experiments/02_stage2_nsga_structure_only/run.py:_hypervolume",
        "bounds_source": relative(BOUNDS_PATH), "reference_point": [1.1, 1.1, 1.1],
        "stored_value": stored_hv, "recomputed_value": recomputed_hv,
        "absolute_difference": abs(stored_hv - recomputed_hv), "tolerance": HV_TOLERANCE,
        "projected_nondominated_count": projected_nd,
        "pass": bool(np.isclose(stored_hv, recomputed_hv, rtol=0.0, atol=HV_TOLERANCE)),
    })
    _write_json(destination / "objective_redundancy.json", {**identity, **runtime._redundancy(pareto_rows)})
    _write_csv(selected_partition, destination / "selected_partition.csv")
    validation = runtime.validate_run_output(destination, context)
    algorithm_evaluations = int(getattr(getattr(result, "algorithm", None), "evaluator", None).n_eval) if getattr(getattr(result, "algorithm", None), "evaluator", None) is not None else None
    elapsed = time.perf_counter() - started
    metadata = {
        **identity, "schema_version": 2, "storage_subject": context["storage_subject"], "run_type": run_type,
        "implementation_commit": implementation_commit, "execution_head": implementation_commit,
        "config_path": relative(STAGE3_CONFIG), "config_sha256": sha256_file(STAGE3_CONFIG),
        "stage2_config_path": relative(STAGE2_CONFIG_PATH), "stage2_config_sha256": sha256_file(STAGE2_CONFIG_PATH),
        "representation_id": REPRESENTATION_ID, "experiment_name": EXPERIMENT_ID,
        "semantic_graph_path": relative(context["graph_provenance"]["paths"]["edges"]),
        "semantic_graph_metadata_path": relative(context["graph_provenance"]["paths"]["metadata"]),
        "semantic_graph_config_sha256": context["semantic_graph_metadata"]["graph_config_sha256"],
        "g_sem_graph_hash": context["semantic_graph_hash"], "semantic_graph_hash": context["semantic_graph_hash"],
        "semantic_input_aggregate_sha256": context["semantic_graph_metadata"]["input_aggregate_sha256"],
        "embedding_aggregate_sha256": context["semantic_graph_metadata"]["embedding_aggregate_sha256"],
        "embedding_file_sha256": context["graph_provenance"]["embedding_source"]["embedding_sha256"],
        "class_mapping_sha256": context["semantic_graph_metadata"]["class_mapping_sha256"],
        "class_mapping_file_sha256": context["graph_provenance"]["mapping_file_sha256"],
        "embedding_source_commit": EXPECTED_EMBEDDING_SOURCE_COMMIT,
        "graph_source_commit": EXPECTED_GRAPH_SOURCE_COMMIT,
        "objective_order": STAGE3_OBJECTIVE_ORDER,
        "report_objective_order": ["coupling", "cohesion", "imbalance", "f_semantic"],
        "population_size": context["population_size"], "generations": context["generations"],
        "evaluations": algorithm_evaluations, "initialization_contract": "experiments/02_stage2_nsga_structure_only/run.py:_seed_initialization_records",
        "projected_front_rule": "final 4D front -> exact 3D nondominance -> exact projected objective tuple deduplication; stable solution_id survivor",
        "projected_hv_implementation": "experiments/02_stage2_nsga_structure_only/run.py:_hypervolume",
        "projected_hv_bounds_source": relative(BOUNDS_PATH), "projected_hv_reference_point": [1.1, 1.1, 1.1],
        "representative_selection_implementation": "experiments/02_stage2_nsga_structure_only/run.py:_select_solution",
        "semantic_objective_used_for_selection": False, "start_timestamp_utc": started_at, "end_timestamp_utc": utc_now(),
        "runtime_seconds": elapsed, "completion_status": "completed", "validation": validation,
        "front_diagnostics": front_diagnostics, "stage2_same_seed_hypervolume": context["stage2_hv"],
        "structural_objective_invariance": structural_invariance_checks(context),
        "no_model_inference": True, "no_graph_fusion": True, "no_semantic_graph_generation": True,
        "semantic_input_source": "frozen Stage 3B semantic_edges.csv only",
    }
    _write_json(destination / "run_metadata.json", metadata)
    _write_json(destination / "run_metrics.json", {
        **identity, "front_size": len(pareto_rows), "projected_front_size": len(projected_rows),
        "selected_solution_id": selected["solution_id"], "projected_hypervolume": stored_hv,
        "runtime_seconds": elapsed, "evaluations": algorithm_evaluations, "validation_pass": True,
    })
    (destination / "run.log").write_text(
        f"start subject={subject} seed={seed} run_type={run_type}\n"
        f"implementation_commit={implementation_commit}\n"
        f"completed runtime_seconds={elapsed:.6f} front_size={len(pareto_rows)} projected_front_size={len(projected_rows)}\n",
        encoding="utf-8",
    )
    _write_csv(_artifact_hashes(destination, identity), destination / "artifact_hashes.csv")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True, choices=SUBJECTS)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--run-type", default="validation", choices=["validation", "formal"])
    args = parser.parse_args()
    path = run_seed(
        args.subject,
        args.seed,
        args.output_dir,
        run_type=args.run_type,
        allow_formal=args.run_type == "formal",
    )
    print(f"Stage 3B {args.run_type} output: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
