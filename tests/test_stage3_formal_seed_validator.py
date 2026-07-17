from pathlib import Path

from scripts.stage3.validate_formal_seed import (
    SUBJECT_CONFIG,
    default_report,
    default_source,
)


ROOT = Path(__file__).resolve().parents[1]


def test_formal_seed_validator_has_frozen_subject_scopes() -> None:
    assert SUBJECT_CONFIG == {
        "jpetstore": {"storage_subject": "jpetstore", "class_count": 24},
        "daytrader": {"storage_subject": "daytrader", "class_count": 53},
        "xerces": {"storage_subject": "xerces-j", "class_count": 814},
    }


def test_formal_seed_validator_resolves_seed_zero_and_formal_paths() -> None:
    assert default_source("jpetstore", 0) == ROOT / "results/jpetstore/04_stage3_semantic/validation/seed_00"
    assert default_source("daytrader", 7) == ROOT / "results/daytrader/04_stage3_semantic/formal/seed_07"
    assert default_report("xerces", 29) == ROOT / "reports/stage3/seed_validation/xerces/seed_29.json"
