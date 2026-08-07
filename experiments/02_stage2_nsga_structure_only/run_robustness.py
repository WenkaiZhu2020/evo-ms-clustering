"""Run Stage 2 raw-only NSGA-II robustness experiments.

This runner keeps one random seed equal to one independent NSGA-II run. It
reuses the formal Stage 2 problem, operators, objectives, repair, and
selected-solution rule from ``run.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import lzma
import platform
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.optimization import encoding
from evo_ms.optimization.objectives import evaluate_structural_objectives
from evo_ms.utils.config_loader import load_yaml


def _load_stage2_runner():
    spec = importlib.util.spec_from_file_location(
        "stage2_structure_only_run",
        SCRIPT_DIR / "run.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError("Could not load Stage 2 runner module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stage2 = _load_stage2_runner()


SUBJECTS = ("jpetstore", "daytrader", "xerces-j", "easymock", "jfreechart")
OBJECTIVE_ORDER = ["coupling", "negative_cohesion", "imbalance"]
FORMAL_SEEDS = list(range(30))
CALIBRATION_SEEDS = list(range(1000, 1010))
DEFAULT_BOUNDS_CONFIG = ROOT / "configs" / "experiments" / "stage2_robustness_bounds.yml"
REFERENCE_POINT = np.full(3, 1.1, dtype=float)
FIXED_EPSILON = 1e-6
BOUND_TOLERANCE = 1e-12
RUN_TYPES = ("smoke", "formal")
SOURCE_FINGERPRINT_PATHS = [
    ROOT / "experiments" / "02_stage2_nsga_structure_only" / "run.py",
    ROOT / "experiments" / "02_stage2_nsga_structure_only" / "run_robustness.py",
    ROOT / "src" / "evo_ms" / "extraction" / "dependency_extractor.py",
    ROOT / "src" / "evo_ms" / "optimization" / "problem.py",
    ROOT / "src" / "evo_ms" / "optimization" / "objectives.py",
    ROOT / "src" / "evo_ms" / "optimization" / "encoding.py",
]


class CalibrationBoundViolation(ValueError):
    """Raised when a formal seed falls outside frozen calibration bounds."""

    def __init__(
        self,
        subject: str,
        seed: int,
        objective: str,
        value: float,
        lower: float,
        upper: float,
    ) -> None:
        self.subject = subject
        self.seed = int(seed)
        self.objective = objective
        self.value = float(value)
        self.lower = float(lower)
        self.upper = float(upper)
        if value < lower:
            self.exceeded_amount = float(lower - value)
        else:
            self.exceeded_amount = float(value - upper)
        super().__init__(
            "calibration-bound violation: "
            f"subject={subject} seed={seed} objective={objective} "
            f"observed={value} lower={lower} upper={upper} "
            f"exceeded_amount={self.exceeded_amount}"
        )


def generate_theoretical_bounds(
    subject: str,
    bounds_config: Path,
    config_path: Path,
) -> Path:
    context = _load_context(subject, config_path)
    raw_edges = context["raw_edges"]
    _validate_nonnegative_raw_weights(raw_edges)
    max_raw_edge_weight = _max_raw_edge_weight(raw_edges)
    class_count = int(len(context["class_nodes"]))
    imbalance_bound = theoretical_imbalance_upper_bound(
        class_count,
        context["max_cluster_ratio"],
    )
    git_state = stage2._git_state(ROOT)
    config_sha = _file_sha256(config_path)
    graph_hashes = _input_graph_hashes(context)
    source_fingerprint = _source_fingerprint()
    working_tree_diff_sha = _working_tree_diff_sha256()

    lower = [0.0, -max_raw_edge_weight, 0.0]
    upper = [1.0, 0.0, imbalance_bound]
    bounds_config.parent.mkdir(parents=True, exist_ok=True)
    data = _normalize_bounds_document(_read_yaml_if_exists(bounds_config))
    data["schema_version"] = 3
    data["bounds_source"] = "theoretical"
    data["calibration_status"] = "not_required"
    data["objective_order"] = OBJECTIVE_ORDER
    data["reference_point"] = _float_list(REFERENCE_POINT)
    data["generated_from_commit"] = git_state["git_head"]
    data["algorithm_config_sha256"] = config_sha
    data["working_tree_dirty"] = git_state["git_dirty"]
    data["working_tree_fingerprint"] = source_fingerprint
    data["working_tree_diff_sha256"] = working_tree_diff_sha
    data["subjects"][subject] = {
        "bounds_source": "theoretical",
        "calibration_status": "not_required",
        "generated_from_commit": git_state["git_head"],
        "working_tree_dirty": git_state["git_dirty"],
        "working_tree_fingerprint": source_fingerprint,
        "working_tree_diff_sha256": working_tree_diff_sha,
        "algorithm_config_sha256": config_sha,
        "graph_input_sha256": graph_hashes["raw_edges"],
        "input_graph_hashes": graph_hashes,
        "class_count": class_count,
        "max_raw_edge_weight": max_raw_edge_weight,
        "cohesion_bound_derivation": (
            "For non-negative aggregated G_raw edge weights, each cluster weighted "
            "density 2*internal_weight/(size*(size-1)) is bounded above by the "
            "maximum aggregated raw edge weight."
        ),
        "imbalance_upper_bound": imbalance_bound,
        "imbalance_bound_method": "exact_extreme_allocation_over_cluster_count",
        "imbalance_bound_tightness": "exact_for_current_size_constraints",
        "bounds_derivation": {
            "coupling": "external_weight/total_weight with non-negative weights gives [0,1]",
            "negative_cohesion": "cohesion in [0,max_raw_edge_weight], so negative cohesion in [-max_raw_edge_weight,0]",
            "imbalance": "max std(cluster_sizes)/mean(cluster_sizes) over feasible integer cluster sizes",
        },
        "objective_order": OBJECTIVE_ORDER,
        "reference_point": _float_list(REFERENCE_POINT),
        "lower_bounds": _float_list(np.asarray(lower, dtype=float)),
        "upper_bounds": _float_list(np.asarray(upper, dtype=float)),
        "bound_tolerance": BOUND_TOLERANCE,
        "space": "pymoo_minimization_objectives",
        "input_graph": "G_raw",
        "stage1_baseline_profile": stage2.RAW_BASELINE_PROFILE,
        "config_path": _relative(config_path),
        "config_sha256": config_sha,
        "generated_at_utc": stage2._utc_now(),
    }
    _write_yaml(bounds_config, data)
    return bounds_config


def run_calibration(
    subject: str,
    calibration_seeds: list[int],
    bounds_config: Path,
    config_path: Path,
) -> Path:
    context = _load_context(subject, config_path)
    objective_rows: list[np.ndarray] = []
    for seed in calibration_seeds:
        seed_result = stage2._run_seed(
            class_nodes=context["class_nodes"],
            raw_edges=context["raw_edges"],
            raw_leiden_clusters=context["stage1_raw_baseline"],
            initialization_config=context["initialization_config"],
            seed=seed,
            population_size=context["population_size"],
            generations=context["generations"],
            max_cluster_ratio=context["max_cluster_ratio"],
        )
        objective_rows.extend(
            np.asarray(solution["F"], dtype=float)
            for solution in seed_result["solutions"]
            if bool(solution["feasible"])
        )
    if not objective_rows:
        raise ValueError("calibration produced no feasible solutions")

    matrix = np.vstack(objective_rows)
    observed_min = np.min(matrix, axis=0)
    observed_max = np.max(matrix, axis=0)
    observed_range = observed_max - observed_min
    margin = np.maximum(0.1 * observed_range, FIXED_EPSILON)
    lower = observed_min - margin
    upper = observed_max + margin
    git_state = stage2._git_state(ROOT)
    config_sha = _file_sha256(config_path)
    status = "formal" if calibration_seeds == CALIBRATION_SEEDS else "smoke"

    bounds_config.parent.mkdir(parents=True, exist_ok=True)
    data = _normalize_bounds_document(_read_yaml_if_exists(bounds_config))
    data["schema_version"] = 2
    data["objective_order"] = OBJECTIVE_ORDER
    data["reference_point"] = _float_list(REFERENCE_POINT)
    data["generated_from_commit"] = git_state["git_head"]
    data["algorithm_config_sha256"] = config_sha
    data["subjects"][subject] = {
        "calibration_status": status,
        "generated_from_commit": git_state["git_head"],
        "working_tree_dirty": git_state["git_dirty"],
        "algorithm_config_sha256": config_sha,
        "calibration_seed_count": int(len(calibration_seeds)),
        "objective_order": OBJECTIVE_ORDER,
        "reference_point": _float_list(REFERENCE_POINT),
        "lower_bounds": _float_list(lower),
        "upper_bounds": _float_list(upper),
        "calibration_seeds": [int(seed) for seed in calibration_seeds],
        "calibration_solution_count": int(len(objective_rows)),
        "margin_rule": "lower=observed_min-max(0.1*observed_range,1e-6); upper=observed_max+max(0.1*observed_range,1e-6)",
        "space": "pymoo_minimization_objectives",
        "input_graph": "G_raw",
        "stage1_baseline_profile": stage2.RAW_BASELINE_PROFILE,
        "config_path": _relative(config_path),
        "config_sha256": config_sha,
        "generated_at_utc": stage2._utc_now(),
        "note": "Smoke bounds are for pipeline checks only. Formal robustness requires calibration_status=formal.",
    }
    _write_yaml(bounds_config, data)
    return bounds_config


def run_robustness(
    subject: str,
    seeds: list[int],
    output_dir: Path | None,
    bounds_config: Path,
    config_path: Path,
    run_type: str,
    allow_smoke_bounds: bool,
    resume: bool = False,
    max_cluster_ratio: float | None = None,
) -> Path:
    context = _load_context(subject, config_path, max_cluster_ratio=max_cluster_ratio)
    bounds = _load_subject_bounds(
        bounds_config,
        subject,
        config_path=config_path,
        run_type=run_type,
        allow_smoke_bounds=allow_smoke_bounds,
    )
    context["run_type"] = run_type
    context["calibration_status"] = bounds["calibration_status"]
    context["bounds_source"] = bounds.get("bounds_source", "")
    context["bounds_derivation"] = bounds.get("bounds_derivation", {})
    context["class_count"] = bounds.get("class_count", len(context["class_nodes"]))
    context["max_raw_edge_weight"] = bounds.get("max_raw_edge_weight")
    context["imbalance_upper_bound"] = bounds.get("imbalance_upper_bound")
    context["imbalance_bound_method"] = bounds.get("imbalance_bound_method")
    _validate_bounds_against_context(bounds, context, run_type)
    default_group = "robustness_smoke" if run_type == "smoke" else "robustness"
    root_output = output_dir or ROOT / "results" / subject / stage2.OUTPUT_LAYER / default_group
    root_output.mkdir(parents=True, exist_ok=True)

    manifest = _base_manifest(context, bounds, seeds, bounds_config, config_path, run_type)
    manifest["start_timestamp_utc"] = stage2._utc_now()
    rows = []
    for seed in seeds:
        seed_dir = root_output / f"seed_{seed:02d}"
        if resume and _seed_output_is_valid(seed_dir, seed, manifest):
            rows.append(_read_json(seed_dir / "run_metrics.json"))
            continue
        rows.append(_run_one_seed(seed, seed_dir, context, bounds, manifest))

    manifest["end_timestamp_utc"] = stage2._utc_now()
    _write_json(root_output / "robustness_manifest.json", manifest)
    pd.DataFrame(rows).sort_values("seed").to_csv(root_output / "raw_runs.csv", index=False)
    return root_output


def verify_seed(
    subject: str,
    seed: int,
    bounds_config: Path,
    config_path: Path,
    allow_smoke_bounds: bool,
) -> list[str]:
    context = _load_context(subject, config_path)
    bounds = _load_subject_bounds(
        bounds_config,
        subject,
        config_path=config_path,
        run_type="smoke" if allow_smoke_bounds else "formal",
        allow_smoke_bounds=allow_smoke_bounds,
    )
    context["bounds_source"] = bounds.get("bounds_source", "")
    context["bounds_derivation"] = bounds.get("bounds_derivation", {})
    context["class_count"] = bounds.get("class_count", len(context["class_nodes"]))
    context["max_raw_edge_weight"] = bounds.get("max_raw_edge_weight")
    context["imbalance_upper_bound"] = bounds.get("imbalance_upper_bound")
    context["imbalance_bound_method"] = bounds.get("imbalance_bound_method")
    _validate_bounds_against_context(bounds, context, "smoke" if allow_smoke_bounds else "formal")
    first = _run_seed_in_memory(seed, context, bounds)
    second = _run_seed_in_memory(seed, context, bounds)
    mismatches = []
    for key in [
        "front_objective_vectors",
        "normalized_objective_vectors",
        "front_solution_count",
        "selected_objectives",
        "selected_partition_key",
        "leiden_diagnostics",
    ]:
        if key in {"front_objective_vectors", "normalized_objective_vectors", "selected_objectives"}:
            if not np.allclose(first[key], second[key], rtol=1e-12, atol=1e-12):
                mismatches.append(key)
        elif first[key] != second[key]:
            mismatches.append(key)
    if not np.isclose(first["hypervolume"], second["hypervolume"], rtol=1e-12, atol=1e-12):
        mismatches.append("hypervolume")
    return mismatches


def verify_seed_subprocess(
    subject: str,
    seed: int,
    bounds_config: Path,
    config_path: Path,
    allow_smoke_bounds: bool,
) -> list[str]:
    with tempfile.TemporaryDirectory(prefix="stage2-verify-") as tmp:
        left = Path(tmp) / "left"
        right = Path(tmp) / "right"
        for output in [left, right]:
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--subject",
                subject,
                "--seeds",
                str(seed),
                "--output-dir",
                str(output),
                "--bounds-config",
                str(bounds_config),
                "--config",
                str(config_path),
            ]
            if allow_smoke_bounds:
                command.append("--allow-smoke-bounds")
            completed = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                return [f"subprocess_failed:{completed.stderr.strip()}"]
        bounds = _load_subject_bounds(
            bounds_config,
            subject,
            config_path=config_path,
            run_type="smoke" if allow_smoke_bounds else "formal",
            allow_smoke_bounds=allow_smoke_bounds,
        )
        left_snapshot = _snapshot_run_output(left / f"seed_{seed:02d}", bounds)
        right_snapshot = _snapshot_run_output(right / f"seed_{seed:02d}", bounds)
        return compare_run_snapshots(left_snapshot, right_snapshot)


def _run_one_seed(
    seed: int,
    seed_dir: Path,
    context: dict[str, Any],
    bounds: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        result = _run_seed_in_memory(seed, context, bounds)
    except CalibrationBoundViolation as exc:
        seed_dir.mkdir(parents=True, exist_ok=True)
        violation_metrics = _violation_metrics(exc, context)
        _write_json(seed_dir / "run_metrics.json", violation_metrics)
        _write_json(
            seed_dir / "run_metadata.json",
            _seed_metadata(seed, manifest, "recomputed_nondominated_front"),
        )
        raise
    runtime_sec = time.perf_counter() - start
    seed_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(_pareto_rows_with_diagnostics(result)).to_csv(
        seed_dir / "pareto_front.csv",
        index=False,
    )
    pd.DataFrame(result["label_rows"]).to_csv(
        seed_dir / "pareto_labels.csv.xz",
        index=False,
        compression={"method": "xz", "preset": 9 | lzma.PRESET_EXTREME},
    )

    metrics = _run_metrics_row(
        context=context,
        seed=seed,
        selected=result["selected_solution"],
        selected_metrics=result["selected_posthoc_metrics"],
        diagnostics=result["diagnostics"],
        hypervolume=result["hypervolume"],
        n_solutions=result["front_solution_count"],
        front_diagnostics=result["front_diagnostics"],
        runtime_sec=runtime_sec,
    )
    _write_json(seed_dir / "run_metrics.json", metrics)
    _write_json(seed_dir / "run_metadata.json", _seed_metadata(seed, manifest, metrics["front_source"]))
    return metrics


def _pareto_rows_with_diagnostics(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach post-hoc partition diagnostics to every persisted Pareto row."""
    diagnostics_by_solution = {
        str(row["solution_id"]): row
        for row in result["posthoc_rows"]
    }
    fields = [
        "weighted_modularity",
        "cluster_count",
        "max_cluster_ratio",
        "singleton_ratio",
        "cluster_size_cv",
    ]
    return [
        {
            **row,
            **{
                field: diagnostics_by_solution[str(row["solution_id"])][field]
                for field in fields
            },
        }
        for row in result["pareto_rows"]
    ]


