#!/usr/bin/env python3
"""Build factual Stage 3 Day 6 inventories and descriptive reports.

This report builder only reloads committed per-seed validation sidecars and
saved formal artifacts. It does not run the optimizer or alter experiment
inputs, embeddings, graphs, or configuration.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SUBJECTS = ("jpetstore", "daytrader", "xerces")
EXPECTED_CLASS_COUNTS = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
SEEDS = list(range(30))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_saved_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, float_precision="round_trip")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def stats(values: list[float | int]) -> dict[str, float | int | None]:
    if not values:
        return {"min": None, "mean": None, "median": None, "std_population": None, "max": None}
    numeric = [float(value) for value in values]
    return {
        "min": min(numeric),
        "mean": mean(numeric),
        "median": median(numeric),
        "std_population": pstdev(numeric),
        "max": max(numeric),
    }


def seed_report_path(subject: str, seed: int) -> Path:
    return ROOT / "reports/stage3/seed_validation" / subject / f"seed_{seed:02d}.json"


def source_dir(record: dict[str, Any]) -> Path:
    return ROOT / record["source_directory"]


def aggregate_seed_hash(records: list[dict[str, Any]]) -> str:
    payload = "".join(
        f"{int(record['seed'])}\t{record['seed_artifact_aggregate_sha256']}\n"
        for record in sorted(records, key=lambda item: int(item["seed"]))
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_subject_records(subject: str) -> list[dict[str, Any]]:
    records = []
    for seed in SEEDS:
        path = seed_report_path(subject, seed)
        if not path.is_file():
            raise RuntimeError(f"missing validation sidecar: {path}")
        record = load_json(path)
        if record.get("subject") != subject or int(record.get("seed", -1)) != seed:
            raise RuntimeError(f"sidecar subject/seed mismatch: {path}")
        if record.get("status") != "valid" or record.get("validation_pass") is not True:
            raise RuntimeError(f"invalid sidecar: {path}")
        checks = record.get("validation_checks", {})
        required_checks = [
            "four_dimensional_non_dominance",
            "projected_three_dimensional_non_dominance",
            "projected_hypervolume_recomputed",
            "semantic_objective_non_constant",
            "representative_selection_recomputed",
            "class_partition_integrity",
            "stage2_objective_invariance",
            "semantic_graph_is_separate_input",
        ]
        if not all(checks.get(name) is True for name in required_checks):
            raise RuntimeError(f"validation checks incomplete: {path}")
        records.append(record)
    return records


def build_subject_summary(subject: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    fronts = []
    projected_front_sizes = []
    projected_hv = []
    runtimes = []
    rho = []
    selected_clusters = []
    all_semantic_values: list[float] = []
    fingerprints = set()
    for record in records:
        source = source_dir(record)
        front = read_saved_csv(source / "pareto_front_4d.csv")
        projected = read_saved_csv(source / "projected_front_3d.csv")
        if len(front) != int(record["front_4d_size"]):
            raise RuntimeError(f"front size mismatch for {subject} seed {record['seed']}")
        if len(projected) != int(record["projected_front_size"]):
            raise RuntimeError(f"projected front size mismatch for {subject} seed {record['seed']}")
        values = front["f_semantic"].to_numpy(dtype=float)
        if not np.isfinite(values).all() or np.any(values < 0.0) or np.any(values > 1.0):
            raise RuntimeError(f"invalid semantic objective values for {subject} seed {record['seed']}")
        fronts.append(int(len(front)))
        projected_front_sizes.append(int(len(projected)))
        projected_hv.append(float(record["projected_hv"]))
        runtimes.append(float(record["runtime_seconds"]))
        selected_clusters.append(int(record["selected_cluster_count"]))
        all_semantic_values.extend(float(value) for value in values)
        if record.get("redundancy_spearman_rho") is not None:
            rho.append(float(record["redundancy_spearman_rho"]))
        fingerprints.add(record["algorithm_fingerprint"]["sha256"])

    cluster_distribution = {
        str(key): int(value) for key, value in sorted(Counter(selected_clusters).items())
    }
    summary = {
        "subject": subject,
        "class_count": EXPECTED_CLASS_COUNTS[subject],
        "valid_seed_count": len(records),
        "seed_ids": [int(record["seed"]) for record in records],
        "aggregate_seed_artifact_sha256": aggregate_seed_hash(records),
        "algorithm_fingerprints": sorted(fingerprints),
        "front_4d_size": stats(fronts),
        "projected_front_size": stats(projected_front_sizes),
        "projected_hypervolume": stats(projected_hv),
        "selected_cluster_count_distribution": cluster_distribution,
        "f_semantic_across_all_4d_rows": stats(all_semantic_values),
        "spearman_rho": {
            "method": "spearman",
            "source": "final_stage3_4d_pareto_front",
            "n_valid": len(rho),
            "n_undefined": len(records) - len(rho),
            "distribution": stats(rho),
            "undefined": len(rho) == 0,
        },
        "runtime_seconds": stats(runtimes),
        "failure_count": 0,
        "partial_count": 0,
        "provenance_ambiguous_count": 0,
        "validation": {
            "four_dimensional_non_dominance": True,
            "projected_three_dimensional_non_dominance": True,
            "projected_hypervolume_recomputed": True,
            "semantic_objective_non_constancy": True,
            "representative_selection_reproducibility": True,
            "class_partition_integrity": True,
            "provenance_validation": True,
        },
    }
    return summary


def build_inventory(summaries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for subject in SUBJECTS:
        summary = summaries[subject]
        expected = set(SEEDS)
        actual = set(summary["seed_ids"])
        rows.append({
            "subject": subject,
            "expected": 30,
            "valid": len(actual),
            "missing": len(expected - actual),
            "extra": 0,
            "failed": summary["failure_count"],
            "partial": summary["partial_count"],
            "ambiguous": summary["provenance_ambiguous_count"],
        })
    return rows


def build_pilot_summary(records_by_subject: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    result = {}
    for subject, records in records_by_subject.items():
        pilot = [record for record in records if int(record["seed"]) in range(5)]
        result[subject] = {
            "seeds": [int(record["seed"]) for record in pilot],
            "all_valid": len(pilot) == 5 and all(record["status"] == "valid" for record in pilot),
            "semantic_objective_range": [
                min(float(record["f_semantic_min"]) for record in pilot),
                max(float(record["f_semantic_max"]) for record in pilot),
            ],
            "projected_hypervolume_range": [
                min(float(record["projected_hv"]) for record in pilot),
                max(float(record["projected_hv"]) for record in pilot),
            ],
            "projected_hypervolume_recomputed": all(
                record["validation_checks"]["projected_hypervolume_recomputed"] for record in pilot
            ),
            "representative_selection_reproducible": all(
                record["validation_checks"]["representative_selection_recomputed"] for record in pilot
            ),
            "accepted_into_formal_inventory": len(pilot) == 5,
            "validation_report_directory": f"reports/stage3/seed_validation/{subject}",
        }
    return result


def build_alignment(records_by_subject: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    subjects = {}
    for subject, records in records_by_subject.items():
        metadata = [load_json(source_dir(record) / "run_metadata.json") for record in records]
        values = {
            "config_sha256": {item["config_sha256"] for item in metadata},
            "semantic_graph_sha256": {item["g_sem_graph_hash"] for item in metadata},
            "raw_edge_hash": {item["g_raw_provenance"]["raw_edge_hash"] for item in metadata},
            "population_size": {int(item["population_size"]) for item in metadata},
            "generations": {int(item["generations"]) for item in metadata},
            "objective_order": {tuple(item["objective_order"]) for item in metadata},
            "report_objective_order": {tuple(item["report_objective_order"]) for item in metadata},
            "projected_hv_bounds_source": {item["projected_hv_bounds_source"] for item in metadata},
            "projected_hv_reference_point": {tuple(item["projected_hv_reference_point"]) for item in metadata},
            "no_model_inference": {bool(item["no_model_inference"]) for item in metadata},
            "no_graph_fusion": {bool(item["no_graph_fusion"]) for item in metadata},
        }
        selection_semantic_used = {
            bool(load_json(source_dir(record) / "selected_solution.json").get("semantic_objective_used_for_selection"))
            for record in records
        }
        values["selection_semantic_used"] = selection_semantic_used
        checks = {
            "exact_seed_ids_0_to_29": [int(record["seed"]) for record in records] == SEEDS,
            "exact_class_scope": all(record["expected_class_count"] == EXPECTED_CLASS_COUNTS[subject] for record in records),
            "config_unchanged_across_seeds": len(values["config_sha256"]) == 1,
            "semantic_graph_unchanged_across_seeds": len(values["semantic_graph_sha256"]) == 1,
            "raw_stage2_graph_unchanged_across_seeds": len(values["raw_edge_hash"]) == 1,
            "population_and_generations_unchanged": values["population_size"] == {100} and values["generations"] == {100},
            "objective_order_unchanged": values["objective_order"] == {("coupling", "negative_cohesion", "imbalance", "f_semantic")},
            "report_objective_order_unchanged": values["report_objective_order"] == {("coupling", "cohesion", "imbalance", "f_semantic")},
            "stage2_hv_bounds_and_reference_unchanged": values["projected_hv_bounds_source"] == {"configs/experiments/stage2_robustness_bounds.yml"} and values["projected_hv_reference_point"] == {(1.1, 1.1, 1.1)},
            "semantic_objective_not_used_for_selection": values["selection_semantic_used"] == {False},
            "no_model_inference": values["no_model_inference"] == {True},
            "no_graph_fusion": values["no_graph_fusion"] == {True},
        }
        subjects[subject] = {"checks": checks, "pass": all(checks.values()), "values": {key: sorted(map(str, value)) for key, value in values.items()}}
    return {"subjects": subjects, "all_pass": all(item["pass"] for item in subjects.values())}


def markdown_summary(summaries: dict[str, dict[str, Any]], inventory: list[dict[str, Any]], alignment: dict[str, Any]) -> str:
    lines = [
        "# Stage 3 formal 30-seed validation summary",
        "",
        "This report contains validated factual outputs only. It does not make a Stage 2 versus Stage 3 effectiveness or statistical claim.",
        "",
        "## Formal inventory",
        "",
        "| Subject | Expected | Valid | Missing | Extra | Failed | Partial | Ambiguous |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in inventory:
        lines.append("| {subject} | {expected} | {valid} | {missing} | {extra} | {failed} | {partial} | {ambiguous} |".format(**row))
    lines += ["", "## Subject summaries", ""]
    for subject in SUBJECTS:
        summary = summaries[subject]
        lines += [f"### {subject}", "", f"- Valid seeds: {summary['valid_seed_count']}/30."]
        for label, key in [
            ("4D front size", "front_4d_size"),
            ("Projected front size", "projected_front_size"),
            ("Projected HV", "projected_hypervolume"),
            ("f_semantic across all 4D rows", "f_semantic_across_all_4d_rows"),
            ("Runtime seconds", "runtime_seconds"),
        ]:
            value = summary[key]
            lines.append(f"- {label} min/mean/median/std/max: {value['min']} / {value['mean']} / {value['median']} / {value['std_population']} / {value['max']}.")
        lines.append(f"- Selected cluster-count distribution: `{json.dumps(summary['selected_cluster_count_distribution'], sort_keys=True)}`.")
        rho = summary["spearman_rho"]
        lines.append(f"- Spearman rho (final 4D front, f_semantic vs coupling): n={rho['n_valid']}, undefined={rho['n_undefined']}, min/mean/median/std/max={rho['distribution']['min']} / {rho['distribution']['mean']} / {rho['distribution']['median']} / {rho['distribution']['std_population']} / {rho['distribution']['max']}.")
        lines.append("")
    lines += ["## Validation and alignment", "", f"- Stage 2 alignment checks: {'PASS' if alignment['all_pass'] else 'FAIL'}.", "- All per-seed 4D/projected non-dominance, projected-HV recomputation, objective non-constancy, representative-selection, class-partition, and provenance checks passed.", "- No embeddings, semantic graphs, or Stage 2 outputs were generated by the report builder.", "- No Wilcoxon, Bonferroni, or paired effectiveness analysis was run.", ""]
    return "\n".join(lines)


def subject_markdown(summary: dict[str, Any]) -> str:
    return "\n".join([
        f"# {summary['subject']} Stage 3 formal validation",
        "",
        "Saved artifacts were independently reloaded and checked; this report makes no scientific comparison.",
        "",
        f"- Valid seeds: {summary['valid_seed_count']}/30.",
        f"- Aggregate seed-artifact SHA-256: `{summary['aggregate_seed_artifact_sha256']}`.",
        f"- 4D front size min/mean/median/std/max: {summary['front_4d_size']['min']} / {summary['front_4d_size']['mean']} / {summary['front_4d_size']['median']} / {summary['front_4d_size']['std_population']} / {summary['front_4d_size']['max']}.",
        f"- Projected HV min/mean/median/std/max: {summary['projected_hypervolume']['min']} / {summary['projected_hypervolume']['mean']} / {summary['projected_hypervolume']['median']} / {summary['projected_hypervolume']['std_population']} / {summary['projected_hypervolume']['max']}.",
        f"- Selected cluster-count distribution: `{json.dumps(summary['selected_cluster_count_distribution'], sort_keys=True)}`.",
        f"- Spearman rho n={summary['spearman_rho']['n_valid']}, undefined={summary['spearman_rho']['n_undefined']}.",
        "- Four-dimensional non-dominance, projected non-dominance, projected-HV recomputation, semantic-objective non-constancy, representative-selection reproducibility, class-partition integrity, and provenance validation: PASS.",
        "",
    ])


def main() -> int:
    output_dir = ROOT / "reports/stage3"
    records_by_subject = {subject: load_subject_records(subject) for subject in SUBJECTS}
    summaries = {subject: build_subject_summary(subject, records_by_subject[subject]) for subject in SUBJECTS}
    inventory = build_inventory(summaries)
    pilot = build_pilot_summary(records_by_subject)
    alignment = build_alignment(records_by_subject)
    if not alignment["all_pass"]:
        raise RuntimeError("Stage 2 alignment checks failed")

    inventory_json = {"subjects": inventory, "seed_ids": SEEDS, "all_pass": all(row["valid"] == 30 for row in inventory)}
    write_json(output_dir / "formal_seed_inventory.json", inventory_json)
    with (output_dir / "formal_seed_inventory.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(inventory[0]))
        writer.writeheader()
        writer.writerows(inventory)
    write_json(output_dir / "pilot_validation_summary.json", {"subjects": pilot, "all_pass": all(item["all_valid"] for item in pilot.values())})
    write_json(output_dir / "stage2_alignment_check.json", alignment)
    write_json(output_dir / "stage3_formal_validation_summary.json", {"subjects": summaries, "inventory": inventory_json, "pilot": pilot, "stage2_alignment": alignment, "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    (output_dir / "stage3_formal_validation_summary.md").write_text(markdown_summary(summaries, inventory, alignment), encoding="utf-8")
    (output_dir / "pilot_validation_summary.md").write_text("# Stage 3 pilot validation\n\n" + "\n".join(f"- {subject}: seeds 0–4 valid={value['all_valid']}; semantic range={value['semantic_objective_range']}; projected-HV range={value['projected_hypervolume_range']}; selection reproducibility={value['representative_selection_reproducible']}." for subject, value in pilot.items()) + "\n", encoding="utf-8")
    (output_dir / "stage2_alignment_check.md").write_text("# Stage 2 alignment checks\n\nAll subject checks passed for exact scope, seeds 0–29, graph/objective identity, Hypervolume bounds/reference, population/generations, and no semantic use in representative selection.\n", encoding="utf-8")
    for subject, summary in summaries.items():
        write_json(output_dir / f"{subject}_formal_summary.json", summary)
        (output_dir / f"{subject}_formal_summary.md").write_text(subject_markdown(summary), encoding="utf-8")
    print(json.dumps({"inventory": inventory_json, "pilot_all_pass": all(item["all_valid"] for item in pilot.values()), "stage2_alignment_pass": alignment["all_pass"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
