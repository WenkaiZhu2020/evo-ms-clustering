import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_day6_inventory_has_three_complete_subjects() -> None:
    report = json.loads((ROOT / "reports/stage3/formal_seed_inventory.json").read_text())
    assert report["all_pass"] is True
    assert {row["subject"] for row in report["subjects"]} == {"jpetstore", "daytrader", "xerces"}
    assert all(row["expected"] == row["valid"] == 30 for row in report["subjects"])


def test_day6_alignment_report_passes() -> None:
    report = json.loads((ROOT / "reports/stage3/stage2_alignment_check.json").read_text())
    assert report["all_pass"] is True
    assert all(item["pass"] for item in report["subjects"].values())
