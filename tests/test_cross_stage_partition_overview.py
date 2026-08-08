from __future__ import annotations

import csv
import hashlib
from io import StringIO
import json
from pathlib import Path

import pytest

from evo_ms.visualization.config import load_visualization_config
from evo_ms.visualization.figures.cross_stage_partition_overview import (
    EXPECTED_CLASSES,
    FIGURE_ID,
    REPRESENTATIVES,
    SUBJECTS,
    build_figure,
    create_figure,
    overview_csv,
    prepare_overview_data,
    similarity_csv,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def prepared():
    config = load_visualization_config()
    return config, prepare_overview_data(config)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_registration_and_authoritative_representatives(prepared) -> None:
    config, data = prepared
    specification = config.figures[FIGURE_ID]
    assert specification.destination == "main_text"
    assert specification.formats == ("svg", "pdf")
    assert specification.generator.endswith("cross_stage_partition_overview")
    for subject in SUBJECTS:
        for stage in (1, 2, 3):
            rows = [row for row in data.segments if row.subject == subject and row.stage == stage]
            seed, solution, _path = REPRESENTATIVES[subject][stage]
            assert {(row.seed, row.solution_id) for row in rows} == {(seed, solution)}


def test_complete_scope_cluster_counts_and_size_order(prepared) -> None:
    _config, data = prepared
    expected_clusters = {
        "jpetstore": (4, 4, 4), "daytrader": (11, 9, 10), "xerces-j": (31, 29, 31)
    }
    for subject in SUBJECTS:
        for stage, expected_k in enumerate(expected_clusters[subject], 1):
            rows = [row for row in data.segments if row.subject == subject and row.stage == stage]
            assert len(rows) == expected_k
            assert sum(len(row.members) for row in rows) == EXPECTED_CLASSES[subject]
            assert sum(row.class_fraction for row in rows) == pytest.approx(1.0)
            assert [row.size_rank for row in rows] == list(range(1, expected_k + 1))
            assert rows == sorted(rows, key=lambda row: (-len(row.members), row.signature))


def test_similarity_is_directly_recomputed_and_deterministic(prepared) -> None:
    config, data = prepared
    assert prepare_overview_data(config) == data
    expected = {
        ("jpetstore", "Stage 1", "Stage 2"): (0.6757617098681219, 0.7522629259735253),
        ("daytrader", "Stage 1", "Stage 3"): (0.9971172874888603, 0.9934873154393553),
        ("xerces-j", "Stage 1", "Stage 2"): (0.9566098775401781, 0.961058927594083),
    }
    for key, values in expected.items():
        row = next(item for item in data.similarities if (item.subject, item.partition_a, item.partition_b) == key)
        assert (row.ari, row.nmi) == pytest.approx(values, abs=1e-12)
    assert len(data.similarities) == 9


def test_csvs_are_complete_relative_and_deterministic(prepared) -> None:
    _config, data = prepared
    overview = overview_csv(data); similarity = similarity_csv(data)
    assert overview == overview_csv(data) and similarity == similarity_csv(data)
    rows = list(csv.DictReader(StringIO(overview)))
    assert len(rows) == sum((4, 4, 4, 11, 9, 10, 31, 29, 31))
    assert len(list(csv.DictReader(StringIO(similarity)))) == 9
    assert "/Users/" not in overview + similarity and "/tmp/" not in overview + similarity
    assert all(len(row["canonical_member_signature"]) == 64 for row in rows)


def test_figure_has_nine_bars_annotations_and_identity_warning(prepared) -> None:
    _config, data = prepared
    figure = create_figure(data)
    try:
        assert len(figure.axes) == 3
        assert sum(len(axis.containers) for axis in figure.axes) == len(data.segments)
        text = "\n".join(item.get_text() for axis in figure.axes for item in axis.texts)
        assert text.count("k = ") == 9
        assert text.count("ARI") == 9 and text.count("NMI") == 9
        assert "segment position does not represent cluster identity across stages" in "\n".join(item.get_text() for item in figure.texts)
    finally:
        import matplotlib.pyplot as plt
        plt.close(figure)


def test_real_outputs_are_deterministic_atomic_and_preserve_formal_inputs(tmp_path: Path, prepared) -> None:
    config, _data = prepared
    protected = {ROOT / path: _hash(ROOT / path) for path in config.figures[FIGURE_ID].inputs}
    first = build_figure(config, output_root=tmp_path / "a", generated_at="fixed", git_commit="abc", git_dirty=True)
    second = build_figure(config, output_root=tmp_path / "b", generated_at="fixed", git_commit="abc", git_dirty=True)
    for kind in ("data", "similarity", "svg", "pdf"):
        assert _hash(first[kind]) == _hash(second[kind])
    assert first["svg"].read_text().lstrip().startswith("<?xml")
    assert first["pdf"].read_bytes().startswith(b"%PDF")
    provenance = json.loads(first["provenance"].read_text())
    assert provenance["renderer"] == "matplotlib"
    assert all(not Path(path).is_absolute() for path in provenance["input_files"])
    assert {path: _hash(path) for path in protected} == protected
    figures = json.loads((tmp_path / "a/manifest.json").read_text())["figures"]
    assert set(figures) == {FIGURE_ID}


def test_render_failure_is_atomic(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema_version":1,"figures":{}}\n')
    before = manifest.read_bytes()
    def fail(_figure, _path, _format):
        raise RuntimeError("synthetic overview render failure")
    with pytest.raises(RuntimeError, match="synthetic overview"):
        build_figure(load_visualization_config(), output_root=tmp_path, manifest_path=manifest, renderer=fail)
    assert manifest.read_bytes() == before
    assert not (tmp_path / "preview/cross_stage/cross_stage_partition_overview.svg").exists()
