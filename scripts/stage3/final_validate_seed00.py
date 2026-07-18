#!/usr/bin/env python3
"""Read-only validation of the saved final Stage 3 seed-0 artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.stage3 import final_seed00_optimizer as adapter  # noqa: E402


REPORT_ROOT = ROOT / "reports/stage3"
SUBJECTS = adapter.SUBJECTS


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


def evaluate_structural(context: dict[str, Any], mapping: dict[str, int]) -> tuple[float, float, float]:
    return tuple(float(value) for value in adapter.stage2.evaluate_structural_objectives(context["raw_edges"], mapping, "raw_weight"))


def evaluate_semantic(context: dict[str, Any], mapping: dict[str, int]) -> float:
    return float(adapter.evaluate_semantic_objective(
        context["semantic_edges"], mapping, total_weight=context["semantic_graph_metadata"]["total_edge_weight"]
    ))


def final_selected_mapping(selected: dict[str, Any], class_ids: list[str]) -> dict[str, int]:
    rows = selected["selected_partition"]
    mapping = {str(row["class_id"]): int(row["cluster_id"]) for row in rows}
    if set(mapping) != set(class_ids) or len(mapping) != len(rows):
        raise ValueError("final Stage 3 selected partition scope mismatch")
    return mapping


def front_validation(context: dict[str, Any], subject: str, front: pd.DataFrame, projected: pd.DataFrame, labels: pd.DataFrame, selected: dict[str, Any]) -> dict[str, Any]:
    objective_columns = ["pymoo_f0_coupling", "pymoo_f1_negative_cohesion", "pymoo_f2_imbalance", "pymoo_f3_f_semantic"]
    matrix = front[objective_columns].to_numpy(dtype=float)
    nd = adapter.runtime._nondominated_indices(matrix)
    ids_ok = front["solution_id"].is_unique
    expected_ids = set(context["class_nodes"]["class_id"].astype(str))
    scope_ok = True
    max_diff = 0.0
    by_id = {row["solution_id"]: row for row in front.to_dict("records")}
    for solution_id, group in labels.groupby("solution_id", sort=False):
        scope_ok = scope_ok and set(group["class_id"].astype(str)) == expected_ids and not group["class_id"].duplicated().any()
        mapping = dict(zip(group["class_id"].astype(str), group["cluster_id"].astype(int), strict=True))
        values = adapter.runtime.evaluate_four_objective_values(
            context["raw_edges"], context["semantic_edges"], mapping, "raw_weight",
            context["semantic_graph_metadata"]["total_edge_weight"],
        )
        row = by_id[solution_id]
        expected = np.asarray([row["coupling"], row["cohesion"], row["imbalance"], row["f_semantic"]], dtype=float)
        max_diff = max(max_diff, float(np.max(np.abs(np.asarray(values) - expected))))
    selected_in_projected = selected["selected_solution_id"] in set(projected["solution_id"])
    front_pass = bool(
        len(front) > 0 and len(projected) > 0 and len(nd) == len(front) and ids_ok and scope_ok
        and max_diff <= 1e-12 and np.isfinite(matrix).all()
        and np.all((front["f_semantic"] >= 0.0) & (front["f_semantic"] <= 1.0))
        and selected_in_projected
    )
    return {
        "subject": subject, "front_size": len(front), "projected_front_size": len(projected),
        "nondominated_count": len(nd), "all_front_nondominated": len(nd) == len(front),
        "unique_solution_ids": bool(ids_ok), "exact_class_scope": bool(scope_ok),
        "objective_recomputation_max_abs_difference": max_diff,
        "selected_in_projected_front": selected_in_projected, "pass": front_pass,
    }


def hv_validation(subject: str, context: dict[str, Any], projected: pd.DataFrame) -> dict[str, Any]:
    path = output(subject) / "projected_front_3d.csv"
    recomputed, nondominated = adapter.runtime._independent_projected_hv(path, context["bounds"])
    stored = json.loads((output(subject) / "projected_hypervolume.json").read_text(encoding="utf-8"))
    saved = float(stored["stored_value"])
    return {
        "subject": subject,
        "stored_hypervolume": saved,
        "independent_recomputed_hypervolume": recomputed,
        "absolute_difference": abs(saved - recomputed),
        "projected_nondominated_count": nondominated,
        "projected_front_rows": len(projected),
        "pass": bool(np.isclose(saved, recomputed, rtol=0.0, atol=adapter.HV_TOLERANCE) and nondominated == len(projected)),
    }


def selector_validation(subject: str, context: dict[str, Any], projected: pd.DataFrame, selected: dict[str, Any]) -> dict[str, Any]:
    posthoc = pd.read_csv(output(subject) / "posthoc_metrics.csv")
    expected = adapter.stage2._select_solution(posthoc.to_dict("records"), projected.to_dict("records"))
    selected_id = selected["selected_solution_id"]
    return {
        "subject": subject,
        "selected_solution_id": selected_id,
        "recomputed_selected_solution_id": expected["solution_id"],
        "semantic_objective_used_for_selection": selected.get("semantic_objective_used_for_selection"),
        "pass": bool(selected_id == expected["solution_id"] and selected.get("semantic_objective_used_for_selection") is False),
    }


def validate_subject(subject: str) -> dict[str, Any]:
    context = adapter.load_context(subject)
    metadata, front, projected, labels, selected = load_output(subject)
    if metadata.get("representation_id") != adapter.REPRESENTATION_ID:
        raise ValueError(f"{subject}: representation mismatch")
    result = adapter.runtime.validate_run_output(output(subject), context)
    front_result = front_validation(context, subject, front, projected, labels, selected)
    if not front_result["pass"]:
        raise ValueError(f"{subject}: final seed-0 front validation failed")
    return {"subject": subject, "representation_id": metadata["representation_id"], "validation_status": "passed", **result}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate saved final Stage 3 seed-0 outputs")
    parser.parse_args()
    rows = [validate_subject(subject) for subject in SUBJECTS]
    print(json.dumps({"status": "PASS", "subjects": rows, "legacy_runtime_dependency": False}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
