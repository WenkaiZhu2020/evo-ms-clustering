from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.evaluation.reference_metrics import calculate_reference_metrics
from evo_ms.evaluation.reference_metrics import reference_mapping_diagnostics


def test_reference_mapping_diagnostics_reports_coverage_and_missing_classes() -> None:
    diagnostics = reference_mapping_diagnostics(
        class_nodes_frame("A", "B", "C"),
        reference_mapping_frame(("A", "account"), ("B", "account"), ("Z", "order")),
    )

    assert diagnostics["reference_coverage_ratio"] == pytest.approx(2 / 3)
    assert diagnostics["unmapped_extracted_classes"]["class_name"].tolist() == ["C"]
    assert diagnostics["reference_classes_not_found"]["class_name"].tolist() == ["Z"]


def test_calculate_reference_metrics_uses_mapped_subset() -> None:
    metrics = calculate_reference_metrics(
        class_nodes_frame("A", "B", "C"),
        clusters_frame(("A", 0), ("B", 0), ("C", 1)),
        reference_mapping_frame(("A", "account"), ("B", "account")),
    )

    assert metrics["reference_coverage_ratio"] == pytest.approx(2 / 3)
    assert metrics["pairwise_precision"] == 1.0
    assert metrics["pairwise_recall"] == 1.0
    assert metrics["pairwise_f1"] == 1.0
    assert metrics["mojofm_vs_reference"] == 100.0
    assert metrics["ari_vs_reference"] == 1.0
    assert metrics["nmi_vs_reference"] == 1.0


def class_nodes_frame(*class_names: str) -> pd.DataFrame:
    return pd.DataFrame({"class_name": list(class_names)})


def clusters_frame(*rows: tuple[str, int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "class_name": [row[0] for row in rows],
            "cluster_id": [row[1] for row in rows],
        }
    )


def reference_mapping_frame(*rows: tuple[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "class_name": [row[0] for row in rows],
            "reference_service": [row[1] for row in rows],
        }
    )
