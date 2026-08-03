"""Run the Stage 2 raw-only structure NSGA-II experiment."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import hashlib
import json
import lzma
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.evaluation.partition_metrics import _edge_weight_split
from evo_ms.evaluation.partition_metrics import _weighted_modularity
from evo_ms.evaluation.partition_metrics import cluster_size_distribution
from evo_ms.evaluation.partition_metrics import partition_similarity
from evo_ms.evaluation.reference_metrics import calculate_reference_metrics
from evo_ms.evaluation.reference_metrics import load_reference_mapping
from evo_ms.extraction.dependency_extractor import load_raw_extracted_subject
from evo_ms.graph.raw_graph_builder import build_raw_edges
from evo_ms.optimization import encoding
from evo_ms.optimization.objectives import evaluate_structural_objectives
from evo_ms.optimization.problem import build_nsga2_algorithm
from evo_ms.optimization.problem import build_structural_problem
from evo_ms.optimization.problem import repair_labels
from evo_ms.utils.config_loader import load_yaml
from evo_ms.utils.logging import get_logger

CONFIG_PATH = ROOT / "configs" / "experiments" / "02_stage2_nsga_structure_only.yml"
OUTPUT_LAYER = "03_stage2_nsga"
RAW_OUTPUT_GROUP = "raw"
RAW_WEIGHT_COLUMN = "raw_weight"
RAW_BASELINE_PROFILE = "raw_reference_leiden"


def run_stage2_nsga(
    root: Path = ROOT,
    subject: str | None = None,
    seeds: Sequence[int] | None = None,
    population_size: int | None = None,
    generations: int | None = None,
    output_group: str | None = None,
    config_path: Path | None = None,
) -> Path:
    """Run raw-only Stage 2 NSGA-II for one subject."""
    config = load_yaml(config_path or CONFIG_PATH)
    _reject_obsolete_config(config)
    subject_name = subject or config.get("subject")
    if not subject_name:
        raise ValueError("Stage 2 run requires a subject")
    seeds = [int(seed) for seed in (seeds if seeds is not None else config["random_seeds"])]
    if not seeds:
        raise ValueError("Stage 2 run requires at least one seed")

    nsga_config = config.get("nsga", {})
    initialization_config = config.get("initialization", {})
    population_size = int(population_size or nsga_config.get("population_size", 100))
    generations = int(generations or nsga_config.get("generations", 100))

    subject_config = _load_subject_config(root, subject_name)
    extracted_dir, extracted, raw_edges = _raw_graph_inputs(root, subject_name, subject_config)
    class_nodes = extracted["class_nodes"]
    stage1_raw_baseline = _frozen_raw_leiden_baseline(root, subject_name, class_nodes)
    reference_mapping = _reference_mapping(root, subject_config, subject_name)

    output_root = root / config.get("output_root", "results")
    output_dir = output_root / subject_name / OUTPUT_LAYER / (output_group or RAW_OUTPUT_GROUP)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = get_logger(__name__)
    seed_results = []
    for seed in seeds:
        logger.info(
            "Running Stage 2 raw NSGA-II subject=%s seed=%s pop=%s gen=%s",
            subject_name,
            seed,
            population_size,
            generations,
        )
        seed_results.append(
            _run_seed(
                class_nodes=class_nodes,
                raw_edges=raw_edges,
                raw_leiden_clusters=stage1_raw_baseline,
                initialization_config=initialization_config,
                seed=seed,
                population_size=population_size,
                generations=generations,
            )
        )

    hv_reference, hv_method = _hypervolume_reference(seed_results)
    pareto_rows, label_rows, posthoc_rows, comparison_rows, hv_rows = _materialize_results(
        subject=subject_name,
        class_nodes=class_nodes,
        raw_edges=raw_edges,
        seed_results=seed_results,
        stage1_raw_baseline=stage1_raw_baseline,
        reference_mapping=reference_mapping,
        hv_reference=hv_reference,
    )
    selected = _select_solution(posthoc_rows, pareto_rows)
    selected_clusters = _clusters_for_solution(label_rows, selected["solution_id"])
    stage1_vs_stage2 = _stage1_vs_stage2_summary(
        subject=subject_name,
        class_nodes=class_nodes,
        raw_edges=raw_edges,
        stage1_raw_baseline=stage1_raw_baseline,
        selected_clusters=selected_clusters,
        selected_solution=selected,
        pareto_front_size=len(pareto_rows),
        population_size=population_size,
        generations=generations,
    )
    hv_summary = _hypervolume_summary(subject_name, hv_rows)

    pd.DataFrame(pareto_rows).to_csv(output_dir / "pareto_front.csv", index=False)
    # pareto_labels is long-format (one row per solution x class) and very large
    # for big subjects (Xerces-J ~98 MB raw); store it xz-compressed.
    pd.DataFrame(label_rows).to_csv(
        output_dir / "pareto_labels.csv.xz",
        index=False,
        compression={"method": "xz", "preset": 9 | lzma.PRESET_EXTREME},
    )
    pd.DataFrame(posthoc_rows).to_csv(output_dir / "posthoc_metrics.csv", index=False)
    pd.DataFrame(comparison_rows).to_csv(output_dir / "leiden_comparison.csv", index=False)
    pd.DataFrame(hv_rows).to_csv(output_dir / "hypervolume_by_seed.csv", index=False)
    pd.DataFrame([hv_summary]).to_csv(output_dir / "hypervolume_summary.csv", index=False)
    pd.DataFrame([selected]).to_csv(output_dir / "selected_solution.csv", index=False)
    selected_clusters.to_csv(output_dir / "selected_partition.csv", index=False)
    pd.DataFrame([stage1_vs_stage2]).to_csv(output_dir / "stage1_vs_stage2.csv", index=False)
    _write_metadata(
        output_dir / "metadata.yml",
        root=root,
        subject=subject_name,
        population_size=population_size,
        generations=generations,
        seeds=seeds,
        extracted_dir=extracted_dir,
        graph_edge_sha256=_frame_sha256(raw_edges),
        hv_reference=hv_reference,
        hv_reference_method=hv_method,
        initialization_config=initialization_config,
        git_state=_git_state(root),
    )
    logger.info("Wrote Stage 2 raw-only outputs to %s", output_dir)
    return output_dir


def _run_seed(
    class_nodes: pd.DataFrame,
    raw_edges: pd.DataFrame,
    raw_leiden_clusters: pd.DataFrame,
    initialization_config: Mapping[str, object],
    seed: int,
    population_size: int,
    generations: int,
    save_history: bool = False,
    callback: object | None = None,
    initialization_observer=None,
) -> dict[str, object]:
    from pymoo.optimize import minimize

    seed_records = _seed_initialization_records(
        class_nodes=class_nodes,
        raw_edges=raw_edges,
        raw_leiden_clusters=raw_leiden_clusters,
        seed=seed,
        config=initialization_config,
    )
    seed_record_by_key = {
        _label_key(np.asarray(record["labels"], dtype=int)): record
        for record in seed_records
    }
    problem = build_structural_problem(
        class_nodes,
        raw_edges,
        RAW_WEIGHT_COLUMN,
        seed=seed,
    )
    algorithm = build_nsga2_algorithm(
        population_size=population_size,
        seed_labels=[record["labels"] for record in seed_records],
        initialization_observer=initialization_observer,
    )
    result = minimize(
        problem,
        algorithm,
        termination=("n_gen", int(generations)),
        seed=int(seed),
        verbose=False,
        save_history=bool(save_history),
        callback=callback,
    )
    labels, _, constraints, front_diagnostics = _front_arrays(result)
    solutions = []
    seen: set[tuple[int, ...]] = set()
    for raw_labels, raw_g in zip(labels, constraints, strict=True):
        canonical = encoding.canonical_relabel(raw_labels)
        key = _label_key(canonical)
        if key in seen:
            continue
        seen.add(key)
        seed_record = seed_record_by_key.get(key)
        cluster_by_class = encoding.to_cluster_by_class(canonical, class_nodes)
        coupling, cohesion, imbalance = evaluate_structural_objectives(
            raw_edges,
            cluster_by_class,
            RAW_WEIGHT_COLUMN,
        )
        solutions.append(
            {
                "labels": canonical,
                "F": np.asarray([coupling, -cohesion, imbalance], dtype=float),
                "G": np.asarray(raw_g, dtype=float),
                "feasible": bool(np.all(np.asarray(raw_g, dtype=float) <= 0.0)),
                "is_injected_seed": seed_record is not None,
                "injected_seed_name": "" if seed_record is None else str(seed_record["name"]),
                "injected_seed_category": "" if seed_record is None else str(seed_record["category"]),
            }
        )
    solutions.sort(key=lambda item: (item["F"][0], item["F"][1], item["F"][2], _label_key(item["labels"])))
    front_diagnostics["n_unique_objective_vectors"] = int(
        len({tuple(_objective_key(solution["F"])) for solution in solutions})
    )
    front_diagnostics["n_unique_canonical_partitions"] = int(
        len({_label_key(solution["labels"]) for solution in solutions})
    )
    front_diagnostics["front_validation_passed"] = bool(
        len(solutions) == front_diagnostics["n_unique_canonical_partitions"]
        and len(solutions) <= front_diagnostics["recomputed_nondominated_size"]
    )
    return {
        "seed": int(seed),
        "solutions": solutions,
        "seed_initialization_count": len(seed_records),
        "seed_initialization_categories": _category_counts(seed_records),
        "front_diagnostics": front_diagnostics,
        # Formal robustness keeps this disabled. The convergence diagnostic is
        # the only caller that requests pymoo's per-generation populations.
        "history": list(result.history) if save_history else [],
    }


def _result_arrays(result) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    labels, objectives, constraints, _ = _front_arrays(result)
    return labels, objectives, constraints


def _front_arrays(result) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    pop_x, pop_f, pop_g = _population_arrays(result.pop)
    opt_x, opt_f, opt_g = _population_arrays(result.opt)
    final_population_size = len(pop_x)
    result_opt_size = len(opt_x)
    feasible_mask = _feasible_mask(pop_g, final_population_size)
    feasible_population_size = int(np.sum(feasible_mask))
    constraint_violating_population_size = int(final_population_size - feasible_population_size)
    if final_population_size == 0:
        labels, objectives, constraints = opt_x, opt_f, opt_g
        recomputed_size = 0
        source = "result.opt" if result_opt_size else "result.pop_fallback"
        used_infeasible_fallback = False
    else:
        pool_mask = feasible_mask if feasible_population_size else np.ones(final_population_size, dtype=bool)
        pool_indices = np.flatnonzero(pool_mask)
        front_local = _nondominated_indices(pop_f[pool_indices])
        front_indices = pool_indices[front_local]
        labels = pop_x[front_indices]
        objectives = pop_f[front_indices]
        constraints = pop_g[front_indices]
        recomputed_size = len(front_indices)
        used_infeasible_fallback = feasible_population_size == 0
        source = "recomputed_nondominated_front"

    canonical_keys = [_label_key(row) for row in labels]
    objective_keys = [_objective_key(row) for row in objectives]
    diagnostics = {
        "front_source": source,
        "final_population_size": int(final_population_size),
        "result_opt_size": int(result_opt_size),
        "feasible_population_size": feasible_population_size,
        "constraint_violating_population_size": constraint_violating_population_size,
        "recomputed_nondominated_size": int(recomputed_size),
        "n_unique_objective_vectors": int(len(set(objective_keys))),
        "n_unique_canonical_partitions": int(len(set(canonical_keys))),
        "front_validation_passed": bool(len(labels) == recomputed_size),
        "has_feasible_solution": bool(feasible_population_size > 0),
        "used_infeasible_fallback": bool(used_infeasible_fallback),
    }
    return labels, objectives, constraints, diagnostics


def _population_arrays(population) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if population is None or len(population) == 0:
        return (
            np.empty((0, 0), dtype=int),
            np.empty((0, 3), dtype=float),
            np.empty((0, 3), dtype=float),
        )
    labels = np.atleast_2d(np.asarray(population.get("X"), dtype=int))
    objectives = np.atleast_2d(np.asarray(population.get("F"), dtype=float))
    constraints = population.get("G")
    if constraints is None:
        constraints = np.zeros((len(labels), 3), dtype=float)
    constraints = np.atleast_2d(np.asarray(constraints, dtype=float))
    return labels, objectives, constraints


def _feasible_mask(constraints: np.ndarray, size: int) -> np.ndarray:
    if size == 0:
        return np.asarray([], dtype=bool)
    if constraints.size == 0:
        return np.ones(size, dtype=bool)
    return np.all(np.atleast_2d(constraints) <= 0.0, axis=1)


def _nondominated_indices(objectives: np.ndarray) -> np.ndarray:
    if len(objectives) == 0:
        return np.asarray([], dtype=int)
    from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

    indices = NonDominatedSorting().do(
        np.asarray(objectives, dtype=float),
        only_non_dominated_front=True,
    )
    return np.asarray(sorted(indices.tolist()), dtype=int)


def _objective_key(values: np.ndarray) -> tuple[str, ...]:
    return tuple(f"{float(value):.12g}" for value in np.asarray(values, dtype=float))


def _materialize_results(
    subject: str,
    class_nodes: pd.DataFrame,
    raw_edges: pd.DataFrame,
    seed_results: list[dict[str, object]],
    stage1_raw_baseline: pd.DataFrame,
    reference_mapping: pd.DataFrame | None,
    hv_reference: np.ndarray,
) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    pareto_rows: list[dict] = []
    label_rows: list[dict] = []
    posthoc_rows: list[dict] = []
    comparison_rows: list[dict] = []
    hv_rows: list[dict] = []

    for seed_result in seed_results:
        seed = int(seed_result["seed"])
        seed_f = []
        for index, solution in enumerate(seed_result["solutions"]):
            labels = np.asarray(solution["labels"], dtype=int)
            coupling, neg_cohesion, imbalance = np.asarray(solution["F"], dtype=float)
            cohesion = -float(neg_cohesion)
            solution_id = f"seed{seed}_solution{index:03d}"
            clusters = encoding.to_clusters_frame(labels, class_nodes)
            cluster_by_class = encoding.to_cluster_by_class(labels, class_nodes)
            seed_f.append(solution["F"])

            pareto_rows.append(
                {
                    "subject": subject,
                    "seed": seed,
                    "solution_id": solution_id,
                    "coupling": float(coupling),
                    "cohesion": cohesion,
                    "imbalance": float(imbalance),
                    "pymoo_f0_coupling": float(coupling),
                    "pymoo_f1_negative_cohesion": float(neg_cohesion),
                    "pymoo_f2_imbalance": float(imbalance),
                    "feasible": bool(solution["feasible"]),
                    "is_injected_seed": bool(solution.get("is_injected_seed", False)),
                    "injected_seed_name": str(solution.get("injected_seed_name", "")),
                    "injected_seed_category": str(solution.get("injected_seed_category", "")),
                    "label_vector": json.dumps(labels.astype(int).tolist()),
                }
            )
            for row in clusters.to_dict("records"):
                label_rows.append(
                    {
                        "subject": subject,
                        "seed": seed,
                        "solution_id": solution_id,
                        "class_id": row["class_id"],
                        "class_name": row["class_name"],
                        "cluster_id": int(row["cluster_id"]),
                    }
                )

            posthoc_rows.append(
                _partition_metrics_row(
                    subject=subject,
                    seed=seed,
                    solution_id=solution_id,
                    class_nodes=class_nodes,
                    clusters=clusters,
                    raw_edges=raw_edges,
                    cluster_by_class=cluster_by_class,
                    reference_mapping=reference_mapping,
                )
            )
            ari, nmi = partition_similarity(class_nodes, clusters, stage1_raw_baseline)
            changed_count, changed_ratio = _changed_partition_ratio(
                class_nodes,
                clusters,
                stage1_raw_baseline,
            )
            comparison_rows.append(
                {
                    "subject": subject,
                    "seed": seed,
                    "solution_id": solution_id,
                    "baseline_profile": RAW_BASELINE_PROFILE,
                    "ari": float(ari),
                    "nmi": float(nmi),
                    "changed_class_count": int(changed_count),
                    "changed_partition_ratio": float(changed_ratio),
                }
            )
        hv_rows.append(
            {
                "subject": subject,
                "seed": seed,
                "hypervolume": _hypervolume(np.asarray(seed_f, dtype=float), hv_reference),
                "solution_count": len(seed_f),
            }
        )
    return pareto_rows, label_rows, posthoc_rows, comparison_rows, hv_rows


def _partition_metrics_row(
    subject: str,
    seed: int,
    solution_id: str,
    class_nodes: pd.DataFrame,
    clusters: pd.DataFrame,
    raw_edges: pd.DataFrame,
    cluster_by_class: dict[str, int],
    reference_mapping: pd.DataFrame | None = None,
) -> dict:
    sizes = clusters.groupby("cluster_id").size()
    class_count = int(len(class_nodes))
    singleton_count = int((sizes == 1).sum()) if not sizes.empty else 0
    internal_weight, external_weight = _edge_weight_split(
        raw_edges,
        cluster_by_class,
        RAW_WEIGHT_COLUMN,
    )
    total_weight = internal_weight + external_weight
    row = {
        "subject": subject,
        "seed": int(seed),
        "solution_id": solution_id,
        "weighted_modularity": _weighted_modularity(raw_edges, cluster_by_class, RAW_WEIGHT_COLUMN),
        "internal_edge_weight_ratio": 0.0 if total_weight == 0 else float(internal_weight / total_weight),
        "internal_external_edge_ratio": _safe_internal_external_ratio(
            internal_weight,
            external_weight,
        ),
        "cluster_count": int(sizes.size),
        "average_cluster_size": float(sizes.mean()) if not sizes.empty else 0.0,
        "max_cluster_size": int(sizes.max()) if not sizes.empty else 0,
        "min_cluster_size": int(sizes.min()) if not sizes.empty else 0,
        "max_cluster_ratio": 0.0
        if class_count == 0 or sizes.empty
        else float(sizes.max() / class_count),
        "singleton_ratio": 0.0 if class_count == 0 else float(singleton_count / class_count),
        "cluster_size_distribution": cluster_size_distribution(clusters),
    }
    if reference_mapping is not None:
        row.update(calculate_reference_metrics(class_nodes, clusters, reference_mapping))
    return row


def _safe_internal_external_ratio(internal_weight: float, external_weight: float) -> float:
    if external_weight == 0:
        return float(internal_weight) if internal_weight > 0 else 0.0
    return float(internal_weight / external_weight)


def _select_solution(posthoc_rows: list[dict], pareto_rows: list[dict]) -> dict:
    if not posthoc_rows:
        raise ValueError("cannot select a solution from an empty Pareto front")
    posthoc_by_id = {row["solution_id"]: row for row in posthoc_rows}
    candidates = [
        row
        for row in pareto_rows
        if bool(row["feasible"]) and row["solution_id"] in posthoc_by_id
    ]
    if not candidates:
        candidates = [row for row in pareto_rows if row["solution_id"] in posthoc_by_id]
    selected = min(
        candidates,
        key=lambda row: (
            -float(posthoc_by_id[row["solution_id"]]["weighted_modularity"]),
            bool(row["is_injected_seed"]),
            float(row["coupling"]),
            -float(row["cohesion"]),
            float(row["imbalance"]),
            _label_tuple_from_row(row),
        ),
    )
    metrics = posthoc_by_id[selected["solution_id"]]
    return {
        **selected,
        "selection_rule": "highest_weighted_modularity_among_feasible_pareto_solutions",
        "selected_weighted_modularity": float(metrics["weighted_modularity"]),
        "selected_cluster_count": int(metrics["cluster_count"]),
        "selected_max_cluster_ratio": float(metrics["max_cluster_ratio"]),
        "selected_singleton_ratio": float(metrics["singleton_ratio"]),
    }


def _clusters_for_solution(label_rows: list[dict], solution_id: str) -> pd.DataFrame:
    rows = [row for row in label_rows if row["solution_id"] == solution_id]
    if not rows:
        raise ValueError(f"missing labels for selected solution: {solution_id}")
    return pd.DataFrame(rows).loc[:, ["class_id", "class_name", "cluster_id"]]


def _stage1_vs_stage2_summary(
    subject: str,
    class_nodes: pd.DataFrame,
    raw_edges: pd.DataFrame,
    stage1_raw_baseline: pd.DataFrame,
    selected_clusters: pd.DataFrame,
    selected_solution: dict,
    pareto_front_size: int,
    population_size: int,
    generations: int,
) -> dict:
    stage1 = _partition_metrics_row(
        subject=subject,
        seed=42,
        solution_id=RAW_BASELINE_PROFILE,
        class_nodes=class_nodes,
        clusters=stage1_raw_baseline,
        raw_edges=raw_edges,
        cluster_by_class=encoding.to_cluster_by_class(
            stage1_raw_baseline["cluster_id"].to_numpy(dtype=int),
            class_nodes,
        ),
    )
    stage2 = _partition_metrics_row(
        subject=subject,
        seed=int(selected_solution["seed"]),
        solution_id=str(selected_solution["solution_id"]),
        class_nodes=class_nodes,
        clusters=selected_clusters,
        raw_edges=raw_edges,
        cluster_by_class=encoding.to_cluster_by_class(
            selected_clusters["cluster_id"].to_numpy(dtype=int),
            class_nodes,
        ),
    )
    ari, nmi = partition_similarity(class_nodes, selected_clusters, stage1_raw_baseline)
    changed_count, changed_ratio = _changed_partition_ratio(
        class_nodes,
        selected_clusters,
        stage1_raw_baseline,
    )
    return {
        "subject": subject,
        "stage1_profile": RAW_BASELINE_PROFILE,
        "stage2_solution_id": selected_solution["solution_id"],
        "selection_rule": selected_solution["selection_rule"],
        "seed": int(selected_solution["seed"]),
        "population_size": int(population_size),
        "generations": int(generations),
        "pareto_front_size": int(pareto_front_size),
        "stage2_coupling": float(selected_solution["coupling"]),
        "stage2_cohesion": float(selected_solution["cohesion"]),
        "stage2_imbalance": float(selected_solution["imbalance"]),
        "stage1_cluster_count": int(stage1["cluster_count"]),
        "stage2_cluster_count": int(stage2["cluster_count"]),
        "stage1_average_cluster_size": float(stage1["average_cluster_size"]),
        "stage2_average_cluster_size": float(stage2["average_cluster_size"]),
        "stage1_max_cluster_size": int(stage1["max_cluster_size"]),
        "stage2_max_cluster_size": int(stage2["max_cluster_size"]),
        "stage1_max_cluster_ratio": float(stage1["max_cluster_ratio"]),
        "stage2_max_cluster_ratio": float(stage2["max_cluster_ratio"]),
        "stage1_singleton_ratio": float(stage1["singleton_ratio"]),
        "stage2_singleton_ratio": float(stage2["singleton_ratio"]),
        "stage1_cluster_size_distribution": stage1["cluster_size_distribution"],
        "stage2_cluster_size_distribution": stage2["cluster_size_distribution"],
        "stage1_weighted_modularity": float(stage1["weighted_modularity"]),
        "stage2_weighted_modularity": float(stage2["weighted_modularity"]),
        "stage1_internal_edge_weight_ratio": float(stage1["internal_edge_weight_ratio"]),
        "stage2_internal_edge_weight_ratio": float(stage2["internal_edge_weight_ratio"]),
        "stage1_internal_external_edge_ratio": float(stage1["internal_external_edge_ratio"]),
        "stage2_internal_external_edge_ratio": float(stage2["internal_external_edge_ratio"]),
        "ari_stage1_raw_vs_stage2": float(ari),
        "nmi_stage1_raw_vs_stage2": float(nmi),
        "changed_class_count": int(changed_count),
        "changed_partition_ratio": float(changed_ratio),
    }


def _changed_partition_ratio(
    class_nodes: pd.DataFrame,
    left_clusters: pd.DataFrame,
    right_clusters: pd.DataFrame,
) -> tuple[int, float]:
    left_neighbors = _same_cluster_neighbors(left_clusters)
    right_neighbors = _same_cluster_neighbors(right_clusters)
    class_ids = class_nodes["class_id"].astype(str).tolist()
    changed = sum(
        1
        for class_id in class_ids
        if left_neighbors.get(class_id, set()) != right_neighbors.get(class_id, set())
    )
    return changed, 0.0 if not class_ids else changed / len(class_ids)


def _same_cluster_neighbors(clusters: pd.DataFrame) -> dict[str, set[str]]:
    neighbors: dict[str, set[str]] = {}
    for _, group in clusters.groupby("cluster_id"):
        class_ids = set(group["class_id"].astype(str))
        for class_id in class_ids:
            neighbors[class_id] = class_ids - {class_id}
    return neighbors


def _hypervolume_reference(seed_results: list[dict[str, object]]) -> tuple[np.ndarray, str]:
    objective_rows = [
        np.asarray(solution["F"], dtype=float)
        for seed_result in seed_results
        for solution in seed_result["solutions"]
    ]
    if not objective_rows:
        reference = np.asarray([1.1, 0.1, 1.1], dtype=float)
        return reference, "fallback_reference_for_empty_front"
    matrix = np.vstack(objective_rows)
    ideal = np.min(matrix, axis=0)
    nadir = np.max(matrix, axis=0)
    span = np.maximum(nadir - ideal, 1e-6)
    reference = nadir + np.maximum(0.1 * span, 1e-6)
    return reference.astype(float), "nadir_plus_10_percent_observed_span"


def _hypervolume(objectives: np.ndarray, reference: np.ndarray) -> float:
    if objectives.size == 0:
        return 0.0
    from pymoo.indicators.hv import HV

    return float(HV(ref_point=np.asarray(reference, dtype=float))(np.asarray(objectives, dtype=float)))


def _hypervolume_summary(subject: str, hv_rows: list[dict]) -> dict:
    values = np.asarray([row["hypervolume"] for row in hv_rows], dtype=float)
    return {
        "subject": subject,
        "seed_count": int(len(values)),
        "hypervolume_mean": float(np.mean(values)) if len(values) else 0.0,
        "hypervolume_std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        "hypervolume_min": float(np.min(values)) if len(values) else 0.0,
        "hypervolume_max": float(np.max(values)) if len(values) else 0.0,
    }


def _raw_graph_inputs(
    root: Path,
    subject: str,
    subject_config: Mapping[str, object],
) -> tuple[Path, dict[str, pd.DataFrame], pd.DataFrame]:
    extracted_dir = root / subject_config.get("extracted_output_path", f"data/extracted/{subject}")
    extracted = load_raw_extracted_subject(extracted_dir)
    raw_edges = build_raw_edges(extracted["class_nodes"], extracted["structural_dependencies"])
    return extracted_dir, extracted, raw_edges


def _seed_initialization_records(
    class_nodes: pd.DataFrame,
    raw_edges: pd.DataFrame,
    raw_leiden_clusters: pd.DataFrame,
    seed: int,
    config: Mapping[str, object],
) -> list[dict[str, object]]:
    """Build deterministic structure-aware initial labels for one NSGA-II seed."""
    if not bool(config.get("enabled", True)):
        return []

    mode = str(config.get("initialisation_mode", "current_warm_start"))
    if mode == "random_only":
        # Deliberately return before reading the Leiden partition.  This makes
        # the diagnostic condition independent of all Leiden-derived labels,
        # including perturbations and graph-grouping target counts.
        return []
    if mode != "current_warm_start":
        raise ValueError(f"unsupported initialisation_mode: {mode}")

    class_ids = class_nodes["class_id"].astype(str).tolist()
    index_by_id = {class_id: index for index, class_id in enumerate(class_ids)}
    raw_leiden_by_class = dict(
        zip(
            raw_leiden_clusters["class_id"].astype(str),
            raw_leiden_clusters["cluster_id"].astype(int),
            strict=True,
        )
    )
    raw_leiden_labels = encoding.canonical_relabel(
        np.asarray([raw_leiden_by_class[class_id] for class_id in class_ids], dtype=int)
    )
    rng = np.random.default_rng(_initialization_rng_seed(seed))
    records: list[dict[str, object]] = []

    if bool(config.get("include_raw_leiden", True)):
        records.append(
            {
                "name": "raw_leiden",
                "category": "raw_leiden",
                "labels": repair_labels(raw_leiden_labels, len(class_ids)),
            }
        )

    records.extend(
        _perturbed_leiden_records(
            raw_leiden_labels=raw_leiden_labels,
            class_ids=class_ids,
            raw_edges=raw_edges,
            index_by_id=index_by_id,
            rng=rng,
            config=config,
        )
    )
    records.extend(
        _graph_grouping_records(
            class_count=len(class_ids),
            raw_edges=raw_edges,
            index_by_id=index_by_id,
            raw_leiden_cluster_count=len(set(raw_leiden_labels.tolist())),
            config=config,
        )
    )
    return _deduplicate_seed_records(records, len(class_ids))


def _perturbed_leiden_records(
    raw_leiden_labels: np.ndarray,
    class_ids: list[str],
    raw_edges: pd.DataFrame,
    index_by_id: dict[str, int],
    rng: np.random.Generator,
    config: Mapping[str, object],
) -> list[dict[str, object]]:
    perturbation_config = config.get("perturbations", {})
    if not isinstance(perturbation_config, Mapping) or not bool(
        perturbation_config.get("enabled", True)
    ):
        return []
    fractions = [
        float(value)
        for value in perturbation_config.get("fractions", [0.005, 0.01, 0.02, 0.05])
    ]
    repetitions = int(perturbation_config.get("per_fraction", 5))
    adjacency = _adjacency_by_class(raw_edges)
    records: list[dict[str, object]] = []
    for fraction in fractions:
        move_count = max(1, int(round(fraction * len(class_ids))))
        for repetition in range(repetitions):
            labels = raw_leiden_labels.copy()
            chosen = rng.choice(len(labels), size=move_count, replace=False)
            for index in chosen:
                neighbor_clusters = [
                    labels[index_by_id[neighbor]]
                    for neighbor in adjacency.get(class_ids[index], set())
                    if neighbor in index_by_id
                ]
                if neighbor_clusters:
                    labels[index] = int(rng.choice(neighbor_clusters))
                else:
                    labels[index] = int(rng.choice(labels))
            records.append(
                {
                    "name": f"raw_leiden_perturb_{fraction:g}_{repetition}",
                    "category": "raw_leiden_perturbation",
                    "labels": repair_labels(labels, len(class_ids)),
                }
            )
    return records


def _graph_grouping_records(
    class_count: int,
    raw_edges: pd.DataFrame,
    index_by_id: dict[str, int],
    raw_leiden_cluster_count: int,
    config: Mapping[str, object],
) -> list[dict[str, object]]:
    grouping_config = config.get("graph_groupings", {})
    if not isinstance(grouping_config, Mapping) or not bool(grouping_config.get("enabled", True)):
        return []
    target_counts = set()
    for offset in grouping_config.get("target_offsets_from_raw_leiden", [-10, 0, 10]):
        target_counts.add(raw_leiden_cluster_count + int(offset))
    if bool(grouping_config.get("include_sqrt_target", True)):
        target_counts.add(int(np.ceil(np.sqrt(class_count) * 2.0)))
    target_counts = {
        max(2, min(int(target), class_count))
        for target in target_counts
    }
    records: list[dict[str, object]] = []
    for target_count in sorted(target_counts):
        records.append(
            {
                "name": f"strongest_edge_grouping_k{target_count}",
                "category": "strongest_edge_grouping",
                "labels": _strongest_edge_grouping_labels(
                    class_count=class_count,
                    raw_edges=raw_edges,
                    index_by_id=index_by_id,
                    target_count=target_count,
                ),
            }
        )
    return records


def _strongest_edge_grouping_labels(
    class_count: int,
    raw_edges: pd.DataFrame,
    index_by_id: dict[str, int],
    target_count: int,
) -> np.ndarray:
    parent = np.arange(class_count, dtype=int)
    sizes = np.ones(class_count, dtype=int)
    cluster_count = class_count
    max_size = max(1, int(np.floor(0.4 * class_count)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return int(index)

    for row in raw_edges.sort_values(
        [RAW_WEIGHT_COLUMN, "source", "target"],
        ascending=[False, True, True],
    ).to_dict("records"):
        if cluster_count <= target_count:
            break
        left = index_by_id.get(str(row["source"]))
        right = index_by_id.get(str(row["target"]))
        if left is None or right is None:
            continue
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root or sizes[left_root] + sizes[right_root] > max_size:
            continue
        if sizes[left_root] < sizes[right_root]:
            left_root, right_root = right_root, left_root
        parent[right_root] = left_root
        sizes[left_root] += sizes[right_root]
        cluster_count -= 1
    return repair_labels(np.asarray([find(index) for index in range(class_count)], dtype=int), class_count)


def _adjacency_by_class(edges: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    adjacency: dict[str, set[str]] = {}
    for row in edges.to_dict("records"):
        source = str(row["source"])
        target = str(row["target"])
        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set()).add(source)
    return {
        class_id: tuple(sorted(neighbors))
        for class_id, neighbors in sorted(adjacency.items())
    }


def _deduplicate_seed_records(
    records: list[dict[str, object]],
    class_count: int,
) -> list[dict[str, object]]:
    unique: list[dict[str, object]] = []
    seen: set[tuple[int, ...]] = set()
    for record in records:
        labels = repair_labels(np.asarray(record["labels"], dtype=int), class_count)
        key = _label_key(labels)
        if key in seen:
            continue
        seen.add(key)
        unique.append({**record, "labels": labels})
    return unique


def _label_key(labels: np.ndarray) -> tuple[int, ...]:
    canonical = encoding.canonical_relabel(labels)
    return tuple(int(value) for value in canonical.tolist())


def _label_tuple_from_row(row: Mapping[str, object]) -> tuple[int, ...]:
    value = row.get("label_vector", "[]")
    if isinstance(value, str):
        labels = json.loads(value)
    else:
        labels = value
    return _label_key(np.asarray(labels, dtype=int))


def _category_counts(records: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        category = str(record["category"])
        counts[category] = counts.get(category, 0) + 1
    return counts


def _initialization_rng_seed(seed: int) -> int:
    return 10_000 + int(seed)


def _frozen_raw_leiden_baseline(
    root: Path,
    subject: str,
    class_nodes: pd.DataFrame,
) -> pd.DataFrame:
    path = (
        root
        / "results"
        / subject
        / "01_stage1_leiden_baseline"
        / RAW_BASELINE_PROFILE
        / "clustering"
        / "stage1_clusters.csv"
    )
    if not path.exists():
        raise FileNotFoundError(f"missing frozen Stage 1 raw Leiden baseline: {path}")
    clusters = pd.read_csv(path)
    return _align_clusters(class_nodes, clusters)


def _reference_mapping(
    root: Path,
    subject_config: Mapping[str, object],
    subject: str,
) -> pd.DataFrame | None:
    if subject != "daytrader":
        return None
    path_value = subject_config.get("reference_mapping_path")
    if not path_value:
        return None
    path = root / str(path_value)
    return load_reference_mapping(path) if path.exists() else None


def _align_clusters(class_nodes: pd.DataFrame, clusters: pd.DataFrame) -> pd.DataFrame:
    cluster_map = dict(zip(clusters["class_id"].astype(str), clusters["cluster_id"], strict=True))
    return pd.DataFrame(
        {
            "class_id": class_nodes["class_id"].astype(str),
            "class_name": class_nodes["class_name"].astype(str),
            "cluster_id": [
                int(cluster_map[str(class_id)])
                for class_id in class_nodes["class_id"].astype(str).tolist()
            ],
        }
    )


def _write_metadata(
    path: Path,
    root: Path,
    subject: str,
    population_size: int,
    generations: int,
    seeds: Sequence[int],
    extracted_dir: Path,
    graph_edge_sha256: str,
    hv_reference: np.ndarray,
    hv_reference_method: str,
    initialization_config: Mapping[str, object],
    git_state: Mapping[str, object],
) -> None:
    metadata = {
        "subject": subject,
        "role": "stage2_raw_structure_only_nsga",
        "input_graph": "G_raw",
        "weight_column": RAW_WEIGHT_COLUMN,
        "stage1_baseline_profile": RAW_BASELINE_PROFILE,
        "population_size": int(population_size),
        "generations": int(generations),
        "seeds": [int(seed) for seed in seeds],
        "source_extracted_data": _relative_dir(root, extracted_dir),
        "extracted_input_sha256": _extracted_input_sha256(extracted_dir),
        "graph_edge_sha256": graph_edge_sha256,
        "hypervolume_reference_point": [float(value) for value in hv_reference],
        "hypervolume_reference_point_method": hv_reference_method,
        "hypervolume_scope": "subject_raw_objective_space_only",
        "initialization": _metadata_initialization(initialization_config),
        "generated_at_utc": _utc_now(),
        "git_head": git_state["git_head"],
        "git_dirty": git_state["git_dirty"],
    }
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(metadata, handle, sort_keys=False)


def _metadata_initialization(config: Mapping[str, object]) -> dict[str, object]:
    return {
        "enabled": bool(config.get("enabled", True)),
        "strategy": str(config.get("strategy", "structure_aware_seeded")),
        "basis": str(config.get("basis", "raw_reference_leiden_and_raw_graph")),
        "include_raw_leiden": bool(config.get("include_raw_leiden", True)),
        "random_fill": bool(config.get("random_fill", True)),
        "perturbations": dict(config.get("perturbations", {})),
        "graph_groupings": dict(config.get("graph_groupings", {})),
        "provenance_columns": [
            "is_injected_seed",
            "injected_seed_name",
            "injected_seed_category",
        ],
    }


def _load_subject_config(root: Path, subject: str) -> dict:
    path = root / "configs" / "subjects" / f"{subject}.yml"
    if not path.exists():
        raise FileNotFoundError(f"missing subject config: {path}")
    return load_yaml(path)


def _reject_obsolete_config(config: Mapping[str, object]) -> None:
    obsolete = [
        key
        for key in ["graph_type", "ssa_lambda", "lambda_values", "rq3", "ssa_ablation"]
        if key in config
    ]
    if obsolete:
        raise ValueError(
            "Stage 2 is raw-only; remove obsolete config fields: "
            + ", ".join(sorted(obsolete))
        )
    profiles = config.get("baseline_leiden_profiles", [])
    if profiles and list(profiles) != [RAW_BASELINE_PROFILE]:
        raise ValueError("Stage 2 compares only with raw_reference_leiden")


def _frame_sha256(frame: pd.DataFrame) -> str:
    data = frame.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _relative_dir(root: Path, path: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        relative = path
    text = relative.as_posix()
    return text if text.endswith("/") else f"{text}/"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extracted_input_sha256(extracted_dir: Path) -> dict[str, str]:
    return {
        name: _sha256(extracted_dir / name)
        for name in ["class_nodes.csv", "structural_dependencies.csv"]
    }


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_state(root: Path) -> dict[str, object]:
    return {
        "git_head": _git_command(root, ["git", "rev-parse", "HEAD"]),
        "git_dirty": _git_dirty(root),
    }


def _git_dirty(root: Path) -> bool | None:
    result = _git_command(
        root,
        ["git", "status", "--porcelain", "--untracked-files=all", "--", ".", ":(exclude)results"],
    )
    return None if result is None else bool(result.strip())


def _git_command(root: Path, command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, cwd=root, check=False, capture_output=True, text=True)
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run raw-only Stage 2 structure NSGA-II.")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--num-seeds", type=int, default=None)
    parser.add_argument("--seeds", default=None, help="comma-separated seed list")
    parser.add_argument("--population-size", type=int, default=None)
    parser.add_argument("--generations", type=int, default=None)
    parser.add_argument("--output-group", default=None)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()

    seeds = None
    if args.seeds:
        seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
    elif args.num_seeds is not None:
        seeds = list(range(args.num_seeds))

    output_dir = run_stage2_nsga(
        subject=args.subject,
        seeds=seeds,
        population_size=args.population_size,
        generations=args.generations,
        output_group=args.output_group,
        config_path=args.config,
    )
    print(f"Stage 2 output: {output_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
