from __future__ import annotations

import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evo_ms.semantic.input_contract import REPRESENTATION_ID, aggregate_input_hash, validate_identity


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HASHES = {
    "jpetstore": "2d9007f75a14f4a4ed6152563241b898837b6c12b66a98a2464b4cc3f969a921",
    "daytrader": "da53d434b820e3c25bc69df63ced807cd0113d412fa36acc9694d1a97631d655",
    "xerces": "65488944220cc3a503994d6f2289e0f7bdc06c619351a2e8243bca243538c8a3",
}


def test_final_input_contract_has_one_representation_and_exact_scope() -> None:
    expected = {"jpetstore": 24, "daytrader": 53, "xerces": 814}
    for subject, count in expected.items():
        path = ROOT / "data/semantic_text/declaration_method_body" / subject / "class_semantic_inputs.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == count
        assert all(row["representation_id"] == REPRESENTATION_ID for row in rows)
        assert aggregate_input_hash(rows) == EXPECTED_HASHES[subject]


def test_identity_validator_rejects_another_representation() -> None:
    validate_identity({"representation_id": REPRESENTATION_ID})
    try:
        validate_identity({"representation_id": "stage3a_class_declaration"})
    except ValueError as exc:
        assert "final Stage 3 representation" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("legacy representation was accepted")
