from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import pytest

from evo_ms.visualization.config import load_visualization_config
from evo_ms.visualization.figures.stage2_daytrader_transition import (
    EXPECTED_CHANGED_CLASSES,
    EXPECTED_CLASS_COUNT,
    EXPECTED_FLOW_COUNT,
    EXPECTED_MAX_FLOW,
    EXPECTED_REFERENCE_CLUSTERS,
    EXPECTED_SINGLETON_FLOWS,
    EXPECTED_TARGET_CLUSTERS,
    FIGURE_ID,
    build_figure,
    flow_penwidth,
    prepare_transition_data,
    transition_csv,
    transition_dot,
)
from evo_ms.visualization.figures.stage3_projection import build_figure as build_stage3
from evo_ms.visualization.figures.stage3_jpetstore_semantic_evidence import build_figure as build_semantic
from evo_ms.visualization.figures.stage123_daytrader_clusters import build_figure as build_clusters
from evo_ms.visualization.figures.stage123_jpetstore_clusters import build_figure as build_jpetstore_clusters
from evo_ms.visualization.figures.stage123_xerces_clusters import build_figure as build_xerces_clusters
from evo_ms.visualization.layout import GraphvizError
from evo_ms.visualization.model import GraphvizRenderResult


ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = "2026-08-06T18:00:00Z"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _deterministic_renderer(request) -> GraphvizRenderResult:
    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"<svg/>\n" if request.output_format == "svg" else b"%PDF-1.4\n%%EOF\n"
    request.output_path.write_bytes(payload)
    return GraphvizRenderResult(
        output_path=request.output_path.resolve(),
        engine="dot",
        version="dot - graphviz version test",
        command=("dot", f"-T{request.output_format}", str(request.dot_path), "-o", str(request.output_path)),
    )


def test_registration_and_approved_representative() -> None:
    config = load_visualization_config()
    assert set(config.figures) == {
        "stage123_daytrader_highest_lowest_clusters",
        "stage123_jpetstore_highest_lowest_clusters",
        FIGURE_ID,
        "stage3_four_to_three_projection",
        "stage3_jpetstore_semantic_evidence_comparison",
        "stage13_xerces_shared_highest_lowest_clusters",
        "stage2_xerces_highest_lowest_clusters",
    }
    specification = config.figures[FIGURE_ID]
    assert specification.stage == "stage2"
    assert specification.destination == "main_text"
    assert specification.enabled
    assert specification.formats == ("dot", "svg", "pdf")
    assert specification.representative_seed == 25
    assert specification.representative_solution == "seed25_solution047"


def test_formal_scope_overlap_and_similarity_invariants() -> None:
    data = prepare_transition_data(load_visualization_config())
    assert data.class_count == EXPECTED_CLASS_COUNT
    assert len(data.reference_clusters) == EXPECTED_REFERENCE_CLUSTERS
    assert len(data.target_clusters) == EXPECTED_TARGET_CLUSTERS
    assert len(data.flows) == EXPECTED_FLOW_COUNT
    assert max(flow.count for flow in data.flows) == EXPECTED_MAX_FLOW
    assert sum(flow.count == 1 for flow in data.flows) == EXPECTED_SINGLETON_FLOWS
    assert data.changed_class_count == EXPECTED_CHANGED_CLASSES
    assert data.ari == pytest.approx(0.8844565559165706, abs=1e-12)
    assert data.nmi == pytest.approx(0.8976621575146645, abs=1e-12)
    assert sum(flow.count for flow in data.flows) == EXPECTED_CLASS_COUNT


def test_cluster_ids_and_barycentric_display_order_are_deterministic() -> None:
    first = prepare_transition_data(load_visualization_config())
    second = prepare_transition_data(load_visualization_config())
    assert first == second
    assert [cluster.display_id for cluster in first.reference_clusters] == [f"L{i}" for i in range(1, 12)]
    assert sorted(cluster.display_id for cluster in first.target_clusters) == [f"S{i}" for i in range(1, 10)]
    assert [cluster.display_order for cluster in first.reference_clusters] == list(range(1, 12))
    assert [cluster.display_order for cluster in first.target_clusters] == list(range(1, 10))
    assert all(cluster.aligned_reference is not None for cluster in first.target_clusters)


def test_intermediate_csv_is_deterministic_complete_and_relative() -> None:
    data = prepare_transition_data(load_visualization_config())
    first = transition_csv(data)
    assert first == transition_csv(data)
    assert len(first.splitlines()) == EXPECTED_FLOW_COUNT + 1
    assert first.splitlines()[0].split(",").count("shared_class_count") == 1
    assert "/Users/" not in first and str(ROOT) not in first
    assert data.reference_path in first and data.target_path in first


def test_square_root_width_rule_is_monotonic_and_stable() -> None:
    config = load_visualization_config()
    lower = float(config.style["transition_flow"]["line_width_min"])
    upper = float(config.style["transition_flow"]["line_width_max"])
    widths = [flow_penwidth(count, EXPECTED_MAX_FLOW, lower, upper) for count in range(1, 14)]
    assert widths == sorted(widths)
    assert len(set(widths)) == len(widths)
    assert widths[-1] == pytest.approx(upper)
    assert flow_penwidth(1, 13, lower, upper) == flow_penwidth(1, 13, lower, upper)


