from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from evo_ms.visualization.config import load_visualization_config


ROOT = Path(__file__).resolve().parents[1]


def _documents() -> tuple[dict, dict]:
    figures = yaml.safe_load((ROOT / "configs/visualization/figures.yml").read_text(encoding="utf-8"))
    style = yaml.safe_load((ROOT / "configs/visualization/style.yml").read_text(encoding="utf-8"))
    return figures, style


def _write_configs(root: Path, figures: dict, style: dict) -> None:
    directory = root / "configs/visualization"
    directory.mkdir(parents=True)
    (directory / "figures.yml").write_text(yaml.safe_dump(figures, sort_keys=False), encoding="utf-8")
    (directory / "style.yml").write_text(yaml.safe_dump(style, sort_keys=False), encoding="utf-8")
    for figure in figures["figures"].values():
        for relative in figure["inputs"]:
            source = root / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("synthetic input\n", encoding="utf-8")


def test_default_configs_load_from_repository_root() -> None:
    config = load_visualization_config()
    assert config.repository_root == ROOT
    assert config.schema_version == 1
    assert set(config.figures) == {
        "stage123_daytrader_highest_lowest_clusters",
        "stage123_jpetstore_highest_lowest_clusters",
        "stage2_daytrader_partition_transition",
        "stage3_four_to_three_projection",
        "stage3_jpetstore_semantic_evidence_comparison",
        "stage13_xerces_shared_highest_lowest_clusters",
        "stage2_xerces_highest_lowest_clusters",
    }
    assert config.output.dot == ROOT / "reports/figures/source"


def test_default_configs_do_not_depend_on_current_working_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = load_visualization_config()
    assert config.figures_config_path == ROOT / "configs/visualization/figures.yml"
    assert config.style_config_path == ROOT / "configs/visualization/style.yml"


def test_missing_required_configuration_key_fails_clearly(tmp_path: Path) -> None:
    figures, style = _documents()
    del figures["output"]["pdf"]
    _write_configs(tmp_path, figures, style)
    with pytest.raises(ValueError, match="output configuration is missing keys: pdf"):
        load_visualization_config(repository_root=tmp_path)


def test_output_outside_repository_is_rejected(tmp_path: Path) -> None:
    figures, style = _documents()
    figures["output"]["svg"] = "../escaped"
    _write_configs(tmp_path, figures, style)
    with pytest.raises(ValueError, match="must remain inside the repository"):
        load_visualization_config(repository_root=tmp_path)


@pytest.mark.parametrize(
    "protected",
    ["data/semantic_graphs/figures", "results/stage1/figures", "results/stage2/figures", "results/stage3/figures"],
)
def test_formal_output_locations_are_rejected(tmp_path: Path, protected: str) -> None:
    figures, style = _documents()
    figures = deepcopy(figures)
    figures["output"]["data"] = protected
    _write_configs(tmp_path, figures, style)
    with pytest.raises(ValueError, match="protected formal location"):
        load_visualization_config(repository_root=tmp_path)


def test_subject_display_names_are_canonical() -> None:
    config = load_visualization_config()
    assert config.style["subjects"] == {
        "jpetstore": "JPetStore",
        "daytrader": "DayTrader",
        "xerces-j": "Xerces-J",
    }


def test_daytrader_representative_is_typed_and_frozen() -> None:
    specification = load_visualization_config().figures["stage2_daytrader_partition_transition"]
    assert specification.representative_seed == 25
    assert specification.representative_solution == "seed25_solution047"


def test_manifest_is_a_schema_valid_catalogue() -> None:
    import json

    manifest = json.loads((ROOT / "reports/figures/manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert isinstance(manifest["figures"], dict)
