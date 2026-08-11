from __future__ import annotations

import csv
import hashlib
from io import StringIO
import json
from pathlib import Path
import re

import pytest

from evo_ms.visualization.config import load_visualization_config
from evo_ms.visualization.figures.stage123_daytrader_clusters import (
    FIGURE_ID,
    STAGE2_SEED,
    STAGE2_SOLUTION,
    STAGE3_SEED,
    STAGE3_SOLUTION,
    build_figure,
    boundary_aggregation_csv,
    boundary_penwidth,
    figure_dot,
    prepare_figure_data,
    profiles_csv,
    selected_csv,
)
from evo_ms.visualization.layout import GraphvizError
from evo_ms.visualization.model import GraphvizRenderResult

ROOT = Path(__file__).resolve().parents[1]
ALL_FIGURES = {
    "stage1_ssa_seed_robustness",
    FIGURE_ID,
    "stage123_jpetstore_highest_lowest_clusters",
    "stage2_daytrader_partition_transition",
    "stage3_four_to_three_projection",
    "stage3_jpetstore_semantic_evidence_comparison",
    "stage13_xerces_balance_highest_lowest_clusters",
    "stage2_xerces_highest_lowest_clusters",
    "stage3_xerces_operating_preference_sensitivity",
}


@pytest.fixture(scope="module")
def prepared():
    config = load_visualization_config()
    return config, prepare_figure_data(config)


def _fake_renderer(request) -> GraphvizRenderResult:
    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    request.output_path.write_bytes(b"<svg/>\n" if request.output_format == "svg" else b"%PDF-1.4\n%%EOF\n")
    return GraphvizRenderResult(request.output_path.resolve(), "neato", "neato test",
                                ("neato", "-n2", f"-T{request.output_format}", str(request.dot_path), "-o", str(request.output_path)))


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exactly_four_figures_and_registered_scientific_metadata() -> None:
    config = load_visualization_config()
    assert set(config.figures) == ALL_FIGURES
    spec = config.figures[FIGURE_ID]
    assert spec.destination == "main_text" and spec.formats == ("dot", "svg", "pdf")
    assert spec.layout_profile == "fixed_comparison"
    assert spec.metadata["subject"] == "daytrader"
    assert spec.metadata["ranking_metric"] == "local weighted-modularity contribution"
    assert spec.metadata["stage2_representative"] == "seed 25 / seed25_solution047"
    assert spec.metadata["stage3_representative"] == "seed 25 / seed25_solution026 / BALANCE P1 medoid"


def test_authoritative_partitions_scope_representatives_and_modularity(prepared) -> None:
    _config, data = prepared
    assert [(p.stage, p.seed, p.solution_id) for p in data.profiles if p.cluster_id == "C01"] == [
        (1, 42, "stage1_seed42"), (2, STAGE2_SEED, STAGE2_SOLUTION), (3, STAGE3_SEED, STAGE3_SOLUTION)
    ]
    for stage, formal in data.formal_modularity:
        profiles = [p for p in data.profiles if p.stage == stage]
        assert sum(len(p.members) for p in profiles) == 53
        assert len({member for p in profiles for member in p.members}) == 53
        assert sum(p.contribution for p in profiles) == pytest.approx(formal, abs=1e-12)


def test_highest_lowest_ties_and_complete_csvs_are_deterministic(prepared) -> None:
    config, data = prepared
    assert prepare_figure_data(config) == data
    assert len(data.selected) == 6
    for stage in (1, 2, 3):
        candidates = [p for p in data.profiles if p.stage == stage]
        selected = {role: p for role, p in data.selected if p.stage == stage}
        assert selected["highest"].contribution == max(p.contribution for p in candidates)
        assert selected["lowest"].contribution == min(p.contribution for p in candidates)
        tied = [p for p in candidates if p.contribution == selected["lowest"].contribution]
        assert selected["lowest"].members == min(p.members for p in tied)
    first = profiles_csv(data); second = selected_csv(data)
    assert first == profiles_csv(data) and second == selected_csv(data)
    assert first.endswith("\n") and second.endswith("\n")
    selected_rows = list(csv.DictReader(StringIO(second)))
    assert len(selected_rows) == 6
    assert all(not Path(row["partition_source"]).is_absolute() for row in selected_rows)
    assert "/Users/" not in first + second
    selected = {(profile.stage, role): profile for role, profile in data.selected}
    assert selected[(1, "highest")].members == selected[(2, "highest")].members == selected[(3, "highest")].members
    assert selected[(1, "lowest")].members == selected[(3, "lowest")].members == (
        "com.ibm.websphere.samples.daytrader.util.WebSocketJMSMessage",
    )
    assert selected[(2, "lowest")].members == (
        "com.ibm.websphere.samples.daytrader.util.WebSocketJMSMessage",
        "com.ibm.websphere.samples.daytrader.web.TradeWebContextListener",
        "com.ibm.websphere.samples.daytrader.web.websocket.JsonEncoder",
    )
    assert selected[(1, "highest")].contribution == pytest.approx(0.08948036306354759)
    assert selected[(2, "lowest")].contribution == pytest.approx(-8.090039964052776e-05)