def _run_seed_in_memory(
    seed: int,
    context: dict[str, Any],
    bounds: dict[str, Any],
) -> dict[str, Any]:
    seed_result = stage2._run_seed(
        class_nodes=context["class_nodes"],
        raw_edges=context["raw_edges"],
        raw_leiden_clusters=context["stage1_raw_baseline"],
        initialization_config=context["initialization_config"],
        seed=seed,
        population_size=context["population_size"],
        generations=context["generations"],
        max_cluster_ratio=context["max_cluster_ratio"],
    )
    front_diagnostics = dict(seed_result.get("front_diagnostics", {}))
    pareto_rows, label_rows, posthoc_rows, _, _ = stage2._materialize_results(
        subject=context["subject"],
        class_nodes=context["class_nodes"],
        raw_edges=context["raw_edges"],
        seed_results=[seed_result],
        stage1_raw_baseline=context["stage1_raw_baseline"],
        reference_mapping=context["reference_mapping"],
        hv_reference=np.asarray([1.1, 0.1, 1.1], dtype=float),
    )
    selected = stage2._select_solution(posthoc_rows, pareto_rows)
    selected_partition = stage2._clusters_for_solution(label_rows, selected["solution_id"])
    selected_posthoc = _row_by_solution_id(posthoc_rows, selected["solution_id"])
    objective_matrix = np.asarray(
        [
            [row["coupling"], row["pymoo_f1_negative_cohesion"], row["imbalance"]]
            for row in pareto_rows
        ],
        dtype=float,
    )
    normalized = _normalize_checked(
        objective_matrix,
        bounds,
        subject=context["subject"],
        seed=seed,
    )
    hypervolume = stage2._hypervolume(normalized, REFERENCE_POINT)
    leiden_f = _raw_leiden_objective_vector(context)
    normalized_leiden = _normalize_checked(
        np.atleast_2d(leiden_f),
        bounds,
        subject=context["subject"],
        seed=seed,
    )
    hv_leiden_only = stage2._hypervolume(normalized_leiden, REFERENCE_POINT)
    diagnostics = _leiden_diagnostics(
        context=context,
        pareto_rows=pareto_rows,
        selected=selected,
        objective_matrix=objective_matrix,
        hypervolume=hypervolume,
        hv_leiden_only=hv_leiden_only,
        leiden_f=leiden_f,
    )
    return {
        "pareto_rows": pareto_rows,
        "label_rows": label_rows,
        "posthoc_rows": posthoc_rows,
        "selected_solution": selected,
        "selected_partition": selected_partition,
        "selected_posthoc_metrics": selected_posthoc,
        "diagnostics": diagnostics,
        "hypervolume": hypervolume,
        "front_objective_vectors": _sorted_vector_rows(objective_matrix),
        "normalized_objective_vectors": _sorted_vector_rows(normalized),
        "front_solution_count": len(pareto_rows),
        "front_diagnostics": front_diagnostics,
        "selected_objectives": np.asarray(
            [selected["coupling"], selected["pymoo_f1_negative_cohesion"], selected["imbalance"]],
            dtype=float,
        ),
        "selected_partition_key": _partition_key_from_label_vector(selected["label_vector"]),
        "leiden_diagnostics": {
            key: diagnostics[key]
            for key in [
                "selected_equals_leiden",
                "exact_leiden_present_in_front",
                "n_non_leiden_partitions",
                "n_injected_seed_solutions",
                "n_non_injected_solutions",
                "leiden_dominated_by_front",
                "n_solutions_dominating_leiden",
            ]
        },
    }


