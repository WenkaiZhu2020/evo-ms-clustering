from pathlib import Path

from evo_ms.visualization.config import load_visualization_config


ROOT = Path(__file__).resolve().parents[1]


def test_cross_stage_overview_is_deprecated_and_not_registered() -> None:
    config = load_visualization_config()
    assert "cross_stage_partition_overview" not in config.figures
    note = (ROOT / "reports/figures/data/cross_stage/DEPRECATED.md").read_text()
    assert "cross_stage_partition_overview.pdf" in note
    assert "cannot regenerate" in note


def test_historical_overview_pdf_is_retained_as_provenance_only() -> None:
    historical = ROOT / "reports/figures/pdf/cross_stage/cross_stage_partition_overview.pdf"
    assert historical.is_file() and historical.read_bytes().startswith(b"%PDF")