def test_every_focal_member_internal_edge_and_aggregate_is_rendered(prepared) -> None:
    config, data = prepared
    dot = figure_dot(config, data)
    assert dot == figure_dot(config, data)
    assert len(re.findall(r'^  "p[123][hl]_panel" ', dot, re.MULTILINE)) == 6
    for role, profile in data.selected:
        prefix = f"p{profile.stage}{role[0]}"
        ids = {class_id: f"{prefix}_f{i:03d}" for i, class_id in enumerate(profile.members, 1)}
        for member in profile.members:
            line = next(line for line in dot.splitlines() if line.startswith(f'  "{ids[member]}" '))
            assert 'fillcolor="#DCEAF7"' in line
        for aggregate in profile.boundary_aggregates:
            summary = f"{prefix}_x{aggregate.external_cluster_id}"
            line = next(line for line in dot.splitlines() if line.startswith(f'  "{summary}" '))
            assert 'fillcolor="#F2F2F2"' in line and 'style="rounded,dashed,filled"' in line
        for left, right, _ in profile.internal_edges:
            line = next(line for line in dot.splitlines() if f'"{ids[left]}" -- "{ids[right]}"' in line)
            assert 'style="solid"' in line
        assert sum(len(a.connections) for a in profile.boundary_aggregates) == sum(
            1 for line in dot.splitlines() if line.startswith(f'  "{prefix}_f') and ' -- ' in line and 'style="dashed"' in line
        )
    assert "best" not in dot.lower() and "worst" not in dot.lower()


def test_boundary_aggregation_is_complete_actual_and_deterministic(prepared) -> None:
    config, data = prepared
    assert prepare_figure_data(config) == data
    text = boundary_aggregation_csv(data)
    assert text == boundary_aggregation_csv(data) and text.endswith("\n")
    rows = list(csv.DictReader(StringIO(text)))
    assert len(rows) == sum(len(profile.boundary_aggregates) for _role, profile in data.selected)
    for role, profile in data.selected:
        aggregates = profile.boundary_aggregates
        assert sum(a.boundary_edge_count for a in aggregates) == len(profile.boundary_edges)
        assert sum(a.boundary_weight for a in aggregates) == pytest.approx(profile.boundary_weight)
        assert {item for aggregate in aggregates for item in aggregate.external_classes} == set(profile.external)
        assert sum(a.boundary_edge_count for a in aggregates) == sum(
            connection.boundary_edge_count for a in aggregates for connection in a.connections
        )
        for aggregate in aggregates:
            assert aggregate.external_cluster_id != profile.cluster_id
            assert aggregate.connected_focal_classes == tuple(sorted(aggregate.connected_focal_classes))
            assert all(class_id in profile.members for class_id in aggregate.connected_focal_classes)


def test_boundary_width_is_deterministic_monotonic_and_singletons_are_annotated(prepared) -> None:
    config, data = prepared
    widths = [boundary_penwidth(value, 100.0, 0.65, 2.8) for value in (1.0, 4.0, 25.0, 100.0)]
    assert widths == sorted(widths) and len(set(widths)) == 4
    assert widths == [boundary_penwidth(value, 100.0, 0.65, 2.8) for value in (1.0, 4.0, 25.0, 100.0)]
    dot = figure_dot(config, data)
    assert dot.count("Isolated singleton") == 2
    assert '"p1l_isolated"' in dot and '"p3l_isolated"' in dot and '"p2l_isolated"' not in dot
    assert "Stage 2 and Stage 3 representatives use the authoritative BALANCE profile." in dot


def test_real_fixed_neato_svg_pdf_relative_provenance_and_manifest(tmp_path: Path) -> None:
    outputs = build_figure(load_visualization_config(), output_root=tmp_path, generated_at="2026-08-06T21:00:00Z",
                           git_commit="abc123", git_dirty=True)
    assert outputs["svg"].read_text().lstrip().startswith("<?xml")
    assert outputs["pdf"].read_bytes().startswith(b"%PDF")
    assert outputs["aggregation"].is_file()
    provenance = json.loads(outputs["provenance"].read_text())
    assert provenance["graphviz_engine"] == "neato"
    assert all(command[:2] == ["neato", "-n2"] for command in provenance["render_command"])
    assert "/Users/" not in outputs["provenance"].read_text() and "/tmp/" not in outputs["provenance"].read_text()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert set(manifest["figures"]) == {FIGURE_ID}


def test_render_failure_publishes_nothing(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"; manifest.write_text('{"schema_version":1,"figures":{}}\n')
    before = manifest.read_bytes()
    def fail(_request): raise GraphvizError("synthetic cluster render failure")
    with pytest.raises(GraphvizError, match="synthetic cluster render failure"):
        build_figure(load_visualization_config(), output_root=tmp_path, manifest_path=manifest, renderer=fail)
    assert manifest.read_bytes() == before
    assert not (tmp_path / "source/cross_stage/daytrader_highest_lowest_clusters.dot").exists()


def test_temporary_build_preserves_formal_inputs_and_existing_three_figures(tmp_path: Path) -> None:
    protected = [ROOT / path for path in load_visualization_config().figures[FIGURE_ID].inputs]
    existing = [path for path in (ROOT / "reports/figures").rglob("*") if path.is_file() and "daytrader_highest_lowest_clusters" not in path.name]
    before = {path: _hash(path) for path in (*protected, *existing)}
    build_figure(load_visualization_config(), output_root=tmp_path, generated_at="fixed", git_commit="abc", git_dirty=True,
                 renderer=_fake_renderer)
    assert {path: _hash(path) for path in before} == before
