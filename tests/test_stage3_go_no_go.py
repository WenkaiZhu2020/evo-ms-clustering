import json
from pathlib import Path

from scripts.stage3.evaluate_go_no_go import evaluate


ROOT = Path(__file__).resolve().parents[1]


def test_go_no_go_uses_frozen_precedence_and_strict_baseline_comparison():
    result = evaluate()
    assert result["overall_status"] == "GO"
    assert result["overall_technical_pass"] is True
    assert result["overall_evidence_pass"] is True
    assert result["cross_subject_evidence"]["random_baseline_subject_pass_count"] == 3
    assert result["cross_subject_evidence"]["required_random_baseline_subject_pass_count"] == 2
    for subject, value in result["subjects"].items():
        assert value["technical_pass"] is True
        assert value["novelty"]["pass"] is True
        structural = value["random_baseline"]
        assert structural["structural_overlap_observed"] > structural["structural_overlap_p95"]
        assert structural["structural_overlap_strict_gt_p95"] is True
        if subject in {"jpetstore", "xerces"}:
            assert structural["same_reference_observed"] is None
            assert structural["same_reference_strict_gt_p95"] is False
        else:
            assert structural["same_reference_observed"] > structural["same_reference_p95"]


def test_every_technical_criterion_has_machine_readable_evidence():
    result = evaluate()
    for value in result["subjects"].values():
        for item in value["technical_criteria"].values():
            assert {"observed", "operator", "expected", "pass", "evidence_source"} <= set(item)
            assert item["evidence_source"]


def test_go_no_go_artifact_matches_evaluation():
    saved = json.loads((ROOT / "reports/stage3/go_no_go_status.json").read_text())
    current = evaluate()
    assert saved["overall_status"] == current["overall_status"]
    assert saved["overall_technical_pass"] == current["overall_technical_pass"]
    assert saved["overall_evidence_pass"] == current["overall_evidence_pass"]