def _leiden_diagnostics(
    context: dict[str, Any],
    pareto_rows: list[dict[str, Any]],
    selected: dict[str, Any],
    objective_matrix: np.ndarray,
    hypervolume: float,
    hv_leiden_only: float,
    leiden_f: np.ndarray,
) -> dict[str, Any]:
    leiden_key = _raw_leiden_key(context)
    front_keys = [
        _partition_key_from_label_vector(row["label_vector"])
        for row in pareto_rows
    ]
    exact_present = any(key == leiden_key for key in front_keys)
    dominating = int(sum(_dominates(row_f, leiden_f) for row_f in objective_matrix))
    return {
        "selected_equals_leiden": _partition_key_from_label_vector(selected["label_vector"]) == leiden_key,
        "exact_leiden_present_in_front": bool(exact_present),
        "n_non_leiden_partitions": int(sum(key != leiden_key for key in front_keys)),
        "n_injected_seed_solutions": int(sum(bool(row["is_injected_seed"]) for row in pareto_rows)),
        "n_non_injected_solutions": int(sum(not bool(row["is_injected_seed"]) for row in pareto_rows)),
        "leiden_dominated_by_front": bool(dominating > 0),
        "n_solutions_dominating_leiden": dominating,
        "hv_leiden_only": float(hv_leiden_only),
        "hv_gain_over_leiden": float(hypervolume - hv_leiden_only),
    }


