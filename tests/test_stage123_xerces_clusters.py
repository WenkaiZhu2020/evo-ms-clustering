from __future__ import annotations

import csv
import hashlib
from io import StringIO
import json
from pathlib import Path
import re

import pytest

from evo_ms.visualization.config import load_visualization_config
from evo_ms.visualization.figures.stage123_xerces_clusters import (
    EXPECTED,
    FIGURE_IDS,
    build_figure,
    class_membership_csv,
    figure_dot,
    package_aggregation,
    package_boundary_csv,
    package_profiles_csv,
    package_relations_csv,
    prepare_figure_data,
)
from evo_ms.visualization.layout import GraphvizError
from evo_ms.visualization.model import GraphvizRenderResult

ROOT = Path(__file__).resolve().parents[1]
OBSOLETE_IDS = {
    "stage1_xerces_highest_lowest_clusters",
    "stage3_xerces_highest_lowest_clusters",
}
NON_XERCES_IDS = {
    "stage123_daytrader_highest_lowest_clusters",
    "stage123_jpetstore_highest_lowest_clusters",
    "stage2_daytrader_partition_transition",
    "stage3_four_to_three_projection",
    "stage3_jpetstore_semantic_evidence_comparison",
}


@pytest.fixture(scope="module")
def prepared():
    config = load_visualization_config()
    return config, prepare_figure_data(config)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fake_renderer(request) -> GraphvizRenderResult:
    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    request.output_path.write_bytes(
        b"<svg/>\n" if request.output_format == "svg" else b"%PDF-1.4\n%%EOF\n"
    )
    return GraphvizRenderResult(
        request.output_path.resolve(),
        "dot",
        "dot test",
        (
            "dot",
            f"-T{request.output_format}",
            str(request.dot_path),
            "-o",
            str(request.output_path),
        ),
    )


def _selected(data, stage: int, role: str):
    return next(
        profile
        for selected_role, profile in data.selected
        if selected_role == role and profile.stage == stage
    )


def test_exactly_seven_figures_and_two_corrected_xerces_registrations() -> None:
    config = load_visualization_config()
    assert set(config.figures) == NON_XERCES_IDS | set(FIGURE_IDS.values())
    assert not OBSOLETE_IDS & set(config.figures)
    assert len(config.figures) == 7
    for figure_id in FIGURE_IDS.values():
        specification = config.figures[figure_id]
        assert specification.destination == "appendix"
        assert specification.formats == ("dot", "svg", "pdf")
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
    assert _selected(data, 1, "lowest").members == _selected(
        data, 3, "lowest"
    ).members


@pytest.mark.parametrize("page,stage", [("stage13", 1), ("stage2", 2)])
def test_package_aggregation_is_complete_exact_and_deterministic(
    prepared, page: str, stage: int
) -> None:
    config, data = prepared
    high = _selected(data, stage, "highest")
    label = "stage1+stage3" if page == "stage13" else "stage2"
    first = package_aggregation(config, label, high)
    second = package_aggregation(config, label, high)
    assert first == second
    assert len(first.profiles) == 10
    assigned = [class_id for class_id, _package_id in first.class_to_package]
    assert assigned == sorted(high.members)
    assert len(assigned) == len(set(assigned)) == len(high.members)
    assert sum(profile.within_edge_count for profile in first.profiles) + sum(
        relation.class_edge_count for relation in first.relations
    ) == len(high.internal_edges)
    assert sum(profile.within_weight for profile in first.profiles) + sum(
        relation.aggregated_weight for relation in first.relations
    ) == pytest.approx(high.internal_weight)
    assert sum(
        relation.boundary_edge_count for relation in first.boundary_relations
    ) == len(high.boundary_edges)
    assert sum(
        relation.aggregated_weight for relation in first.boundary_relations
    ) == pytest.approx(high.boundary_weight)
    for exporter in (
        class_membership_csv,
        package_profiles_csv,
        package_relations_csv,
        package_boundary_csv,
    ):
        text = exporter(first)
        assert text == exporter(second)
        assert text.endswith("\n")
        assert "/Users/" not in text


