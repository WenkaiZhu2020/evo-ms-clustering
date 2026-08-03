"""Canonical reporting-only analysis for final Stage 3.

This module reads frozen Stage 2 and final Declaration + Method Body artifacts.
It never runs an optimizer or regenerates semantic evidence.  The path checks
are intentionally strict so a historical Stage 2 representative or Stage 3A
artifact cannot silently enter the final Section 4.3 statistics.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import rankdata, wilcoxon
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from evo_ms.evaluation.partition_ops import changed_partition_ratio
from evo_ms.optimization.semantic_objective import (
    evaluate_semantic_objective,
    semantic_total_weight,
)
from evo_ms.repository_layout import stage3_subject_root


SUBJECTS = ("jpetstore", "daytrader", "xerces")
DISPLAY_SUBJECT = {
    "jpetstore": "JPetStore",
    "daytrader": "DayTrader",
    "xerces": "Xerces-J",
}
STORAGE_SUBJECT = {
    "jpetstore": "jpetstore",
    "daytrader": "daytrader",
    "xerces": "xerces-j",
}
EXPECTED_SEEDS = tuple(range(30))
EXPECTED_PAIRS = {(subject, seed) for subject in SUBJECTS for seed in EXPECTED_SEEDS}
TOL = 1e-12
ALPHA = 0.05

ACTIVE_STAGE2_PROFILE = Path(
    "results/stage2/cross_subject/operating_profile/"
    "canonical_operating_solution_per_seed.csv"
)
PROJECTED_HV_SOURCE = Path(
    "results/stage3/cross_subject/stage2_comparison/paired_per_seed.csv"
)
STAGE2_PROFILE_ID = "stage2_5pct_modularity_band"
STAGE3_PROFILE_ID = "stage3_final_projected_front_operating_selector"


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_csv(path, float_precision="round_trip")


def _normalise_subject(value: str) -> str:
    subject = str(value).strip().lower()
    if subject == "xerces-j":
        return "xerces"
    return subject


def _validate_final_path(path: Path) -> None:
    lowered = path.as_posix().lower()
    forbidden = ("stage3a", "stage3-semantic", "04_stage3_semantic", "declaration_only")
    if any(token in lowered for token in forbidden):
        raise ValueError(f"legacy Stage 3 path is forbidden: {path}")


def _validate_pairs(frame: pd.DataFrame, source: str) -> pd.DataFrame:
    required = {"subject", "seed"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{source} lacks subject/seed columns")
    output = frame.copy()
    output["subject"] = output["subject"].map(_normalise_subject)
    output["seed"] = output["seed"].astype(int)
    pairs = list(zip(output["subject"], output["seed"], strict=True))
    observed = set(pairs)
    if len(pairs) != len(observed):
        raise ValueError(f"{source} contains duplicate subject/seed rows")
    missing = sorted(EXPECTED_PAIRS - observed)
    extra = sorted(observed - EXPECTED_PAIRS)
    if missing or extra:
        raise ValueError(f"{source} seed alignment failed: missing={missing}, extra={extra}")
    return output.sort_values(["subject", "seed"], kind="stable").reset_index(drop=True)


def load_active_stage2_profile(root: Path) -> pd.DataFrame:
    """Load only the frozen Section 4.2 five-percent operating profile."""
    path = (root / ACTIVE_STAGE2_PROFILE).resolve()
    expected = (root / ACTIVE_STAGE2_PROFILE).resolve()
    if path != expected:
        raise ValueError("active Stage 2 profile path was substituted")
    frame = _validate_pairs(_read_csv(path), str(ACTIVE_STAGE2_PROFILE))
    if not frame["canonical_operating_profile"].astype(bool).all():
        raise ValueError("Stage 2 profile contains a non-canonical row")
    if not np.allclose(frame["budget"].astype(float), 0.05, rtol=0.0, atol=TOL):
        raise ValueError("Stage 2 profile is not the frozen 5% modularity band")
    expected_rule = {"minimum_imbalance_within_relative_modularity_band"}
    if set(frame["selection_rule"].astype(str)) != expected_rule:
        raise ValueError("Stage 2 profile uses an unexpected selection rule")
    return frame


def load_projected_hv_pairs(root: Path) -> pd.DataFrame:
    """Load the accepted HV pair columns without reading legacy semantic columns."""
    path = root / PROJECTED_HV_SOURCE
    frame = _validate_pairs(_read_csv(path), str(PROJECTED_HV_SOURCE))
    required = {"stage2_hv", "stage3_projected_hv"}
    if not required.issubset(frame.columns):
        raise ValueError("accepted projected-HV source lacks required columns")
    return frame[["subject", "seed", "stage2_hv", "stage3_projected_hv"]].copy()


def _class_nodes(root: Path, subject: str) -> pd.DataFrame:
    path = root / "data/extracted" / STORAGE_SUBJECT[subject] / "class_nodes.csv"
    frame = _read_csv(path)
    if frame["class_id"].astype(str).duplicated().any():
        raise ValueError(f"duplicate structural class ID for {subject}")
    return frame


def _semantic_edges(root: Path, subject: str) -> pd.DataFrame:
    path = root / "data/semantic_graphs/declaration_method_body" / subject / "semantic_edges.csv"
    _validate_final_path(path)
    return _read_csv(path)


def _vector_partition(class_nodes: pd.DataFrame, vector: str | Sequence[int]) -> pd.DataFrame:
    labels = json.loads(vector) if isinstance(vector, str) else list(vector)
    if len(labels) != len(class_nodes):
        raise ValueError(f"label vector length {len(labels)} != class count {len(class_nodes)}")
    return pd.DataFrame(
        {
            "class_id": class_nodes["class_id"].astype(str).tolist(),
            "cluster_id": [int(value) for value in labels],
        }
    )


def _stage3_selected(root: Path, subject: str, seed: int) -> tuple[str, pd.DataFrame, float]:
    phase = "validation" if seed == 0 else "formal"
    path = stage3_subject_root(subject, root) / phase / f"seed_{seed:02d}" / "selected_solution.json"
    _validate_final_path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("representation_id") != "declaration_method_body_v1":
        raise ValueError(f"unexpected Stage 3 representation in {path}")
    partition = pd.DataFrame(payload["selected_partition"])[["class_id", "cluster_id"]].copy()
    partition["class_id"] = partition["class_id"].astype(str)
    partition["cluster_id"] = partition["cluster_id"].astype(int)
    return (
        str(payload["selected_solution_id"]),
        partition,
        float(payload["selected_four_objective_row"]["f_semantic"]),
    )


def _partition_map(partition: pd.DataFrame) -> dict[str, int]:
    if partition["class_id"].duplicated().any():
        raise ValueError("partition contains duplicate class IDs")
    return dict(
        zip(
            partition["class_id"].astype(str),
            partition["cluster_id"].astype(int),
            strict=True,
        )
    )


def _validate_universe(
    subject: str,
    class_nodes: pd.DataFrame,
    semantic_edges: pd.DataFrame,
    *partitions: pd.DataFrame,
) -> None:
    expected = set(class_nodes["class_id"].astype(str))
    graph_ids = set(semantic_edges["class_id_a"].astype(str)) | set(
        semantic_edges["class_id_b"].astype(str)
    )
    if graph_ids != expected:
        raise ValueError(f"semantic/structural class universe mismatch for {subject}")
    for partition in partitions:
        if set(partition["class_id"].astype(str)) != expected:
            raise ValueError(f"partition class universe mismatch for {subject}")


def canonical_partition_key(partition: pd.DataFrame) -> tuple[int, ...]:
    """Canonical labels after sorting classes; cluster label names are irrelevant."""
    ordered = partition[["class_id", "cluster_id"]].copy()
    ordered["class_id"] = ordered["class_id"].astype(str)
    ordered = ordered.sort_values("class_id", kind="stable")
    remap: dict[int, int] = {}
    labels: list[int] = []
    for raw in ordered["cluster_id"].astype(int):
        if raw not in remap:
            remap[raw] = len(remap)
        labels.append(remap[raw])
    return tuple(labels)


def build_selected_fsemantic_pairs(root: Path) -> pd.DataFrame:
    """Recompute both selected partitions on the same final semantic graph."""
    stage2 = load_active_stage2_profile(root).set_index(["subject", "seed"])
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        class_nodes = _class_nodes(root, subject)
        semantic_edges = _semantic_edges(root, subject)
        total_weight = semantic_total_weight(semantic_edges)
        for seed in EXPECTED_SEEDS:
            stage2_row = stage2.loc[(subject, seed)]
            stage2_partition = _vector_partition(class_nodes, str(stage2_row["label_vector"]))
            stage3_solution_id, stage3_partition, saved_stage3_fsemantic = _stage3_selected(
                root, subject, seed
            )
            _validate_universe(
                subject,
                class_nodes,
                semantic_edges,
                stage2_partition,
                stage3_partition,
            )
            stage2_value = evaluate_semantic_objective(
                semantic_edges,
                _partition_map(stage2_partition),
                total_weight=total_weight,
            )
            stage3_value = evaluate_semantic_objective(
                semantic_edges,
                _partition_map(stage3_partition),
                total_weight=total_weight,
            )
            if not np.isclose(stage3_value, saved_stage3_fsemantic, rtol=0.0, atol=TOL):
                raise ValueError(
                    f"Stage 3 selected f_semantic recomputation mismatch for {subject} seed {seed}"
                )
            rows.append(
                {
                    "subject": subject,
                    "seed": seed,
                    "stage2_profile_id": STAGE2_PROFILE_ID,
                    "stage3_profile_id": STAGE3_PROFILE_ID,
                    "stage2_solution_id": str(stage2_row["solution_id"]),
                    "stage3_solution_id": stage3_solution_id,
                    "stage2_f_semantic": float(stage2_value),
                    "stage3_f_semantic": float(stage3_value),
                    "delta_stage3_minus_stage2": float(stage3_value - stage2_value),
                    "stage2_profile_source": ACTIVE_STAGE2_PROFILE.as_posix(),
                    "stage3_profile_source": (
                        f"results/stage3/subjects/{STORAGE_SUBJECT[subject]}/declaration_method_body/"
                        f"{'validation' if seed == 0 else 'formal'}/seed_{seed:02d}/selected_solution.json"
                    ),
                    "semantic_graph_source": (
                        f"data/semantic_graphs/declaration_method_body/{subject}/semantic_edges.csv"
                    ),
                    "formula": "1 - W_semantic,intra / W_semantic,total",
                }
            )
    return _validate_pairs(pd.DataFrame(rows), "recomputed selected f_semantic")


def _descriptive(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values, ddof=1)),
        "iqr": float(np.quantile(values, 0.75) - np.quantile(values, 0.25)),
    }


def rank_biserial(differences: Sequence[float]) -> float:
    """Signed rank-biserial effect for Stage 3 minus Stage 2 differences."""
    values = np.asarray(differences, dtype=float)
    nonzero = values[values != 0.0]
    if len(nonzero) == 0:
        return 0.0
    ranks = rankdata(np.abs(nonzero), method="average")
    positive = float(ranks[nonzero > 0.0].sum())
    negative = float(ranks[nonzero < 0.0].sum())
    return float((positive - negative) / (positive + negative))


def paired_wilcoxon(differences: Sequence[float]) -> tuple[float, float]:
    """Two-sided SciPy Wilcoxon with explicit ``wilcox`` zero handling."""
    values = np.asarray(differences, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Wilcoxon differences must be finite")
    if np.all(values == 0.0):
        return 0.0, 1.0
    result = wilcoxon(
        values,
        zero_method="wilcox",
        correction=False,
        alternative="two-sided",
        method="auto",
    )
    return float(result.statistic), float(result.pvalue)


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    """Return Holm step-down adjusted p-values in input order."""
    values = np.asarray(p_values, dtype=float)
    if len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("Holm family must contain finite p-values")
    order = np.argsort(values, kind="stable")
    adjusted = np.empty(len(values), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        candidate = min(1.0, float((len(values) - rank) * values[index]))
        running = max(running, candidate)
        adjusted[index] = running
    return adjusted.tolist()


def _formal_row(
    subject: str,
    metric: str,
    stage2: np.ndarray,
    stage3: np.ndarray,
    direction: str,
    stage2_profile_id: str,
    stage3_profile_id: str,
    source_artifacts: str,
) -> dict[str, Any]:
    if len(stage2) != 30 or len(stage3) != 30:
        raise ValueError(f"{subject}/{metric} must contain exactly 30 pairs")
    differences = stage3 - stage2
    statistic, raw_p = paired_wilcoxon(differences)
    if direction == "higher_is_better":
        better = int(np.sum(differences > 0.0))
        worse = int(np.sum(differences < 0.0))
    elif direction == "lower_is_better":
        better = int(np.sum(differences < 0.0))
        worse = int(np.sum(differences > 0.0))
    else:
        raise ValueError(direction)
    ties = int(np.sum(differences == 0.0))
    left = _descriptive(stage2)
    right = _descriptive(stage3)
    return {
        "subject": subject,
        "metric": metric,
        "n_pairs": 30,
        "stage2_mean": left["mean"],
        "stage2_median": left["median"],
        "stage2_std": left["std"],
        "stage2_iqr": left["iqr"],
        "stage3_mean": right["mean"],
        "stage3_median": right["median"],
        "stage3_std": right["std"],
        "stage3_iqr": right["iqr"],
        "paired_median_difference": float(np.median(differences)),
        "better_count": better,
        "tie_count": ties,
        "worse_count": worse,
        "wilcoxon_statistic": statistic,
        "raw_p_value": raw_p,
        "holm_adjusted_p_value": np.nan,
        "alpha": ALPHA,
        "corrected_significant": False,
        "rank_biserial": rank_biserial(differences),
        "comparison_direction": direction,
        "stage2_profile_id": stage2_profile_id,
        "stage3_profile_id": stage3_profile_id,
        "source_artifacts": source_artifacts,
        "difference_definition": "Stage 3 - Stage 2",
        "wilcoxon_zero_method": "wilcox",
        "correction_family": "six confirmatory rows only",
    }


def build_formal_tests(
    root: Path,
    selected_pairs: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build the exact 3 subjects × 2 primary-metric confirmatory family."""
    hv = load_projected_hv_pairs(root).set_index(["subject", "seed"])
    selected = (
        build_selected_fsemantic_pairs(root) if selected_pairs is None else selected_pairs
    )
    selected = _validate_pairs(selected, "selected f_semantic pairs").set_index(
        ["subject", "seed"]
    )
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        keys = [(subject, seed) for seed in EXPECTED_SEEDS]
        hv_subject = hv.loc[keys]
        rows.append(
            _formal_row(
                subject,
                "projected_hypervolume",
                hv_subject["stage2_hv"].to_numpy(dtype=float),
                hv_subject["stage3_projected_hv"].to_numpy(dtype=float),
                "higher_is_better",
                "accepted_stage2_projected_front",
                "final_stage3_projected_front",
                PROJECTED_HV_SOURCE.as_posix(),
            )
        )
        selected_subject = selected.loc[keys]
        rows.append(
            _formal_row(
                subject,
                "selected_f_semantic",
                selected_subject["stage2_f_semantic"].to_numpy(dtype=float),
                selected_subject["stage3_f_semantic"].to_numpy(dtype=float),
                "lower_is_better",
                STAGE2_PROFILE_ID,
                STAGE3_PROFILE_ID,
                (
                    f"{ACTIVE_STAGE2_PROFILE.as_posix()}; "
                    "results/stage3/subjects/<subject>/declaration_method_body/"
                    "{validation,formal}/seed_*/selected_solution.json; "
                    "data/semantic_graphs/declaration_method_body/<subject>/semantic_edges.csv"
                ),
            )
        )
    frame = pd.DataFrame(rows)
    if len(frame) != 6 or frame[["subject", "metric"]].duplicated().any():
        raise ValueError("confirmatory family must contain exactly six unique rows")
    adjusted = holm_adjust(frame["raw_p_value"].astype(float).tolist())
    frame["holm_adjusted_p_value"] = adjusted
    frame["corrected_significant"] = frame["holm_adjusted_p_value"] <= ALPHA
    return frame