def _run_metrics_row(
    context: dict[str, Any],
    seed: int,
    selected: dict[str, Any],
    selected_metrics: dict[str, Any],
    diagnostics: dict[str, Any],
    hypervolume: float,
    n_solutions: int,
    front_diagnostics: dict[str, Any],
    runtime_sec: float,
) -> dict[str, Any]:
    row = {
        "subject": context["subject"],
        "seed": int(seed),
        "run_type": context["run_type"],
        "calibration_status": context["calibration_status"],
        "bounds_source": context.get("bounds_source", ""),
        "class_count": context.get("class_count"),
        "max_raw_edge_weight": context.get("max_raw_edge_weight"),
        "imbalance_upper_bound": context.get("imbalance_upper_bound"),
        "imbalance_bound_method": context.get("imbalance_bound_method"),
        "calibration_bound_violation": False,
        "hypervolume": float(hypervolume),
        "hv_leiden_only": diagnostics["hv_leiden_only"],
        "hv_gain_over_leiden": diagnostics["hv_gain_over_leiden"],
        "n_solutions": int(n_solutions),
        "n_non_leiden_partitions": diagnostics["n_non_leiden_partitions"],
        "n_injected_seed_solutions": diagnostics["n_injected_seed_solutions"],
        "n_non_injected_solutions": diagnostics["n_non_injected_solutions"],
        "exact_leiden_present_in_front": diagnostics["exact_leiden_present_in_front"],
        "leiden_dominated_by_front": diagnostics["leiden_dominated_by_front"],
        "n_solutions_dominating_leiden": diagnostics["n_solutions_dominating_leiden"],
        "runtime_sec": float(runtime_sec),
        **_front_metric_fields(front_diagnostics),
        "solution_id": selected["solution_id"],
        "coupling": float(selected["coupling"]),
        "cohesion": float(selected["cohesion"]),
        "imbalance": float(selected["imbalance"]),
        "weighted_modularity": float(selected_metrics["weighted_modularity"]),
        "internal_edge_weight_ratio": float(selected_metrics["internal_edge_weight_ratio"]),
        "internal_external_edge_ratio": float(selected_metrics["internal_external_edge_ratio"]),
        "cluster_count": int(selected_metrics["cluster_count"]),
        "average_cluster_size": float(selected_metrics["average_cluster_size"]),
        "maximum_cluster_size": int(selected_metrics["max_cluster_size"]),
        "minimum_cluster_size": int(selected_metrics["min_cluster_size"]),
        "max_cluster_ratio": float(selected_metrics["max_cluster_ratio"]),
        "singleton_ratio": float(selected_metrics["singleton_ratio"]),
        "selected_equals_leiden": diagnostics["selected_equals_leiden"],
        "selected_is_injected_seed": bool(selected["is_injected_seed"]),
        "selected_seed_name": str(selected["injected_seed_name"]),
    }
    for key in [
        "mojofm_vs_reference",
        "pairwise_precision",
        "pairwise_recall",
        "pairwise_f1",
        "ari_vs_reference",
        "nmi_vs_reference",
        "reference_coverage_ratio",
    ]:
        row[key] = _optional_float(selected_metrics.get(key))
    return row


