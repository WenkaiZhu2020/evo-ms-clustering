from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DOC_ROOT = ROOT / "docs/stage3/findings"
MACHINE_ROOT = ROOT / "results/stage3"
PROVENANCE_ROOT = MACHINE_ROOT / "provenance"


def test_stage3_has_one_human_document_root() -> None:
    assert DOC_ROOT.is_dir()
    assert (DOC_ROOT / "chapter4_3_data_pack.md").is_file()
    assert not (ROOT / "docs/reports/05_stage3_declaration_method_body").exists()
    assert not (ROOT / "reports/stage3").exists()


def test_migration_manifest_is_machine_provenance() -> None:
    path = PROVENANCE_ROOT / "report_migration_manifest.yml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert document["machine_result_root"] == "results/stage3"
    assert document["human_report_root"] == "docs/stage3/findings"
    assert document["inventory_summary"] == {
        "source_effective_file_count": 80,
        "source_tracked_file_count": 79,
        "preserved_byte_identical_artifact_count": 78,
        "rewritten_human_readme_count": 1,
        "deleted_empty_ignored_log_count": 1,
        "note": "78 + 1 + 1 = 80",
    }


def test_current_report_locator_is_not_write_configuration() -> None:
    locator = json.loads(
        (PROVENANCE_ROOT / "current_report_locator.json").read_text(encoding="utf-8")
    )
    assert locator["machine_result_root"] == "results/stage3"
    assert locator["human_report_root"] == "docs/stage3/findings"
    assert locator["canonical_data_pack"] == "docs/stage3/findings/chapter4_3_data_pack.md"
    assert locator["purpose"] == "current_location_only"
    assert locator["runtime_write_configuration"] is False


def test_active_stage3_paths_do_not_use_the_retired_document_root() -> None:
    paths = [
        ROOT / "configs/experiments/05_stage3_declaration_method_body.yml",
        *sorted((ROOT / "experiments/05_stage3_declaration_method_body").glob("*.py")),
        *sorted((ROOT / "scripts/05_stage3_declaration_method_body").glob("*.sh")),
    ]
    for path in paths:
        assert "docs/reports/05_stage3_declaration_method_body" not in path.read_text(
            encoding="utf-8"
        )