def test_dot_is_deterministic_and_contains_every_flow() -> None:
    config = load_visualization_config()
    data = prepare_transition_data(config)
    dot = transition_dot(config, data)
    assert dot == transition_dot(config, data)
    assert "rankdir=\"LR\"" in dot
    assert "Leiden baseline\\n11 clusters" in dot
    assert "Stage 2 representative\\n9 clusters - seed 25" in dot
    assert len(re.findall(r'^  "L\d+" -> "S\d+" ', dot, flags=re.MULTILINE)) == EXPECTED_FLOW_COUNT
    for flow in data.flows:
        assert dot.count(f'"{flow.source}" -> "{flow.target}"') == 1


def test_real_graphviz_svg_pdf_and_relative_provenance(tmp_path: Path) -> None:
    outputs = build_figure(
        load_visualization_config(),
        output_root=tmp_path,
        generated_at=FIXED_TIME,
        git_commit="abc123",
        git_dirty=True,
    )
    assert outputs["svg"].read_text(encoding="utf-8").lstrip().startswith("<?xml")
    assert outputs["pdf"].read_bytes().startswith(b"%PDF")
    assert len(outputs["data"].read_text(encoding="utf-8").splitlines()) == 16
    provenance = outputs["provenance"].read_text(encoding="utf-8")
    assert str(tmp_path) not in provenance
    assert "/Users/" not in provenance and "/tmp/" not in provenance


def test_manifest_can_contain_exactly_all_formal_figures(tmp_path: Path) -> None:
    config = load_visualization_config()
    build_stage3(
        config,
        output_root=tmp_path,
        generated_at=FIXED_TIME,
        git_commit="abc123",
        git_dirty=True,
        renderer=_deterministic_renderer,
    )
    build_figure(
        config,
        output_root=tmp_path,
        generated_at=FIXED_TIME,
        git_commit="abc123",
        git_dirty=True,
        renderer=_deterministic_renderer,
    )
    build_semantic(
        config,
        output_root=tmp_path,
        generated_at=FIXED_TIME,
        git_commit="abc123",
        git_dirty=True,
        renderer=_deterministic_renderer,
    )
    build_clusters(
        config,
        output_root=tmp_path,
        generated_at=FIXED_TIME,
        git_commit="abc123",
        git_dirty=True,
        renderer=_deterministic_renderer,
    )
    build_jpetstore_clusters(
        config,
        output_root=tmp_path,
        generated_at=FIXED_TIME,
        git_commit="abc123",
        git_dirty=True,
        renderer=_deterministic_renderer,
    )
    for xerces_figure_id in (
        "stage13_xerces_shared_highest_lowest_clusters",
        "stage2_xerces_highest_lowest_clusters",
    ):
        build_xerces_clusters(
            config,
            figure_id=xerces_figure_id,
            output_root=tmp_path,
            generated_at=FIXED_TIME,
            git_commit="abc123",
            git_dirty=True,
        )
    figures = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))["figures"]
    assert set(figures) == {
        "stage123_daytrader_highest_lowest_clusters",
        "stage123_jpetstore_highest_lowest_clusters",
        FIGURE_ID,
        "stage3_four_to_three_projection",
        "stage3_jpetstore_semantic_evidence_comparison",
        "stage13_xerces_shared_highest_lowest_clusters",
        "stage2_xerces_highest_lowest_clusters",
    }


def test_render_failure_does_not_update_manifest_or_publish_outputs(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema_version": 1, "figures": {"stage3_four_to_three_projection": {}}}\n')
    original = manifest.read_bytes()

    def fail(_request):
        raise GraphvizError("synthetic transition rendering failure")

    with pytest.raises(GraphvizError, match="synthetic transition rendering failure"):
        build_figure(
            load_visualization_config(),
            output_root=tmp_path,
            manifest_path=manifest,
            renderer=fail,
        )
    assert manifest.read_bytes() == original
    assert not (tmp_path / "source/stage2/daytrader_partition_transition.dot").exists()
    assert not (tmp_path / "data/stage2/daytrader_partition_transition.csv").exists()


def test_temporary_build_does_not_modify_stage3_or_formal_results(tmp_path: Path) -> None:
    stage3_paths = tuple((ROOT / "reports/figures").rglob("*stage3_four_to_three_projection*"))
    before = {path: _hash(path) for path in stage3_paths if path.is_file()}
    protected = (ROOT / "results/stage2/cross_subject/operating_profile/canonical_operating_solution_per_seed.csv")
    protected_hash = _hash(protected)
    build_figure(
        load_visualization_config(),
        output_root=tmp_path,
        renderer=_deterministic_renderer,
    )
    assert {path: _hash(path) for path in before} == before
    assert _hash(protected) == protected_hash
