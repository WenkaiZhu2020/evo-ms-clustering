from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def _normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def test_final_repository_has_one_supported_installation_entry() -> None:
    assert (ROOT / "pyproject.toml").is_file()
    assert (ROOT / "uv.lock").is_file()
    assert not (ROOT / "requirements.txt").exists()
    assert not (ROOT / "requirements-stage3-lock.txt").exists()
    assert not (ROOT / "requirements").exists()
    contract = json.loads(
        (ROOT / "configs/reproducibility/environments.json").read_text(encoding="utf-8")
    )
    supported = contract["supported_final_environment"]
    assert supported["installation_command"] == "uv sync --frozen"
    assert supported["scope"] == ["stage1", "stage2", "stage3"]


def test_uv_lock_preserves_every_historical_stage3_version() -> None:
    historical = ROOT / "results/stage3/provenance/environment/historical_stage3_requirements_lock.txt"
    expected: dict[str, str] = {}
    for line in historical.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            name, version = line.split("==", 1)
            expected[_normalise(name)] = version
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    actual = {
        _normalise(package["name"]): package["version"]
        for package in lock["package"]
        if package["name"] != "evo-ms-clustering"
    }
    assert set(expected).issubset(actual)
    assert {name: actual[name] for name in expected} == expected
