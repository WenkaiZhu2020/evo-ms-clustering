from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_subject_compile_scripts_exist() -> None:
    for config_path in sorted((ROOT / "configs" / "subjects").glob("*.yml")):
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        command = str(config.get("compile_command", ""))
        for token in shlex.split(command):
            if token.startswith("scripts/") and token.endswith(".sh"):
                assert (ROOT / token).is_file(), f"missing script declared by {config_path}: {token}"


def test_environment_contract_schema_and_formal_manifest_versions() -> None:
    path = ROOT / "configs" / "reproducibility" / "environments.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    supported = spec["supported_reproduction_environment"]
    assert spec["schema_version"] == 1
    assert supported["dependency_manager"] == "uv"
    assert supported["lockfile"] == "uv.lock"
    assert supported["python"] == "3.13.7"
    assert spec["stages"]["stage3"]["status"] == "not present in stage2-nsga"

    evidence = spec["formal_manifest_evidence"]
    for relative in evidence["manifest_locations"]:
        manifest = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        assert manifest["python_version"].split()[0] == evidence["python"]
        for package, version in evidence["packages"].items():
            assert manifest[f"{package}_version"] == version


def test_uv_lock_contains_supported_direct_versions() -> None:
    lock_text = (ROOT / "uv.lock").read_text(encoding="utf-8")
    for package, version in {
        "numpy": "2.4.4",
        "pandas": "2.2.3",
        "igraph": "1.0.0",
        "leidenalg": "0.12.0",
        "pymoo": "0.6.2",
    }.items():
        assert f'name = "{package}"' in lock_text
        assert f'version = "{version}"' in lock_text


def test_formal_seed_sets_are_exactly_zero_to_twenty_nine() -> None:
    for subject in ("jpetstore", "daytrader", "xerces-j"):
        path = ROOT / "results" / subject / "03_stage2_nsga" / "robustness_final_30seeds" / "robustness_manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        assert manifest["formal_seeds"] == list(range(30))


def test_stage3_and_legacy_dependency_entries_are_absent() -> None:
    stage3_name = "stage" + "3"
    assert not list((ROOT / "experiments").glob("*" + stage3_name + "*"))
    assert not (ROOT / "scripts" / stage3_name).exists()
    assert not list((ROOT / "results").glob("*/05_" + stage3_name + "*"))
    assert not (ROOT / "requirements").exists()
    assert not (ROOT / "configs" / "reproducibility" / ("stage2_formal_" + "environment.json")).exists()
    assert not (ROOT / "scripts" / "reproducibility" / ("check" + "_stage2_environment.py")).exists()
    assert not (ROOT / "scripts" / "reproducibility" / ("verify" + "_stage2_formal_provenance.py")).exists()


def test_public_documentation_paths_exist_and_are_referenced() -> None:
    paths = (
        ROOT / "docs" / "reproducibility" / "README.md",
        ROOT / "scripts" / "reproducibility" / "verify.py",
        ROOT / "results" / "FORMAL_RESULTS_INDEX.md",
        ROOT / "configs" / "reproducibility" / "environments.json",
    )
    assert all(path.is_file() for path in paths)
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/reproducibility/README.md" in root_readme
    assert "scripts/reproducibility/verify.py" in root_readme


@pytest.mark.parametrize(
    "arguments",
    [
        ("--stage", "stage2", "--environment-only"),
        ("--stage", "stage2", "--skip-environment"),
    ],
)
def test_unified_verifier_modes(arguments: tuple[str, ...]) -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/reproducibility/verify.py", *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["passed"] is True
