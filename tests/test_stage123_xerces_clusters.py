from __future__ import annotations

import csv
import hashlib
from io import StringIO
import json
from pathlib import Path

import numpy as np
import pytest
from matplotlib.text import Text

from evo_ms.visualization.config import load_visualization_config
from evo_ms.visualization.figures.stage123_xerces_clusters import (
    EXPECTED,
    FIGURE_IDS,
    boundary_profile_csv,
    boundary_display_rows,
    build_figure,
    create_figure,
    interaction_matrix,
    lowest_profile_csv,
    membership_csv,
    package_profiles_csv,
    package_relations_csv,
    prepare_composite_data,
    prepare_figure_data,
    top_boundary_destinations_csv,
    top_internal_relations,
    top_internal_relations_csv,
)

ROOT = Path(__file__).resolve().parents[1]
OBSOLETE_IDS = {
    "stage1_xerces_highest_lowest_clusters",
    "stage3_xerces_highest_lowest_clusters",
}
NON_XERCES_IDS = {
    "stage1_ssa_seed_robustness",
    "stage123_daytrader_highest_lowest_clusters",
    "stage123_jpetstore_highest_lowest_clusters",
    "stage2_daytrader_partition_transition",
    "stage3_four_to_three_projection",
    "stage3_jpetstore_semantic_evidence_comparison",
    "stage3_xerces_operating_preference_sensitivity",
}


