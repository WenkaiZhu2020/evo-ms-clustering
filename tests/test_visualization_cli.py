from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"
CLI = ROOT / "scripts/visualization/build_figures.py"


def _run(*arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(PYTHON), str(CLI), *arguments],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_list_succeeds_with_registered_catalogue_from_another_cwd(tmp_path: Path) -> None:
    completed = _run("--list", cwd=tmp_path)
    assert completed.returncode == 0
    assert "stage2_daytrader_partition_transition\tstage2\tenabled" in completed.stdout
    assert "stage3_four_to_three_projection\tstage3\tenabled" in completed.stdout


def test_validate_config_succeeds() -> None:
    completed = _run("--validate-config")
    assert completed.returncode == 0, completed.stderr
    assert "Visualisation configuration is valid." in completed.stdout
    assert "dot:" in completed.stdout
    assert "neato:" in completed.stdout
    assert "sfdp:" in completed.stdout


def test_smoke_test_writes_only_to_supplied_temporary_directory(tmp_path: Path) -> None:
    before = set((ROOT / "reports/figures").rglob("synthetic*"))
    completed = _run("--smoke-test", "--output-dir", str(tmp_path))
    assert completed.returncode == 0, completed.stderr
    expected = {
        "synthetic.dot",
        "synthetic.svg",
        "synthetic.pdf",
        "synthetic.provenance.json",
    }
    assert {path.name for path in tmp_path.iterdir()} == expected
    assert set((ROOT / "reports/figures").rglob("synthetic*")) == before
    provenance = (tmp_path / "synthetic.provenance.json").read_text(encoding="utf-8")
    assert str(tmp_path) not in provenance
    assert "/Users/" not in provenance
    assert "/private/" not in provenance
    assert json.loads(provenance)["figure_id"] == "synthetic-smoke-test"


def test_running_without_operation_fails_clearly() -> None:
    completed = _run()
    assert completed.returncode != 0
    assert "one of the arguments" in completed.stderr


def test_smoke_test_rejects_repository_output_location() -> None:
    completed = _run("--smoke-test", "--output-dir", str(ROOT / "reports/figures/preview"))
    assert completed.returncode == 2
    assert "outside the repository" in completed.stderr


def test_smoke_test_does_not_write_formal_or_documentation_outputs(tmp_path: Path) -> None:
    completed = _run("--smoke-test", "--output-dir", str(tmp_path))
    assert completed.returncode == 0, completed.stderr
    for relative in (
        "data/semantic_graphs/synthetic.dot",
        "results/stage1/synthetic.dot",
        "results/stage2/synthetic.dot",
        "results/stage3/synthetic.dot",
        "docs/synthetic.svg",
    ):
        assert not (ROOT / relative).exists()