def _load_context(
    subject: str,
    config_path: Path,
    max_cluster_ratio: float | None = None,
) -> dict[str, Any]:
    if subject not in SUBJECTS:
        raise ValueError(f"subject must be one of: {', '.join(SUBJECTS)}")
    config = load_yaml(config_path)
    stage2._reject_obsolete_config(config)
    nsga_config = config.get("nsga", {})
    subject_config = stage2._load_subject_config(ROOT, subject)
    extracted_dir, extracted, raw_edges = stage2._raw_graph_inputs(ROOT, subject, subject_config)
    class_nodes = extracted["class_nodes"]
    return {
        "subject": subject,
        "config": config,
        "subject_config": subject_config,
        "config_path": config_path,
        "population_size": int(nsga_config.get("population_size", 100)),
        "generations": int(nsga_config.get("generations", 100)),
        "max_cluster_ratio": stage2.resolve_max_cluster_ratio(config, max_cluster_ratio),
        "initialization_config": config.get("initialization", {}),
        "extracted_dir": extracted_dir,
        "class_nodes": class_nodes,
        "raw_edges": raw_edges,
        "stage1_raw_baseline": stage2._frozen_raw_leiden_baseline(ROOT, subject, class_nodes),
        "reference_mapping": stage2._reference_mapping(ROOT, subject_config, subject),
        "run_type": "",
        "calibration_status": "",
    }


def _input_graph_hashes(context: dict[str, Any]) -> dict[str, str]:
    return {
        "class_nodes.csv": stage2._sha256(context["extracted_dir"] / "class_nodes.csv"),
        "structural_dependencies.csv": stage2._sha256(
            context["extracted_dir"] / "structural_dependencies.csv"
        ),
        "raw_edges": stage2._frame_sha256(context["raw_edges"]),
    }


def _validate_nonnegative_raw_weights(raw_edges: pd.DataFrame) -> None:
    weights = raw_edges["raw_weight"].to_numpy(dtype=float)
    if np.any(~np.isfinite(weights)):
        raise ValueError("G_raw contains non-finite raw_weight values")
    if np.any(weights < 0.0):
        raise ValueError("theoretical bounds require non-negative G_raw raw_weight values")


def _max_raw_edge_weight(raw_edges: pd.DataFrame) -> float:
    if raw_edges.empty:
        return 0.0
    return float(np.max(raw_edges["raw_weight"].to_numpy(dtype=float)))


def theoretical_imbalance_upper_bound(
    class_count: int,
    max_cluster_ratio: float = stage2.DEFAULT_MAX_CLUSTER_RATIO,
) -> float:
    """Exact max of np.std(cluster_sizes)/mean under current size constraints.

    The objective uses population standard deviation. For fixed n and k,
    maximizing variance is equivalent to maximizing the sum of squared cluster
    sizes. Because x^2 is convex, the maximum under the active lower and upper
    integer bounds is reached by concentrating remaining classes into as few
    clusters as possible. Singleton count is unconstrained in final Stage 2.
    """
    n = int(class_count)
    if n <= 0:
        return 0.0
    max_cluster_size = int(np.floor(n * max_cluster_ratio))
    if max_cluster_size < 1:
        return 0.0
    best = 0.0
    for cluster_count in range(2, n + 1):
        if cluster_count * 1 > n or cluster_count * max_cluster_size < n:
            continue
        sizes = _extreme_cluster_sizes(
            class_count=n,
            cluster_count=cluster_count,
            max_cluster_size=max_cluster_size,
        )
        values = np.asarray(sizes, dtype=float)
        imbalance = float(np.std(values) / np.mean(values))
        best = max(best, imbalance)
    return float(best)


def _extreme_cluster_sizes(
    class_count: int,
    cluster_count: int,
    max_cluster_size: int,
) -> list[int]:
    """Most imbalanced legal sizes for fixed n, k, and max cluster size."""
    sizes = [1] * cluster_count
    surplus = class_count - cluster_count
    index = 0
    while surplus > 0 and index < len(sizes):
        add = min(surplus, max_cluster_size - sizes[index])
        sizes[index] += add
        surplus -= add
        index += 1
    if surplus != 0:
        raise ValueError("cluster count cannot satisfy max-cluster bound")
    return sizes


def _validate_theoretical_bounds_schema(bounds: dict[str, Any]) -> None:
    lower = np.asarray(bounds["lower_bounds"], dtype=float)
    upper = np.asarray(bounds["upper_bounds"], dtype=float)
    max_raw_edge_weight = float(bounds["max_raw_edge_weight"])
    if not np.allclose(lower, [0.0, -max_raw_edge_weight, 0.0], rtol=0.0, atol=1e-15):
        raise ValueError("theoretical lower bounds do not match objective derivation")
    if not np.isclose(upper[0], 1.0, rtol=0.0, atol=1e-15):
        raise ValueError("theoretical coupling upper bound must be 1.0")
    if not np.isclose(upper[1], 0.0, rtol=0.0, atol=1e-15):
        raise ValueError("theoretical negative cohesion upper bound must be 0.0")
    if not (np.isfinite(upper[2]) and upper[2] > 0.0):
        raise ValueError("theoretical imbalance upper bound must be positive")


def _validate_bounds_against_context(
    bounds: dict[str, Any],
    context: dict[str, Any],
    run_type: str,
) -> None:
    if run_type != "formal" or bounds.get("bounds_source") != "theoretical":
        return
    _validate_nonnegative_raw_weights(context["raw_edges"])
    _validate_theoretical_bounds_schema(bounds)
    graph_hashes = _input_graph_hashes(context)
    if bounds.get("graph_input_sha256") != graph_hashes["raw_edges"]:
        raise ValueError("bounds graph_input_sha256 does not match current G_raw")
    if int(bounds.get("class_count", -1)) != int(len(context["class_nodes"])):
        raise ValueError("bounds class_count does not match current subject")
    if not np.isclose(
        float(bounds.get("max_raw_edge_weight")),
        _max_raw_edge_weight(context["raw_edges"]),
        rtol=0.0,
        atol=1e-15,
    ):
        raise ValueError("bounds max_raw_edge_weight does not match current G_raw")
    expected_imbalance = theoretical_imbalance_upper_bound(
        len(context["class_nodes"]),
        context["max_cluster_ratio"],
    )
    if float(bounds.get("imbalance_upper_bound")) + 1e-12 < expected_imbalance:
        raise ValueError("bounds imbalance_upper_bound does not cover current constraints")


