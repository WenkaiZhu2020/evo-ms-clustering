from __future__ import annotations

import csv
import hashlib
from io import StringIO
import json
from pathlib import Path

import pytest

from evo_ms.visualization.config import load_visualization_config
from evo_ms.visualization.figures.stage1_ssa_seed_robustness import (
    FIGURE_ID,
    SUBJECTS,
    build_figure,
    create_figure,
    observations_csv,
    prepare_robustness_data,
    summary_csv,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def prepared():
    config = load_visualization_config()
    return config, prepare_robustness_data(config)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_registration_and_formal_scope(prepared) -> None:
    config, data = prepared
    specification = config.figures[FIGURE_ID]
    assert specification.stage == "stage1" and specification.destination == "main_text"
    assert specification.formats == ("svg", "pdf")
    assert len(data.observations) == 3 * (435 + 30)
    for subject in SUBJECTS:
        assert sum(row.subject == subject and row.comparison_type == "seed_variation" for row in data.observations) == 435
        assert sum(row.subject == subject and row.comparison_type == "ssa_effect" for row in data.observations) == 30


def test_exact_one_minus_ari_transform_and_no_nmi(prepared) -> None:
    _config, data = prepared
    assert all(row.partition_distance == pytest.approx(1.0 - row.ari, abs=1e-15) for row in data.observations)
    text = observations_csv(data) + summary_csv(data)
    assert "nmi" not in text.lower()


def test_subject_specific_interpretations_and_values(prepared) -> None:
    _config, data = prepared
    summaries = {row.subject: row for row in data.summaries}
    jpet = summaries["jpetstore"]
    jpet_seed = [row.partition_distance for row in data.observations if row.subject == "jpetstore" and row.comparison_type == "seed_variation"]
    assert set(jpet_seed) == {0.0}
    assert jpet.raw_distinct_partitions == 1 and jpet.within_seed_variation is None
    assert "N/A" in jpet.interpretation and "within" not in jpet.interpretation.lower()
    assert jpet.ssa_mean == pytest.approx(0.12340710932260227, abs=1e-12)
    assert summaries["daytrader"].ssa_mean == pytest.approx(0.10855708994098473, abs=1e-12)
    assert summaries["xerces-j"].ssa_mean == pytest.approx(0.28246515231151664, abs=1e-12)
    assert summaries["daytrader"].within_seed_variation is True
    assert summaries["xerces-j"].within_seed_variation is True


def test_csvs_are_deterministic_complete_and_nullable(prepared) -> None:
    config, data = prepared
    assert prepare_robustness_data(config) == data
    observations = observations_csv(data); summaries = summary_csv(data)
    assert observations == observations_csv(data) and summaries == summary_csv(data)
    rows = list(csv.DictReader(StringIO(observations)))
    assert len(rows) == 1395
    summary_rows = list(csv.DictReader(StringIO(summaries)))
    assert len(summary_rows) == 3
    assert next(row for row in summary_rows if row["subject"] == "jpetstore")["within_seed_variation"] == ""
    assert "/Users/" not in observations + summaries and "/tmp/" not in observations + summaries


def test_plot_has_shared_axis_all_points_and_correct_annotations(prepared) -> None:
    _config, data = prepared
    figure = create_figure(data)
    try:
        assert len(figure.axes) == 3
        assert len({axis.get_ylim() for axis in figure.axes}) == 1
        for axis, subject in zip(figure.axes, SUBJECTS, strict=True):
            point_collections = [collection for collection in axis.collections if len(collection.get_offsets()) == 30]
            assert len(point_collections) == 1
            text = "\n".join(item.get_text() for item in axis.texts)
            if subject == "jpetstore":
                assert "Seed-invariant raw baseline" in text and "N/A" in text
            else:
                assert "within observed seed-variation band" in text
        assert "1 - ARI" in "\n".join(item.get_text() for item in figure.texts)
    finally:
        import matplotlib.pyplot as plt
        plt.close(figure)


def test_real_outputs_deterministic_provenance_and_formal_hashes(tmp_path: Path, prepared) -> None:
    config, _data = prepared
    protected = {ROOT / path: _hash(ROOT / path) for path in config.figures[FIGURE_ID].inputs}
    first = build_figure(config, output_root=tmp_path / "a", generated_at="fixed", git_commit="abc", git_dirty=True)
    second = build_figure(config, output_root=tmp_path / "b", generated_at="fixed", git_commit="abc", git_dirty=True)
    for kind in ("data", "summary", "svg", "pdf"):
        assert _hash(first[kind]) == _hash(second[kind])
    provenance = json.loads(first["provenance"].read_text())
    assert "not persisted" in provenance["method_note"]
    assert all(not Path(path).is_absolute() for path in provenance["input_files"])
    assert {path: _hash(path) for path in protected} == protected


def test_render_failure_is_atomic(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"; manifest.write_text('{"schema_version":1,"figures":{}}\n')
    before = manifest.read_bytes()
    def fail(_figure, _path, _format): raise RuntimeError("synthetic robustness render failure")
    with pytest.raises(RuntimeError, match="synthetic robustness"):
        build_figure(load_visualization_config(), output_root=tmp_path, manifest_path=manifest, renderer=fail)
    assert manifest.read_bytes() == before
    assert not (tmp_path / "preview/stage1/stage1_ssa_seed_robustness.svg").exists()
