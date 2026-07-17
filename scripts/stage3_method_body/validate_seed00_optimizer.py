#!/usr/bin/env python3
"""Validate the isolated Stage 3B seed-0 optimizer outputs.

This script is intentionally post-run validation only.  It never writes to a
Stage 3A result/report namespace and never runs a seed other than zero.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.stage3_method_body import run_seed00_optimizer as adapter


REPORT_ROOT = ROOT / "reports/stage3_method_body"
SUBJECTS = adapter.SUBJECTS
STAGE2_STORAGE = adapter.STORAGE_SUBJECT
SCIENTIFIC_REPRO_FILES = (
    "pareto_front_4d.csv",
    "projected_front_3d.csv",
    "partition_labels.csv",
    "posthoc_metrics.csv",
    "selected_partition.csv",
    "selected_solution.json",
    "projected_hypervolume.json",
    "objective_redundancy.json",
)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def output(subject: str) -> Path:
    return adapter.output_dir(subject)


def load_output(subject: str) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    directory = output(subject)
    metadata = json.loads((directory / "run_metadata.json").read_text(encoding="utf-8"))
    front = pd.read_csv(directory / "pareto_front_4d.csv", float_precision="round_trip")
    projected = pd.read_csv(directory / "projected_front_3d.csv", float_precision="round_trip")
    labels = pd.read_csv(directory / "partition_labels.csv")
    selected = json.loads((directory / "selected_solution.json").read_text(encoding="utf-8"))
    return metadata, front, projected, labels, selected


def mapping_from_partition(path: Path, class_ids: list[str]) -> dict[str, int] | None:
    if not path.is_file():
        return None
    frame = pd.read_csv(path, dtype={"class_id": str})
    if set(frame["class_id"].astype(str)) != set(class_ids) or frame["class_id"].duplicated().any():
        return None
    return dict(zip(frame["class_id"].astype(str), frame["cluster_id"].astype(int), strict=True))


def stage2_selected_mapping(subject: str, class_ids: list[str]) -> dict[str, int] | None:
    path = ROOT / "results" / STAGE2_STORAGE[subject] / "03_stage2_nsga/robustness/seed_00/selected_partition.csv"
    return mapping_from_partition(path, class_ids)


def stage3a_selected_mapping(subject: str, class_ids: list[str]) -> dict[str, int] | None:
    path = ROOT / "results" / subject / "04_stage3_semantic/validation/seed_00/selected_partition.csv"
    return mapping_from_partition(path, class_ids)


def stage3b_selected_mapping(subject: str, selected: dict[str, Any], class_ids: list[str]) -> dict[str, int]:
    rows = selected["selected_partition"]
    observed = {str(row["class_id"]): int(row["cluster_id"]) for row in rows}
    if set(observed) != set(class_ids) or len(observed) != len(rows):
        raise ValueError(f"{subject}: Stage 3B selected partition scope mismatch")
    return observed


def evaluate_structural(context: dict[str, Any], mapping: dict[str, int]) -> tuple[float, float, float]:
    return tuple(float(value) for value in adapter.stage2.evaluate_structural_objectives(context["raw_edges"], mapping, "raw_weight"))


def evaluate_semantic(context: dict[str, Any], mapping: dict[str, int]) -> float:
    return float(adapter.evaluate_semantic_objective(
        context["semantic_edges"], mapping, total_weight=context["semantic_graph_metadata"]["total_edge_weight"]
    ))


def pre_run_checks(context: dict[str, Any]) -> dict[str, Any]:
    labels = adapter.encoding.canonical_relabel(np.arange(len(context["class_nodes"])) % 2)
    mapping = adapter.encoding.to_cluster_by_class(labels, context["class_nodes"])
    problem = adapter.build_four_objective_problem(
        context["class_nodes"], context["raw_edges"], context["semantic_edges"], "raw_weight",
        seed=0, max_cluster_ratio=context["max_cluster_ratio"],
    )
    out: dict[str, Any] = {}
    problem._evaluate(labels, out)
    values = np.asarray(out["F"], dtype=float)
    out["finite_four_objectives"] = bool(np.isfinite(values).all())
    out["semantic_in_range"] = bool(0.0 <= values[3] <= 1.0)
    out["structural_direct_evaluation"] = list(evaluate_structural(context, mapping))
    out["semantic_direct_evaluation"] = evaluate_semantic(context, mapping)
    out["pass"] = bool(out["finite_four_objectives"] and out["semantic_in_range"])
    return out


def structural_regression(context: dict[str, Any], subject: str, front: pd.DataFrame, labels: pd.DataFrame) -> list[dict[str, Any]]:
    n = len(context["class_nodes"])
    class_ids = context["class_nodes"]["class_id"].astype(str).tolist()
    fixed: dict[str, dict[str, int]] = {}
    fixed["fixed_leiden"] = dict(zip(class_ids, context["stage1_raw_baseline"]["cluster_id"].astype(int), strict=True))
    fixed["all_one"] = dict.fromkeys(class_ids, 0)
    fixed["deterministic_two_cluster"] = {class_id: index % 2 for index, class_id in enumerate(class_ids)}
    fixed["deterministic_three_cluster"] = {class_id: index % 3 for index, class_id in enumerate(class_ids)}
    rng = np.random.default_rng(42)
    shuffled = np.arange(n) % 4
    rng.shuffle(shuffled)
    fixed["seeded_shuffle_42"] = dict(zip(class_ids, shuffled.astype(int), strict=True))
    external = {
        "stage2_seed00_selected": stage2_selected_mapping(subject, class_ids),
        "stage3a_seed00_selected": stage3a_selected_mapping(subject, class_ids),
    }
    rows: list[dict[str, Any]] = []
    for name, mapping in {**fixed, **{key: value for key, value in external.items() if value is not None}}.items():
        values2 = evaluate_structural(context, mapping)
        values3 = adapter.stage3a.evaluate_four_objective_values(
            context["raw_edges"], context["semantic_edges"], mapping, "raw_weight",
            context["semantic_graph_metadata"]["total_edge_weight"],
        )[:3]
        diffs = np.abs(np.asarray(values2) - np.asarray(values3))
        rows.append({
            "subject": subject, "partition_source": name, "solution_id": "",
            "stage2_coupling": values2[0], "stage2_cohesion": values2[1], "stage2_imbalance": values2[2],
            "stage3b_coupling": values3[0], "stage3b_cohesion": values3[1], "stage3b_imbalance": values3[2],
            "max_abs_difference": float(diffs.max()), "pass": bool(np.array_equal(values2, values3)),
        })
    label_groups = {solution_id: group for solution_id, group in labels.groupby("solution_id", sort=False)}
    for solution_id, group in label_groups.items():
        mapping = dict(zip(group["class_id"].astype(str), group["cluster_id"].astype(int), strict=True))
        values2 = evaluate_structural(context, mapping)
        values3 = adapter.stage3a.evaluate_four_objective_values(
            context["raw_edges"], context["semantic_edges"], mapping, "raw_weight",
            context["semantic_graph_metadata"]["total_edge_weight"],
        )[:3]
        diffs = np.abs(np.asarray(values2) - np.asarray(values3))
        rows.append({
            "subject": subject, "partition_source": "saved_stage3b_front", "solution_id": solution_id,
            "stage2_coupling": values2[0], "stage2_cohesion": values2[1], "stage2_imbalance": values2[2],
            "stage3b_coupling": values3[0], "stage3b_cohesion": values3[1], "stage3b_imbalance": values3[2],
            "max_abs_difference": float(diffs.max()), "pass": bool(np.array_equal(values2, values3)),
        })
    return rows


def semantic_sanity(context: dict[str, Any], subject: str, selected: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    class_ids = context["class_nodes"]["class_id"].astype(str).tolist()
    partitions = {
        "all_one": dict.fromkeys(class_ids, 0),
        "all_singletons": dict(zip(class_ids, range(len(class_ids)), strict=True)),
        "fixed_leiden": dict(zip(class_ids, context["stage1_raw_baseline"]["cluster_id"].astype(int), strict=True)),
        "stage2_seed00_selected": stage2_selected_mapping(subject, class_ids),
        "stage3a_seed00_selected": stage3a_selected_mapping(subject, class_ids),
        "stage3b_seed00_selected": stage3b_selected_mapping(subject, selected, class_ids),
    }
    partitions = {key: value for key, value in partitions.items() if value is not None}
    rng = np.random.default_rng(42)
    random_labels = np.arange(len(class_ids)) % 4
    rng.shuffle(random_labels)
    partitions["seeded_shuffle_42"] = dict(zip(class_ids, random_labels.astype(int), strict=True))
    rows = []
    for name, mapping in partitions.items():
        value = evaluate_semantic(context, mapping)
        rows.append({"subject": subject, "partition_source": name, "semantic_objective": value, "finite": np.isfinite(value), "in_range": 0.0 <= value <= 1.0})
    values = np.asarray([row["semantic_objective"] for row in rows], dtype=float)
    summary = {
        "subject": subject, "partition_count": len(rows), "minimum": float(values.min()), "maximum": float(values.max()),
        "mean": float(values.mean()), "std": float(values.std(ddof=0)), "unique_values": int(len(set(values.tolist()))),
        "varies": bool(values.max() > values.min()), "all_finite": bool(np.isfinite(values).all()),
        "all_in_range": bool(np.all((values >= 0.0) & (values <= 1.0))), "pass": bool(np.isfinite(values).all() and np.all((values >= 0.0) & (values <= 1.0)) and values.max() > values.min()),
    }
    return rows, summary


def front_validation(context: dict[str, Any], subject: str, front: pd.DataFrame, projected: pd.DataFrame, labels: pd.DataFrame, selected: dict[str, Any]) -> dict[str, Any]:
    objective_columns = ["pymoo_f0_coupling", "pymoo_f1_negative_cohesion", "pymoo_f2_imbalance", "pymoo_f3_f_semantic"]
    matrix = front[objective_columns].to_numpy(dtype=float)
    nd = adapter.stage3a._nondominated_indices(matrix)
    ids_ok = front["solution_id"].is_unique
    scope_ok = True
    max_diff = 0.0
    expected_ids = set(context["class_nodes"]["class_id"].astype(str))
    by_id = {row["solution_id"]: row for row in front.to_dict("records")}
    for solution_id, group in labels.groupby("solution_id", sort=False):
        scope_ok = scope_ok and set(group["class_id"].astype(str)) == expected_ids and not group["class_id"].duplicated().any()
        mapping = dict(zip(group["class_id"].astype(str), group["cluster_id"].astype(int), strict=True))
        values = adapter.stage3a.evaluate_four_objective_values(
            context["raw_edges"], context["semantic_edges"], mapping, "raw_weight",
            context["semantic_graph_metadata"]["total_edge_weight"],
        )
        row = by_id[solution_id]
        expected = np.asarray([row["coupling"], row["cohesion"], row["imbalance"], row["f_semantic"]], dtype=float)
        max_diff = max(max_diff, float(np.max(np.abs(np.asarray(values) - expected))))
    front_pass = bool(
        len(front) > 0 and len(projected) > 0 and len(nd) == len(front) and ids_ok and scope_ok
        and max_diff <= 1e-12 and np.isfinite(matrix).all()
        and np.all((front["f_semantic"] >= 0.0) & (front["f_semantic"] <= 1.0))
        and selected["selected_solution_id"] in set(projected["solution_id"])
    )
    return {
        "subject": subject, "front_size": len(front), "projected_front_size": len(projected),
        "nondominated_count": len(nd), "all_front_nondominated": len(nd) == len(front),
        "unique_solution_ids": bool(ids_ok), "exact_class_scope": bool(scope_ok),
        "objective_recomputation_max_abs_difference": max_diff, "selected_in_projected_front": selected["selected_solution_id"] in set(projected["solution_id"]),
        "f_semantic_min": float(front["f_semantic"].min()), "f_semantic_max": float(front["f_semantic"].max()),
        "f_semantic_varies": bool(front["f_semantic"].max() > front["f_semantic"].min()), "pass": front_pass,
    }


def front_diagnostics(subject: str, front: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {"subject": subject, "front_size": len(front)}
    for name in ("coupling", "cohesion", "imbalance", "f_semantic"):
        values = front[name].to_numpy(dtype=float)
        result[f"{name}_min"] = float(values.min())
        result[f"{name}_mean"] = float(values.mean())
        result[f"{name}_max"] = float(values.max())
        result[f"{name}_std"] = float(values.std(ddof=0))
    semantic = front["f_semantic"].to_numpy(dtype=float)
    for name in ("coupling", "cohesion", "imbalance"):
        values = front[name].to_numpy(dtype=float)
        if len(values) < 2 or len(set(semantic.tolist())) <= 1 or len(set(values.tolist())) <= 1:
            result[f"spearman_f_semantic_vs_{name}"] = None
            result[f"spearman_f_semantic_vs_{name}_p"] = None
        else:
            corr = spearmanr(semantic, values)
            result[f"spearman_f_semantic_vs_{name}"] = float(corr.statistic)
            result[f"spearman_f_semantic_vs_{name}_p"] = float(corr.pvalue)
    result["semantic_objective_constant"] = bool(front["f_semantic"].nunique() <= 1)
    result["diagnostic_only"] = True
    return result


def hv_validation(subject: str, context: dict[str, Any], projected: pd.DataFrame) -> dict[str, Any]:
    path = output(subject) / "projected_front_3d.csv"
    recomputed, nd = adapter.stage3a._independent_projected_hv(path, context["bounds"])
    stored = json.loads((output(subject) / "projected_hypervolume.json").read_text(encoding="utf-8"))
    saved = float(stored["stored_value"])
    return {
        "subject": subject, "stored_hypervolume": saved, "independent_recomputed_hypervolume": recomputed,
        "absolute_difference": abs(saved - recomputed), "tolerance": adapter.HV_TOLERANCE,
        "projected_nondominated_count": nd, "projected_front_rows": len(projected),
        "reference_point": "[1.1, 1.1, 1.1]", "bounds_source": "configs/experiments/stage2_robustness_bounds.yml",
        "stored_hypervolume_type": "comparable_projected_3d", "native_4d_hypervolume": "not stored; non-comparable internal diagnostic",
        "pass": bool(np.isclose(saved, recomputed, rtol=0.0, atol=adapter.HV_TOLERANCE) and nd == len(projected)),
    }


def selector_validation(subject: str, context: dict[str, Any], projected: pd.DataFrame, selected: dict[str, Any]) -> dict[str, Any]:
    posthoc = pd.read_csv(output(subject) / "posthoc_metrics.csv")
    projected_rows = projected.to_dict("records")
    posthoc_rows = posthoc.to_dict("records")
    expected = adapter.stage2._select_solution(posthoc_rows, projected_rows)
    selected_id = selected["selected_solution_id"]
    selected_mapping = stage3b_selected_mapping(subject, selected, context["class_nodes"]["class_id"].astype(str).tolist())
    stage1 = dict(zip(context["class_nodes"]["class_id"].astype(str), context["stage1_raw_baseline"]["cluster_id"].astype(int), strict=True))
    stage1_frame = pd.DataFrame({"class_id": list(stage1), "cluster_id": list(stage1.values())})
    selected_frame = pd.DataFrame({"class_id": list(selected_mapping), "cluster_id": list(selected_mapping.values())})
    ari, nmi = adapter.stage2.partition_similarity(context["class_nodes"], selected_frame, stage1_frame)
    return {
        "subject": subject, "selected_solution_id": selected_id, "recomputed_selected_solution_id": expected["solution_id"],
        "selection_rule": expected["selection_rule"], "semantic_objective_used_for_selection": selected.get("semantic_objective_used_for_selection"),
        "selected_weighted_modularity": expected["selected_weighted_modularity"], "selected_cluster_count": expected["selected_cluster_count"],
        "selected_ari_vs_raw_leiden": float(ari), "selected_nmi_vs_raw_leiden": float(nmi),
        "pass": bool(selected_id == expected["solution_id"] and selected.get("semantic_objective_used_for_selection") is False),
    }


def selected_comparison(subject: str, context: dict[str, Any], selected: dict[str, Any]) -> dict[str, Any]:
    class_ids = context["class_nodes"]["class_id"].astype(str).tolist()
    records: dict[str, dict[str, Any] | None] = {
        "stage2_seed00": stage2_selected_mapping(subject, class_ids),
        "stage3a_seed00": stage3a_selected_mapping(subject, class_ids),
        "stage3b_seed00": stage3b_selected_mapping(subject, selected, class_ids),
    }
    rows = []
    b_mapping = records["stage3b_seed00"]
    for source, mapping in records.items():
        if mapping is None:
            rows.append({"subject": subject, "source": source, "available": False, "diagnostic_label": "SINGLE-SEED DIAGNOSTIC — NOT EFFECTIVENESS EVIDENCE"})
            continue
        structural = evaluate_structural(context, mapping)
        posthoc = adapter.stage2._partition_metrics_row(
            subject=subject, seed=0, solution_id=source, class_nodes=context["class_nodes"],
            clusters=pd.DataFrame({"class_id": list(mapping), "class_name": list(mapping), "cluster_id": list(mapping.values())}),
            raw_edges=context["raw_edges"], cluster_by_class=mapping, reference_mapping=None,
        )
        ari = nmi = None
        if b_mapping is not None:
            left = pd.DataFrame({"class_id": list(mapping), "cluster_id": list(mapping.values())})
            right = pd.DataFrame({"class_id": list(b_mapping), "cluster_id": list(b_mapping.values())})
            ari, nmi = adapter.stage2.partition_similarity(context["class_nodes"], left, right)
        rows.append({
            "subject": subject, "source": source, "available": True, "coupling": structural[0], "cohesion": structural[1],
            "imbalance": structural[2], "f_semantic_on_stage3b_graph": evaluate_semantic(context, mapping),
            "cluster_count": posthoc["cluster_count"], "weighted_modularity": posthoc["weighted_modularity"],
            "ari_vs_stage3b": ari, "nmi_vs_stage3b": nmi,
            "diagnostic_label": "SINGLE-SEED DIAGNOSTIC — NOT EFFECTIVENESS EVIDENCE",
        })
    return rows


def reproducibility_check() -> tuple[list[dict[str, Any]], str]:
    root = Path(tempfile.mkdtemp(prefix="stage3b-seed00-repro-"))
    rows = []
    try:
        for subject in SUBJECTS:
            canonical = output(subject)
            second = adapter.run_seed(subject, 0, adapter.output_dir(subject, root), run_type="validation_reproducibility")
            comparisons = []
            for name in SCIENTIFIC_REPRO_FILES:
                left = (canonical / name).read_bytes()
                right = (second / name).read_bytes()
                comparisons.append({"file": name, "byte_identical": left == right, "canonical_sha256": hashlib.sha256(left).hexdigest(), "second_sha256": hashlib.sha256(right).hexdigest()})
            rows.append({"subject": subject, "temporary_root": str(root), "files_compared": len(comparisons), "byte_identical_files": sum(item["byte_identical"] for item in comparisons), "all_byte_identical": all(item["byte_identical"] for item in comparisons), "file_details": comparisons})
    finally:
        shutil.rmtree(root)
    return rows, "canonical accepted output versus a clean temporary external destination; variable timestamps, runtime metadata, logs, and aggregate hash ledgers were excluded"


def graph_diagnostic_rows(subjects: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    overlap = pd.read_csv(REPORT_ROOT / "semantic_structural_overlap.csv").set_index("subject")
    random = pd.read_csv(REPORT_ROOT / "semantic_graph_random_baseline_summary.csv").set_index("subject")
    comparison = pd.read_csv(REPORT_ROOT / "stage3a_vs_stage3b_graph_comparison.csv").set_index("subject")
    empty = pd.read_csv(REPORT_ROOT / "empty_vs_nonempty_body_graph_change.csv")
    overlap_rows = []
    random_rows = []
    comparison_rows = []
    for subject in subjects:
        o = overlap.loc[subject].to_dict(); r = random.loc[subject].to_dict(); c = comparison.loc[subject].to_dict()
        identity = {"subject": subject, "graph_hash": adapter.EXPECTED_GRAPH_HASHES[subject], "diagnostic_source": "validated Stage 3B graph reports"}
        overlap_rows.append({**identity, **o})
        random_rows.append({**identity, **r, "go_threshold_rule": "observed structural overlap > frozen random p95"})
        comparison_rows.append({**identity, **c})
    return overlap_rows, random_rows, comparison_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-repro", action="store_true")
    args = parser.parse_args()
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    log_lines = [f"start_utc={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}", "seed=0 only"]
    all_contexts: dict[str, dict[str, Any]] = {}
    structural_rows: list[dict[str, Any]] = []
    semantic_rows: list[dict[str, Any]] = []
    semantic_summaries: list[dict[str, Any]] = []
    front_rows: list[dict[str, Any]] = []
    front_diag_rows: list[dict[str, Any]] = []
    hv_rows: list[dict[str, Any]] = []
    selector_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    runtime_rows: list[dict[str, Any]] = []
    per_subject: list[dict[str, Any]] = []
    pre_run: dict[str, Any] = {}
    try:
        for subject in SUBJECTS:
            context = adapter.load_context(subject)
            all_contexts[subject] = context
            metadata, front, projected, labels, selected = load_output(subject)
            if metadata.get("representation_id") != adapter.REPRESENTATION_ID or metadata.get("experiment_name") != adapter.EXPERIMENT_ID:
                raise ValueError(f"{subject}: accepted result identity mismatch")
            if metadata.get("graph_sha256") != adapter.EXPECTED_GRAPH_HASHES[subject] or metadata.get("input_aggregate_sha256") != adapter.EXPECTED_INPUT_HASHES[subject]:
                raise ValueError(f"{subject}: accepted result provenance mismatch")
            pre_run[subject] = pre_run_checks(context)
            structural_rows.extend(structural_regression(context, subject, front, labels))
            semantic, semantic_summary = semantic_sanity(context, subject, selected)
            semantic_rows.extend(semantic)
            semantic_summaries.append(semantic_summary)
            front_result = front_validation(context, subject, front, projected, labels, selected)
            front_rows.append(front_result)
            front_diag_rows.append(front_diagnostics(subject, front))
            hv_rows.append(hv_validation(subject, context, projected))
            selector_rows.append(selector_validation(subject, context, projected, selected))
            comparison_rows.extend(selected_comparison(subject, context, selected))
            runtime_rows.append({"subject": subject, "seed": 0, "runtime_seconds": metadata.get("runtime_seconds"), "evaluations": metadata.get("evaluations"), "front_size": len(front), "projected_front_size": len(projected), "selected_solution_id": selected["selected_solution_id"], "implementation_commit": metadata.get("implementation_commit")})
            per_subject.append({
                "subject": subject, "expected_class_count": adapter.EXPECTED_COUNTS[subject], "front_size": len(front),
                "projected_front_size": len(projected), "semantic_objective_min": front_result["f_semantic_min"],
                "semantic_objective_max": front_result["f_semantic_max"], "semantic_objective_varies": front_result["f_semantic_varies"],
                "structural_regression_pass": all(row["pass"] for row in structural_rows if row["subject"] == subject),
                "semantic_sanity_pass": semantic_summary["pass"], "front_validation_pass": front_result["pass"],
                "hypervolume_validation_pass": hv_rows[-1]["pass"], "selector_validation_pass": selector_rows[-1]["pass"],
                "pre_run_smoke_pass": pre_run[subject]["pass"], "graph_hash": adapter.EXPECTED_GRAPH_HASHES[subject],
                "input_aggregate_sha256": adapter.EXPECTED_INPUT_HASHES[subject], "embedding_aggregate_sha256": adapter.EXPECTED_EMBEDDING_HASHES[subject],
            })
        repro_rows, repro_method = reproducibility_check() if not args.skip_repro else ([], "skipped by command line")
        overlap_rows, random_rows, graph_comparison_rows = graph_diagnostic_rows(list(SUBJECTS))
        write_csv(REPORT_ROOT / "structural_objective_regression.csv", structural_rows)
        write_csv(REPORT_ROOT / "seed00_semantic_objective_sanity.csv", semantic_rows)
        write_csv(REPORT_ROOT / "seed00_pareto_validation.csv", front_rows)
        write_csv(REPORT_ROOT / "seed00_semantic_front_diagnostics.csv", front_diag_rows)
        write_csv(REPORT_ROOT / "seed00_hypervolume_validation.csv", hv_rows)
        write_csv(REPORT_ROOT / "seed00_selector_validation.csv", selector_rows)
        write_csv(REPORT_ROOT / "seed00_stage2_stage3a_stage3b_comparison.csv", comparison_rows)
        write_csv(REPORT_ROOT / "seed00_runtime_summary.csv", runtime_rows)
        # These graph-stage reports are frozen prerequisites.  Read them for
        # the seed-0 comparison, but never rewrite the graph-stage namespace.
        repro_flat = []
        for result in repro_rows:
            repro_flat.append({"subject": result["subject"], "files_compared": result["files_compared"], "byte_identical_files": result["byte_identical_files"], "all_byte_identical": result["all_byte_identical"], "temporary_root_removed": True})
        write_csv(REPORT_ROOT / "seed00_optimizer_reproducibility.csv", repro_flat)
        overall_repro = all(row["all_byte_identical"] for row in repro_rows) if repro_rows else False
        write_json(REPORT_ROOT / "seed00_optimizer_reproducibility.md.json", {"method": repro_method, "subjects": repro_rows, "overall_pass": overall_repro})
        reproducibility_lines = ["# Stage 3B seed-0 optimizer reproducibility", "", f"Method: {repro_method}.", "", "The accepted scientific files were compared byte-for-byte; timestamped metadata, runtime logs, and artifact ledgers were excluded.", ""]
        for row in repro_rows:
            reproducibility_lines.append(f"- {row['subject']}: {row['byte_identical_files']}/{row['files_compared']} scientific files byte-identical — **{'PASS' if row['all_byte_identical'] else 'FAIL'}**.")
        (REPORT_ROOT / "seed00_optimizer_reproducibility.md").write_text("\n".join(reproducibility_lines) + "\n", encoding="utf-8")
        artifact_rows = []
        for subject in SUBJECTS:
            for path in sorted(output(subject).rglob("*")):
                if path.is_file():
                    artifact_rows.append({"subject": subject, "representation_id": adapter.REPRESENTATION_ID, "path": relative(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
        write_csv(REPORT_ROOT / "seed00_optimizer_artifact_hashes.csv", artifact_rows)
        validation_pass = all(row["structural_regression_pass"] and row["semantic_sanity_pass"] and row["front_validation_pass"] and row["hypervolume_validation_pass"] and row["selector_validation_pass"] and row["pre_run_smoke_pass"] for row in per_subject) and overall_repro
        manifest = {
            "experiment_name": adapter.EXPERIMENT_ID, "experiment_id": adapter.EXPERIMENT_ID, "representation_id": adapter.REPRESENTATION_ID,
            "validation_type": "controlled_single_seed", "seed": 0, "subjects": SUBJECTS,
            "subject_class_counts": adapter.EXPECTED_COUNTS, "optimizer_contract_source": "frozen Stage 3A plus unchanged Stage 2 helpers",
            "semantic_graph_substitution_only": True, "no_formal_seed_range_run": True, "no_embeddings_generated": True,
            "no_semantic_graph_generated": True, "outputs": {subject: relative(output(subject)) for subject in SUBJECTS},
            "graph_hashes": adapter.EXPECTED_GRAPH_HASHES, "input_aggregate_hashes": adapter.EXPECTED_INPUT_HASHES,
            "embedding_aggregate_hashes": adapter.EXPECTED_EMBEDDING_HASHES,
            "reports": ["seed00_optimizer_validation_summary.md", "seed00_optimizer_validation_per_subject.csv", "structural_objective_regression.csv", "seed00_semantic_objective_sanity.csv", "seed00_pareto_validation.csv", "seed00_semantic_front_diagnostics.csv", "seed00_hypervolume_validation.csv", "seed00_selector_validation.csv", "seed00_stage2_stage3a_stage3b_comparison.csv", "seed00_optimizer_reproducibility.md", "seed00_optimizer_reproducibility.csv", "seed00_runtime_summary.csv", "seed00_optimizer_artifact_hashes.csv"],
            "reproducibility_pass": overall_repro, "validation_pass": validation_pass, "diagnostic_boundary": "SINGLE-SEED DIAGNOSTIC — NOT EFFECTIVENESS EVIDENCE",
            "execution_commit": runtime_rows[0]["implementation_commit"], "generated_at_utc": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        }
        write_json(REPORT_ROOT / "seed00_optimizer_manifest.json", manifest)
        summary_lines = [
            "# Stage 3B seed-0 optimizer validation", "", "## Scope", "",
            "This is a controlled seed-0 validation of the isolated declaration-plus-method-body semantic graph. No formal seeds, NSGA-II runs beyond seed 0, embedding generation, graph generation, Hypervolume comparison across seeds, or decomposition-quality analysis was performed.", "",
            "**SINGLE-SEED DIAGNOSTIC — NOT EFFECTIVENESS EVIDENCE**", "",
            "## Frozen optimizer boundary", "",
            "Structural objectives, initialization, operators, repair, population size, generations, semantic objective formula, four-dimensional Pareto front, projected three-dimensional Hypervolume, and representative selector were reused from the frozen Stage 3A/Stage 2 implementation. Only the validated Stage 3B semantic graph was substituted.", "",
            "## Subject results", "",
            "| Subject | Front | Projected | Structural | Semantic | Front | HV | Selector | Reproducibility |", "|---|---:|---:|---|---|---|---|---|---|",
        ]
        for row in per_subject:
            summary_lines.append(f"| {row['subject']} | {row['front_size']} | {row['projected_front_size']} | {row['structural_regression_pass']} | {row['semantic_sanity_pass']} | {row['front_validation_pass']} | {row['hypervolume_validation_pass']} | {row['selector_validation_pass']} | {next((x['all_byte_identical'] for x in repro_rows if x['subject'] == row['subject']), False)} |")
        summary_lines += ["", "## Acceptance interpretation", "", f"- All subject-level validation gates: **{validation_pass}**.", f"- Formal seed range 0–29: **not run**.", "- Stage 2 and Stage 3A results were read only for diagnostic comparison; they were not modified.", "- A PASS here permits the next controlled formal-seed task only; it is not evidence of decomposition-quality improvement.", ""]
        (REPORT_ROOT / "seed00_optimizer_validation_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")
        write_csv(REPORT_ROOT / "seed00_optimizer_validation_per_subject.csv", per_subject)
        log_lines.append(f"validation_pass={validation_pass}")
        log_lines.append(f"reproducibility_pass={overall_repro}")
    except Exception as exc:
        log_lines.append(f"failure={type(exc).__name__}: {exc}")
        (REPORT_ROOT / "logs").mkdir(parents=True, exist_ok=True)
        (REPORT_ROOT / "logs/seed00_optimizer_validation.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        raise
    (REPORT_ROOT / "logs").mkdir(parents=True, exist_ok=True)
    (REPORT_ROOT / "logs/seed00_optimizer_validation.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(f"seed-0 validation pass: {validation_pass}")
    return 0 if validation_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