def _base_manifest(
    context: dict[str, Any],
    bounds: dict[str, Any],
    seeds: list[int],
    bounds_config: Path,
    config_path: Path,
    run_type: str,
) -> dict[str, Any]:
    git_state = stage2._git_state(ROOT)
    return {
        "subject": context["subject"],
        "role": "stage2_raw_structure_only_nsga_robustness",
        "run_type": run_type,
        "calibration_status": bounds["calibration_status"],
        "bounds_source": bounds.get("bounds_source", ""),
        "bounds_derivation": bounds.get("bounds_derivation", {}),
        "front_source": "recomputed_nondominated_front",
        "git_commit": git_state["git_head"],
        "working_tree_dirty": git_state["git_dirty"],
        "source_fingerprint": _source_fingerprint(),
        "working_tree_diff_sha256": _working_tree_diff_sha256(),
        "config_path": _relative(config_path),
        "config_snapshot": context["config"],
        "algorithm_config_sha256": _file_sha256(config_path),
        "bounds_config_sha256": _file_sha256(bounds_config),
        "bounds_config": _relative(bounds_config),
        "input_graph": "G_raw",
        "input_graph_hashes": _input_graph_hashes(context),
        "stage1_leiden_partition_hash": stage2._frame_sha256(context["stage1_raw_baseline"]),
        "formal_seeds": [int(seed) for seed in seeds],
        "calibration_seeds": [int(seed) for seed in bounds.get("calibration_seeds", [])],
        "normalization_bounds": {
            "lower_bounds": bounds["lower_bounds"],
            "upper_bounds": bounds["upper_bounds"],
        },
        "class_count": bounds.get("class_count"),
        "max_raw_edge_weight": bounds.get("max_raw_edge_weight"),
        "imbalance_upper_bound": bounds.get("imbalance_upper_bound"),
        "imbalance_bound_method": bounds.get("imbalance_bound_method"),
        "reference_point": _float_list(REFERENCE_POINT),
        "objective_order": OBJECTIVE_ORDER,
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "pymoo_version": _package_version("pymoo"),
        "platform": platform.platform(),
    }


def _seed_metadata(seed: int, manifest: dict[str, Any], front_source: str) -> dict[str, Any]:
    return {
        "subject": manifest["subject"],
        "seed": int(seed),
        "run_type": manifest["run_type"],
        "calibration_status": manifest["calibration_status"],
        "bounds_source": manifest["bounds_source"],
        "bounds_derivation": manifest["bounds_derivation"],
        "git_commit": manifest["git_commit"],
        "working_tree_dirty": manifest["working_tree_dirty"],
        "source_fingerprint": manifest["source_fingerprint"],
        "working_tree_diff_sha256": manifest["working_tree_diff_sha256"],
        "algorithm_config_sha256": manifest["algorithm_config_sha256"],
        "bounds_config_sha256": manifest["bounds_config_sha256"],
        "class_count": manifest["class_count"],
        "max_raw_edge_weight": manifest["max_raw_edge_weight"],
        "imbalance_upper_bound": manifest["imbalance_upper_bound"],
        "imbalance_bound_method": manifest["imbalance_bound_method"],
        "normalization_bounds": manifest["normalization_bounds"],
        "reference_point": manifest["reference_point"],
        "objective_order": manifest["objective_order"],
        "front_source": front_source,
    }


def _seed_output_is_valid(seed_dir: Path, seed: int, manifest: dict[str, Any]) -> bool:
    required = [
        "pareto_front.csv",
        "pareto_labels.csv.xz",
        "run_metrics.json",
        "run_metadata.json",
    ]
    if not all((seed_dir / name).exists() for name in required):
        return False
    metadata = _read_json(seed_dir / "run_metadata.json")
    metrics = _read_json(seed_dir / "run_metrics.json")
    front_source = metrics.get("front_source")
    if front_source not in {"result.opt", "result.pop_fallback", "recomputed_nondominated_front"}:
        return False
    return metadata == _seed_metadata(seed, manifest, str(front_source))


def _load_subject_bounds(
    bounds_config: Path,
    subject: str,
    config_path: Path,
    run_type: str,
    allow_smoke_bounds: bool,
) -> dict[str, Any]:
    data = _normalize_bounds_document(_read_yaml_if_exists(bounds_config))
    subjects = data.get("subjects", {})
    if subject not in subjects:
        raise FileNotFoundError(
            f"missing frozen robustness bounds for {subject}: run --calibrate first"
        )
    bounds = subjects[subject]
    if list(bounds.get("objective_order", [])) != OBJECTIVE_ORDER:
        raise ValueError("bounds objective_order does not match robustness runner")
    if list(bounds.get("reference_point", [])) != _float_list(REFERENCE_POINT):
        raise ValueError("bounds reference_point does not match robustness runner")
    status = str(bounds.get("calibration_status", ""))
    bounds_source = str(bounds.get("bounds_source", "empirical"))
    if run_type == "formal":
        if bounds_source != "theoretical" or status != "not_required":
            raise ValueError(
                "formal robustness requires theoretical bounds with calibration_status=not_required"
            )
    elif bounds_source != "theoretical" and not allow_smoke_bounds:
        raise ValueError("empirical or smoke bounds require --allow-smoke-bounds")
    current_git = stage2._git_state(ROOT)["git_head"]
    if bounds.get("generated_from_commit") != current_git:
        raise ValueError("bounds generated_from_commit does not match current git commit")
    current_config_sha = _file_sha256(config_path)
    if bounds.get("algorithm_config_sha256") != current_config_sha:
        raise ValueError("bounds algorithm_config_sha256 does not match current config")
    lower = np.asarray(bounds["lower_bounds"], dtype=float)
    upper = np.asarray(bounds["upper_bounds"], dtype=float)
    if lower.shape != (3,) or upper.shape != (3,) or np.any(upper <= lower):
        raise ValueError("invalid robustness bounds")
    if bounds_source == "theoretical":
        _validate_theoretical_bounds_schema(bounds)
    return bounds


