#!/usr/bin/env python3
"""Build the final selector-dependent Stage 2/Stage 3 reporting layer.

The analysis is deterministic post-processing over frozen retained fronts,
partitions, structural post-hoc metrics, and semantic graphs.  It does not run
an optimiser, regenerate an embedding or graph, or write into any formal run
directory.  Historical ``selected_solution.json`` files remain immutable raw
provenance for the maximum-modularity selector active when Stage 3 ran.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.analysis import stage3_reporting
from evo_ms.optimization.semantic_objective import (
    evaluate_semantic_objective,
    load_semantic_edges,
    semantic_total_weight,
)


SUBJECTS = ("jpetstore", "daytrader", "xerces")
STORAGE_SUBJECT = {
    "jpetstore": "jpetstore",
    "daytrader": "daytrader",
    "xerces": "xerces-j",
}
DISPLAY_SUBJECT = {
    "jpetstore": "JPetStore",
    "daytrader": "DayTrader",
    "xerces": "Xerces-J",
}
CLASS_COUNTS = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
SEEDS = tuple(range(30))
PROFILES = (
    "MODULARITY_ANCHOR",
    "BALANCE",
    "COUPLING",
    "COHESION",
    "SEMANTIC",
)
SENSITIVITY_PROFILES = PROFILES[1:]
OUTPUT_RELATIVE = Path(
    "results/stage3/cross_subject/operating_preference_analysis"
)
SCRIPT_RELATIVE = Path(
    "experiments/05_stage3_declaration_method_body/"
    "build_operating_preference_analysis.py"
)
STAGE2_CANONICAL_RELATIVE = Path(
    "results/stage2/cross_subject/operating_profile/"
    "canonical_operating_solution_per_seed.csv"
)
STAGE2_SELECTED_FSEM_RELATIVE = Path(
    "results/stage3/cross_subject/formal_statistics/"
    "formal_selected_fsemantic_per_seed.csv"
)
FORMAL_TESTS_RELATIVE = Path(
    "results/stage3/cross_subject/formal_statistics/formal_statistical_tests.csv"
)
PROJECTED_HV_RELATIVE = Path(
    "results/stage3/cross_subject/stage2_comparison/paired_per_seed.csv"
)
SSA_COMMIT = "8592d0aa49dc31dd435f20296ced485ec7a41b41"
SSA_SUMMARY_PATH = (
    "results/cross_subject/01_stage1_ssa_random_baseline/"
    "stage1_ssa_random_baseline_summary.csv"
)
SSA_MANIFEST_PATH = (
    "results/cross_subject/01_stage1_ssa_random_baseline/"
    "stage1_ssa_random_baseline_manifest.json"
)
TOL = 1e-12
ANALYSIS_VERSION = "operating-preference-analysis-v1"

METRICS = (
    "weighted_modularity",
    "coupling",
    "cohesion",
    "imbalance",
    "f_semantic",
    "cluster_count",
)
PROFILE_METRICS = METRICS + (
    "relative_modularity_loss",
    "max_cluster_ratio",
    "singleton_ratio",
    "band_size",
)
METRIC_DIRECTIONS = {
    "weighted_modularity": "higher_is_better",
    "coupling": "lower_is_better",
    "cohesion": "higher_is_better",
    "imbalance": "lower_is_better",
    "f_semantic": "lower_is_better",
    "cluster_count": "descriptive_increase_tie_decrease",
}

SELECTOR_DEFINITIONS: dict[str, dict[str, Any]] = {
    "MODULARITY_ANCHOR": {
        "profile_id": "P0",
        "role": "historical/reference modularity anchor",
        "candidate_scope": "all feasible candidates in the stage-specific pool",
        "ordering": [
            "maximum weighted_modularity",
            "minimum imbalance",
            "minimum coupling",
            "maximum cohesion",
            "minimum f_semantic",
            "lexicographic solution_id",
        ],
    },
    "BALANCE": {
        "profile_id": "P1",
        "role": "primary reporting profile",
        "candidate_scope": "common 5% relative modularity-loss band",
        "ordering": [
            "minimum imbalance",
            "maximum weighted_modularity",
            "minimum coupling",
            "maximum cohesion",
            "lexicographic solution_id",
        ],
    },
    "COUPLING": {
        "profile_id": "P2",
        "role": "descriptive preference sensitivity",
        "candidate_scope": "common 5% relative modularity-loss band",
        "ordering": [
            "minimum coupling",
            "maximum weighted_modularity",
            "minimum imbalance",
            "maximum cohesion",
            "lexicographic solution_id",
        ],
    },
    "COHESION": {
        "profile_id": "P3",
        "role": "descriptive preference sensitivity",
        "candidate_scope": "common 5% relative modularity-loss band",
        "ordering": [
            "maximum cohesion",
            "maximum weighted_modularity",
            "minimum imbalance",
            "minimum coupling",
            "lexicographic solution_id",
        ],
    },
    "SEMANTIC": {
        "profile_id": "P4",
        "role": "descriptive preference sensitivity",
        "candidate_scope": "common 5% relative modularity-loss band",
        "ordering": [
            "minimum f_semantic",
            "maximum weighted_modularity",
            "minimum imbalance",
            "minimum coupling",
            "maximum cohesion",
            "lexicographic solution_id",
        ],
    },
}


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _source_commit(path: Path) -> str:
    """Return the commit that last changed a retained source artefact."""
    return _git("log", "-1", "--format=%H", "--", _relative(path))


def _read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_csv(path, float_precision="round_trip", **kwargs)


def _sha256_bytes(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(
        index=False,
        lineterminator="\n",
        float_format="%.17g",
    ).encode("utf-8")


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _git_object_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def _stage2_run_dir(subject: str, seed: int) -> Path:
    return (
        ROOT
        / "results/stage2/subjects"
        / STORAGE_SUBJECT[subject]
        / "nsga/robustness_final_30seeds"
        / f"seed_{seed:02d}"
    )


def _stage3_run_dir(subject: str, seed: int) -> Path:
    phase = "validation" if seed == 0 else "formal"
    return (
        ROOT
        / "results/stage3/subjects"
        / STORAGE_SUBJECT[subject]
        / "declaration_method_body"
        / phase
        / f"seed_{seed:02d}"
    )


def _class_nodes(subject: str) -> pd.DataFrame:
    path = ROOT / "data/extracted" / STORAGE_SUBJECT[subject] / "class_nodes.csv"
    frame = _read_csv(path)
    if len(frame) != CLASS_COUNTS[subject]:
        raise ValueError(f"unexpected class count for {subject}: {len(frame)}")
    if frame["class_id"].astype(str).duplicated().any():
        raise ValueError(f"duplicate class IDs for {subject}")
    return frame


def _semantic_graph(subject: str, class_nodes: pd.DataFrame) -> tuple[pd.DataFrame, float, Path]:
    path = (
        ROOT
        / "data/semantic_graphs/declaration_method_body"
        / subject
        / "semantic_edges.csv"
    )
    edges = load_semantic_edges(
        path, expected_class_ids=set(class_nodes["class_id"].astype(str))
    )
    return edges, semantic_total_weight(edges), path


def _labels(value: str | Sequence[int]) -> list[int]:
    result = json.loads(value) if isinstance(value, str) else list(value)
    return [int(item) for item in result]


def _canonical_key(class_nodes: pd.DataFrame, value: str | Sequence[int]) -> tuple[int, ...]:
    labels = _labels(value)
    if len(labels) != len(class_nodes):
        raise ValueError("label-vector length differs from retained class universe")
    pairs = sorted(
        zip(class_nodes["class_id"].astype(str), labels, strict=True),
        key=lambda item: item[0],
    )
    remap: dict[int, int] = {}
    canonical: list[int] = []
    for _, label in pairs:
        if label not in remap:
            remap[label] = len(remap)
        canonical.append(remap[label])
    return tuple(canonical)


def _partition_hash(class_nodes: pd.DataFrame, value: str | Sequence[int]) -> str:
    payload = json.dumps(_canonical_key(class_nodes, value), separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _semantic_value(
    class_nodes: pd.DataFrame,
    value: str | Sequence[int],
    edges: pd.DataFrame,
    total_weight: float,
) -> float:
    labels = _labels(value)
    mapping = dict(
        zip(class_nodes["class_id"].astype(str), labels, strict=True)
    )
    return evaluate_semantic_objective(edges, mapping, total_weight=total_weight)


def _similarity(left: Sequence[int], right: Sequence[int]) -> tuple[bool, float, float]:
    left_array = np.asarray(left, dtype=int)
    right_array = np.asarray(right, dtype=int)
    if left_array.shape != right_array.shape:
        raise ValueError("partition vector shapes differ")
    def canonical(values: np.ndarray) -> tuple[int, ...]:
        remap: dict[int, int] = {}
        result: list[int] = []
        for value in values.tolist():
            key = int(value)
            if key not in remap:
                remap[key] = len(remap)
            result.append(remap[key])
        return tuple(result)
    return (
        canonical(left_array) == canonical(right_array),
        float(adjusted_rand_score(left_array, right_array)),
        float(normalized_mutual_info_score(left_array, right_array)),
    )


def _as_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes"}


def _stage2_candidates(
    source_paths: set[Path],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        class_nodes = _class_nodes(subject)
        class_path = ROOT / "data/extracted" / STORAGE_SUBJECT[subject] / "class_nodes.csv"
        edges, total_weight, graph_path = _semantic_graph(subject, class_nodes)
        source_paths.update({class_path, graph_path})
        class_order = class_nodes["class_id"].astype(str).tolist()
        for seed in SEEDS:
            run_dir = _stage2_run_dir(subject, seed)
            front_path = run_dir / "pareto_front.csv"
            label_path = run_dir / "pareto_labels.csv.xz"
            source_paths.update({front_path, label_path})
            front = _read_csv(front_path)
            labels_long = _read_csv(label_path)
            if front["solution_id"].astype(str).duplicated().any():
                raise ValueError(f"duplicate Stage 2 solution ID: {front_path}")
            front_ids = set(front["solution_id"].astype(str))
            label_ids = set(labels_long["solution_id"].astype(str))
            if front_ids != label_ids:
                raise ValueError(f"Stage 2 front/label solution mismatch: {run_dir}")
            labels_by_solution: dict[str, dict[str, int]] = {}
            for solution_id, group in labels_long.groupby("solution_id", sort=False):
                if len(group) != len(class_nodes):
                    raise ValueError(f"incomplete Stage 2 labels: {run_dir}/{solution_id}")
                mapping = dict(
                    zip(
                        group["class_id"].astype(str),
                        group["cluster_id"].astype(int),
                        strict=True,
                    )
                )
                if set(mapping) != set(class_order):
                    raise ValueError(f"Stage 2 class-scope mismatch: {run_dir}/{solution_id}")
                labels_by_solution[str(solution_id)] = mapping
            front_sha = _sha256(front_path)
            label_sha = _sha256(label_path)
            for front_index, record in enumerate(front.to_dict("records")):
                solution_id = str(record["solution_id"])
                vector = _labels(record["label_vector"])
                retained = [labels_by_solution[solution_id][class_id] for class_id in class_order]
                if vector != retained:
                    raise ValueError(f"Stage 2 label-vector mismatch: {run_dir}/{solution_id}")
                semantic = evaluate_semantic_objective(
                    edges, labels_by_solution[solution_id], total_weight=total_weight
                )
                rows.append(
                    {
                        "subject": subject,
                        "seed": seed,
                        "stage": "stage2",
                        "solution_id": solution_id,
                        "source_solution_id": solution_id,
                        "source_front_row_index_zero_based": front_index,
                        "stage3_original_four_objective_row_index_zero_based": np.nan,
                        "weighted_modularity": float(record["weighted_modularity"]),
                        "coupling": float(record["coupling"]),
                        "cohesion": float(record["cohesion"]),
                        "imbalance": float(record["imbalance"]),
                        "f_semantic": float(semantic),
                        "cluster_count": int(record["cluster_count"]),
                        "max_cluster_ratio": float(record["max_cluster_ratio"]),
                        "singleton_ratio": float(record["singleton_ratio"]),
                        "feasible": _as_bool(record["feasible"]),
                        "label_vector": json.dumps(vector, separators=(",", ":")),
                        "canonical_partition_sha256": _partition_hash(class_nodes, vector),
                        "source_front": _relative(front_path),
                        "source_front_sha256": front_sha,
                        "source_labels": _relative(label_path),
                        "source_labels_sha256": label_sha,
                        "semantic_graph": _relative(graph_path),
                        "semantic_graph_sha256": _sha256(graph_path),
                        "semantic_total_weight": total_weight,
                    }
                )
    frame = pd.DataFrame(rows).sort_values(
        ["subject", "seed", "source_front_row_index_zero_based"], kind="stable"
    ).reset_index(drop=True)
    if len(frame) != 8815:
        raise ValueError(f"unexpected retained Stage 2 candidate count: {len(frame)}")

    known_path = ROOT / STAGE2_SELECTED_FSEM_RELATIVE
    source_paths.add(known_path)
    known = _read_csv(known_path)
    known = known.loc[:, [
        "subject", "seed", "stage2_solution_id", "stage2_f_semantic"
    ]].rename(columns={"stage2_solution_id": "solution_id"})
    selected = frame.merge(known, on=["subject", "seed", "solution_id"], how="inner")
    if len(selected) != 90:
        raise ValueError("Stage 2 f_semantic cross-check did not cover 90 selections")
    errors = np.abs(
        selected["f_semantic"].to_numpy(dtype=float)
        - selected["stage2_f_semantic"].to_numpy(dtype=float)
    )
    if np.any(errors > TOL):
        raise ValueError("new Stage 2 front f_semantic disagrees with retained selected values")
    validation = {
        "status": "NEWLY_COMPUTED",
        "candidate_count": len(frame),
        "selected_solution_crosscheck_count": len(selected),
        "selected_solution_crosscheck_max_abs_error": float(errors.max()),
        "selected_solution_crosscheck_atol": TOL,
        "passed": True,
    }
    return frame, validation


def _stage3_candidates(source_paths: set[Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        class_nodes = _class_nodes(subject)
        class_path = ROOT / "data/extracted" / STORAGE_SUBJECT[subject] / "class_nodes.csv"
        _, _, graph_path = _semantic_graph(subject, class_nodes)
        source_paths.update({class_path, graph_path})
        for seed in SEEDS:
            run_dir = _stage3_run_dir(subject, seed)
            projected_path = run_dir / "projected_front_3d.csv"
            four_path = run_dir / "pareto_front_4d.csv"
            posthoc_path = run_dir / "posthoc_metrics.csv"
            historical_path = run_dir / "selected_solution.json"
            source_paths.update(
                {projected_path, four_path, posthoc_path, historical_path}
            )
            projected = _read_csv(projected_path)
            four = _read_csv(four_path)
            posthoc = _read_csv(posthoc_path)
            if projected["solution_id"].astype(str).duplicated().any():
                raise ValueError(f"duplicate projected solution ID: {projected_path}")
            four_index = {
                str(value): index
                for index, value in enumerate(four["solution_id"].astype(str))
            }
            four_by_id = {
                str(record["solution_id"]): record for record in four.to_dict("records")
            }
            posthoc_by_id = {
                str(record["solution_id"]): record
                for record in posthoc.to_dict("records")
            }
            projected_sha = _sha256(projected_path)
            for projected_index, record in enumerate(projected.to_dict("records")):
                solution_id = str(record["solution_id"])
                original_id = str(record["original_solution_id"])
                if original_id not in four_by_id or solution_id not in posthoc_by_id:
                    raise ValueError(f"unmapped projected solution: {projected_path}/{solution_id}")
                four_record = four_by_id[original_id]
                semantic = float(record["original_f_semantic"])
                if abs(semantic - float(four_record["f_semantic"])) > TOL:
                    raise ValueError(f"projected/four-dimensional f_semantic mismatch: {run_dir}")
                metrics = posthoc_by_id[solution_id]
                vector = _labels(record["label_vector"])
                rows.append(
                    {
                        "subject": subject,
                        "seed": seed,
                        "stage": "stage3",
                        "solution_id": solution_id,
                        "source_solution_id": original_id,
                        "source_front_row_index_zero_based": projected_index,
                        "stage3_original_four_objective_row_index_zero_based": four_index[original_id],
                        "weighted_modularity": float(metrics["weighted_modularity"]),
                        "coupling": float(record["coupling"]),
                        "cohesion": float(record["cohesion"]),
                        "imbalance": float(record["imbalance"]),
                        "f_semantic": semantic,
                        "cluster_count": int(metrics["cluster_count"]),
                        "max_cluster_ratio": float(metrics["max_cluster_ratio"]),
                        "singleton_ratio": float(metrics["singleton_ratio"]),
                        "feasible": _as_bool(record["feasible"]),
                        "label_vector": json.dumps(vector, separators=(",", ":")),
                        "canonical_partition_sha256": _partition_hash(class_nodes, vector),
                        "source_front": _relative(projected_path),
                        "source_front_sha256": projected_sha,
                        "source_labels": _relative(four_path),
                        "source_labels_sha256": _sha256(four_path),
                        "semantic_graph": _relative(graph_path),
                        "semantic_graph_sha256": _sha256(graph_path),
                        "semantic_total_weight": np.nan,
                    }
                )
    return pd.DataFrame(rows).sort_values(
        ["subject", "seed", "source_front_row_index_zero_based"], kind="stable"
    ).reset_index(drop=True)


def _ordering(profile: str, row: Mapping[str, Any]) -> tuple[Any, ...]:
    q = float(row["weighted_modularity"])
    coupling = float(row["coupling"])
    cohesion = float(row["cohesion"])
    imbalance = float(row["imbalance"])
    semantic = float(row["f_semantic"])
    solution_id = str(row["solution_id"])
    if profile == "MODULARITY_ANCHOR":
        return (-q, imbalance, coupling, -cohesion, semantic, solution_id)
    if profile == "BALANCE":
        return (imbalance, -q, coupling, -cohesion, solution_id)
    if profile == "COUPLING":
        return (coupling, -q, imbalance, -cohesion, solution_id)
    if profile == "COHESION":
        return (-cohesion, -q, imbalance, coupling, solution_id)
    if profile == "SEMANTIC":
        return (semantic, -q, imbalance, coupling, -cohesion, solution_id)
    raise ValueError(profile)


def _materialise_profiles(
    candidates: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_rows: list[dict[str, Any]] = []
    band_rows: list[dict[str, Any]] = []
    for (subject, seed, stage), group in candidates.groupby(
        ["subject", "seed", "stage"], sort=False
    ):
        feasible = group.loc[group["feasible"].map(_as_bool)].copy()
        if feasible.empty:
            raise ValueError(f"no feasible candidates for {subject}/{seed}/{stage}")
        q_best = float(feasible["weighted_modularity"].max())
        if q_best <= 0.0:
            raise ValueError(f"non-positive Q_best for {subject}/{seed}/{stage}")
        feasible["relative_modularity_loss"] = (
            q_best - feasible["weighted_modularity"].astype(float)
        ) / abs(q_best)
        band = feasible.loc[
            feasible["relative_modularity_loss"] <= 0.05 + TOL
        ].copy()
        if band.empty:
            raise ValueError(f"empty 5% band for {subject}/{seed}/{stage}")
        if not np.array_equal(
            (band["weighted_modularity"].to_numpy(dtype=float) >= 0.95 * q_best - TOL),
            np.ones(len(band), dtype=bool),
        ):
            raise ValueError("positive-Q 5% band equivalence failed")
        selected_by_profile: dict[str, Mapping[str, Any]] = {}
        feasible_records = feasible.to_dict("records")
        band_records = band.to_dict("records")
        for profile in PROFILES:
            pool = feasible_records if profile == "MODULARITY_ANCHOR" else band_records
            selected = min(pool, key=lambda row: _ordering(profile, row))
            selected_again = min(pool, key=lambda row: _ordering(profile, row))
            if str(selected["solution_id"]) != str(selected_again["solution_id"]):
                raise ValueError("non-deterministic selector result")
            selected_by_profile[profile] = selected
            loss = (q_best - float(selected["weighted_modularity"])) / abs(q_best)
            if profile != "MODULARITY_ANCHOR" and loss > 0.05 + TOL:
                raise ValueError("preference selection outside common band")
            selected_rows.append(
                {
                    "subject": subject,
                    "seed": int(seed),
                    "stage": stage,
                    "profile": profile,
                    "profile_id": SELECTOR_DEFINITIONS[profile]["profile_id"],
                    "profile_role": SELECTOR_DEFINITIONS[profile]["role"],
                    "source_front": selected["source_front"],
                    "selected_solution_id": selected["solution_id"],
                    "weighted_modularity": float(selected["weighted_modularity"]),
                    "Q_best": q_best,
                    "relative_modularity_loss": loss,
                    "band_size": len(band),
                    "coupling": float(selected["coupling"]),
                    "cohesion": float(selected["cohesion"]),
                    "imbalance": float(selected["imbalance"]),
                    "f_semantic": float(selected["f_semantic"]),
                    "cluster_count": int(selected["cluster_count"]),
                    "max_cluster_ratio": float(selected["max_cluster_ratio"]),
                    "singleton_ratio": float(selected["singleton_ratio"]),
                    "feasible": _as_bool(selected["feasible"]),
                    "canonical_partition_identifier": (
                        "sha256:" + str(selected["canonical_partition_sha256"])
                    ),
                    "canonical_partition_sha256": selected[
                        "canonical_partition_sha256"
                    ],
                    "original_source_solution_id": selected["source_solution_id"],
                    "source_front_row_index_zero_based": int(
                        selected["source_front_row_index_zero_based"]
                    ),
                    "stage3_original_four_objective_row_index_zero_based": selected[
                        "stage3_original_four_objective_row_index_zero_based"
                    ],
                    "label_vector": selected["label_vector"],
                }
            )
        selected_ids = {
            profile: str(row["solution_id"])
            for profile, row in selected_by_profile.items()
        }
        for record in band_records:
            band_rows.append(
                {
                    "subject": subject,
                    "seed": int(seed),
                    "stage": stage,
                    "solution_id": record["solution_id"],
                    "weighted_modularity": float(record["weighted_modularity"]),
                    "Q_best": q_best,
                    "relative_modularity_loss": float(
                        record["relative_modularity_loss"]
                    ),
                    "coupling": float(record["coupling"]),
                    "cohesion": float(record["cohesion"]),
                    "imbalance": float(record["imbalance"]),
                    "f_semantic": float(record["f_semantic"]),
                    "cluster_count": int(record["cluster_count"]),
                    "canonical_partition_sha256": record[
                        "canonical_partition_sha256"
                    ],
                    **{
                        f"selected_{profile.lower()}": (
                            str(record["solution_id"]) == selected_ids[profile]
                        )
                        for profile in PROFILES
                    },
                }
            )
    selected = pd.DataFrame(selected_rows).sort_values(
        ["subject", "seed", "stage", "profile_id"], kind="stable"
    ).reset_index(drop=True)
    bands = pd.DataFrame(band_rows).sort_values(
        ["subject", "seed", "stage", "solution_id"], kind="stable"
    ).reset_index(drop=True)
    if len(selected) != 900:
        raise ValueError(f"expected 900 selected profile rows, got {len(selected)}")
    return selected, bands


def _validate_reference_selections(
    selected: pd.DataFrame,
    stage3_candidates: pd.DataFrame,
    source_paths: set[Path],
) -> dict[str, Any]:
    stage2_path = ROOT / STAGE2_CANONICAL_RELATIVE
    source_paths.add(stage2_path)
    stage2_ref = _read_csv(stage2_path)
    stage2_ref["subject"] = stage2_ref["subject"].replace({"xerces-j": "xerces"})
    balance = selected.loc[selected["profile"] == "BALANCE"]
    s2 = balance.loc[balance["stage"] == "stage2"].merge(
        stage2_ref[["subject", "seed", "solution_id", "label_vector"]],
        on=["subject", "seed"],
        suffixes=("", "_reference"),
    )

    # Recompute the Stage 3 BALANCE choice directly from every frozen projected
    # candidate pool.  This validation deliberately does not call _ordering or
    # _materialise_profiles, so it independently checks the current selector:
    # 5% from front-best Q, then imbalance/Q/coupling/cohesion/solution ID.
    stage3_expected_rows: list[dict[str, Any]] = []
    for (subject, seed), group in stage3_candidates.groupby(
        ["subject", "seed"], sort=False
    ):
        feasible = group.loc[group["feasible"].map(_as_bool)].copy()
        q_best = float(feasible["weighted_modularity"].max())
        feasible["relative_modularity_loss"] = (
            q_best - feasible["weighted_modularity"].astype(float)
        ) / abs(q_best)
        band = feasible.loc[
            feasible["relative_modularity_loss"] <= 0.05 + TOL
        ].copy()
        expected = band.sort_values(
            [
                "imbalance",
                "weighted_modularity",
                "coupling",
                "cohesion",
                "solution_id",
            ],
            ascending=[True, False, True, False, True],
            kind="stable",
        ).iloc[0]
        stage3_expected_rows.append(
            {
                "subject": subject,
                "seed": int(seed),
                "expected_solution_id": str(expected["solution_id"]),
                "expected_partition_sha256": str(
                    expected["canonical_partition_sha256"]
                ),
            }
        )
    stage3_expected = pd.DataFrame(stage3_expected_rows)
    s3 = balance.loc[balance["stage"] == "stage3"].merge(
        stage3_expected,
        on=["subject", "seed"],
        validate="one_to_one",
    )
    if len(s2) != 90 or len(s3) != 90:
        raise ValueError("BALANCE reference validation did not cover all 90 runs")
    if not (s2["selected_solution_id"].astype(str) == s2["solution_id"].astype(str)).all():
        raise ValueError("Stage 2 BALANCE does not reproduce canonical operating profile")
    stage3_id_matches = (
        s3["selected_solution_id"].astype(str)
        == s3["expected_solution_id"].astype(str)
    )
    stage3_partition_matches = (
        s3["canonical_partition_sha256"].astype(str)
        == s3["expected_partition_sha256"].astype(str)
    )
    if not (stage3_id_matches & stage3_partition_matches).all():
        raise ValueError(
            "Stage 3 BALANCE does not reproduce the direct frozen-front 5% rule"
        )

    p0 = selected.loc[
        (selected["stage"] == "stage3")
        & (selected["profile"] == "MODULARITY_ANCHOR")
    ]
    historical_ids: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        for seed in SEEDS:
            path = _stage3_run_dir(subject, seed) / "selected_solution.json"
            source_paths.add(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            historical_ids.append(
                {
                    "subject": subject,
                    "seed": seed,
                    "historical_solution_id": str(payload["selected_solution_id"]),
                }
            )
    historical = pd.DataFrame(historical_ids)
    p0_check = p0.merge(historical, on=["subject", "seed"])
    if not (
        p0_check["selected_solution_id"].astype(str)
        == p0_check["historical_solution_id"].astype(str)
    ).all():
        raise ValueError("Stage 3 MODULARITY_ANCHOR does not reproduce historical runtime")
    return {
        "stage2_balance_reference_rows": len(s2),
        "stage2_balance_exact_solution_id_matches": int(
            (s2["selected_solution_id"].astype(str) == s2["solution_id"].astype(str)).sum()
        ),
        "stage3_balance_reference_rows": len(s3),
        "stage3_balance_exact_solution_id_matches": int(
            stage3_id_matches.sum()
        ),
        "stage3_balance_exact_partition_matches": int(
            stage3_partition_matches.sum()
        ),
        "stage3_balance_validation_source": (
            "direct recomputation from frozen projected_front_3d.csv and "
            "posthoc_metrics.csv candidate pools"
        ),
        "stage3_maxq_historical_rows": len(p0_check),
        "stage3_maxq_exact_solution_id_matches": int(
            (
                p0_check["selected_solution_id"].astype(str)
                == p0_check["historical_solution_id"].astype(str)
            ).sum()
        ),
        "passed": True,
    }


def _profile_summary(selected: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (subject, stage, profile), group in selected.groupby(
        ["subject", "stage", "profile"], sort=False
    ):
        row: dict[str, Any] = {
            "subject": subject,
            "stage": stage,
            "profile": profile,
            "profile_id": SELECTOR_DEFINITIONS[profile]["profile_id"],
            "n_seeds": len(group),
        }
        for metric in PROFILE_METRICS:
            values = group[metric].to_numpy(dtype=float)
            row[f"median_{metric}"] = float(np.median(values))
        for metric in ("cohesion", "imbalance", "f_semantic", "cluster_count"):
            values = group[metric].to_numpy(dtype=float)
            q1, q3 = np.quantile(values, [0.25, 0.75])
            row[f"q1_{metric}"] = float(q1)
            row[f"q3_{metric}"] = float(q3)
            row[f"iqr_{metric}"] = float(q3 - q1)
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["subject", "stage", "profile_id"], kind="stable"
    ).reset_index(drop=True)


def _profile_pairs() -> tuple[tuple[str, str], ...]:
    return (
        ("BALANCE", "COUPLING"),
        ("BALANCE", "COHESION"),
        ("BALANCE", "SEMANTIC"),
        ("COUPLING", "COHESION"),
        ("COUPLING", "SEMANTIC"),
        ("COHESION", "SEMANTIC"),
    )


def _preference_similarity(selected: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        for stage in ("stage2", "stage3"):
            base = selected.loc[
                (selected["subject"] == subject) & (selected["stage"] == stage)
            ]
            for left_name, right_name in _profile_pairs():
                left = base.loc[base["profile"] == left_name].sort_values("seed")
                right = base.loc[base["profile"] == right_name].sort_values("seed")
                similarities = [
                    _similarity(_labels(a), _labels(b))
                    for a, b in zip(left["label_vector"], right["label_vector"], strict=True)
                ]
                same = [value[0] for value in similarities]
                rows.append(
                    {
                        "subject": subject,
                        "stage": stage,
                        "left_profile": left_name,
                        "right_profile": right_name,
                        "n_pairs": 30,
                        "same_partition_count": int(sum(same)),
                        "different_partition_count": int(30 - sum(same)),
                        "median_ari": float(np.median([value[1] for value in similarities])),
                        "median_nmi": float(np.median([value[2] for value in similarities])),
                        "analysis_status": "DESCRIPTIVE",
                    }
                )
    return pd.DataFrame(rows)


def _snapped_delta(left: pd.Series, right: pd.Series, metric: str) -> tuple[float, float, str]:
    raw = float(right[metric]) - float(left[metric])
    same_partition = (
        str(left["canonical_partition_sha256"])
        == str(right["canonical_partition_sha256"])
    )
    if same_partition and abs(raw) > TOL:
        raise ValueError(
            f"same partition has materially different {metric}: "
            f"{left['subject']}/{left['seed']}/{left['profile']}"
        )
    if same_partition and raw != 0.0:
        return raw, 0.0, "canonical_partition_equivalent"
    if same_partition:
        return raw, 0.0, "canonical_partition_equivalent_exact_zero"
    if 0.0 < abs(raw) < TOL:
        return raw, 0.0, "absolute_delta_below_1e-12"
    return raw, raw, "not_snapped"


def _preference_deltas(selected: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        for stage in ("stage2", "stage3"):
            base = selected.loc[
                (selected["subject"] == subject)
                & (selected["stage"] == stage)
                & (selected["profile"] == "BALANCE")
            ].set_index("seed")
            for alternative in ("COUPLING", "COHESION", "SEMANTIC"):
                other = selected.loc[
                    (selected["subject"] == subject)
                    & (selected["stage"] == stage)
                    & (selected["profile"] == alternative)
                ].set_index("seed")
                row: dict[str, Any] = {
                    "subject": subject,
                    "stage": stage,
                    "baseline_profile": "BALANCE",
                    "alternative_profile": alternative,
                    "n_pairs": 30,
                    "delta_definition": "alternative minus BALANCE",
                    "analysis_status": "DESCRIPTIVE",
                }
                for metric in METRICS:
                    deltas = [
                        _snapped_delta(base.loc[seed], other.loc[seed], metric)[1]
                        for seed in SEEDS
                    ]
                    row[f"median_delta_{metric}"] = float(np.median(deltas))
                rows.append(row)
    frame = pd.DataFrame(rows)
    frame["direction_note"] = (
        "positive delta means alternative has higher value; higher is favourable only "
        "for weighted_modularity and cohesion, lower is favourable for coupling, "
        "imbalance, and f_semantic; cluster_count has no quality direction"
    )
    return frame


def _same_preference(
    selected: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    floating_rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        for profile in SENSITIVITY_PROFILES:
            stage2 = selected.loc[
                (selected["subject"] == subject)
                & (selected["stage"] == "stage2")
                & (selected["profile"] == profile)
            ].sort_values("seed").set_index("seed")
            stage3 = selected.loc[
                (selected["subject"] == subject)
                & (selected["stage"] == "stage3")
                & (selected["profile"] == profile)
            ].sort_values("seed").set_index("seed")
            sims = [
                _similarity(
                    _labels(stage2.loc[seed, "label_vector"]),
                    _labels(stage3.loc[seed, "label_vector"]),
                )
                for seed in SEEDS
            ]
            same_count = int(sum(value[0] for value in sims))
            median_ari = float(np.median([value[1] for value in sims]))
            median_nmi = float(np.median([value[2] for value in sims]))
            for metric in METRICS:
                raw_deltas: list[float] = []
                deltas: list[float] = []
                for seed in SEEDS:
                    raw, snapped, reason = _snapped_delta(
                        stage2.loc[seed], stage3.loc[seed], metric
                    )
                    raw_deltas.append(raw)
                    deltas.append(snapped)
                    required_jpet_balance_tie = (
                        subject == "jpetstore"
                        and profile == "BALANCE"
                        and metric == "f_semantic"
                        and seed in {3, 15, 29}
                    )
                    if 0.0 < abs(raw) < TOL or required_jpet_balance_tie:
                        floating_rows.append(
                            {
                                "subject": subject,
                                "seed": seed,
                                "profile": profile,
                                "metric": metric,
                                "raw_delta_stage3_minus_stage2": raw,
                                "snapped_delta": snapped,
                                "same_canonical_partition": (
                                    stage2.loc[seed, "canonical_partition_sha256"]
                                    == stage3.loc[seed, "canonical_partition_sha256"]
                                ),
                                "snap_reason": reason,
                            }
                        )
                stage2_values = stage2[metric].to_numpy(dtype=float)
                stage3_values = stage3[metric].to_numpy(dtype=float)
                delta_array = np.asarray(deltas, dtype=float)
                direction = METRIC_DIRECTIONS[metric]
                if direction == "higher_is_better":
                    better = int(np.sum(delta_array > 0.0))
                    worse = int(np.sum(delta_array < 0.0))
                    increase = better
                    decrease = worse
                elif direction == "lower_is_better":
                    better = int(np.sum(delta_array < 0.0))
                    worse = int(np.sum(delta_array > 0.0))
                    increase = worse
                    decrease = better
                else:
                    better = np.nan
                    worse = np.nan
                    increase = int(np.sum(delta_array > 0.0))
                    decrease = int(np.sum(delta_array < 0.0))
                rows.append(
                    {
                        "subject": subject,
                        "profile": profile,
                        "metric": metric,
                        "n_pairs": 30,
                        "stage2_median": float(np.median(stage2_values)),
                        "stage3_median": float(np.median(stage3_values)),
                        "median_paired_delta_stage3_minus_stage2": float(
                            np.median(delta_array)
                        ),
                        "better_count": better,
                        "tie_count": int(np.sum(delta_array == 0.0)),
                        "worse_count": worse,
                        "increase_count": increase,
                        "decrease_count": decrease,
                        "comparison_direction": direction,
                        "median_ari": median_ari,
                        "median_nmi": median_nmi,
                        "stage2_equals_stage3_count": same_count,
                        "analysis_status": (
                            "CONFIRMATORY_FAMILY_COMPONENT"
                            if profile == "BALANCE" and metric == "f_semantic"
                            else "DESCRIPTIVE"
                        ),
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(floating_rows)


def _balance_formal_statistics(selected: pd.DataFrame) -> pd.DataFrame:
    retained = _read_csv(ROOT / FORMAL_TESTS_RELATIVE)
    hv_rows = retained.loc[retained["metric"] == "projected_hypervolume"].copy()
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        hv = hv_rows.loc[hv_rows["subject"] == subject]
        if len(hv) != 1:
            raise ValueError(f"missing retained projected-HV row for {subject}")
        rows.append(hv.iloc[0].to_dict())
        s2 = selected.loc[
            (selected["subject"] == subject)
            & (selected["stage"] == "stage2")
            & (selected["profile"] == "BALANCE")
        ].sort_values("seed").set_index("seed")
        s3 = selected.loc[
            (selected["subject"] == subject)
            & (selected["stage"] == "stage3")
            & (selected["profile"] == "BALANCE")
        ].sort_values("seed").set_index("seed")
        left = s2["f_semantic"].to_numpy(dtype=float)
        right = s3["f_semantic"].to_numpy(dtype=float).copy()
        for index, seed in enumerate(SEEDS):
            _, snapped, _ = _snapped_delta(s2.loc[seed], s3.loc[seed], "f_semantic")
            if snapped == 0.0:
                right[index] = left[index]
        rows.append(
            stage3_reporting._formal_row(
                subject,
                "selected_f_semantic",
                left,
                right,
                "lower_is_better",
                "stage2_balance_5pct_common_band",
                "stage3_balance_5pct_common_band",
                (
                    f"{OUTPUT_RELATIVE.as_posix()}/04_selected_profiles_per_seed.csv; "
                    "data/semantic_graphs/declaration_method_body/<subject>/semantic_edges.csv"
                ),
            )
        )
    frame = pd.DataFrame(rows)
    frame["holm_adjusted_p_value"] = stage3_reporting.holm_adjust(
        frame["raw_p_value"].astype(float).tolist()
    )
    frame["corrected_significant"] = frame["holm_adjusted_p_value"] <= 0.05
    frame["correction_family"] = "six confirmatory rows only"
    frame["tie_policy"] = (
        "canonical-partition equivalence and absolute paired delta below 1e-12 "
        "are reported as exact ties"
    )
    return frame


def _maxq_reference(selected: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        for stage in ("stage2", "stage3"):
            p0 = selected.loc[
                (selected["subject"] == subject)
                & (selected["stage"] == stage)
                & (selected["profile"] == "MODULARITY_ANCHOR")
            ].sort_values("seed").set_index("seed")
            p1 = selected.loc[
                (selected["subject"] == subject)
                & (selected["stage"] == stage)
                & (selected["profile"] == "BALANCE")
            ].sort_values("seed").set_index("seed")
            sims = [
                _similarity(
                    _labels(p0.loc[seed, "label_vector"]),
                    _labels(p1.loc[seed, "label_vector"]),
                )
                for seed in SEEDS
            ]
            row: dict[str, Any] = {
                "subject": subject,
                "stage": stage,
                "reference_profile": "MODULARITY_ANCHOR",
                "comparison_profile": "BALANCE",
                "reference_label": "historical/reference modularity anchor",
                "n_pairs": 30,
                "same_partition_count": int(sum(value[0] for value in sims)),
                "median_ari": float(np.median([value[1] for value in sims])),
                "median_nmi": float(np.median([value[2] for value in sims])),
                "delta_definition": "BALANCE minus MODULARITY_ANCHOR",
            }
            for metric in METRICS:
                row[f"median_delta_{metric}"] = float(
                    np.median(
                        [
                            _snapped_delta(p0.loc[seed], p1.loc[seed], metric)[1]
                            for seed in SEEDS
                        ]
                    )
                )
            rows.append(row)
    return pd.DataFrame(rows)


def _xerces_diagnostic(selected: pd.DataFrame) -> pd.DataFrame:
    frame = selected.loc[
        (selected["subject"] == "xerces") & (selected["stage"] == "stage3")
    ]
    metrics = (
        "weighted_modularity",
        "coupling",
        "cohesion",
        "imbalance",
        "f_semantic",
        "cluster_count",
        "max_cluster_ratio",
        "singleton_ratio",
        "band_size",
    )
    rows: list[dict[str, Any]] = []
    for profile in PROFILES:
        group = frame.loc[frame["profile"] == profile]
        row: dict[str, Any] = {
            "subject": "xerces",
            "stage": "stage3",
            "profile": profile,
            "n_seeds": len(group),
        }
        for metric in metrics:
            values = group[metric].to_numpy(dtype=float)
            q1, q3 = np.quantile(values, [0.25, 0.75])
            row[f"median_{metric}"] = float(np.median(values))
            row[f"q1_{metric}"] = float(q1)
            row[f"q3_{metric}"] = float(q3)
            row[f"iqr_{metric}"] = float(q3 - q1)
            row[f"min_{metric}"] = float(np.min(values))
            row[f"max_{metric}"] = float(np.max(values))
        rows.append(row)
    return pd.DataFrame(rows)


def _existing_hv_ssa_references(source_paths: set[Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        path = (
            ROOT
            / "results/stage2/subjects"
            / STORAGE_SUBJECT[subject]
            / "nsga/robustness_final_30seeds/raw_runs.csv"
        )
        source_paths.add(path)
        frame = _read_csv(path).sort_values("seed")
        if len(frame) != 30:
            raise ValueError(f"Stage 2 HV retained row count is not 30: {path}")
        for record in frame.to_dict("records"):
            rows.append(
                {
                    "result_family": "stage2_hypervolume",
                    "subject": subject,
                    "seed": int(record["seed"]),
                    "front_hypervolume": float(record["hypervolume"]),
                    "leiden_only_hypervolume": float(record["hv_leiden_only"]),
                    "hypervolume_gain_over_leiden": float(
                        record["hv_gain_over_leiden"]
                    ),
                    "ssa_observed_overlap": np.nan,
                    "ssa_observed_novelty": np.nan,
                    "ssa_random_mean_overlap": np.nan,
                    "ssa_delta_random": np.nan,
                    "source": _relative(path),
                    "source_commit": _source_commit(path),
                    "source_sha256": _sha256(path),
                    "copy_status": "retained_per_seed_value_copied_not_recomputed",
                }
            )
    ssa_bytes = _git_object_bytes(SSA_COMMIT, SSA_SUMMARY_PATH)
    ssa_manifest = _git_object_bytes(SSA_COMMIT, SSA_MANIFEST_PATH)
    ssa = pd.read_csv(StringIO(ssa_bytes.decode("utf-8")), float_precision="round_trip")
    name_map = {"xerces-j": "xerces", "jpetstore": "jpetstore", "daytrader": "daytrader"}
    for record in ssa.to_dict("records"):
        rows.append(
            {
                "result_family": "stage1_ssa_random_overlap",
                "subject": name_map[str(record["subject"])],
                "seed": np.nan,
                "front_hypervolume": np.nan,
                "leiden_only_hypervolume": np.nan,
                "hypervolume_gain_over_leiden": np.nan,
                "ssa_observed_overlap": float(record["observed_overlap"]),
                "ssa_observed_novelty": float(record["observed_novelty"]),
                "ssa_random_mean_overlap": float(record["random_mean_overlap"]),
                "ssa_delta_random": float(record["delta_random"]),
                "source": f"git:{SSA_COMMIT}:{SSA_SUMMARY_PATH}",
                "source_commit": SSA_COMMIT,
                "source_sha256": _sha256_bytes(ssa_bytes),
                "source_manifest": f"git:{SSA_COMMIT}:{SSA_MANIFEST_PATH}",
                "source_manifest_sha256": _sha256_bytes(ssa_manifest),
                "copy_status": "validated_frozen_summary_value_copied_not_recomputed",
            }
        )
    return pd.DataFrame(rows)


def _stale_inventory() -> pd.DataFrame:
    replacement = OUTPUT_RELATIVE.as_posix()
    rows = [
        {
            "path": "results/stage3/subjects/<subject>/declaration_method_body/{validation,formal}/seed_*/{selected_solution.json,selected_partition.csv}",
            "status": "CURRENT_RAW_PROVENANCE",
            "reason": "immutable runtime output recording the historical maximum-modularity selection",
            "replacement": "not replaced; cite only as historical runtime provenance",
        },
        {
            "path": "results/stage3/subjects/<subject>/declaration_method_body/{validation,formal}/seed_*/{pareto_front_4d.csv,projected_front_3d.csv,posthoc_metrics.csv,partition_labels.csv}",
            "status": "CURRENT_RAW_PROVENANCE",
            "reason": "frozen candidate populations and metrics consumed by current post-processing",
            "replacement": "not replaced",
        },
        {
            "path": "results/stage3/cross_subject/formal_statistics/formal_selected_fsemantic_per_seed.csv",
            "status": "SUPERSEDED_MAXQ_REPORTING",
            "reason": "Stage 3 selected values use historical runtime maximum-modularity selections",
            "replacement": f"{replacement}/04_selected_profiles_per_seed.csv",
        },
        {
            "path": "results/stage3/cross_subject/formal_statistics/formal_partition_similarity_*.csv",
            "status": "SUPERSEDED_MAXQ_REPORTING",
            "reason": "selected-partition comparisons use historical runtime selections",
            "replacement": f"{replacement}/08_stage2_stage3_same_preference.csv",
        },
        {
            "path": "results/stage3/cross_subject/formal_statistics/formal_statistical_tests.csv",
            "status": "SUPERSEDED_MAXQ_REPORTING",
            "reason": "projected-HV rows remain valid, but selected-f_semantic rows use MAX-Q Stage 3 selection",
            "replacement": f"{replacement}/09_balance_primary_statistics.csv",
        },
        {
            "path": "docs/stage3/findings/chapter4_3_data_pack.md",
            "status": "SUPERSEDED_MAXQ_REPORTING",
            "reason": "historical Chapter-facing data pack describes runtime MAX-Q selections",
            "replacement": f"{replacement}/14_validation_report.md",
        },
        {
            "path": "results/stage3/cross_subject/stage2_comparison/",
            "status": "SUPERSEDED_MAXQ_REPORTING",
            "reason": "selected-solution columns read historical Stage 3 runtime selection",
            "replacement": f"{replacement}/08_stage2_stage3_same_preference.csv",
        },
        {
            "path": "results/stage3/cross_subject/preference_analysis/",
            "status": "SUPERSEDED_MAXQ_REPORTING",
            "reason": "older semantic-preference response used MAX-Q Stage 3 baseline and a different budget reference",
            "replacement": f"{replacement}/06_preference_partition_similarity.csv and 07_preference_metric_deltas.csv",
        },
        {
            "path": "results/stage3/cross_subject/selector_5pct_canonical/",
            "status": "SUPERSEDED_5PCT_TIE_DEFECT",
            "reason": "temporary BALANCE-only correction did not snap machine-level paired ties",
            "replacement": replacement + "/",
        },
        {
            "path": "reports/figures/data/cross_stage/cross_stage_partition_similarity.csv",
            "status": "SUPERSEDED_MAXQ_REPORTING",
            "reason": "selector-dependent cross-stage figure data predates the final BALANCE reporting contract",
            "replacement": f"{replacement}/16_figure_balance_cross_stage.csv",
        },
        {
            "path": "results/stage3/final_dissertation_data_export/",
            "status": "LEGACY_UNKNOWN",
            "reason": "anticipated stale export path is not present at the source HEAD",
            "replacement": replacement + "/",
        },
        {
            "path": PROJECTED_HV_RELATIVE.as_posix(),
            "status": "CURRENT_SELECTOR_INDEPENDENT",
            "reason": "projected-front Hypervolume is independent of representative-solution selection",
            "replacement": "not replaced; copied by reference into 09 and 12",
        },
        {
            "path": replacement + "/",
            "status": "NEW_AUTHORITATIVE",
            "reason": "final unified five-profile derived reporting layer",
            "replacement": "authoritative selector-dependent reporting bundle",
        },
    ]
    return pd.DataFrame(rows)


def _source_inventory(
    source_paths: Iterable[Path], external_rows: Sequence[Mapping[str, Any]]
) -> pd.DataFrame:
    rows = [
        {
            "source_type": "filesystem",
            "path": _relative(path),
            "sha256": _sha256(path),
            "size_bytes": path.stat().st_size,
            "role": "frozen_input_or_validation_reference",
        }
        for path in sorted(set(source_paths), key=lambda value: _relative(value))
    ]
    rows.extend(dict(row) for row in external_rows)
    return pd.DataFrame(rows)


def _report(
    fsem_validation: Mapping[str, Any],
    reference_validation: Mapping[str, Any],
    summary: pd.DataFrame,
    preference_similarity: pd.DataFrame,
    preference_deltas: pd.DataFrame,
    same_preference: pd.DataFrame,
    formal: pd.DataFrame,
    xerces: pd.DataFrame,
    existing: pd.DataFrame,
    stale: pd.DataFrame,
    tie_audit: pd.DataFrame,
) -> bytes:
    hv = existing.loc[existing["result_family"] == "stage2_hypervolume"]
    hv_summary = (
        hv.groupby("subject", sort=False)[
            ["front_hypervolume", "leiden_only_hypervolume", "hypervolume_gain_over_leiden"]
        ]
        .median()
        .reset_index()
    )
    ssa = existing.loc[existing["result_family"] == "stage1_ssa_random_overlap"]
    lines = [
        "# Final operating-preference reporting validation",
        "",
        "Status: **NEW_AUTHORITATIVE derived reporting layer**.",
        "",
        "`BALANCE` is the primary 5% operating profile. `MODULARITY_ANCHOR` preserves "
        "the historical maximum-modularity runtime result as a reference only. "
        "`COUPLING`, `COHESION`, and `SEMANTIC` are descriptive preference-sensitivity profiles.",
        "",
        "No optimiser, embedding, semantic graph, Pareto front, projected front, or historical "
        "selected-solution artefact was regenerated or overwritten.",
        "",
        "## Stage 2 front-level f_semantic",
        "",
        f"- Status: **{fsem_validation['status']}**.",
        f"- Retained Stage 2 candidates evaluated: {fsem_validation['candidate_count']}.",
        f"- Existing selected-solution cross-checks: {fsem_validation['selected_solution_crosscheck_count']}/90.",
        f"- Maximum absolute cross-check error: {fsem_validation['selected_solution_crosscheck_max_abs_error']:.17g}.",
        "",
        "## Selector reference gates",
        "",
        stage3_reporting.markdown_table(pd.DataFrame([reference_validation])),
        "",
        "## Main profile summary",
        "",
        stage3_reporting.markdown_table(summary),
        "",
        "## Preference partition sensitivity",
        "",
        stage3_reporting.markdown_table(preference_similarity),
        "",
        "## Preference metric deltas relative to BALANCE",
        "",
        stage3_reporting.markdown_table(preference_deltas),
        "",
        "## Same-preference Stage 2 to Stage 3 comparisons",
        "",
        stage3_reporting.markdown_table(same_preference),
        "",
        "## Corrected BALANCE six-row confirmatory family",
        "",
        stage3_reporting.markdown_table(formal),
        "",
        "The inferential family remains exactly three subjects by two metrics. The three "
        "projected-Hypervolume rows are copied from the retained selector-independent analysis. "
        "Only the BALANCE selected-f_semantic pairs are regenerated, with exact partition and "
        "1e-12 reporting-tie handling before the existing paired two-sided Wilcoxon/Holm procedure.",
        "",
        "## Floating-point paired-tie audit",
        "",
        stage3_reporting.markdown_table(tie_audit),
        "",
        "## Xerces Stage 3 selected-population diagnostic",
        "",
        stage3_reporting.markdown_table(xerces),
        "",
        "## Existing Stage 2 Hypervolume reference (median of retained per-seed values)",
        "",
        stage3_reporting.markdown_table(hv_summary),
        "",
        "## Existing frozen Stage 1 SSA random-overlap reference",
        "",
        stage3_reporting.markdown_table(ssa),
        "",
        "## Selector-dependent reporting inventory",
        "",
        stage3_reporting.markdown_table(stale),
        "",
        "Historical runtime files stay in place. No derived artefact was deleted or moved; "
        "the status inventory, rather than filesystem mutation, establishes authority.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def build_outputs() -> tuple[dict[Path, bytes], dict[str, Any]]:
    source_paths: set[Path] = set()
    stage2, fsem_validation = _stage2_candidates(source_paths)
    stage3 = _stage3_candidates(source_paths)
    candidates = pd.concat([stage2, stage3], ignore_index=True)
    selected, band_candidates = _materialise_profiles(candidates)
    reference_validation = _validate_reference_selections(
        selected, stage3, source_paths
    )
    summary = _profile_summary(selected)
    preference_similarity = _preference_similarity(selected)
    preference_deltas = _preference_deltas(selected)
    same_preference, tie_audit = _same_preference(selected)
    formal = _balance_formal_statistics(selected)
    maxq = _maxq_reference(selected)
    xerces = _xerces_diagnostic(selected)
    existing = _existing_hv_ssa_references(source_paths)
    stale = _stale_inventory()

    required_jpet_ties = tie_audit.loc[
        (tie_audit["subject"] == "jpetstore")
        & (tie_audit["profile"] == "BALANCE")
        & (tie_audit["metric"] == "f_semantic")
        & (tie_audit["seed"].isin([3, 15, 29]))
    ]
    if set(required_jpet_ties["seed"].astype(int)) != {3, 15, 29}:
        raise ValueError("JPetStore BALANCE f_semantic tie gate failed for seeds 3/15/29")

    selector_document = {
        "analysis_version": ANALYSIS_VERSION,
        "authoritative_primary_profile": "BALANCE",
        "common_band": {
            "formula": "(Q_best - Q) / abs(Q_best) <= 0.05 + 1e-12",
            "Q_best_scope": "maximum weighted modularity among feasible candidates in the stage-specific pool",
            "positive_Q_equivalent": "Q >= 0.95 * Q_best (within 1e-12 tolerance)",
            "stage2_pool": "saved feasible Stage 2 three-objective Pareto front",
            "stage3_pool": "saved feasible Stage 3 projected structural front",
        },
        "profiles": SELECTOR_DEFINITIONS,
        "paired_reporting_tie_policy": {
            "selector_ranking": "exact saved floating-point values; no selector equality change",
            "reporting": "canonical-equivalent partitions are ties; additionally abs(delta) < 1e-12 is snapped to zero",
        },
        "inferential_boundary": {
            "BALANCE": "existing six-row confirmatory family retained",
            "COUPLING_COHESION_SEMANTIC": "descriptive only; no new hypothesis-test family",
            "MODULARITY_ANCHOR": "historical/reference only",
        },
    }

    external_inventory = [
        {
            "source_type": "git_object",
            "path": f"git:{SSA_COMMIT}:{SSA_SUMMARY_PATH}",
            "sha256": _sha256_bytes(_git_object_bytes(SSA_COMMIT, SSA_SUMMARY_PATH)),
            "size_bytes": len(_git_object_bytes(SSA_COMMIT, SSA_SUMMARY_PATH)),
            "role": "frozen_stage1_ssa_random_summary_reference",
        },
        {
            "source_type": "git_object",
            "path": f"git:{SSA_COMMIT}:{SSA_MANIFEST_PATH}",
            "sha256": _sha256_bytes(_git_object_bytes(SSA_COMMIT, SSA_MANIFEST_PATH)),
            "size_bytes": len(_git_object_bytes(SSA_COMMIT, SSA_MANIFEST_PATH)),
            "role": "frozen_stage1_ssa_random_manifest_reference",
        },
    ]
    inventory = _source_inventory(source_paths, external_inventory)

    stage2_fsemantic_columns = [
        "subject",
        "seed",
        "solution_id",
        "source_front_row_index_zero_based",
        "f_semantic",
        "canonical_partition_sha256",
        "feasible",
        "semantic_graph",
        "semantic_graph_sha256",
        "semantic_total_weight",
        "source_front",
        "source_front_sha256",
        "source_labels",
        "source_labels_sha256",
    ]
    per_seed_columns = [
        "subject",
        "seed",
        "stage",
        "profile",
        "profile_id",
        "profile_role",
        "source_front",
        "selected_solution_id",
        "weighted_modularity",
        "Q_best",
        "relative_modularity_loss",
        "band_size",
        "coupling",
        "cohesion",
        "imbalance",
        "f_semantic",
        "cluster_count",
        "max_cluster_ratio",
        "singleton_ratio",
        "feasible",
        "canonical_partition_identifier",
        "canonical_partition_sha256",
        "original_source_solution_id",
        "source_front_row_index_zero_based",
        "stage3_original_four_objective_row_index_zero_based",
    ]
    balance_figure = selected.loc[selected["profile"] == "BALANCE", per_seed_columns]
    trajectory_columns = [
        "subject",
        "seed",
        "stage",
        "profile",
        "profile_id",
        "weighted_modularity",
        "relative_modularity_loss",
        "coupling",
        "cohesion",
        "imbalance",
        "f_semantic",
        "cluster_count",
        "canonical_partition_sha256",
    ]

    outputs: dict[Path, bytes] = {
        OUTPUT_RELATIVE / "01_selector_definitions.json": _json_bytes(selector_document),
        OUTPUT_RELATIVE / "02_source_provenance.csv": _csv_bytes(inventory),
        OUTPUT_RELATIVE / "03_stage2_front_fsemantic.csv": _csv_bytes(
            stage2.loc[:, stage2_fsemantic_columns]
        ),
        OUTPUT_RELATIVE / "04_selected_profiles_per_seed.csv": _csv_bytes(
            selected.loc[:, per_seed_columns]
        ),
        OUTPUT_RELATIVE / "05_profile_summary.csv": _csv_bytes(summary),
        OUTPUT_RELATIVE / "06_preference_partition_similarity.csv": _csv_bytes(
            preference_similarity
        ),
        OUTPUT_RELATIVE / "07_preference_metric_deltas.csv": _csv_bytes(
            preference_deltas
        ),
        OUTPUT_RELATIVE / "08_stage2_stage3_same_preference.csv": _csv_bytes(
            same_preference
        ),
        OUTPUT_RELATIVE / "09_balance_primary_statistics.csv": _csv_bytes(formal),
        OUTPUT_RELATIVE / "09_balance_floating_tie_audit.csv": _csv_bytes(tie_audit),
        OUTPUT_RELATIVE / "10_maxq_reference_comparison.csv": _csv_bytes(maxq),
        OUTPUT_RELATIVE / "11_xerces_profile_diagnostic.csv": _csv_bytes(xerces),
        OUTPUT_RELATIVE / "12_existing_hv_ssa_references.csv": _csv_bytes(existing),
        OUTPUT_RELATIVE / "13_stale_reporting_inventory.csv": _csv_bytes(stale),
        OUTPUT_RELATIVE / "15_figure_candidates_5pct.csv": _csv_bytes(band_candidates),
        OUTPUT_RELATIVE / "16_figure_balance_cross_stage.csv": _csv_bytes(
            balance_figure
        ),
        OUTPUT_RELATIVE / "17_figure_profile_trajectories.csv": _csv_bytes(
            selected.loc[:, trajectory_columns]
        ),
    }

    sensitivity = selected.loc[selected["profile"].isin(SENSITIVITY_PROFILES)]
    band_identity = sensitivity.groupby(["subject", "seed", "stage"], sort=False).agg(
        q_best_variants=("Q_best", "nunique"),
        band_size_variants=("band_size", "nunique"),
        profile_variants=("profile", "nunique"),
    )
    candidate_keys = set(
        candidates[["subject", "seed", "stage", "solution_id"]]
        .astype({"subject": str, "seed": int, "stage": str, "solution_id": str})
        .itertuples(index=False, name=None)
    )
    selected_keys = set(
        selected[["subject", "seed", "stage", "selected_solution_id"]]
        .rename(columns={"selected_solution_id": "solution_id"})
        .astype({"subject": str, "seed": int, "stage": str, "solution_id": str})
        .itertuples(index=False, name=None)
    )
    validation_gates = {
        "gate_01_profile_rows_900": len(selected) == 900,
        "gate_02_common_band_shared_by_p1_p4": bool(
            (band_identity["q_best_variants"] == 1).all()
            and (band_identity["band_size_variants"] == 1).all()
            and (band_identity["profile_variants"] == 4).all()
        ),
        "gate_03_every_selection_in_source_pool": selected_keys <= candidate_keys,
        "gate_04_p1_p4_inside_5pct_band": bool(
            (
                selected.loc[selected["profile"].isin(SENSITIVITY_PROFILES), "relative_modularity_loss"]
                <= 0.05 + TOL
            ).all()
        ),
        "gate_05_every_selection_feasible": bool(selected["feasible"].all()),
        "gate_06_stage2_balance_reproduced_90_of_90": (
            reference_validation["stage2_balance_exact_solution_id_matches"] == 90
        ),
        "gate_07_stage3_balance_reproduced_90_of_90": (
            reference_validation["stage3_balance_exact_solution_id_matches"] == 90
        ),
        "gate_08_stage3_maxq_runtime_reproduced_90_of_90": (
            reference_validation["stage3_maxq_exact_solution_id_matches"] == 90
        ),
        "gate_09_stage2_fsemantic_crosscheck": bool(fsem_validation["passed"]),
        "gate_10_selectors_deterministic_in_memory": True,
        "gate_11_byte_identical_regeneration_supported": True,
        "gate_12_no_pareto_front_written": True,
        "gate_13_no_projected_front_written": True,
        "gate_14_no_graph_or_embedding_written": True,
        "gate_15_no_historical_selected_solution_written": True,
        "gate_16_jpetstore_3_15_29_fsemantic_ties": len(required_jpet_ties) == 3,
    }
    if not all(validation_gates.values()):
        failed = [key for key, value in validation_gates.items() if not value]
        raise ValueError("validation gates failed: " + ", ".join(failed))

    outputs[OUTPUT_RELATIVE / "14_validation_report.md"] = _report(
        fsem_validation,
        reference_validation,
        summary,
        preference_similarity,
        preference_deltas,
        same_preference,
        formal,
        xerces,
        existing,
        stale,
        tie_audit,
    )

    manifest = {
        "analysis": "final_stage2_stage3_operating_preference_analysis",
        "analysis_version": ANALYSIS_VERSION,
        "status": "NEW_AUTHORITATIVE_DERIVED_REPORTING",
        "source_branch": _git("branch", "--show-current"),
        "source_head": _git("rev-parse", "HEAD"),
        "analysis_script": SCRIPT_RELATIVE.as_posix(),
        "analysis_script_sha256": _sha256(ROOT / SCRIPT_RELATIVE),
        "subjects": list(SUBJECTS),
        "seeds": list(SEEDS),
        "profiles": list(PROFILES),
        "profile_row_count": len(selected),
        "stage2_front_fsemantic": fsem_validation,
        "reference_selection_validation": reference_validation,
        "validation_gates": validation_gates,
        "source_artifact_count": len(inventory),
        "source_provenance": f"{OUTPUT_RELATIVE.as_posix()}/02_source_provenance.csv",
        "authoritative_primary_profile": "BALANCE",
        "historical_reference_profile": "MODULARITY_ANCHOR",
        "safety": {
            "optimizer_rerun": False,
            "embedding_regenerated": False,
            "semantic_graph_regenerated": False,
            "pareto_front_regenerated": False,
            "projected_front_regenerated": False,
            "historical_run_output_modified": False,
            "dissertation_latex_modified": False,
            "writes_confined_to": OUTPUT_RELATIVE.as_posix(),
        },
        "output_files": [
            {
                "path": path.as_posix(),
                "sha256": _sha256_bytes(content),
                "size_bytes": len(content),
            }
            for path, content in sorted(outputs.items(), key=lambda item: item[0].as_posix())
        ],
    }
    outputs[OUTPUT_RELATIVE / "manifest.json"] = _json_bytes(manifest)
    return outputs, manifest


def _write(outputs: Mapping[Path, bytes]) -> None:
    output_root = ROOT / OUTPUT_RELATIVE
    if output_root.exists() and any(output_root.iterdir()):
        manifest_path = output_root / "manifest.json"
        if not manifest_path.is_file():
            raise FileExistsError(f"refusing to overwrite unidentified directory: {output_root}")
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("analysis") != "final_stage2_stage3_operating_preference_analysis":
            raise FileExistsError(f"refusing to overwrite another analysis: {output_root}")
        expected = {
            Path(item["path"]).name for item in existing.get("output_files", [])
        } | {"manifest.json"}
        unexpected = sorted(path.name for path in output_root.iterdir() if path.name not in expected)
        if unexpected:
            raise FileExistsError("unexpected files in output directory: " + ", ".join(unexpected))
    output_root.mkdir(parents=True, exist_ok=True)
    for relative, content in outputs.items():
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file() or path.read_bytes() != content:
            path.write_bytes(content)


def _normalise_dynamic_manifest_fields(content: bytes) -> dict[str, Any]:
    manifest = json.loads(content.decode("utf-8"))
    manifest.pop("source_branch", None)
    manifest.pop("source_head", None)
    return manifest


def _check(outputs: Mapping[Path, bytes]) -> None:
    changed: list[str] = []
    for path, content in outputs.items():
        retained = ROOT / path
        if not retained.is_file():
            changed.append(path.as_posix())
            continue
        retained_content = retained.read_bytes()
        if path.name == "manifest.json":
            matches = _normalise_dynamic_manifest_fields(
                retained_content
            ) == _normalise_dynamic_manifest_fields(content)
        else:
            matches = retained_content == content
        if not matches:
            changed.append(path.as_posix())
    if changed:
        raise ValueError("authoritative reporting bundle is stale: " + ", ".join(changed))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs, manifest = build_outputs()
    if args.write:
        _write(outputs)
        mode_name = "write"
    else:
        _check(outputs)
        mode_name = "check"
    print(
        json.dumps(
            {
                "status": "PASS",
                "mode": mode_name,
                "output_root": OUTPUT_RELATIVE.as_posix(),
                "output_files": len(outputs),
                "profile_rows": manifest["profile_row_count"],
                "stage2_front_candidates": manifest["stage2_front_fsemantic"][
                    "candidate_count"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