@pytest.fixture(scope="module")
def prepared():
    config = load_visualization_config()
    data = prepare_figure_data(config)
    return config, data


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fake_renderer(_figure, output_path: Path, output_format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(
        b"<svg/>\n" if output_format == "svg" else b"%PDF-1.4\n%%EOF\n"
    )


def _selected(data, stage: int, role: str):
    return next(
        profile
        for selected_role, profile in data.selected
        if selected_role == role and profile.stage == stage
    )


def test_exactly_nine_figures_and_two_matplotlib_xerces_registrations() -> None:
    config = load_visualization_config()
    assert set(config.figures) == NON_XERCES_IDS | set(FIGURE_IDS.values())
    assert not OBSOLETE_IDS & set(config.figures)
    assert len(config.figures) == 9
    for figure_id in FIGURE_IDS.values():
        specification = config.figures[figure_id]
        assert specification.destination == "appendix"
        assert specification.formats == ("svg", "pdf")
        assert "dot" not in specification.formats
        assert (
            specification.generator
            == "evo_ms.visualization.figures.stage123_xerces_clusters"
        )


def test_scope_modularity_representatives_and_accepted_clusters(prepared) -> None:
    _config, data = prepared
    for stage, formal in data.formal_modularity:
        profiles = [profile for profile in data.profiles if profile.stage == stage]
        assert sum(len(profile.members) for profile in profiles) == 814
        assert len({member for profile in profiles for member in profile.members}) == 814
        assert sum(profile.contribution for profile in profiles) == pytest.approx(
            formal, abs=1e-12
        )
        high = _selected(data, stage, "highest")
        low = _selected(data, stage, "lowest")
        seed, solution, high_id, high_n, high_edges, low_id, low_n, destinations = (
            EXPECTED[stage]
        )
        assert (
            high.seed,
            high.solution_id,
            high.cluster_id,
            len(high.members),
            len(high.internal_edges),
        ) == (seed, solution, high_id, high_n, high_edges)
        assert (low.cluster_id, len(low.members), len(high.boundary_aggregates)) == (
            low_id,
            low_n,
            destinations,
        )
    assert _selected(data, 1, "highest").members == _selected(
        data, 3, "highest"
    ).members
    assert _selected(data, 1, "lowest").members != _selected(data, 3, "lowest").members


@pytest.mark.parametrize("page,stage", [("stage13", 3), ("stage2", 2)])
def test_composition_matrix_boundary_and_lowest_reconcile(
    prepared, page: str, stage: int
) -> None:
    config, data = prepared
    first = prepare_composite_data(config, data, page)
    second = prepare_composite_data(config, data, page)
    assert first == second
    assert len(first.packages) == 10
    expected_classes = 118 if page == "stage13" else 115
    assert len(first.class_to_package) == expected_classes
    assert len({class_id for class_id, _package in first.class_to_package}) == expected_classes
    assert sum(len(profile.member_classes) for profile in first.packages) == expected_classes
    by_id = {profile.package_id: profile for profile in first.packages}
    expected_order = tuple(
        profile.package_id
        for profile in sorted(
            first.packages,
            key=lambda profile: (-len(profile.member_classes), profile.package_name),
        )
    )
    assert first.package_order == expected_order
    assert len([relation for relation in first.relations if relation.source_package == relation.target_package]) == 10
    assert all(
        relation.source_package <= relation.target_package
        for relation in first.relations
    )
    assert sum(relation.class_edge_count for relation in first.relations) == len(
        first.high.internal_edges
    )
    assert sum(relation.aggregated_weight for relation in first.relations) == pytest.approx(
        first.high.internal_weight
    )
    matrix = interaction_matrix(first)
    assert matrix.shape == (10, 10)
    assert np.array_equal(matrix, matrix.T)
    assert np.triu(matrix).sum() == pytest.approx(first.high.internal_weight)
    for index, package_id in enumerate(first.package_order):
        assert matrix[index, index] == pytest.approx(by_id[package_id].within_weight)
    assert sum(boundary.boundary_edge_count for boundary in first.boundaries) == len(
        first.high.boundary_edges
    )
    assert sum(boundary.aggregated_weight for boundary in first.boundaries) == pytest.approx(
        first.high.boundary_weight
    )
    assert list(first.boundaries) == sorted(
        first.boundaries,
        key=lambda boundary: (-boundary.aggregated_weight, boundary.external_cluster_id),
    )
    top_relations = top_internal_relations(first)
    assert len(top_relations) == 5
    assert list(top_relations) == sorted(
        (
            relation
            for relation in first.relations
            if relation.source_package != relation.target_package
        ),
        key=lambda relation: (
            -relation.aggregated_weight,
            relation.source_package,
            relation.target_package,
        ),
    )[:5]
    displayed = boundary_display_rows(first)
    assert len(displayed) == 6
    assert displayed[-1]["external_cluster_id"] == "OTHER"
    assert displayed[-1]["destination_cluster_count"] == len(first.boundaries) - 5
    assert sum(float(row["aggregated_boundary_weight"]) for row in displayed) == pytest.approx(
        first.high.boundary_weight
    )
    assert first.low.cluster_id == ("C06" if page == "stage13" else "C27")
    assert len(first.low.members) == (3 if page == "stage13" else 2)


@pytest.mark.parametrize("page", ["stage13", "stage2"])
def test_csv_contracts_are_deterministic_complete_and_relative(prepared, page: str) -> None:
    config, data = prepared
    first = prepare_composite_data(config, data, page)
    second = prepare_composite_data(config, data, page)
    exporters = (
        membership_csv,
        package_profiles_csv,
        package_relations_csv,
        boundary_profile_csv,
        top_internal_relations_csv,
        top_boundary_destinations_csv,
        lowest_profile_csv,
    )
    for exporter in exporters:
        text = exporter(first)
        assert text == exporter(second)
        assert text.endswith("\n")
        assert "/Users/" not in text and "/tmp/" not in text
    memberships = list(csv.DictReader(StringIO(membership_csv(first))))
    packages = list(csv.DictReader(StringIO(package_profiles_csv(first))))
    relations = list(csv.DictReader(StringIO(package_relations_csv(first))))
    boundaries = list(csv.DictReader(StringIO(boundary_profile_csv(first))))
    lowest = list(csv.DictReader(StringIO(lowest_profile_csv(first))))
    top_internal = list(csv.DictReader(StringIO(top_internal_relations_csv(first))))
    top_boundary = list(csv.DictReader(StringIO(top_boundary_destinations_csv(first))))
    assert len(memberships) == len(first.high.members)
    assert len(packages) == 10
    assert len(relations) == 37
    assert len(boundaries) == (15 if page == "stage13" else 16)
    assert len(lowest) == (5 if page == "stage13" else 2)
    assert len(top_internal) == 5
    assert len(top_boundary) == 6


@pytest.mark.parametrize("page", ["stage13", "stage2"])
def test_composite_figure_contains_required_areas_and_no_network(prepared, page: str) -> None:
    config, data = prepared
    composite = prepare_composite_data(config, data, page)
    figure = create_figure(composite)
    try:
        titles = [
            axis.get_title(location)
            for axis in figure.axes
            for location in ("left", "center", "right")
        ]
        all_text = "\n".join(
            text.get_text() for axis in figure.axes for text in axis.texts
        )
        assert f"Composition of {composite.high.cluster_id}" in "\n".join(titles)
        assert "Structural summary" in "\n".join(titles)
        assert "Strongest external destinations" in "\n".join(titles)
        assert f"{composite.high.cluster_id} - Highest-contributing focal cluster" in all_text
        assert f"{composite.low.cluster_id} - Lowest-contributing\ncluster" in all_text
        assert "Complete package-interaction data are available in the companion CSV." in all_text
        assert not any(axis.images for axis in figure.axes)
        assert "Internal package interaction" not in all_text
        assert "Aggregated structural weight" not in all_text
        assert all(not axis.lines for axis in figure.axes)
    finally:
        import matplotlib.pyplot as plt

        plt.close(figure)


@pytest.mark.parametrize("page", ["stage13", "stage2"])
def test_layout_panels_and_important_text_stay_inside_canvas(
    prepared, page: str
) -> None:
    config, data = prepared
    figure = create_figure(prepare_composite_data(config, data, page))
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        canvas = figure.bbox
        tolerance = 2.0
        for artist in figure.findobj(match=Text):
            if not artist.get_visible() or not artist.get_text().strip():
                continue
            extent = artist.get_window_extent(renderer)
            assert extent.x0 >= canvas.x0 - tolerance, artist.get_text()
            assert extent.y0 >= canvas.y0 - tolerance, artist.get_text()
            assert extent.x1 <= canvas.x1 + tolerance, artist.get_text()
            assert extent.y1 <= canvas.y1 + tolerance, artist.get_text()

        panels = {
            axis.get_gid(): axis.get_position()
            for axis in figure.axes
            if axis.get_gid() in {"header", "composition", "structural", "boundary", "lowest"}
        }
        assert set(panels) == {"header", "composition", "structural", "boundary", "lowest"}
        assert panels["lowest"].y1 < panels["boundary"].y0
        assert panels["boundary"].y1 < panels["structural"].y0
        assert panels["composition"].x1 < panels["structural"].x0
        lowest_patch = next(axis for axis in figure.axes if axis.get_gid() == "lowest").patch
        extent = lowest_patch.get_window_extent(renderer)
        assert extent.x0 >= canvas.x0 - tolerance
        assert extent.y0 >= canvas.y0 - tolerance
        assert extent.x1 <= canvas.x1 + tolerance
        assert extent.y1 <= canvas.y1 + tolerance
    finally:
        import matplotlib.pyplot as plt

        plt.close(figure)


def test_two_real_matplotlib_renders_are_deterministic_and_relative(tmp_path: Path) -> None:
    config = load_visualization_config()
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    for figure_id in FIGURE_IDS.values():
        first = build_figure(
            config,
            figure_id=figure_id,
            output_root=first_root,
            generated_at="2026-08-07T01:00:00Z",
            git_commit="abc",
            git_dirty=True,
        )
        second = build_figure(
            config,
            figure_id=figure_id,
            output_root=second_root,
            generated_at="2026-08-07T01:00:00Z",
            git_commit="abc",
            git_dirty=True,
        )
        assert first["svg"].read_text().lstrip().startswith("<?xml")
        assert first["pdf"].read_bytes().startswith(b"%PDF")
        assert _hash(first["svg"]) == _hash(second["svg"])
        assert _hash(first["pdf"]) == _hash(second["pdf"])
        assert "dot" not in first
        provenance = json.loads(first["provenance"].read_text())
        assert provenance["renderer"] == "matplotlib"
        assert "/Users/" not in first["provenance"].read_text()
        assert "/tmp/" not in first["provenance"].read_text()
    figures = json.loads((first_root / "manifest.json").read_text())["figures"]
    assert set(figures) == set(FIGURE_IDS.values())
    assert all(figure["formats"] == ["svg", "pdf"] for figure in figures.values())
    assert all("dot" not in figure["outputs"] for figure in figures.values())


def test_render_failure_is_atomic(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema_version":1,"figures":{}}\n')
    before = manifest.read_bytes()

    def fail(_figure, _path, _format):
        raise RuntimeError("synthetic Matplotlib render failure")

    with pytest.raises(RuntimeError, match="synthetic Matplotlib render failure"):
        build_figure(
            load_visualization_config(),
            figure_id=FIGURE_IDS["stage13"],
            output_root=tmp_path,
            manifest_path=manifest,
            renderer=fail,
        )
    assert manifest.read_bytes() == before
    assert not (
        tmp_path
        / "preview/cross_stage/xerces_stage13_balance_highest_lowest_clusters.svg"
    ).exists()
    assert not (tmp_path / "source/cross_stage").exists()


def test_temporary_build_preserves_formal_inputs_and_non_xerces_figures(
    tmp_path: Path,
) -> None:
    config = load_visualization_config()
    protected = [
        ROOT / path for path in config.figures[FIGURE_IDS["stage13"]].inputs
    ]
    existing = [
        path
        for path in (ROOT / "reports/figures").rglob("*")
        if path.is_file()
        and not path.name.startswith(".")
        and "xerces" not in path.name.lower()
    ]
    before = {path: _hash(path) for path in (*protected, *existing)}
    for figure_id in FIGURE_IDS.values():
        build_figure(
            config,
            figure_id=figure_id,
            output_root=tmp_path,
            generated_at="fixed",
            git_commit="abc",
            git_dirty=True,
            renderer=_fake_renderer,
        )
    assert {path: _hash(path) for path in before} == before
