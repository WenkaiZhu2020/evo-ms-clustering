from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.extraction.evidence_weight_validation import (
    DEFAULT_EXPECTED_EXTRACTED_EVIDENCE_WEIGHTS,
)
from evo_ms.extraction.evidence_weight_validation import expected_extracted_evidence_weights
from evo_ms.extraction.evidence_weight_validation import validate_extracted_evidence_weights


def test_validate_extracted_evidence_weights_accepts_expected_embedded_weights() -> None:
    validate_extracted_evidence_weights(
        pd.DataFrame(
            {
                "source": ["A", "A"],
                "target": ["B", "C"],
                "dependency_type": ["type", "call"],
                "weight": [1.0, 2.0],
            }
        ),
        pd.DataFrame(
            {
                "source": ["B", "C"],
                "target": ["C", "D"],
                "flow_type": ["return_value_flow", "argument_passing_flow"],
                "weight": [3.0, 3.0],
            }
        ),
        DEFAULT_EXPECTED_EXTRACTED_EVIDENCE_WEIGHTS,
        subject="fixture",
    )


def test_validate_extracted_evidence_weights_rejects_unexpected_csv_row_weight() -> None:
    with pytest.raises(ValueError, match="method_call expected 2.0"):
        validate_extracted_evidence_weights(
            pd.DataFrame(
                {
                    "source": ["A"],
                    "target": ["B"],
                    "dependency_type": ["call"],
                    "weight": [1.0],
                }
            ),
            pd.DataFrame(columns=["source", "target", "flow_type", "weight"]),
            DEFAULT_EXPECTED_EXTRACTED_EVIDENCE_WEIGHTS,
        )


def test_expected_extracted_evidence_weights_rejects_unknown_yaml_key() -> None:
    with pytest.raises(ValueError, match="unsupported expected evidence weight key"):
        expected_extracted_evidence_weights({"expected_extracted_evidence_weights": {"type": 1.0}})