def build_formal_summary(tests: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in tests.itertuples(index=False):
        for stage in ("stage2", "stage3"):
            rows.append(
                {
                    "subject": row.subject,
                    "metric": row.metric,
                    "stage": stage,
                    "seed_count": row.n_pairs,
                    "mean": getattr(row, f"{stage}_mean"),
                    "median": getattr(row, f"{stage}_median"),
                    "sample_std": getattr(row, f"{stage}_std"),
                    "iqr": getattr(row, f"{stage}_iqr"),
                    "profile_id": getattr(row, f"{stage}_profile_id"),
                }
            )
    return pd.DataFrame(rows)


def build_partition_similarity(
    root: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare active matching-seed selections with unambiguous metrics."""
    stage2 = load_active_stage2_profile(root).set_index(["subject", "seed"])
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        class_nodes = _class_nodes(root, subject)
        for seed in EXPECTED_SEEDS:
            left = _vector_partition(class_nodes, str(stage2.loc[(subject, seed), "label_vector"]))
            _, right, _ = _stage3_selected(root, subject, seed)
            _validate_universe(subject, class_nodes, _semantic_edges(root, subject), left, right)
            left_map = _partition_map(left)
            right_map = _partition_map(right)
            class_ids = sorted(left_map)
            left_labels = [left_map[class_id] for class_id in class_ids]
            right_labels = [right_map[class_id] for class_id in class_ids]
            changed_count, changed_ratio = changed_partition_ratio(
                class_nodes,
                left,
                right,
            )
            identical = canonical_partition_key(left) == canonical_partition_key(right)
            rows.append(
                {
                    "subject": subject,
                    "seed": seed,
                    "exact_identical": bool(identical),
                    "adjusted_rand_index": float(
                        adjusted_rand_score(left_labels, right_labels)
                    ),
                    "normalized_mutual_information": float(
                        normalized_mutual_info_score(left_labels, right_labels)
                    ),
                    "class_level_changed_count": int(changed_count),
                    "changed_partition_ratio": float(changed_ratio),
                    "stage2_profile_id": STAGE2_PROFILE_ID,
                    "stage3_profile_id": STAGE3_PROFILE_ID,
                }
            )
    per_seed = _validate_pairs(pd.DataFrame(rows), "partition similarity")
    summaries: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        frame = per_seed.loc[per_seed["subject"] == subject]
        identical_count = int(frame["exact_identical"].sum())
        non_identical = len(frame) - identical_count
        summaries.append(
            {
                "subject": subject,
                "n_pairs": len(frame),
                "exact_identical_count": identical_count,
                "non_identical_pair_count": non_identical,
                "non_identical_pair_proportion": float(non_identical / len(frame)),
                "ari_mean": float(frame["adjusted_rand_index"].mean()),
                "ari_median": float(frame["adjusted_rand_index"].median()),
                "nmi_mean": float(frame["normalized_mutual_information"].mean()),
                "nmi_median": float(frame["normalized_mutual_information"].median()),
                "class_level_changed_partition_ratio_mean": float(
                    frame["changed_partition_ratio"].mean()
                ),
                "definition": (
                    "matching-seed Stage 2/Stage 3 partition pairs not exactly identical "
                    "after canonical label normalization, divided by paired seeds"
                ),
            }
        )
    return per_seed, pd.DataFrame(summaries)


def build_input_control_summary(root: Path) -> pd.DataFrame:
    """Separate model context truncation from the 256-token body budget."""
    manifest_path = (
        root / "results/stage3/provenance/embedding_generation_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for subject in SUBJECTS:
        quality_path = (
            root / "results/stage3/data_quality/semantic_input/input_quality_per_class.csv"
        )
        quality = _read_csv(quality_path)
        quality = quality.loc[quality["subject"].map(_normalise_subject) == subject].copy()
        affected = quality.loc[quality["body_tokens_truncated"].astype(int) > 0]
        values = manifest["subjects"][subject]
        tokenizer_count = int(values["tokenizer_truncated_count"])
        body_count = int(values["contract_body_truncated_count"])
        if tokenizer_count != 0:
            raise ValueError(f"embedding tokenizer truncation unexpectedly occurred for {subject}")
        if body_count != len(affected):
            raise ValueError(f"body-budget count mismatch for {subject}")
        rows.append(
            {
                "subject": subject,
                "class_count": len(quality),
                "embedding_model_max_tokens": int(values["max_sequence_length"]),
                "model_tokenizer_truncation_count": tokenizer_count,
                "embedding_context_limit_exceeded_count": tokenizer_count,
                "method_body_budget_tokens": 256,
                "body_budget_capped_classes": body_count,
                "body_tokens_removed_by_budget": int(
                    affected["body_tokens_truncated"].astype(int).sum()
                ),
                "affected_class_ids": ";".join(
                    affected.sort_values("class_id", kind="stable")["class_id"].astype(str)
                ),
            }
        )
    return pd.DataFrame(rows)


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n", float_format="%.17g").encode(
        "utf-8"
    )


def markdown_table(frame: pd.DataFrame, columns: Sequence[str] | None = None) -> str:
    view = frame if columns is None else frame.loc[:, list(columns)]
    headers = [str(column) for column in view.columns]
    rows = [[str(value) for value in row] for row in view.itertuples(index=False, name=None)]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def replace_generated_block(text: str, name: str, content: str) -> str:
    start = f"<!-- BEGIN GENERATED: {name} -->"
    end = f"<!-- END GENERATED: {name} -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"report must contain one generated block named {name}")
    before, remainder = text.split(start, 1)
    _, after = remainder.split(end, 1)
    return f"{before}{start}\n{content.rstrip()}\n{end}{after}"


def render_report_blocks(
    report_text: str,
    tests: pd.DataFrame,
    selected_pairs: pd.DataFrame,
    similarity_summary: pd.DataFrame,
    input_controls: pd.DataFrame,
) -> str:
    """Refresh the critical machine-backed blocks in the canonical data pack."""
    formal_columns = [
        "subject",
        "metric",
        "n_pairs",
        "paired_median_difference",
        "better_count",
        "tie_count",
        "worse_count",
        "raw_p_value",
        "holm_adjusted_p_value",
        "rank_biserial",
        "corrected_significant",
    ]
    formal = (
        "**Formal confirmatory family: exactly three subjects × two primary metrics "
        "(six rows).** Differences are Stage 3 − Stage 2; Wilcoxon is paired, "
        "two-sided, with SciPy `zero_method=\"wilcox\"`; Holm is applied across "
        "these six rows only (family-wise alpha 0.05).\n\n"
        + markdown_table(tests, formal_columns)
    )
    pair_columns = [
        "subject",
        "seed",
        "stage2_solution_id",
        "stage3_solution_id",
        "stage2_f_semantic",
        "stage3_f_semantic",
        "delta_stage3_minus_stage2",
    ]
    semantic = (
        "**Selected `f_semantic` pairs.** Stage 2 uses only the frozen 5% "
        "modularity-band profile; both partitions are evaluated on the same final "
        "Declaration + Method Body graph.\n\n"
        + markdown_table(selected_pairs, pair_columns)
    )
    partition = (
        "`non_identical_pair_proportion` is the number of matching-seed selected "
        "partition pairs that are not exactly identical after canonical label "
        "normalization, divided by the number of paired seeds. A value of 1.0 does "
        "not mean every class changed. `changed_partition_ratio` remains the separate "
        "class-level same-cluster-neighbour metric.\n\n"
        + markdown_table(similarity_summary)
    )
    inputs = (
        "No semantic input reached the embedding model's 32,768-token context limit, "
        "and tokenizer truncation was disabled. A separate 256-token method-body "
        "evidence budget affected no JPetStore classes, one DayTrader class, and "
        "seven Xerces-J classes.\n\n"
        + markdown_table(input_controls)
    )
    contract = "\n".join(
        [
            "- Active Stage 2 profile: `" + ACTIVE_STAGE2_PROFILE.as_posix() + "`.",
            "- Stage 3 profile: final matching-seed `selected_solution.json` from the projected-front operating selector.",
            "- Projected-HV source: `" + PROJECTED_HV_SOURCE.as_posix() + "`; its accepted HV columns are unchanged.",
            "- Selected `f_semantic`: recomputed for both selected partitions on `data/semantic_graphs/declaration_method_body/<subject>/semantic_edges.csv`.",
            "- Confirmatory family: three subjects × projected_hypervolume/selected_f_semantic; paired two-sided Wilcoxon; Holm over exactly six rows; alpha 0.05.",
            "- Structural selected-profile tests and preference-response analyses are separate exploratory families.",
            "- Partition terminology: `non_identical_pair_proportion` is pair-level; `changed_partition_ratio` is class-level.",
            "- Token controls: model tokenizer truncation count is zero; the independent method-body evidence budget is 256 tokens.",
            "- No experiment, embedding, semantic graph, Pareto front, projected front, or selected solution was regenerated.",
        ]
    )
    output = replace_generated_block(report_text, "formal_statistics", formal)
    output = replace_generated_block(output, "selected_fsemantic_pairs", semantic)
    output = replace_generated_block(output, "partition_similarity", partition)
    output = replace_generated_block(output, "input_controls", inputs)
    output = replace_generated_block(output, "canonical_reporting_contract", contract)
    return output


def reporting_outputs(root: Path) -> Mapping[Path, bytes]:
    """Build every canonical reporting output in memory before any write."""
    selected = build_selected_fsemantic_pairs(root)
    tests = build_formal_tests(root, selected)
    summary = build_formal_summary(tests)
    similarity_per_seed, similarity_summary = build_partition_similarity(root)
    controls = build_input_control_summary(root)
    base = Path("results/stage3")
    outputs: dict[Path, bytes] = {
        base / "cross_subject/formal_statistics/formal_selected_fsemantic_per_seed.csv": csv_bytes(selected),
        base / "cross_subject/formal_statistics/formal_statistical_tests.csv": csv_bytes(tests),
        base / "cross_subject/formal_statistics/formal_summary.csv": csv_bytes(summary),
        base / "cross_subject/formal_statistics/formal_partition_similarity_per_seed.csv": csv_bytes(
            similarity_per_seed
        ),
        base / "cross_subject/formal_statistics/formal_partition_similarity_summary.csv": csv_bytes(
            similarity_summary
        ),
        base / "data_quality/semantic_input/input_control_summary.csv": csv_bytes(controls),
    }
    report_path = Path("docs/stage3/findings/chapter4_3_data_pack.md")
    report_text = (root / report_path).read_text(encoding="utf-8")
    outputs[report_path] = render_report_blocks(
        report_text,
        tests,
        selected,
        similarity_summary,
        controls,
    ).encode("utf-8")
    return outputs


def write_reporting_outputs(root: Path, *, check: bool = False) -> list[Path]:
    """Write or byte-check deterministic reporting outputs only."""
    outputs = reporting_outputs(root)
    changed: list[Path] = []
    for relative, content in outputs.items():
        path = root / relative
        current = path.read_bytes() if path.exists() else None
        if current != content:
            changed.append(relative)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
    if check and changed:
        raise ValueError("reporting outputs are stale: " + ", ".join(map(str, changed)))
    return changed
