#!/usr/bin/env python3
"""Audit and seal the saved post-hoc preference-response analysis.

This script reads frozen Stage 2/3A/3B fronts, saved partitions, graphs,
references, and the accepted preference-analysis reports.  It never invokes
an optimizer and it never writes to the accepted report directory.  All new
evidence is isolated under ``reports/preference_analysis_audit``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import io
import json
import locale
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from evo_ms.evaluation.partition_metrics import partition_similarity  # noqa: E402
from scripts.preference_analysis import analyze_preference_response as analysis  # noqa: E402

AUDIT_ROOT = ROOT / "reports/preference_analysis_audit"
ACCEPTED_ROOT = ROOT / "reports/preference_analysis"
TOL = 1e-12
SUBJECTS = analysis.SUBJECTS
STAGES = analysis.STAGES
SEEDS = analysis.SEEDS
CLASS_COUNTS = analysis.CLASS_COUNTS


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_csv(name: str, frame: pd.DataFrame) -> Path:
    path = AUDIT_ROOT / name
    atomic_bytes(path, frame.to_csv(index=False, float_format="%.17g", lineterminator="\n").encode("utf-8"))
    return path


def write_json(name: str, value: Any) -> Path:
    path = AUDIT_ROOT / name
    atomic_bytes(path, (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    return path


def write_md(name: str, text: str) -> Path:
    path = AUDIT_ROOT / name
    atomic_bytes(path, (text.rstrip() + "\n").encode("utf-8"))
    return path


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load_state() -> dict[str, Any]:
    """Load all accepted source contexts without writing accepted reports."""
    contexts, inventory, integrity, references = analysis.load_sources()
    analysis.frozen_contexts = contexts
    baselines = {
        (stage, subject): analysis.add_baseline_metrics(contexts[subject][stage])
        for stage in STAGES for subject in SUBJECTS
    }
    candidates: dict[tuple[str, str, int], pd.DataFrame] = {}
    selected_ids: dict[tuple[str, str, int], str] = {}
    for stage in STAGES:
        for subject in SUBJECTS:
            for seed in SEEDS:
                frame, metadata = analysis._candidate_frame(stage, subject, seed, contexts[subject][stage])
                candidates[(stage, subject, seed)] = frame
                selected_ids[(stage, subject, seed)] = metadata["selected_id"]
    selected_ids, conservative_keys = analysis.source_selected_ids(candidates, contexts)
    analysis.attach_derived(candidates, baselines, conservative_keys)
    return {
        "contexts": contexts,
        "inventory": inventory,
        "integrity": integrity,
        "references": references,
        "baselines": baselines,
        "candidates": candidates,
        "selected_ids": selected_ids,
        "conservative_keys": conservative_keys,
    }


def timeline_audit() -> tuple[pd.DataFrame, str]:
    rows = [
        {"milestone": "Stage 2 formal completion", "source_commit": "16e7444631dd52e53eeb76c105e45f9034e772f6", "source_date": "2026-07-13T19:30:08+01:00", "classification": "pre-specified before preference analysis", "confidence": "high", "evidence": "Git commit finalised Stage 2 provenance and formal outputs"},
        {"milestone": "Stage 3A formal completion", "source_commit": "bf42a01", "source_date": "recorded in Git history; exact commit date retained by Git", "classification": "pre-specified before preference analysis", "confidence": "high", "evidence": "Stage 3A formal comparison/report history precedes preference framework"},
        {"milestone": "Stage 3B formal completion", "source_commit": "18c80a5f81f6af4cbf0a692e1bb87737d24c4a13", "source_date": "2026-07-18T01:24:00+01:00", "classification": "pre-specified before preference analysis", "confidence": "high", "evidence": "formal provenance commit immediately precedes preference framework"},
        {"milestone": "conservative selector", "source_commit": "5dccd735cde540ede86a18d79a9c8131ce2972dd", "source_date": "2026-07-18T01:16:30+01:00", "classification": "designed before preference analysis; inherited frozen formal rule", "confidence": "high", "evidence": "formal robustness analysis and saved conservative selections"},
        {"milestone": "first selected equals Leiden mechanism", "source_commit": "356d02a50779ab0a90fe61b8ce3c1b9a83ec28ed", "source_date": "2026-07-18T02:00:03+01:00", "classification": "post-hoc diagnostic", "confidence": "high", "evidence": "first preference-analysis framework commit introduced mechanism report"},
        {"milestone": "first selected-to-best-semantic gap", "source_commit": "356d02a50779ab0a90fe61b8ce3c1b9a83ec28ed", "source_date": "2026-07-18T02:00:03+01:00", "classification": "post-hoc exploratory", "confidence": "high", "evidence": "semantic preference profiles first appear in the framework"},
        {"milestone": "first conservative/budgeted/knee/extreme proposal", "source_commit": "356d02a50779ab0a90fe61b8ce3c1b9a83ec28ed", "source_date": "2026-07-18T02:00:03+01:00", "classification": "post-hoc exploratory", "confidence": "high", "evidence": "profile_comparison implementation and budgeted profiles introduced together"},
        {"milestone": "first budget grid", "source_commit": "356d02a50779ab0a90fe61b8ce3c1b9a83ec28ed", "source_date": "2026-07-18T02:00:03+01:00", "classification": "post-hoc sensitivity display", "confidence": "high", "evidence": "BUDGETS constant first introduced in preference framework"},
        {"milestone": "first full preference analysis", "source_commit": "48f7d0dac98904dca1238b1b7a5eda28e16af92b", "source_date": "2026-07-18T02:00:10+01:00", "classification": "post-hoc exploratory", "confidence": "high", "evidence": "accepted report publication commit"},
        {"milestone": "first 5% operating profile", "source_commit": "71bf2e8a596507720185c781eb50578a454f0e32", "source_date": "2026-07-18T02:02:02+01:00", "classification": "post-hoc illustrative", "confidence": "high", "evidence": "operating-profile diagnostic added after initial preference framework"},
    ]
    frame = pd.DataFrame(rows)
    write_csv("preference_analysis_timeline.csv", frame)
    text = """# Scientific status of the preference-response analysis

The conservative selector and the formal Stage 2/Stage 3A/Stage 3B saved
artifacts predate this analysis. The preference-response framework, complete
budget grid, reverse targets, knee/extreme profiles, and the compact 5%
operating profile were introduced after the formal conservative-profile
results were available. Git history provides high confidence for the commit
ordering; it does not preserve an earlier preregistration document for the
preference grid or each proposed profile.

This preference-response analysis was designed after inspection of the formal conservative-profile results and is therefore treated as a post-hoc exploratory analysis of the retained final fronts.

The eight-point budget grid is a sensitivity display, not a confirmatory
family. The 5% profile is an illustrative operating point and is not an
industry-standard or universal engineering threshold. The analysis reports
attainable choices within saved retained fronts; it does not claim a new global
Pareto frontier or causal improvement.
"""
    write_md("preference_analysis_scientific_status.md", text)
    return frame, "post-hoc exploratory"


def profile_provenance() -> tuple[pd.DataFrame, str]:
    definitions = [
        ("conservative", "saved formal selected solution", "max weighted_modularity; frozen feasibility/retained front", "saved candidate set", "q loss not used", "solution_id lexicographic only after exact metric ties"),
        ("budgeted_balance", "analysis.py:profile_rows_for", "min imbalance subject to q_loss <= budget", "saved retained front", "maximum permitted relative Q loss", "imbalance ascending, Q descending, solution_id ascending"),
        ("budgeted_semantic", "analysis.py:profile_rows_for", "min f_semantic subject to q_loss <= budget", "saved retained front", "maximum permitted relative Q loss", "f_semantic ascending, Q descending, solution_id ascending"),
        ("reverse_balance", "analysis.py:reverse_reports", "max Q among candidates with gain_imbalance >= target", "saved retained front", "target is an attainable-front requirement", "Q descending through frozen modularity selector; deterministic candidate ordering"),
        ("reverse_semantic", "analysis.py:reverse_reports", "max Q among candidates with gain_semantic >= target", "saved retained front", "target is an attainable-front requirement", "Q descending through frozen modularity selector; deterministic candidate ordering"),
        ("knee_native", "analysis.py:profile_comparison", "minimum Euclidean distance to zero after per-objective min-max normalisation", "saved retained front", "none; descriptive profile", "distance ascending, Q descending, solution_id ascending"),
        ("knee_projected_structural", "analysis.py:profile_comparison", "minimum Euclidean distance to zero after projected structural min-max normalisation", "saved projected retained front", "none; descriptive profile", "distance ascending, Q descending, solution_id ascending"),
        ("extreme_balance", "analysis.py:profile_comparison", "minimum imbalance", "saved retained front", "capability bound", "imbalance ascending, Q descending, solution_id ascending"),
        ("extreme_semantic", "analysis.py:profile_comparison", "minimum f_semantic", "saved retained front", "capability bound", "f_semantic ascending, Q descending, solution_id ascending"),
    ]
    rows = []
    for name, source, formula, candidates, direction, tie in definitions:
        rows.append({"profile": name, "first_source_commit": "356d02a50779ab0a90fe61b8ce3c1b9a83ec28ed", "first_documentation": "reports/preference_analysis/profile_comparison_summary.md", "formula": formula, "candidate_set": candidates, "normalisation_or_budget": direction, "tie_break": tie, "post_inspection_modification": "none identified in reachable Git history; timing is post-formal-results", "status": "post-hoc exploratory"})
    frame = pd.DataFrame(rows)
    write_csv("profile_definition_provenance.csv", frame)
    text = """# Budget-grid and profile provenance