@pytest.mark.parametrize("page,stage", [("stage13", 1), ("stage2", 2)])
def test_dot_has_explicit_focal_frame_and_separates_external_nodes(
    prepared, page: str, stage: int
) -> None:
    config, data = prepared
    high = _selected(data, stage, "highest")
    low = _selected(data, stage, "lowest")
    label = "stage1+stage3" if page == "stage13" else "stage2"
    aggregation = package_aggregation(config, label, high)
    dot = figure_dot(config, page, high, low, aggregation)
    assert dot == figure_dot(config, page, high, low, aggregation)
    assert "subgraph cluster_focal" in dot
    assert "subgraph cluster_lowest" in dot
    assert "Package nodes are internal subdivisions of the framed focal cluster." in dot
    assert f"{high.cluster_id} - Highest-contributing focal cluster" in dot
    assert f"{len(high.members)} classes aggregated into 10 package nodes" in dot
    assert f"q_c = {high.contribution:.6f}" in dot
    assert f"W_in = {high.internal_weight:.0f}" in dot
    assert f"W_boundary = {high.boundary_weight:.0f}" in dot
    focal_body = dot.split("subgraph cluster_focal", 1)[1].split("\n  }", 1)[0]
    for profile in aggregation.profiles:
        assert f'"pkg_{profile.package_id}"' in focal_body
    assert '"ext_' not in focal_body
    assert not re.search(r'"f_F\d{3}"', dot)
    assert low.cluster_id + " - Lowest-contributing cluster" in dot
    for class_id in low.members:
        assert class_id.rsplit(".", 1)[-1] in dot
    if page == "stage13":
        assert "Isolated singleton" in dot
        assert "Stage 1 and Stage 3 select the same highest- and lowest-contributing clusters." in dot
    else:
        assert "Isolated singleton" not in dot
        assert '"low_01"' in dot and '"low_02"' in dot


def test_two_real_dot_renders_relative_provenance_and_manifest(tmp_path: Path) -> None:
    config = load_visualization_config()
    for figure_id in FIGURE_IDS.values():
        outputs = build_figure(
            config,
            figure_id=figure_id,
            output_root=tmp_path,
            generated_at="2026-08-06T23:00:00Z",
            git_commit="abc",
            git_dirty=True,
        )
        assert outputs["svg"].read_text().lstrip().startswith("<?xml")
        assert outputs["pdf"].read_bytes().startswith(b"%PDF")
        provenance = json.loads(outputs["provenance"].read_text())
        assert provenance["graphviz_engine"] == "dot"
        assert all(command[0] == "dot" for command in provenance["render_command"])
        assert "/Users/" not in outputs["provenance"].read_text()
        assert "/tmp/" not in outputs["provenance"].read_text()
    figures = json.loads((tmp_path / "manifest.json").read_text())["figures"]
    assert set(figures) == set(FIGURE_IDS.values())
    assert not OBSOLETE_IDS & set(figures)


def test_render_failure_is_atomic(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema_version":1,"figures":{}}\n')
    before = manifest.read_bytes()

    def fail(_request):
        raise GraphvizError("synthetic Xerces render failure")

    with pytest.raises(GraphvizError, match="synthetic Xerces render failure"):
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
        / "source/cross_stage/xerces_stage13_shared_highest_lowest_clusters.dot"
    ).exists()


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
        if path.is_file() and "xerces" not in path.name.lower()
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


def test_generated_package_csvs_have_expected_row_counts(tmp_path: Path) -> None:
    outputs = build_figure(
        load_visualization_config(),
        figure_id=FIGURE_IDS["stage13"],
        output_root=tmp_path,
        generated_at="fixed",
        git_commit="abc",
        git_dirty=True,
        renderer=_fake_renderer,
    )
    assert len(list(csv.DictReader(StringIO(outputs["class_membership"].read_text())))) == 118
    assert len(list(csv.DictReader(StringIO(outputs["package_profiles"].read_text())))) == 10
