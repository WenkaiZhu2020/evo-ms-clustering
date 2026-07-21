from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SENSITIVITY = ROOT / "results/cross_subject/03_stage2_nsga/modularity_band/sensitivity"
MAX_CLUSTER = ROOT / "results/cross_subject/03_stage2_nsga/final_statistics/max_cluster_posthoc_sensitivity_current_band"


def _selector_module():
    path = ROOT / "experiments/02_stage2_nsga_structure_only/analyze_modularity_band.py"
    spec = importlib.util.spec_from_file_location("sensitivity_selector_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sensitivity_profiles_cover_all_required_budgets() -> None:
    profiles = pd.read_csv(SENSITIVITY / "sensitivity_profiles_per_seed.csv")
    assert len(profiles) == 360
    assert sorted(profiles["budget"].unique()) == [0.01, 0.03, 0.05, 0.10]
    assert not profiles[["subject", "seed", "budget"]].duplicated().any()
    assert set(profiles.groupby(["subject", "budget"], sort=False).size()) == {30}


def test_five_percent_sensitivity_matches_canonical() -> None:
    selector = _selector_module()
    profiles = pd.read_csv(SENSITIVITY / "sensitivity_profiles_per_seed.csv")
    canonical = pd.read_csv(
        ROOT / "results/cross_subject/03_stage2_nsga/modularity_band/canonical_operating_solution_per_seed.csv"
    )
    selected = profiles.loc[profiles["budget"] == 0.05].merge(
        canonical[["subject", "seed", "solution_id", "weighted_modularity", "label_vector"]],
        on=["subject", "seed"],
        suffixes=("_sensitivity", "_canonical"),
        validate="one_to_one",
    )
    assert (selected["solution_id_sensitivity"] == selected["solution_id_canonical"]).all()
    assert (selected["weighted_modularity_sensitivity"] - selected["weighted_modularity_canonical"]).abs().max() <= 1e-12
    canonical_tuples = selected["label_vector"].map(
        lambda value: json.dumps(list(selector.canonical_label_tuple(value)), separators=(",", ":"))
    )
    assert (selected["selected_label_tuple"] == canonical_tuples).all()


def test_sensitivity_manifest_records_posthoc_scope() -> None:
    manifest = json.loads((SENSITIVITY / "sensitivity_manifest.json").read_text(encoding="utf-8"))
    assert manifest["canonical_budget"] == 0.05
    assert manifest["no_optimizer_run"] is True
    assert manifest["no_seed_rerun"] is True
    assert manifest["q_max_role"].endswith("Leiden")
    assert manifest["cohesion_role"].startswith("report-only")


def test_current_max_cluster_replacement_is_separate_from_historical_tables() -> None:
    detail = pd.read_csv(MAX_CLUSTER / "posthoc_max_cluster_sensitivity_per_seed.csv")
    assert len(detail) == 360
    assert sorted(detail["band_budget"].unique()) == [0.05]
    assert not detail[["subject", "seed", "threshold"]].duplicated().any()
    historical = ROOT / "results/cross_subject/03_stage2_nsga/final_statistics/max_cluster_posthoc_sensitivity"
    assert not historical.exists()
