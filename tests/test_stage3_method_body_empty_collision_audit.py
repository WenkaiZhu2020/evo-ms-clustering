from __future__ import annotations

import csv
from pathlib import Path

from scripts.stage3_method_body.audit_empty_bodies_and_collisions import (
    EXPECTED_COUNTS,
    EXPECTED_EMPTY,
    classify_collision,
    classify_empty_body,
    compare_artifact_hashes,
    control_sample_ids,
    extractor_failure_classes,
    load_input_rows,
)


ROOT = Path(__file__).resolve().parents[1]


def test_empty_body_categories_distinguish_no_body_filtering_and_failure() -> None:
    assert classify_empty_body(
        class_synthetic=False, concrete_method_count=0, normalized_token_count=0,
        raw_candidate_count=0, body_failure=False, classfile_resolved=True,
        concrete_declared_method_count=0,
    ) == ("A", "no_concrete_body")
    assert classify_empty_body(
        class_synthetic=False, concrete_method_count=1, normalized_token_count=0,
        raw_candidate_count=0, body_failure=False, classfile_resolved=True,
        concrete_declared_method_count=1,
    ) == ("B", "concrete_body_no_permitted_evidence")
    assert classify_empty_body(
        class_synthetic=False, concrete_method_count=1, normalized_token_count=0,
        raw_candidate_count=3, body_failure=False, classfile_resolved=True,
        concrete_declared_method_count=1,
    ) == ("D", "meaningful_candidates_correctly_filtered")
    assert classify_empty_body(
        class_synthetic=False, concrete_method_count=0, normalized_token_count=0,
        raw_candidate_count=0, body_failure=True, classfile_resolved=True,
        concrete_declared_method_count=1,
    ) == ("E", "suspected_extraction_failure")
    assert classify_empty_body(
        class_synthetic=True, concrete_method_count=0, normalized_token_count=0,
        raw_candidate_count=0, body_failure=False, classfile_resolved=True,
        concrete_declared_method_count=0,
    ) == ("C", "generated_or_template_equivalent")


def test_collision_categories_cover_equivalence_and_failure_cases() -> None:
    assert classify_collision(
        raw_body_equivalence=True, normalized_equivalence=True,
        permitted_before_budget_equivalence=True, extraction_failure=False,
        generated_equivalence=False,
    ) == "A"
    assert classify_collision(
        raw_body_equivalence=True, normalized_equivalence=True,
        permitted_before_budget_equivalence=True, extraction_failure=False,
        generated_equivalence=True,
    ) == "B"
    assert classify_collision(
        raw_body_equivalence=False, normalized_equivalence=True,
        permitted_before_budget_equivalence=True, extraction_failure=False,
        generated_equivalence=False,
    ) == "C"
    assert classify_collision(
        raw_body_equivalence=False, normalized_equivalence=True,
        permitted_before_budget_equivalence=False, extraction_failure=False,
        generated_equivalence=False,
    ) == "D"
    assert classify_collision(
        raw_body_equivalence=False, normalized_equivalence=True,
        permitted_before_budget_equivalence=True, extraction_failure=True,
        generated_equivalence=False,
    ) == "E"
    assert classify_collision(
        raw_body_equivalence=False, normalized_equivalence=False,
        permitted_before_budget_equivalence=False, extraction_failure=False,
        generated_equivalence=False,
    ) == "F"


def test_extractor_failure_detection_is_specific_to_body_evidence_warnings(tmp_path: Path) -> None:
    log = tmp_path / "extractor.log"
    log.write_text(
        "WARNING: could not retrieve Jimple body for method-body evidence <p.C: void f()>\n"
        "WARNING: unresolved SSA reference in structural extraction\n",
        encoding="utf-8",
    )
    classes, failures, unresolved = extractor_failure_classes(log)
    assert classes == {"p.C"}
    assert failures == 1
    assert unresolved == 1


def test_artifact_hash_comparison_detects_missing_and_changed_files() -> None:
    rows = compare_artifact_hashes(
        {"a": "1", "removed": "2"},
        {"a": "1", "changed": "3"},
    )
    by_path = {row["relative_path"]: row for row in rows}
    assert by_path["a"]["unchanged"] == "true"
    assert by_path["removed"]["unchanged"] == "false"
    assert by_path["changed"]["unchanged"] == "false"


def test_control_sample_selection_is_deterministic_and_frozen_inventory_counts() -> None:
    rows_by_subject = {subject: load_input_rows(subject) for subject in EXPECTED_COUNTS}
    first = control_sample_ids(rows_by_subject)
    second = control_sample_ids(rows_by_subject)
    assert first == second
    for subject, rows in rows_by_subject.items():
        assert len(rows) == EXPECTED_COUNTS[subject]
        assert sum(row["body_empty"] == "true" for row in rows) == EXPECTED_EMPTY[subject]
        assert len({class_id for _, class_id in first[subject]}) == len(first[subject])


def test_saved_audit_reports_have_expected_safe_classification() -> None:
    path = ROOT / "reports/stage3_method_body/empty_body_class_audit.csv"
    if not path.exists():
        return
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    assert len(rows) == sum(EXPECTED_EMPTY.values())
    assert not {row["classification"] for row in rows} - {"A", "C"}
    assert all(row["body_loading_failure"] == "false" for row in rows)
