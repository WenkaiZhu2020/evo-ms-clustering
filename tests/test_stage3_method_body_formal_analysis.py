from pathlib import Path

import pandas as pd

from scripts.stage3_method_body import analyze_formal_stage3b as analysis


def test_formal_and_validation_namespaces_are_disjoint_and_exact() -> None:
    for subject in analysis.SUBJECTS:
        assert analysis.stage3b_dir(subject, 0).parts[-2:] == ("validation", "seed_00")
        assert analysis.stage3b_dir(subject, 1).parts[-2:] == ("formal", "seed_01")
        assert analysis.stage3b_dir(subject, 29).parts[-2:] == ("formal", "seed_29")
        assert "04_stage3_semantic" not in str(analysis.stage3b_dir(subject, 1))


def test_holm_adjustment_is_monotone_and_bounded() -> None:
    adjusted = analysis._holm([0.001, 0.02, 0.5, 0.5])
    assert all(0.0 <= value <= 1.0 for value in adjusted)
    assert adjusted[0] <= adjusted[1] <= adjusted[2]
    assert adjusted[2] == adjusted[3]


def test_formal_reports_contain_three_complete_30_seed_inventories() -> None:
    root = Path("reports/stage3_method_body")
    inventory = pd.read_csv(root / "formal_seed_inventory.csv")
    validation = pd.read_csv(root / "formal_validation_per_seed.csv")
    assert len(inventory) == 90
    assert set(inventory["seed"]) == set(range(30))
    assert len(validation) == 180
    assert set(validation["validation_status"]) == {"passed"}
    assert set(validation["representation"]) == {"stage3a", "stage3b"}


def test_registered_formal_spot_checks_are_byte_identical() -> None:
    spot = pd.read_csv(Path("reports/stage3_method_body/formal_reproducibility_spotcheck.csv"))
    assert list(zip(spot["subject"], spot["seed"], strict=True)) == [("jpetstore", 7), ("daytrader", 13), ("xerces", 29)]
    assert spot["all_byte_identical"].astype(bool).all()


def test_formal_results_do_not_create_optimizer_or_graph_namespaces() -> None:
    for subject in analysis.SUBJECTS:
        assert not (Path("results") / subject / "05_stage3_declaration_method_body" / "optimization").exists()
        assert not (Path("results") / subject / "05_stage3_declaration_method_body" / "graph").exists()
        assert not (Path("data/semantic_graphs") / "declaration_method_body" / subject / "seed_01").exists()
