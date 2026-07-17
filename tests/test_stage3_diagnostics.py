import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_diagnostic_outputs_cover_all_subjects_and_preserve_null_reference_policy():
    for subject in ("jpetstore", "daytrader", "xerces"):
        directory = ROOT / "results" / subject / "04_stage3_semantic" / "diagnostics"
        assert {path.name for path in directory.iterdir()} == {
            "graph_structure.json",
            "novelty_alignment.json",
            "random_baseline_metrics.csv",
            "random_baseline_summary.json",
            "representation_ties.json",
            "top_weight_edges.csv",
        }
        summary = json.loads((directory / "random_baseline_summary.json").read_text())
        assert summary["repetitions"] == 1000
        assert summary["quantile_method"] == "numpy.quantile(method='higher')"
        assert summary["baseline_code_path"] == "scripts/stage3/random_graph_baseline.py"
        reference = summary["metrics"]["same_reference_service_ratio"]
        if subject in {"jpetstore", "xerces"}:
            assert reference["observed"] is None
            assert reference["valid_random_value_count"] == 0
        else:
            assert reference["observed"] is not None
            assert reference["valid_random_value_count"] == 1000


def test_xerces_has_expected_eleven_duplicate_groups():
    path = ROOT / "results/xerces/04_stage3_semantic/diagnostics/representation_ties.json"
    report = json.loads(path.read_text())
    assert report["duplicate_text_group_count"] == 11
    assert report["identical_embedding_group_count"] == 11
    assert report["xerces_expected_duplicate_groups"] == 11
    assert len(report["duplicate_text_groups"]) == 11


def test_random_metrics_have_one_thousand_rows_per_subject():
    for subject in ("jpetstore", "daytrader", "xerces"):
        path = ROOT / "results" / subject / "04_stage3_semantic" / "diagnostics/random_baseline_metrics.csv"
        lines = path.read_text().splitlines()
        assert len(lines) == 1001
        assert lines[1].split(",")[1] == "0"
        assert lines[-1].split(",")[1] == "999"