def _normalize_bounds_document(data: dict[str, Any]) -> dict[str, Any]:
    if not data:
        return {
            "schema_version": 2,
            "objective_order": OBJECTIVE_ORDER,
            "reference_point": _float_list(REFERENCE_POINT),
            "subjects": {},
        }
    if "subjects" in data:
        data.setdefault("schema_version", 2)
        data.setdefault("objective_order", OBJECTIVE_ORDER)
        data.setdefault("reference_point", _float_list(REFERENCE_POINT))
        data.setdefault("subjects", {})
        return data
    subjects = {
        key: value
        for key, value in data.items()
        if isinstance(value, dict) and "lower_bounds" in value and "upper_bounds" in value
    }
    return {
        "schema_version": 2,
        "objective_order": OBJECTIVE_ORDER,
        "reference_point": _float_list(REFERENCE_POINT),
        "subjects": subjects,
    }


def _front_metric_fields(front_diagnostics: dict[str, Any]) -> dict[str, Any]:
    return {
        "front_source": str(front_diagnostics.get("front_source", "")),
        "final_population_size": int(front_diagnostics.get("final_population_size", 0)),
        "result_opt_size": int(front_diagnostics.get("result_opt_size", 0)),
        "feasible_population_size": int(front_diagnostics.get("feasible_population_size", 0)),
        "constraint_violating_population_size": int(
            front_diagnostics.get("constraint_violating_population_size", 0)
        ),
        "recomputed_nondominated_size": int(front_diagnostics.get("recomputed_nondominated_size", 0)),
        "n_unique_objective_vectors": int(front_diagnostics.get("n_unique_objective_vectors", 0)),
        "n_unique_canonical_partitions": int(front_diagnostics.get("n_unique_canonical_partitions", 0)),
        "front_validation_passed": bool(front_diagnostics.get("front_validation_passed", False)),
        "has_feasible_solution": bool(front_diagnostics.get("has_feasible_solution", False)),
        "used_infeasible_fallback": bool(front_diagnostics.get("used_infeasible_fallback", False)),
    }


def _violation_metrics(exc: CalibrationBoundViolation, context: dict[str, Any]) -> dict[str, Any]:
    return {
        "subject": exc.subject,
        "seed": exc.seed,
        "run_type": context.get("run_type", ""),
        "calibration_status": context.get("calibration_status", ""),
        "bounds_source": context.get("bounds_source", ""),
        "class_count": context.get("class_count"),
        "max_raw_edge_weight": context.get("max_raw_edge_weight"),
        "imbalance_upper_bound": context.get("imbalance_upper_bound"),
        "imbalance_bound_method": context.get("imbalance_bound_method"),
        "calibration_bound_violation": True,
        "violation_objective": exc.objective,
        "violation_observed_value": exc.value,
        "violation_lower_bound": exc.lower,
        "violation_upper_bound": exc.upper,
        "violation_exceeded_amount": exc.exceeded_amount,
    }


def _normalize_checked(
    objectives: np.ndarray,
    bounds: dict[str, Any],
    subject: str = "",
    seed: int = -1,
) -> np.ndarray:
    lower = np.asarray(bounds["lower_bounds"], dtype=float)
    upper = np.asarray(bounds["upper_bounds"], dtype=float)
    matrix = np.atleast_2d(np.asarray(objectives, dtype=float))
    tolerance = float(bounds.get("bound_tolerance", BOUND_TOLERANCE))
    below = matrix < (lower - tolerance)
    above = matrix > (upper + tolerance)
    if np.any(below) or np.any(above):
        bad = np.argwhere(below | above)[0]
        objective = OBJECTIVE_ORDER[int(bad[1])]
        value = float(matrix[int(bad[0]), int(bad[1])])
        raise CalibrationBoundViolation(
            subject=subject,
            seed=seed,
            objective=objective,
            value=value,
            lower=float(lower[int(bad[1])]),
            upper=float(upper[int(bad[1])]),
        )
    return (matrix - lower) / (upper - lower)


def _snapshot_run_output(seed_dir: Path, bounds: dict[str, Any]) -> dict[str, Any]:
    pareto = pd.read_csv(seed_dir / "pareto_front.csv")
    metrics = _read_json(seed_dir / "run_metrics.json")
    selected_id = str(metrics["solution_id"])
    selected_rows = pareto.loc[pareto["solution_id"].astype(str) == selected_id]
    if len(selected_rows) != 1:
        raise ValueError(f"expected exactly one selected solution in {seed_dir}")
    selected = selected_rows.iloc[0].to_dict()
    labels = pd.read_csv(seed_dir / "pareto_labels.csv.xz", compression="xz")
    selected_partition = labels.loc[labels["solution_id"].astype(str) == selected_id]
    if selected_partition.empty:
        raise ValueError(f"missing selected labels for {selected_id} in {seed_dir}")
    objectives = pareto.loc[
        :,
        ["coupling", "pymoo_f1_negative_cohesion", "imbalance"],
    ].to_numpy(dtype=float)
    normalized = _normalize_checked(objectives, bounds)
    return {
        "front_objective_vectors": _sorted_vector_rows(objectives),
        "front_partitions": sorted(
            _partition_key_from_label_vector(value)
            for value in pareto["label_vector"].astype(str).tolist()
        ),
        "normalized_objective_vectors": _sorted_vector_rows(normalized),
        "hypervolume": float(metrics["hypervolume"]),
        "selected_solution": {
            "coupling": float(selected["coupling"]),
            "negative_cohesion": float(selected["pymoo_f1_negative_cohesion"]),
            "imbalance": float(selected["imbalance"]),
        },
        "selected_partition": stage2._label_key(
            selected_partition["cluster_id"].to_numpy(dtype=int)
        ),
        "leiden_diagnostics": {
            key: metrics[key]
            for key in [
                "selected_equals_leiden",
                "exact_leiden_present_in_front",
                "n_non_leiden_partitions",
                "n_injected_seed_solutions",
                "n_non_injected_solutions",
                "leiden_dominated_by_front",
                "n_solutions_dominating_leiden",
            ]
        },
        "front_validation_diagnostics": {
            key: metrics[key]
            for key in [
                "front_source",
                "final_population_size",
                "result_opt_size",
                "feasible_population_size",
                "constraint_violating_population_size",
                "recomputed_nondominated_size",
                "n_unique_objective_vectors",
                "n_unique_canonical_partitions",
                "front_validation_passed",
                "has_feasible_solution",
                "used_infeasible_fallback",
            ]
        },
    }