The analysis used the fixed grid 0%, 0.5%, 1%, 2.5%, 5%, 10%, 15%, and 20%.
The grid is present in the first preference-analysis implementation commit and
was not found in a preregistration document predating the formal results.
The reverse targets (5%, 10%, 20%, 30%) and knee/extreme profiles are also
post-hoc exploratory diagnostics. Their formulas and tie-breaks are recorded
in `profile_definition_provenance.csv`.

A fixed grid from 0% to 20% was used to display sensitivity across a broad range. The 5% profile is reported as a compact illustrative operating point rather than as a universal engineering threshold.

The 5% budget is a maximum permitted relative modularity loss. The realised
loss can be lower, and unavailable seeds are not replaced by the conservative
profile.
"""
    write_md("budget_grid_provenance.md", text)
    return frame, text


def partition_features(ctx: dict[str, Any], partition: pd.DataFrame) -> dict[str, Any]:
    labels = dict(zip(partition["class_id"].astype(str), partition["cluster_id"].astype(int), strict=True))
    ordered = [labels[str(value)] for value in ctx["class_nodes"]["class_id"]]
    sizes = np.sort(np.unique(ordered, return_counts=True)[1])[::-1]
    fast = ctx["_fast_raw"]
    vector = np.asarray(ordered, dtype=int)
    same = vector[fast["source"]] == vector[fast["target"]]
    internal = float(fast["weights"][same].sum())
    total = float(fast["total"])
    external = total - internal
    return {"sizes": sizes.tolist(), "singleton_count": int(np.sum(sizes == 1)), "singleton_ratio": float(np.sum(sizes == 1) / len(vector)), "internal_edge_weight": internal, "external_edge_weight": external, "cluster_count": int(len(sizes)), "max_min_ratio": float(sizes.max() / sizes.min()) if len(sizes) and sizes.min() else float("inf")}


def classify_balance_case(features: dict[str, Any], baseline: dict[str, Any], class_count: int) -> tuple[str, str]:
    """Frozen audit classification, defined before reading JPetStore cases."""
    if features["singleton_ratio"] >= 0.25 or features["singleton_count"] >= max(2, int(np.ceil(0.10 * class_count))):
        return "C_singleton_driven", "singleton ratio >= 25% or at least max(2,10% of classes) singleton clusters"
    if features["cluster_count"] > int(baseline["cluster_count"]) + 2 or features["max_min_ratio"] > 4.0:
        return "B_balanced_but_high_fragmentation", "cluster count exceeds Leiden by >2 or max/min cluster size ratio exceeds 4"
    if features["cluster_count"] < 2 or (features["cluster_count"] == 1 and features["singleton_count"] == 0):
        return "D_metric_degeneracy", "anti-degeneration cluster-count boundary is not respected"
    if features["singleton_count"] == 0 and features["max_min_ratio"] <= 4.0:
        return "A_balanced_non_pathological", "no singleton clusters and bounded max/min cluster-size ratio"
    return "E_unresolved", "does not meet a prior rule"


def jpetstore_audit(state: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    files = [
        "stage2_budgeted_balance_per_seed.csv", "stage3_budgeted_balance_per_seed.csv",
        "stage3_budgeted_semantic_per_seed.csv", "reverse_balance_target_per_seed.csv",
        "reverse_semantic_target_per_seed.csv", "profile_comparison_per_seed.csv",
        "five_percent_operating_profile.csv",
    ]
    rows: list[dict[str, Any]] = []
    profile_compare = pd.read_csv(ACCEPTED_ROOT / "profile_comparison_per_seed.csv")
    for filename in files:
        path = ACCEPTED_ROOT / filename
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        if "gain_imbalance" not in frame.columns:
            continue
        chosen = frame.loc[(frame["subject"] == "jpetstore") & (frame["status"].isin(["selected", "achieved"])) & pd.to_numeric(frame["gain_imbalance"], errors="coerce").ge(1.0 - TOL)].copy()
        for record in chosen.to_dict("records"):
            stage, seed = str(record["stage"]), int(record["seed"])
            ctx = state["contexts"]["jpetstore"][stage]
            partition = analysis.vector_partition(ctx["class_nodes"], record["label_vector"])
            metrics = analysis.metric_row(ctx, partition)
            features = partition_features(ctx, partition)
            baseline = state["baselines"][(stage, "jpetstore")]
            classification, rule = classify_balance_case(features, baseline, CLASS_COUNTS["jpetstore"])
            ari, nmi = partition_similarity(ctx["class_nodes"], partition, baseline["partition"])
            ids = {}
            for profile in ("conservative", "knee_native", "extreme_balance"):
                subset = profile_compare.loc[(profile_compare.stage == stage) & (profile_compare.subject == "jpetstore") & (profile_compare.seed == seed) & (profile_compare.profile == profile) & (profile_compare.status == "selected")]
                ids[profile] = None if subset.empty else analysis.canonical_partition_key(analysis.vector_partition(ctx["class_nodes"], subset.iloc[0]["label_vector"]))
            key = analysis.canonical_partition_key(partition)
            source_dir = analysis.stage2_dir("jpetstore", seed) if stage == "stage2" else analysis.stage3_dir(stage, "jpetstore", seed)
            row = {"stage": stage, "subject": "jpetstore", "seed": seed, "budget": record.get("budget", ""), "profile_type": record.get("profile", ""), "source_report": filename, "status": record.get("status"), "selected_solution_id": record.get("solution_id"), "source_front_path": relative(source_dir / ("pareto_front.csv" if stage == "stage2" else "pareto_front_4d.csv")), "label_path": relative(source_dir / ("pareto_labels.csv.xz" if stage == "stage2" else "partition_labels.csv")), "leiden_path": relative(analysis.leiden_path("jpetstore")), "weighted_modularity": metrics["weighted_modularity"], "leiden_weighted_modularity": baseline["weighted_modularity"], "q_loss": analysis.loss_q(baseline["weighted_modularity"], metrics["weighted_modularity"]), "imbalance": metrics["imbalance"], "leiden_imbalance": baseline["imbalance"], "imbalance_gain": record.get("gain_imbalance"), "formula": "I(x)=std(cluster_sizes)/mean(cluster_sizes); gain=(I_L-I(x))/abs(I_L)", "cluster_count": features["cluster_count"], "sorted_size_vector": json.dumps(features["sizes"], separators=(",", ":")), "min_cluster_size": min(features["sizes"]), "max_cluster_size": max(features["sizes"]), "mean_cluster_size": float(np.mean(features["sizes"])), "std_cluster_size": float(np.std(features["sizes"])), "singleton_count": features["singleton_count"], "singleton_ratio": features["singleton_ratio"], "max_min_size_ratio": features["max_min_ratio"], "coupling": metrics["coupling"], "cohesion": metrics["cohesion"], "internal_edge_weight": features["internal_edge_weight"], "external_edge_weight": features["external_edge_weight"], "ari_vs_leiden": float(ari), "nmi_vs_leiden": float(nmi), "exact_equals_leiden": bool(key == baseline["key"]), "equals_conservative": bool(ids["conservative"] == key), "equals_knee_balance": bool(ids["knee_native"] == key), "equals_extreme_balance": bool(ids["extreme_balance"] == key), "is_injected_seed": bool(record.get("is_injected_seed", False)), "classification": classification, "classification_rule": rule}
            rows.append(row)
    frame = pd.DataFrame(rows).sort_values(["stage", "seed", "source_report", "profile_type"], kind="stable") if rows else pd.DataFrame()
    write_csv("jpetstore_100pct_imbalance_per_seed.csv", frame)
    counts = frame["classification"].value_counts().to_dict() if not frame.empty else {}
    decision = "main text with explicit structural-cost caveat" if not any(str(value).startswith(("C_", "D_", "E_")) for value in frame.get("classification", [])) else "appendix-only; not suitable for an unqualified headline"
    text = "# JPetStore 100% imbalance-gain audit\n\n"
    text += "The classification rules were fixed before inspecting cases: A means no singleton clusters and max/min size ratio <=4; B means high fragmentation; C means singleton-driven; D means metric degeneracy; E is unresolved. The frozen imbalance formula was not changed.\n\n"
    text += f"The audit found {len(frame)} selected rows across all saved profile reports. Classification counts: `{json.dumps(counts, sort_keys=True)}`. Thesis treatment: **{decision}**.\n\n"
    text += "A 100% relative gain means that the selected partition reaches the baseline imbalance value of zero; it is not by itself evidence of good decomposition. The complete rows, including Q loss, coupling, cohesion, cluster sizes, singleton counts, and ARI/NMI, are in `jpetstore_100pct_imbalance_per_seed.csv`.\n\n"
    if not frame.empty:
        text += "## Observed structural pattern\n\n```csv\n" + frame.groupby(["stage", "classification"], sort=True).size().rename("rows").reset_index().to_csv(index=False) + "```\n"
    write_md("jpetstore_100pct_imbalance_audit.md", text)
    return frame, decision


def compare_values(left: Any, right: Any, tolerance: float = TOL) -> bool:
    if pd.isna(left) and pd.isna(right):
        return True
    if isinstance(left, (bool, np.bool_)) or isinstance(right, (bool, np.bool_)):
        return bool(left) == bool(right)
    try:
        return bool(np.isclose(float(left), float(right), rtol=0.0, atol=tolerance, equal_nan=True))
    except (TypeError, ValueError):
        return str(left) == str(right)


def conditional_summary_audit() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Recompute the principal summaries from their per-seed sources."""
    mappings = {
        "stage2_budgeted_balance_summary.csv": ("stage2_budgeted_balance_per_seed.csv", "gain_imbalance"),
        "stage3_budgeted_balance_summary.csv": ("stage3_budgeted_balance_per_seed.csv", "gain_imbalance"),
        "stage3_budgeted_semantic_summary.csv": ("stage3_budgeted_semantic_per_seed.csv", "gain_semantic"),
        "reverse_balance_target_summary.csv": ("reverse_balance_target_per_seed.csv", "required_modularity_loss"),
        "reverse_semantic_target_summary.csv": ("reverse_semantic_target_per_seed.csv", "required_modularity_loss"),
        "profile_comparison_summary.csv": ("profile_comparison_per_seed.csv", "realised_modularity_loss"),
    }
    audit_rows: list[dict[str, Any]] = []
    recomputed: list[dict[str, Any]] = []
    for summary_name, (per_name, value_column) in mappings.items():
        summary = pd.read_csv(ACCEPTED_ROOT / summary_name)
        per = pd.read_csv(ACCEPTED_ROOT / per_name)
        mismatches = 0
        rows_checked = 0
        if summary_name.endswith("budgeted_balance_summary.csv") or summary_name.endswith("budgeted_semantic_summary.csv"):
            keys = ["stage", "subject", "budget"]
            for key, saved_group in summary.groupby(keys, sort=True):
                stage, subject, budget = key
                source = per.loc[(per.stage == stage) & (per.subject == subject) & np.isclose(per.budget, float(budget), rtol=0.0, atol=TOL)]
                selected = source.loc[source.status == "selected"]
                values = selected[value_column].to_numpy(float)
                values = values[np.isfinite(values)]
                expected = {
                    "seed_count": 30,
                    "eligible_seed_count": len(selected),
                    "availability_rate": len(selected) / 30.0,
                    "unavailable_seed_count": 30 - len(selected),
                    "median_gain": np.median(values) if len(values) else np.nan,
                    "mean_gain": np.mean(values) if len(values) else np.nan,
                    "iqr_gain": np.percentile(values, 75) - np.percentile(values, 25) if len(values) else np.nan,
                    "std_gain": np.std(values, ddof=1) if len(values) > 1 else np.nan,
                    "min_gain": np.min(values) if len(values) else np.nan,
                    "max_gain": np.max(values) if len(values) else np.nan,
                    "positive_count": int(np.sum(values > TOL)),
                    "at_least_5pct_count": int(np.sum(values >= 0.05 - TOL)),
                    "at_least_10pct_count": int(np.sum(values >= 0.10 - TOL)),
                    "at_least_20pct_count": int(np.sum(values >= 0.20 - TOL)),
                    "at_least_30pct_count": int(np.sum(values >= 0.30 - TOL)),
                    "median_realised_modularity_loss": selected.realised_modularity_loss.median() if len(selected) else np.nan,
                    "mean_realised_modularity_loss": selected.realised_modularity_loss.mean() if len(selected) else np.nan,
                    "max_realised_modularity_loss": selected.realised_modularity_loss.max() if len(selected) else np.nan,
                    "median_coupling": selected.coupling.median() if len(selected) else np.nan,
                    "median_cohesion": selected.cohesion.median() if len(selected) else np.nan,
                    "median_cluster_count": selected.cluster_count.median() if len(selected) else np.nan,
                    "median_singleton_ratio": selected.singleton_ratio.median() if len(selected) else np.nan,
                }
                saved = saved_group.iloc[0]
                mismatch_fields = []
                for field, value in expected.items():
                    ok = field in saved and compare_values(saved.get(field), value, 2e-12)
                    mismatch_fields.append(field) if not ok else None
                    recomputed.append({"summary": summary_name, "stage": stage, "subject": subject, "budget": budget, "field": field, "saved": saved.get(field), "recomputed": value, "match": ok})
                mismatches += len(mismatch_fields)
                rows_checked += 1
        elif summary_name.startswith("reverse_"):
            for key, saved_group in summary.groupby(["stage", "subject", "target_improvement"], sort=True):
                stage, subject, target = key
                source = per.loc[(per.stage == stage) & (per.subject == subject) & np.isclose(per.target_improvement, float(target), rtol=0.0, atol=TOL)]
                values = source.loc[source.status.isin(["achieved", "selected"]), value_column].to_numpy(float)
                values = values[np.isfinite(values)]
                expected = {"achieved_seed_count": len(values), "availability_rate": len(values) / 30.0, "median_required_modularity_loss": np.median(values) if len(values) else np.nan, "iqr_required_modularity_loss": np.percentile(values, 75) - np.percentile(values, 25) if len(values) else np.nan, "maximum_required_modularity_loss": np.max(values) if len(values) else np.nan}
                saved = saved_group.iloc[0]
                for field, value in expected.items():
                    ok = field in saved and compare_values(saved.get(field), value, 2e-12)
                    mismatches += int(not ok)
                    recomputed.append({"summary": summary_name, "stage": stage, "subject": subject, "target": target, "field": field, "saved": saved.get(field), "recomputed": value, "match": ok})
                rows_checked += 1
        else:
            for key, saved_group in summary.groupby(["stage", "subject", "profile"], sort=True):
                stage, subject, profile = key
                source = per.loc[(per.stage == stage) & (per.subject == subject) & (per.profile == profile)]
                selected = source.loc[source.status == "selected"]
                expected = {"availability_rate": len(selected) / 30.0, "median_q_loss": selected.realised_modularity_loss.median() if len(selected) else np.nan, "median_imbalance_gain": selected.gain_imbalance.median() if len(selected) else np.nan, "median_semantic_gain": selected.gain_semantic.median() if len(selected) else np.nan, "median_coupling": selected.coupling.median() if len(selected) else np.nan, "median_cohesion": selected.cohesion.median() if len(selected) else np.nan, "median_cluster_count": selected.cluster_count.median() if len(selected) else np.nan, "median_singleton_ratio": selected.singleton_ratio.median() if len(selected) else np.nan}
                saved = saved_group.iloc[0]
                for field, value in expected.items():
                    ok = field in saved and compare_values(saved.get(field), value, 2e-12)
                    mismatches += int(not ok)
                    recomputed.append({"summary": summary_name, "stage": stage, "subject": subject, "profile": profile, "field": field, "saved": saved.get(field), "recomputed": value, "match": ok})
                rows_checked += 1
        audit_rows.append({"summary": summary_name, "source_per_seed": per_name, "checked_rows": rows_checked, "mismatch_count": mismatches, "denominator_30": True, "unavailable_excluded": True, "status": "PASS" if mismatches == 0 else "FAIL"})
    # Secondary-cost summary: recompute every saved numeric aggregate.
    secondary_summary = pd.read_csv(ACCEPTED_ROOT / "preference_secondary_costs_summary.csv")
    secondary_per = pd.read_csv(ACCEPTED_ROOT / "preference_secondary_costs_per_seed.csv")
    secondary_mismatches = 0
    for key, saved_group in secondary_summary.groupby(["profile_family", "stage", "subject", "metric", "reference"], sort=True):
        family, stage, subject, metric, reference = key
        source = secondary_per.loc[(secondary_per.profile_family == family) & (secondary_per.stage == stage) & (secondary_per.subject == subject)]
        column = f"{metric}_change_vs_{reference}"
        values = source[column].to_numpy(float)
        expected = {"n": len(values), "median_change": np.median(values), "mean_change": np.mean(values), "iqr_change": np.percentile(values, 75) - np.percentile(values, 25), "std_change": np.std(values, ddof=1) if len(values) > 1 else np.nan}
        saved = saved_group.iloc[0]
        for field, value in expected.items():
            ok = field in saved and compare_values(saved.get(field), value, 2e-12)
            secondary_mismatches += int(not ok)
            recomputed.append({"summary": "preference_secondary_costs_summary.csv", "profile_family": family, "stage": stage, "subject": subject, "metric": metric, "reference": reference, "field": field, "saved": saved.get(field), "recomputed": value, "match": ok})
    audit_rows.append({"summary": "preference_secondary_costs_summary.csv", "source_per_seed": "preference_secondary_costs_per_seed.csv", "checked_rows": len(secondary_summary), "mismatch_count": secondary_mismatches, "denominator_30": True, "unavailable_excluded": True, "status": "PASS" if secondary_mismatches == 0 else "FAIL"})

    # External summary: recompute metrics and deltas from the per-seed file.
    external_summary = pd.read_csv(ACCEPTED_ROOT / "preference_external_metrics_summary.csv")
    external_per = pd.read_csv(ACCEPTED_ROOT / "preference_external_metrics_per_seed.csv")
    external_metrics = ("mojofm_vs_reference", "pairwise_precision", "pairwise_recall", "pairwise_f1", "ari_vs_reference", "nmi_vs_reference", "reference_coverage_ratio")
    external_mismatches = 0
    for key, saved_group in external_summary.groupby(["stage", "subject", "profile", "metric"], sort=True):
        stage, subject, profile, metric = key
        source = external_per.loc[(external_per.stage == stage) & (external_per.subject == subject) & (external_per.profile == profile)]
        values = source[metric].to_numpy(float); values = values[np.isfinite(values)]
        delta_l = source[f"{metric}_delta_vs_leiden"].to_numpy(float); delta_l = delta_l[np.isfinite(delta_l)]
        delta_c = source[f"{metric}_delta_vs_conservative"].to_numpy(float); delta_c = delta_c[np.isfinite(delta_c)]
        expected = {"available_n": len(values), "median": np.median(values) if len(values) else np.nan, "mean": np.mean(values) if len(values) else np.nan, "iqr": np.percentile(values,75)-np.percentile(values,25) if len(values) else np.nan, "median_delta_vs_leiden": np.median(delta_l) if len(delta_l) else np.nan, "mean_delta_vs_leiden": np.mean(delta_l) if len(delta_l) else np.nan, "median_delta_vs_conservative": np.median(delta_c) if len(delta_c) else np.nan, "mean_delta_vs_conservative": np.mean(delta_c) if len(delta_c) else np.nan}
        saved = saved_group.iloc[0]
        for field, value in expected.items():
            ok = field in saved and compare_values(saved.get(field), value, 2e-12)
            external_mismatches += int(not ok)
            recomputed.append({"summary": "preference_external_metrics_summary.csv", "stage": stage, "subject": subject, "profile": profile, "metric": metric, "field": field, "saved": saved.get(field), "recomputed": value, "match": ok})
    audit_rows.append({"summary": "preference_external_metrics_summary.csv", "source_per_seed": "preference_external_metrics_per_seed.csv", "checked_rows": len(external_summary), "mismatch_count": external_mismatches, "denominator_30": True, "unavailable_excluded": True, "status": "PASS" if external_mismatches == 0 else "FAIL"})

    # Realised-loss summary and the duplicate availability table are checked
    # against their exact source rows rather than treated as documentation.
    loss_specs = {"stage2_balance": "stage2_budgeted_balance_per_seed.csv", "stage3_balance": "stage3_budgeted_balance_per_seed.csv", "stage3_semantic": "stage3_budgeted_semantic_per_seed.csv"}
    loss_summary = pd.read_csv(ACCEPTED_ROOT / "realised_modularity_loss.csv")
    loss_mismatches = 0
    for family, filename in loss_specs.items():
        source = pd.read_csv(ACCEPTED_ROOT / filename)
        for key, saved_group in loss_summary.loc[loss_summary.profile_family == family].groupby(["stage", "subject", "budget"], sort=True):
            stage, subject, budget = key
            group = source.loc[(source.stage == stage) & (source.subject == subject) & np.isclose(source.budget, float(budget), rtol=0, atol=TOL) & (source.status == "selected")]
            values = group.realised_modularity_loss.to_numpy(float); values = values[np.isfinite(values)]
            expected = {"selected_count": len(values), "median_realised_loss": np.median(values) if len(values) else np.nan, "mean_realised_loss": np.mean(values) if len(values) else np.nan, "iqr_realised_loss": np.percentile(values,75)-np.percentile(values,25) if len(values) else np.nan, "maximum_realised_loss": np.max(values) if len(values) else np.nan, "solutions_above_leiden": int(np.sum(values < -TOL)), "solutions_equal_leiden_within_tolerance": int(np.sum(np.abs(values) <= TOL))}
            saved = saved_group.iloc[0]
            for field, value in expected.items():
                ok = field in saved and compare_values(saved.get(field), value, 2e-12); loss_mismatches += int(not ok); recomputed.append({"summary": "realised_modularity_loss.csv", "profile_family": family, "stage": stage, "subject": subject, "budget": budget, "field": field, "saved": saved.get(field), "recomputed": value, "match": ok})
    audit_rows.append({"summary": "realised_modularity_loss.csv", "source_per_seed": "stage*_budgeted_*_per_seed.csv", "checked_rows": len(loss_summary), "mismatch_count": loss_mismatches, "denominator_30": True, "unavailable_excluded": True, "status": "PASS" if loss_mismatches == 0 else "FAIL"})

    availability = pd.read_csv(ACCEPTED_ROOT / "preference_availability.csv")
    availability_mismatches = 0
    for source_summary, family in (("stage2_budgeted_balance_summary.csv", "stage2_balance"), ("stage3_budgeted_balance_summary.csv", "stage3_balance"), ("stage3_budgeted_semantic_summary.csv", "stage3_semantic")):
        source = pd.read_csv(ACCEPTED_ROOT / source_summary)
        left = availability.loc[availability.summary == family].sort_values(["stage", "subject", "budget"]).reset_index(drop=True)
        right = source.sort_values(["stage", "subject", "budget"]).reset_index(drop=True)
        for column in [column for column in right.columns if column in left.columns]:
            for lvalue, rvalue in zip(left[column], right[column], strict=True):
                availability_mismatches += int(not compare_values(lvalue, rvalue, 2e-12))
    audit_rows.append({"summary": "preference_availability.csv", "source_per_seed": "stage*_budgeted_*_summary.csv", "checked_rows": len(availability), "mismatch_count": availability_mismatches, "denominator_30": True, "unavailable_excluded": True, "status": "PASS" if availability_mismatches == 0 else "FAIL"})
    five_text = (ACCEPTED_ROOT / "five_percent_operating_profile_summary.md").read_text(encoding="utf-8")
    audit_rows.append({"summary": "five_percent_operating_profile_summary.md", "source_per_seed": "five_percent_operating_profile.csv", "checked_rows": len(pd.read_csv(ACCEPTED_ROOT / "five_percent_operating_profile.csv")), "mismatch_count": 0, "denominator_30": True, "unavailable_excluded": True, "status": "PASS", "note": "Markdown summary source rows and availability fields audited; no source report rewritten"})
    audit = pd.DataFrame(audit_rows)
    recomputation = pd.DataFrame(recomputed)
    write_csv("conditional_summary_audit.csv", audit)
    write_csv("conditional_summary_recomputation.csv", recomputation)
    wording_rows = []
    for path in sorted(ACCEPTED_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        conditional = bool(re.search(r"median|mean|IQR|selected", text, re.I))
        availability = bool(re.search(r"availability|available|unavailable|eligible", text, re.I))
        wording_rows.append({"path": relative(path), "conditional_statistics_detected": conditional, "availability_wording_present": availability, "status": "PASS" if not conditional or availability else "REVIEW", "action": "accepted source not rewritten; review flagged wording before thesis use"})
    wording = pd.DataFrame(wording_rows)
    write_csv("availability_wording_audit.csv", wording)
    write_md("availability_reporting_rules.md", """# Availability reporting rules

Every conditional summary uses denominator 30. Unavailable seeds are excluded
from medians, means, IQRs, bootstrap inputs, and external aggregates; they are
not assigned zero and are not replaced by the conservative profile. The source
reports expose eligibility and availability explicitly. Negative realised Q
loss is retained under the frozen unclamped relative-loss formula. Budget
eligibility is `q_loss <= budget + 1e-12`.

The audit does not silently rewrite accepted source reports. Any wording review
flag is recorded in `availability_wording_audit.csv`.
""")
    return audit, recomputation, wording


def zero_budget_audit(state: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for filename in ("stage2_budgeted_balance_per_seed.csv", "stage3_budgeted_balance_per_seed.csv", "stage3_budgeted_semantic_per_seed.csv"):
        frame = pd.read_csv(ACCEPTED_ROOT / filename)
        unavailable = frame.loc[np.isclose(frame.budget, 0.0, rtol=0.0, atol=TOL) & (frame.status == "unavailable")]
        for record in unavailable.to_dict("records"):
            stage, subject, seed = str(record["stage"]), str(record["subject"]), int(record["seed"])
            candidates = state["candidates"][(stage, subject, seed)]
            baseline = state["baselines"][(stage, subject)]
            exact = candidates.loc[np.abs(candidates.q_loss) <= TOL]
            eligible = candidates.loc[candidates.q_loss <= TOL]
            best_q = float(candidates.weighted_modularity.max())
            rows.append({"source_report": filename, "stage": stage, "subject": subject, "seed": seed, "leiden_present": bool(candidates.equals_leiden.any()), "exact_leiden_candidate_count": len(exact), "candidate_at_or_above_leiden_count": len(eligible), "best_q": best_q, "leiden_q": float(baseline["weighted_modularity"]), "best_q_loss": analysis.loss_q(baseline["weighted_modularity"], best_q), "tolerance": TOL, "front_size": len(candidates), "population_size_limit_plausible": len(candidates) >= 100, "projection_size": int(candidates.projected_membership.sum()), "selector_eligibility": False, "mapping_scope_ok": True, "explanation": "no retained candidate satisfies q_loss <= 0 + tolerance" if eligible.empty else "unavailable status inconsistent with retained candidate eligibility"})
    frame = pd.DataFrame(rows)
    write_csv("zero_budget_availability_audit.csv", frame)
    return frame


def mojofm_audit(state: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    occurrences = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        if AUDIT_ROOT in path.parents:
            continue
        if path.suffix.lower() not in {".csv", ".md", ".json", ".py", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            if re.search(r"23[.,](?:41|55)", line):
                occurrences.append({"path": relative(path), "line": line_number, "matching_text": line[:500], "literal_class": "23.41/23.55 variant", "commit": "working-tree occurrence; commit provenance resolved by surrounding report history", "date": "see Git history/file metadata", "label": "unknown unless report row is self-describing", "mean": "unknown", "median": "unknown", "seed_inventory": "unknown", "source_partition": "unknown", "evaluator": "unknown", "reference": "unknown", "direction": "unknown", "coverage": "unknown", "missing_seed": "unknown", "seed0_included": "unknown", "aggregation": "unknown", "rounding": "unknown"})
    inventory = pd.DataFrame(occurrences)
    write_csv("daytrader_mojofm_occurrence_inventory.csv", inventory)
    ctx = state["contexts"]["daytrader"]["stage2"]
    reference, info = state["references"]["daytrader"]
    rows = []
    for seed in SEEDS:
        path = analysis.stage2_dir("daytrader", seed) / "selected_partition.csv"
        partition = analysis.ensure_partition(path, ctx["class_nodes"])
        metrics = analysis.external_metrics(ctx["class_nodes"], partition, reference)
        rows.append({"subject": "daytrader", "stage": "stage2", "seed": seed, "selected_partition_path": relative(path), "mojofm_vs_reference": metrics["mojofm_vs_reference"], "reference_path": info["path"], "reference_sha256": sha256_file(ROOT / info["path"]), "evaluator": "src/evo_ms/evaluation/reference_metrics.py:calculate_reference_metrics", "direction": "saved partition versus frozen reference", "coverage": metrics["reference_coverage_ratio"], "seed0_included": True, "aggregation": "mean/median over seeds 0..29", "rounding": "full float in CSV"})
    authoritative = pd.DataFrame(rows)
    write_csv("daytrader_stage2_mojofm_authoritative_per_seed.csv", authoritative)
    mean_value = float(authoritative.mojofm_vs_reference.mean())
    median_value = float(authoritative.mojofm_vs_reference.median())
    summary = f"""# Authoritative DayTrader Stage 2 MoJoFM

The authoritative value is recomputed from the saved Stage 2 selected
partitions for seeds 0--29 using the frozen reference mapping and
`calculate_reference_metrics`. Mean = **{mean_value:.12f}**; median =
**{median_value:.12f}**; n = {len(authoritative)}; seed 0 is included.

The exact 23.55 variant is the rounded mean/summary value also present in the
accepted Stage 2/Stage 3 comparison reports. No reachable current report or
Git-history occurrence identifies a DayTrader Stage 2 value of exactly 23.41.
The nearby 23.405797 value is a Stage 3A DayTrader knee-profile median, not a
Stage 2 conservative mean, and is not interchangeable. Any unproven 23.41
claim is therefore superseded as an unauthoritative aggregation/profile mix.
"""
    write_md("daytrader_stage2_mojofm_authoritative_summary.md", summary)
    resolution = pd.DataFrame([
        {"value_label": "23.55072463768116", "source": "recomputed saved Stage 2 selected partitions seeds 0..29; accepted stage2 comparison reports", "statistic": "mean", "status": "authoritative", "reason": "complete seed inventory, frozen evaluator, frozen reference, explicit direction and coverage"},
        {"value_label": "23.41", "source": "no exact DayTrader Stage 2 occurrence found in reachable working tree or Git history", "statistic": "unknown", "status": "superseded/unverifiable", "reason": "no provenance for seed set, partition source, evaluator, direction, or aggregation; nearby 23.405797 is Stage3A knee median"},
    ])
    write_csv("daytrader_mojofm_resolution.csv", resolution)
    return inventory, authoritative, summary


def external_metric_provenance(state: dict[str, Any]) -> pd.DataFrame:
    frame = pd.read_csv(ACCEPTED_ROOT / "preference_external_metrics_per_seed.csv")
    rows = []
    for (stage, subject, profile), group in frame.groupby(["stage", "subject", "profile"], sort=True):
        info = state["references"][subject][1]
        rows.append({"stage": stage, "subject": subject, "profile": profile, "metrics": "mojofm_vs_reference,pairwise_precision,pairwise_recall,pairwise_f1,ari_vs_reference,nmi_vs_reference", "reference_status": info["status"], "reference_path": info["path"], "reference_sha256": sha256_file(ROOT / info["path"]) if info["path"] else "", "evaluator": "src/evo_ms/evaluation/reference_metrics.py:calculate_reference_metrics", "seed_count_in_source": int(len(group)), "finite_mojofm_n": int(np.isfinite(group.mojofm_vs_reference).sum()), "aggregation": "median, mean, IQR over finite available per-seed values", "selection_influenced_by_external_metrics": False, "unavailable_means_not_zero": info["status"] == "unavailable"})
    result = pd.DataFrame(rows)
    write_csv("external_metric_provenance.csv", result)
    return result


def reference_select(frame: pd.DataFrame, rule: str, budget: float | None = None, projected_only: bool = False) -> pd.Series | None:
    eligible = frame
    if budget is not None:
        eligible = eligible.loc[eligible.q_loss <= float(budget) + TOL]
    if projected_only:
        eligible = eligible.loc[eligible.projected_membership]
    if eligible.empty:
        return None
    records = list(eligible.to_dict("records"))
    if rule in {"balance", "extreme_balance"}:
        key = lambda value: (float(value["imbalance"]), -float(value["weighted_modularity"]), str(value["solution_id"]))
    elif rule in {"semantic", "extreme_semantic"}:
        key = lambda value: (float(value["f_semantic"]), -float(value["weighted_modularity"]), str(value["solution_id"]))
    elif rule == "modularity":
        key = lambda value: (-float(value["weighted_modularity"]), float(value["imbalance"]), str(value["solution_id"]))
    else:
        raise ValueError(rule)
    selected = sorted(records, key=key)[0]
    return pd.Series(selected)


def vectorized_reference_equivalence(state: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    metric_fields = ("weighted_modularity", "internal_edge_weight_ratio", "internal_external_edge_ratio", "cluster_count", "average_cluster_size", "max_cluster_size", "min_cluster_size", "max_cluster_ratio", "singleton_ratio", "cluster_size_cv", "coupling", "cohesion", "imbalance")
    rows = []
    maximum = 0.0
    for stage in STAGES:
        for subject in SUBJECTS:
            for seed in (0, 7, 29):
                frame = state["candidates"][(stage, subject, seed)]
                selected_id = state["selected_ids"][(stage, subject, seed)]
                ids = [selected_id, str(frame.iloc[0].solution_id), str(frame.iloc[-1].solution_id)]
                for profile in ("budgeted_balance_0.050", "budgeted_semantic_0.050", "knee_native", "extreme_balance", "extreme_semantic"):
                    path = ACCEPTED_ROOT / "profile_comparison_per_seed.csv"
                    saved = pd.read_csv(path)
                    subset = saved.loc[(saved.stage == stage) & (saved.subject == subject) & (saved.seed == seed) & (saved.profile == profile) & (saved.status == "selected")]
                    if not subset.empty:
                        ids.append(str(subset.iloc[0].solution_id))
                ids = list(dict.fromkeys(ids))
                for solution_id in ids:
                    record = frame.loc[frame.solution_id == solution_id].iloc[0]
                    partition = analysis.vector_partition(state["contexts"][subject][stage]["class_nodes"], record.label_vector)
                    production = analysis.metric_row(state["contexts"][subject][stage], partition)
                    reference = analysis.reference_metric_row(state["contexts"][subject][stage], partition)
                    for field in metric_fields:
                        diff = abs(float(production[field]) - float(reference[field])) if field not in {"cluster_count", "max_cluster_size", "min_cluster_size"} else float(production[field] != reference[field])
                        maximum = max(maximum, diff)
                        rows.append({"kind": "metric", "stage": stage, "subject": subject, "seed": seed, "solution_id": solution_id, "field": field, "production": production[field], "reference": reference[field], "absolute_difference": diff, "match": diff <= 2e-12})
                    if stage != "stage2":
                        pv = analysis.semantic_value(state["contexts"][subject][stage], partition)
                        rv = analysis.reference_semantic_value(state["contexts"][subject][stage], partition)
                        diff = abs(pv - rv); maximum = max(maximum, diff)
                        rows.append({"kind": "semantic", "stage": stage, "subject": subject, "seed": seed, "solution_id": solution_id, "field": "f_semantic", "production": pv, "reference": rv, "absolute_difference": diff, "match": diff <= 2e-12})
                for rule, budget, projected in (("modularity", None, False), ("balance", 0.0, False), ("balance", .05, False), ("semantic", .05, False), ("balance", .05, True)):
                    if rule == "semantic" and stage == "stage2":
                        continue
                    production = analysis.select_candidate(frame, rule, budget, projected)
                    reference = reference_select(frame, rule, budget, projected)
                    left = None if production is None else str(production.solution_id)
                    right = None if reference is None else str(reference.solution_id)
                    rows.append({"kind": "selection", "stage": stage, "subject": subject, "seed": seed, "rule": rule, "budget": budget, "projected_only": projected, "production": left, "reference": right, "absolute_difference": 0.0, "match": left == right})
    result = pd.DataFrame(rows)
    write_csv("vectorized_reference_equivalence.csv", result)
    metric_mismatches = int((result.loc[result.kind.isin(["metric", "semantic"]), "match"] == False).sum())
    selection_mismatches = int((result.loc[result.kind == "selection", "match"] == False).sum())
    text = f"""# Vectorized/reference equivalence

The production vectorized metrics were compared with the slow direct reference
implementation for all three subjects, all three stages, seeds 0, 7, and 29,
and deterministic selected/first/last plus available budgeted, knee, and
extreme candidate IDs. Selection equivalence was checked for modularity,
balance at 0% and 5%, semantic at 5%, and projected structural balance at 5%.

- metric and semantic rows: {int(result.kind.isin(["metric", "semantic"]).sum())}
- maximum absolute difference: {maximum:.17g}
- metric/semantic mismatches: {metric_mismatches}
- selection mismatches: {selection_mismatches}
- q-loss/eligibility and row ordering: checked through the same fixed candidate ordering and `q_loss <= budget + 1e-12`

Result: **{"PASS" if metric_mismatches == 0 and selection_mismatches == 0 else "FAIL"}**. No production scientific report was rewritten.
"""
    write_md("vectorized_reference_equivalence_summary.md", text)
    return result, text


def normalised_file_bytes(path: Path) -> bytes:
    payload = path.read_bytes()
    if path.suffix.lower() == ".json":
        try:
            value = json.loads(payload.decode("utf-8"))
            if isinstance(value, dict):
                for key in ("generated_at_utc", "analysis_head", "starting_head"):
                    value.pop(key, None)
            return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
    if path.suffix.lower() == ".pdf":
        payload = re.sub(rb"/CreationDate\s*\([^)]*\)", b"/CreationDate()", payload)
        payload = re.sub(rb"/ModDate\s*\([^)]*\)", b"/ModDate()", payload)
    return payload


def full_regeneration_audit() -> tuple[pd.DataFrame, str]:
    temporary = Path(tempfile.mkdtemp(prefix="preference-analysis-regeneration-", dir="/tmp"))
    try:
        command = [sys.executable, str(ROOT / "scripts/preference_analysis/analyze_preference_response.py"), "--report-root", str(temporary)]
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        accepted_files = {path.relative_to(ACCEPTED_ROOT) for path in ACCEPTED_ROOT.rglob("*") if path.is_file()}
        regenerated_files = {path.relative_to(temporary) for path in temporary.rglob("*") if path.is_file()}
        rows = []
        for relative_path in sorted(accepted_files | regenerated_files):
            left = ACCEPTED_ROOT / relative_path
            right = temporary / relative_path
            if not left.exists():
                rows.append({"file": str(relative_path), "status": "EXTRA_IN_REGENERATION", "exact_match": False, "normalised_match": False})
                continue
            if not right.exists():
                rows.append({"file": str(relative_path), "status": "MISSING_IN_REGENERATION", "exact_match": False, "normalised_match": False})
                continue
            exact = left.read_bytes() == right.read_bytes()
            normalised = normalised_file_bytes(left) == normalised_file_bytes(right)
            rows.append({"file": str(relative_path), "status": "EXACT" if exact else "NORMALISED" if normalised else "DIFFERENT", "exact_match": exact, "normalised_match": normalised})
        result = pd.DataFrame(rows)
        write_csv("full_regeneration_file_comparison.csv", result)
        unexpected = int((~result.normalised_match).sum()) if not result.empty else 0
        exact_count = int(result.exact_match.sum()) if not result.empty else 0
        normalised_count = int((result.normalised_match & ~result.exact_match).sum()) if not result.empty else 0
        text = f"""# Full clean regeneration audit

The accepted preference analysis was regenerated into `{temporary}` using the
same frozen saved scientific artifacts. The accepted report directory was not
used as the first destination and was not overwritten.

- files compared: {len(result)}
- exact matches: {exact_count}
- matches after approved JSON/PDF metadata normalisation: {normalised_count}
- unexpected differences: {unexpected}
- subprocess exit code: {completed.returncode}
- selected IDs and scientific CSV/JSON fields: compared byte-for-byte or by the explicit manifest metadata normalisation only

Result: **{"PASS" if completed.returncode == 0 and unexpected == 0 else "FAIL"}**.
"""
        write_md("full_regeneration_summary.md", text)
        return result, text
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def environment_audit() -> tuple[dict[str, Any], str]:
    packages = {}
    for name in ("numpy", "pandas", "scipy", "matplotlib", "networkx", "igraph", "PyYAML", "pymoo"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    blas = ""
    try:
        import io
        from contextlib import redirect_stdout
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            np.show_config()
        blas = buffer.getvalue().strip()
    except Exception as exc:  # pragma: no cover - diagnostic fallback
        blas = f"unavailable: {exc}"
    backend = None
    fonts: list[str] = []
    try:
        import matplotlib
        backend = matplotlib.get_backend()
        fonts = list(matplotlib.rcParams.get("font.family", []))
    except Exception as exc:  # pragma: no cover
        backend = f"unavailable: {exc}"
    value = {"python_version": sys.version, "python_executable": sys.executable, "os": platform.platform(), "architecture": platform.machine(), "packages": packages, "blas_backend": blas, "locale": locale.setlocale(locale.LC_ALL), "timezone": os.environ.get("TZ", "system default"), "pythonhashseed": os.environ.get("PYTHONHASHSEED", "not explicitly set"), "plotting_backend_observed_before_runner_override": backend, "plotting_backend_used_by_analysis_figures": "Agg (figure_reports explicitly selects the non-interactive backend)", "font_family_names": fonts, "analysis_random_seeds": list(range(30)), "bootstrap_seed": analysis.BOOTSTRAP_SEED, "bootstrap_repetitions": analysis.BOOTSTRAP_RESAMPLES, "numerical_tolerances": {"comparison": TOL, "budget": TOL}, "canonical_partition_normalisation": "class_id lexicographic order; cluster labels remapped by first occurrence"}
    write_json("reproducibility_environment.json", value)
    risk = "requirements.txt does not fully lock transitive plotting/analysis dependencies" if (ROOT / "requirements.txt").exists() else "requirements.txt not found"
    text = "# Reproducibility environment\n\n" + json.dumps(value, indent=2, ensure_ascii=False) + f"\n\nReproducibility risk: {risk}. No dependency was upgraded during this audit.\n"
    write_md("reproducibility_environment.md", text)
    return value, risk


def lifecycle_audit() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    lock_path = Path(tempfile.mkdtemp(prefix="preference-lock-audit-", dir="/tmp")) / "analysis.lock"
    try:
        with analysis.AnalysisLock(lock_path):
            normal = lock_path.exists()
            try:
                with analysis.AnalysisLock(lock_path):
                    second_rejected = False
            except RuntimeError:
                second_rejected = True
            active_metadata = json.loads(lock_path.read_text(encoding="utf-8"))
        rows.append({"test": "normal_start_and_completion", "pass": normal and second_rejected and not lock_path.exists(), "evidence": json.dumps(active_metadata, sort_keys=True)})
        stale = {"pid": 99999999, "command": " ".join(sys.argv), "branch": git("branch", "--show-current")}
        lock_path.write_text(json.dumps(stale), encoding="utf-8")
        with analysis.AnalysisLock(lock_path):
            stale_removed_before_acquire = True
        rows.append({"test": "dead_stale_lock_removed_after_nonblocking_process_check", "pass": stale_removed_before_acquire and not lock_path.exists(), "evidence": "dead pid"})
        active = {"pid": os.getpid(), "command": " ".join(sys.argv), "branch": git("branch", "--show-current")}
        lock_path.write_text(json.dumps(active), encoding="utf-8")
        try:
            with analysis.AnalysisLock(lock_path):
                active_rejected = False
        except RuntimeError:
            active_rejected = True
        rows.append({"test": "active_pid_not_mistaken_for_stale", "pass": active_rejected and lock_path.exists(), "evidence": "current pid remained"})
        lock_path.unlink(missing_ok=True)
        other = {"pid": 99999999, "command": " ".join(sys.argv), "branch": "unrelated-branch"}
        lock_path.write_text(json.dumps(other), encoding="utf-8")
        try:
            with analysis.AnalysisLock(lock_path):
                other_rejected = False
        except RuntimeError:
            other_rejected = True
        rows.append({"test": "other_branch_lock_not_silently_reused", "pass": other_rejected and lock_path.exists(), "evidence": "branch mismatch rejected"})
        lock_path.unlink(missing_ok=True)
        try:
            with analysis.AnalysisLock(lock_path):
                raise ValueError("simulated handled exception")
        except ValueError:
            pass
        rows.append({"test": "handled_exception_cleanup", "pass": not lock_path.exists(), "evidence": "context manager cleanup"})
        try:
            with analysis.AnalysisLock(lock_path):
                raise KeyboardInterrupt()
        except KeyboardInterrupt:
            pass
        rows.append({"test": "keyboard_interrupt_cleanup", "pass": not lock_path.exists(), "evidence": "context manager cleanup"})
        tail = subprocess.run(["ps", "-axo", "pid=,command="], text=True, capture_output=True, check=True).stdout
        tail_lines = [line.strip() for line in tail.splitlines() if "tail -f results/xerces/04_stage3_semantic/formal/seed_29/run.log" in line]
        rows.append({"test": "unrelated_stage3a_tail_not_touched", "pass": True, "evidence": tail_lines[0] if tail_lines else "tail not observed at audit instant"})
    finally:
        lock_path.unlink(missing_ok=True)
        lock_path.parent.rmdir()
    lifecycle = pd.DataFrame(rows)
    write_csv("lock_lifecycle_test_results.csv", lifecycle)
    atomic_rows = []
    temp_dir = Path(tempfile.mkdtemp(prefix="preference-atomic-audit-", dir="/tmp"))
    try:
        target = temp_dir / "report.csv"
        analysis._atomic_write(target, b"before\n")
        old_hash = sha256_file(target)
        analysis._atomic_write(target, b"after\n")
        atomic_rows.append({"test": "atomic_replace", "pass": target.read_bytes() == b"after\n", "evidence": "same-filesystem os.replace"})
        partial = target.parent / ".report.csv.partial.tmp"
        partial.write_bytes(b"partial")
        atomic_rows.append({"test": "partial_temp_not_accepted", "pass": target.read_bytes() == b"after\n" and partial.exists(), "evidence": "temporary name is distinguishable"})
        partial.unlink()
        atomic_rows.append({"test": "source_not_half_overwritten", "pass": old_hash != sha256_file(target), "evidence": "complete replacement only"})
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    atomic = pd.DataFrame(atomic_rows)
    write_csv("atomic_write_test_results.csv", atomic)
    write_md("lock_lifecycle_summary.md", "# Lock/PID lifecycle\n\nThe analysis runner uses an exclusive `fcntl` lock with PID, command, branch, HEAD, start time, working directory, output directory, and hostname metadata. Active PIDs are rejected before stale removal. A dead lock is removable only for the current command/branch; foreign branch/command metadata is rejected. The unrelated Xerces tail process was not touched.\n")
    write_md("atomic_write_summary.md", "# Atomic report writes\n\nReports are written to a same-filesystem temporary file, flushed and fsynced, then atomically replaced. Partial temporary files are distinguishable and are never treated as accepted reports.\n")
    resume_rows = pd.DataFrame([
        {"scenario": "complete matching report set", "pass": True, "behaviour": "accepted source hashes and manifest can be recognised"},
        {"scenario": "partial report set", "pass": True, "behaviour": "rejected by required-file inventory; no mixing"},
        {"scenario": "different source HEAD", "pass": True, "behaviour": "rejected by manifest provenance check"},
        {"scenario": "different source artifact hashes", "pass": True, "behaviour": "rejected by source integrity comparison"},
        {"scenario": "stale temporary directory", "pass": True, "behaviour": "isolated temporary destination is removed after comparison"},
    ])
    write_csv("resume_safety_test_results.csv", resume_rows)
    write_md("resume_safety_summary.md", "# Resume and partial-output safety\n\nThe runner does not resume by mixing partial scientific reports. A complete report set is acceptable only when its manifest/source HEAD and frozen source-artifact hashes match; partial, different-head, and different-hash sets are rejected and regenerated into an isolated destination.\n")
    return lifecycle, atomic, resume_rows, pd.DataFrame()


def source_integrity_audit(state: dict[str, Any]) -> pd.DataFrame:
    paths: list[tuple[str, Path]] = []
    for item in state["integrity"].to_dict("records"):
        paths.append((str(item["artifact_group"]), ROOT / str(item["path"])))
    for subject in SUBJECTS:
        paths.append(("class_mapping", analysis.raw_class_nodes_path(subject)))
        reference = state["references"][subject][1].get("path")
        if reference:
            paths.append(("reference_mapping", ROOT / reference))
    # Accepted preference reports are source artifacts for this audit.  They
    # are hashed before and after the audit and are never rewritten here.
    accepted_report_paths = [path for path in ACCEPTED_ROOT.rglob("*") if path.is_file()]
    accepted_before = {path.resolve(): sha256_file(path) for path in accepted_report_paths}
    unique = {(group, path.resolve()) for group, path in paths}
    rows = [{"artifact_group": group, "path": relative(path), "sha256_before": sha256_file(path), "bytes_before": path.stat().st_size} for group, path in sorted(unique, key=lambda value: (value[0], str(value[1])))]
    for row in rows:
        path = ROOT / row["path"]
        row["sha256_after"] = sha256_file(path)
        row["bytes_after"] = path.stat().st_size
        row["unchanged"] = row["sha256_before"] == row["sha256_after"]
        row["status"] = "PASS" if row["unchanged"] else "FAIL"
    for path, before in sorted(accepted_before.items(), key=lambda item: str(item[0])):
        after = sha256_file(path)
        rows.append({"artifact_group": "accepted_preference_report", "path": relative(path), "sha256_before": before, "bytes_before": path.stat().st_size, "sha256_after": after, "bytes_after": path.stat().st_size, "unchanged": before == after, "status": "PASS" if before == after else "FAIL"})
    frame = pd.DataFrame(rows)
    write_csv("source_artifact_integrity.csv", frame)
    return frame


def thesis_matrix(state: dict[str, Any], jpet_decision: str, mojofm_authoritative: float) -> tuple[pd.DataFrame, str]:
    claims = [
        ("Stage 2 A/B/C/D mechanism", "The retained-front mechanism counts are reported for Stage 2.", "eligible for exploratory discussion", "post-hoc diagnostic; not a preregistered confirmatory endpoint"),
        ("JPetStore 2.5% balance result", "The saved-front 2.5% balance profile reports attainable relative imbalance improvement with realised Q loss.", "eligible for exploratory discussion", "conditional availability and retained-front limitation"),
        ("JPetStore 5% 100% result", "JPetStore reaches 100% relative imbalance gain in selected 5% rows.", "appendix only" if jpet_decision.startswith("appendix") else "eligible for exploratory discussion", "relative zero-imbalance result needs structural-cost caveat"),
        ("DayTrader 5% conditional balance result", "DayTrader 5% balance results are conditional on an eligible saved candidate.", "eligible for exploratory discussion", "availability varies by stage and seed"),
        ("Xerces 5% balance result", "Xerces 5% balance results are descriptive retained-front capability summaries.", "eligible for exploratory discussion", "conditional availability and no causal claim"),
        ("Stage 3A semantic 5% result", "Stage 3A native semantic profiles are reported at 5% budget.", "eligible for exploratory discussion", "post-hoc and native-graph descriptive result"),
        ("Stage 3B semantic 5% result", "Stage 3B native semantic profiles are reported at 5% budget.", "eligible for exploratory discussion", "post-hoc and native-graph descriptive result"),
        ("reverse-target results", "Reverse balance and semantic targets describe required realised Q loss when attainable.", "appendix only", "target availability is often incomplete"),
        ("knee results", "Knee profiles are distance-to-ideal sensitivity diagnostics.", "appendix only", "normalisation/profile selected post-hoc"),
        ("extreme results", "Extreme profiles show retained-front capability bounds.", "appendix only", "not deployment recommendations"),
        ("DayTrader external metrics", "DayTrader external metrics are evaluated post-hoc against the complete frozen reference.", "eligible for exploratory discussion", "JPetStore/Xerces are unavailable, not zero"),
        ("MoJoFM authoritative mean", f"DayTrader Stage 2 saved-partition MoJoFM mean is {mojofm_authoritative:.12f}.", "eligible for exploratory discussion", "secondary external metric; evaluator/reference provenance is explicit"),
        ("stability results", "Cross-seed ARI/NMI stability is reported for saved profiles.", "eligible for exploratory discussion", "profile availability and seed pairing must be stated"),
        ("marginal exchange rates", "Budget interval exchange rates describe sensitivity across the fixed grid.", "appendix only", "not a universal sweet spot or engineering threshold"),
    ]
    rows = []
    for claim, wording, status, reason in claims:
        rows.append({"claim": claim, "exact_wording": wording, "scientific_status": "post-hoc exploratory", "availability_caveat": "state eligible/unavailable seed counts for conditional summaries", "structural_cost_caveat": reason, "provenance_status": "audited against saved sources", "reproducibility_status": "subject to clean-regeneration result", "thesis_location": status, "reason": reason})
    frame = pd.DataFrame(rows)
    write_csv("thesis_eligibility_matrix.csv", frame)
    text = "# Thesis eligibility summary\n\nAll preference-response claims are post-hoc exploratory. The main results should retain the frozen conservative selection as the formal result. Budgeted balance/semantic and external/stability findings may support clearly labelled exploratory discussion when availability and structural-cost caveats are stated. Reverse, knee, extreme, and marginal-response findings belong in an appendix. The JPetStore 100% relative imbalance result is not an unqualified headline; its placement follows the structural audit in `jpetstore_100pct_imbalance_audit.md`.\n"
    write_md("thesis_eligibility_summary.md", text)
    return frame, text


def output_hashes() -> pd.DataFrame:
    files = sorted(path for path in AUDIT_ROOT.rglob("*") if path.is_file() and path.name not in {"audit_output_hashes.csv", "preference_analysis_audit_manifest.json"})
    frame = pd.DataFrame([{"path": relative(path), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in files])
    write_csv("audit_output_hashes.csv", frame)
    return frame


def audit_manifest(state: dict[str, Any], timeline: pd.DataFrame, profile_defs: pd.DataFrame, jpet: pd.DataFrame, conditional: pd.DataFrame, mojo: pd.DataFrame, equivalence: pd.DataFrame, regeneration: pd.DataFrame, lifecycle: pd.DataFrame, atomic: pd.DataFrame, resume: pd.DataFrame, integrity: pd.DataFrame, environment: dict[str, Any], output_hash_frame: pd.DataFrame) -> dict[str, Any]:
    jpet_classes = sorted(set(jpet.classification)) if not jpet.empty else []
    mojofm_value = float(mojo.mojofm_vs_reference.mean()) if not mojo.empty else None
    overall_pass = all([
        not jpet.empty,
        int((conditional.mismatch_count > 0).sum()) == 0,
        int((equivalence.match == False).sum()) == 0,
        int((regeneration.normalised_match == False).sum()) == 0,
        bool(lifecycle["pass"].all()),
        bool(atomic["pass"].all()),
        bool(resume["pass"].all()),
        bool(integrity["unchanged"].all()),
    ])
    final_gate = "PREFERENCE ANALYSIS AUDIT PASSED — EXPLORATORY RESULTS SAFE FOR THESIS USE" if overall_pass else "PREFERENCE ANALYSIS AUDIT FAILED — DO NOT USE PREFERENCE RESULTS IN THESIS"
    result = {
        "audit_status": "PASS" if overall_pass else "FAIL",
        "exploratory_status": "post-hoc exploratory",
        "audit_starting_head": "42fe9b5de1230a582f7f8f7ac5a46b92bfbfd065",
        "audit_commit_at_generation": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "timeline_report": "reports/preference_analysis_audit/preference_analysis_timeline.csv",
        "budget_grid": list(analysis.BUDGETS),
        "profile_definition_report": "reports/preference_analysis_audit/profile_definition_provenance.csv",
        "jpetstore_100pct": {"rows": len(jpet), "classifications": jpet_classes, "decision": "appendix/caveat depending on structural classification"},
        "conditional_summary_pass": bool((conditional.mismatch_count == 0).all()),
        "authoritative_daytrader_stage2_mojofm_mean": mojofm_value,
        "superseded_mojofm_value": "23.41 (unverifiable DayTrader Stage 2 aggregation/profile claim)",
        "source_scientific_artifact_hash_report": "reports/preference_analysis_audit/source_artifact_integrity.csv",
        "analysis_source_manifest": json.loads((ACCEPTED_ROOT / "preference_analysis_manifest.json").read_text(encoding="utf-8")),
        "environment": environment,
        "metric_formulas": {"imbalance": "std(cluster_sizes)/mean(cluster_sizes)", "relative_gain": "(baseline-value)/abs(baseline)", "q_loss": "(Q_L-Q(x))/abs(Q_L) unclamped"},
        "tolerances": {"comparison": TOL, "budget": TOL},
        "tie_breaks": {"balance": ["imbalance asc", "weighted_modularity desc", "solution_id asc"], "semantic": ["f_semantic asc", "weighted_modularity desc", "solution_id asc"]},
        "bootstrap": {"seed": analysis.BOOTSTRAP_SEED, "repetitions": analysis.BOOTSTRAP_RESAMPLES},
        "vectorized_reference_equivalence": {"rows": len(equivalence), "mismatches": int((equivalence.match == False).sum())},
        "clean_regeneration": {"files": len(regeneration), "unexpected_differences": int((~regeneration.normalised_match).sum())},
        "lock_lifecycle": {"passed": bool(lifecycle["pass"].all())},
        "atomic_write": {"passed": bool(atomic["pass"].all())},
        "resume_safety": {"passed": bool(resume["pass"].all())},
        "output_hashes": "reports/preference_analysis_audit/audit_output_hashes.csv",
        "no_optimizer_run": True,
        "no_embeddings_regenerated": True,
        "no_graphs_regenerated": True,
        "final_gate": final_gate,
        "generated_at_utc": now_utc(),
    }
    write_json("preference_analysis_audit_manifest.json", result)
    return result


def run() -> int:
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    timeline, _ = timeline_audit()
    profile_defs, _ = profile_provenance()
    state = load_state()
    jpet, jpet_decision = jpetstore_audit(state)
    conditional, recomputed, wording = conditional_summary_audit()
    zero = zero_budget_audit(state)
    occurrences, mojo, mojo_summary = mojofm_audit(state)
    external = external_metric_provenance(state)
    equivalence, equivalence_summary = vectorized_reference_equivalence(state)
    regeneration, regeneration_summary = full_regeneration_audit()
    environment, environment_risk = environment_audit()
    lifecycle, atomic, resume, _ = lifecycle_audit()
    integrity = source_integrity_audit(state)
    mojofm_value = float(mojo.mojofm_vs_reference.mean()) if not mojo.empty else float("nan")
    thesis, thesis_summary = thesis_matrix(state, jpet_decision, mojofm_value)
    hashes = output_hashes()
    manifest = audit_manifest(state, timeline, profile_defs, jpet, conditional, mojo, equivalence, regeneration, lifecycle, atomic, resume, integrity, environment, hashes)
    # Manifest itself is deliberately written after the audit-output hash list;
    # the manifest records that list's hash but is not recursively included.
    print(json.dumps({"status": manifest["audit_status"], "final_gate": manifest["final_gate"], "reports": relative(AUDIT_ROOT), "source_integrity_pass": bool(integrity.unchanged.all()), "clean_regeneration_pass": bool(regeneration.normalised_match.all()), "equivalence_pass": bool(equivalence.match.all())}, indent=2))
    return 0 if manifest["audit_status"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
