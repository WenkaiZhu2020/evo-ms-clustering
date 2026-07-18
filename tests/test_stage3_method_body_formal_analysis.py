"""Focused checks for the final Stage 3 saved-analysis namespace."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.stage3_method_body import analyze_formal_stage3b as analysis


def test_formal_and_validation_namespaces_are_final_and_exact() -> None:
    for subject in analysis.SUBJECTS:
        assert analysis.stage3b_dir(subject, 0).parts[-2:] == ("validation", "seed_00")
        assert analysis.stage3b_dir(subject, 1).parts[-2:] == ("formal", "seed_01")
        assert analysis.stage3b_dir(subject, 29).parts[-2:] == ("formal", "seed_29")
        assert "05_stage3_declaration_method_body" in str(analysis.stage3b_dir(subject, 1))


def test_final_formal_inventory_is_complete_and_single_representation() -> None:
    root = Path("reports/stage3_method_body")
    inventory = pd.read_csv(root / "formal_seed_inventory.csv")
    assert len(inventory) == 90
    assert set(inventory["seed"]) == set(range(30))
    assert set(inventory["representation_id"]) == {"declaration_method_body_v1"}
    assert inventory["artifact_hash_status"].eq("passed").all()


def test_registered_formal_spot_checks_are_byte_identical() -> None:
    spot = pd.read_csv(Path("reports/stage3_method_body/formal_reproducibility_spotcheck.csv"))
    assert list(zip(spot["subject"], spot["seed"], strict=True)) == [("jpetstore", 7), ("daytrader", 13), ("xerces", 29)]
    assert spot["all_byte_identical"].astype(bool).all()


def test_final_experiment_manifest_is_read_only_provenance() -> None:
    manifest = json.loads(Path("reports/stage3_method_body/formal_experiment_manifest.json").read_text(encoding="utf-8"))
    assert manifest["representation_id"] == "declaration_method_body_v1"
    assert manifest["optimizer_run"] is False
    assert manifest["semantic_graphs_regenerated"] is False


def test_formal_results_do_not_create_optimizer_or_graph_namespaces() -> None:
    for subject in analysis.SUBJECTS:
        assert not (Path("results") / subject / "05_stage3_declaration_method_body" / "optimization").exists()
        assert not (Path("results") / subject / "05_stage3_declaration_method_body" / "graph").exists()