def compare_run_snapshots(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for key in ["front_objective_vectors", "normalized_objective_vectors"]:
        if not np.allclose(left[key], right[key], rtol=1e-12, atol=1e-12):
            mismatches.append(key)
    if left["front_partitions"] != right["front_partitions"]:
        mismatches.append("front_partitions")
    if not np.isclose(left["hypervolume"], right["hypervolume"], rtol=1e-12, atol=1e-12):
        mismatches.append("hypervolume")
    for key in ["coupling", "negative_cohesion", "imbalance"]:
        if not np.isclose(
            left["selected_solution"][key],
            right["selected_solution"][key],
            rtol=1e-12,
            atol=1e-12,
        ):
            mismatches.append(f"selected_solution.{key}")
    if left["selected_partition"] != right["selected_partition"]:
        mismatches.append("selected_partition")
    for key in ["leiden_diagnostics", "front_validation_diagnostics"]:
        if left[key] != right[key]:
            mismatches.append(key)
    return mismatches


def _raw_leiden_objective_vector(context: dict[str, Any]) -> np.ndarray:
    labels = context["stage1_raw_baseline"]["cluster_id"].to_numpy(dtype=int)
    cluster_by_class = encoding.to_cluster_by_class(labels, context["class_nodes"])
    coupling, cohesion, imbalance = evaluate_structural_objectives(
        context["raw_edges"],
        cluster_by_class,
        stage2.RAW_WEIGHT_COLUMN,
    )
    return np.asarray([coupling, -cohesion, imbalance], dtype=float)


def _raw_leiden_key(context: dict[str, Any]) -> tuple[int, ...]:
    labels = context["stage1_raw_baseline"]["cluster_id"].to_numpy(dtype=int)
    return stage2._label_key(labels)


def _partition_key_from_label_vector(label_vector: str) -> tuple[int, ...]:
    return stage2._label_key(np.asarray(json.loads(label_vector), dtype=int))


def _dominates(left: np.ndarray, right: np.ndarray) -> bool:
    return bool(np.all(left <= right) and np.any(left < right))


def _row_by_solution_id(rows: list[dict[str, Any]], solution_id: str) -> dict[str, Any]:
    for row in rows:
        if row["solution_id"] == solution_id:
            return row
    raise ValueError(f"missing row for solution_id={solution_id}")


def _sorted_vector_rows(matrix: np.ndarray) -> np.ndarray:
    rows = sorted(tuple(float(value) for value in row) for row in np.atleast_2d(matrix))
    return np.asarray(rows, dtype=float)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _float_list(values: np.ndarray) -> list[float]:
    return [float(value) for value in np.asarray(values, dtype=float).tolist()]


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_fingerprint() -> dict[str, str]:
    return {
        _relative(path): _file_sha256(path)
        for path in SOURCE_FINGERPRINT_PATHS
    }


def _working_tree_diff_sha256() -> str:
    command = ["git", "diff", "--"] + [_relative(path) for path in SOURCE_FINGERPRINT_PATHS]
    diff = stage2._git_command(ROOT, command) or ""
    return hashlib.sha256(diff.encode("utf-8")).hexdigest()


def _read_yaml_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _parse_seeds(value: str | None, default: list[int]) -> list[int]:
    if value:
        return [int(part.strip()) for part in value.split(",") if part.strip()]
    return list(default)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Stage 2 raw-only robustness.")
    parser.add_argument("--subject", required=True, choices=SUBJECTS)
    parser.add_argument("--seeds", default=None)
    parser.add_argument("--num-seeds", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--bounds-config", type=Path, default=DEFAULT_BOUNDS_CONFIG)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--generate-theoretical-bounds", action="store_true")
    parser.add_argument("--calibration-seeds", default=None)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--verify-subprocess", action="store_true")
    parser.add_argument("--allow-smoke-bounds", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--config", type=Path, default=stage2.CONFIG_PATH)
    parser.add_argument("--max-cluster-ratio", type=float, default=None)
    args = parser.parse_args()

    if args.generate_theoretical_bounds:
        path = generate_theoretical_bounds(args.subject, args.bounds_config, args.config)
        print(f"Theoretical bounds: {_relative(path)}")
        return 0

    if args.calibrate:
        calibration_seeds = _parse_seeds(args.calibration_seeds, CALIBRATION_SEEDS)
        path = run_calibration(args.subject, calibration_seeds, args.bounds_config, args.config)
        print(f"Calibration bounds: {_relative(path)}")
        return 0

    if args.seeds:
        seeds = _parse_seeds(args.seeds, FORMAL_SEEDS)
    elif args.num_seeds is not None:
        seeds = list(range(args.num_seeds))
    else:
        seeds = FORMAL_SEEDS
    run_type = "smoke" if args.allow_smoke_bounds else "formal"

    if args.verify:
        if len(seeds) != 1:
            raise ValueError("--verify requires exactly one seed via --seeds")
        mismatches = verify_seed(
            args.subject,
            seeds[0],
            args.bounds_config,
            args.config,
            allow_smoke_bounds=args.allow_smoke_bounds,
        )
        if mismatches:
            print("VERIFY FAILED: " + ", ".join(mismatches), file=sys.stderr)
            return 1
        print(f"VERIFY PASSED subject={args.subject} seed={seeds[0]}")
        return 0

    if args.verify_subprocess:
        if len(seeds) != 1:
            raise ValueError("--verify-subprocess requires exactly one seed via --seeds")
        mismatches = verify_seed_subprocess(
            args.subject,
            seeds[0],
            args.bounds_config,
            args.config,
            allow_smoke_bounds=args.allow_smoke_bounds,
        )
        if mismatches:
            print("VERIFY SUBPROCESS FAILED: " + ", ".join(mismatches), file=sys.stderr)
            return 1
        print(f"VERIFY SUBPROCESS PASSED subject={args.subject} seed={seeds[0]}")
        return 0

    output_dir = run_robustness(
        subject=args.subject,
        seeds=seeds,
        output_dir=args.output_dir,
        bounds_config=args.bounds_config,
        config_path=args.config,
        run_type=run_type,
        allow_smoke_bounds=args.allow_smoke_bounds,
        resume=args.resume,
        max_cluster_ratio=args.max_cluster_ratio,
    )
    print(f"Robustness output: {_relative(output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
