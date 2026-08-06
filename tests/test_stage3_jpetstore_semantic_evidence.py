from __future__ import annotations

from collections import Counter
import csv
import hashlib
from io import StringIO
import json
import math
from pathlib import Path
import re

import pytest

from evo_ms.visualization.config import load_visualization_config
from evo_ms.visualization.figures.stage3_jpetstore_semantic_evidence import (
    EXPECTED_CLASS_COUNT,
    EXPECTED_OVERLAP,
    EXPECTED_SEMANTIC_EDGES,
    EXPECTED_SEMANTIC_ONLY,
    EXPECTED_STRUCTURAL_EDGES,
    EXPECTED_STRUCTURAL_ONLY,
    EXPECTED_UNION_EDGES,
    FIGURE_ID,
    build_figure,
    edge_category_csv,
    evidence_dot,
    generate_master_positions,
    initial_layout_dot,
    master_position_csv,
    prepare_evidence_data,
)
from evo_ms.visualization.layout import GraphvizError
from evo_ms.visualization.model import GraphvizRenderResult


ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = "2026-08-06T20:00:00Z"
FORMAL_IDS = {
    "stage123_daytrader_highest_lowest_clusters",
    "stage123_jpetstore_highest_lowest_clusters",
    "stage2_daytrader_partition_transition",
    "stage3_four_to_three_projection",
    FIGURE_ID,
    "stage13_xerces_shared_highest_lowest_clusters",
    "stage2_xerces_highest_lowest_clusters",
}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fake_renderer(request) -> GraphvizRenderResult:
    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    request.output_path.write_bytes(b"<svg/>\n" if request.output_format == "svg" else b"%PDF-1.4\n%%EOF\n")
    return GraphvizRenderResult(
        request.output_path.resolve(), "neato", "neato - graphviz version test",
        ("neato", "-n2", f"-T{request.output_format}", str(request.dot_path), "-o", str(request.output_path)),
    )


@pytest.fixture(scope="module")
def prepared():
    config = load_visualization_config()
    return config, prepare_evidence_data(config)


@pytest.fixture(scope="module")
def positioned(tmp_path_factory, prepared):
    config, data = prepared
    directory = tmp_path_factory.mktemp("jpetstore-positions")
    positions = generate_master_positions(config, data, directory / "union.dot")
    return config, data, positions


def test_registration_preserves_all_three_formal_figure_ids() -> None:
    config = load_visualization_config()
    assert set(config.figures) == FORMAL_IDS
    specification = config.figures[FIGURE_ID]
    assert specification.stage == "stage3"
    assert specification.destination == "main_text"
    assert specification.enabled
    assert specification.formats == ("dot", "svg", "pdf")
    assert specification.layout_profile == "fixed_comparison"
    assert specification.generator == "evo_ms.visualization.figures.stage3_jpetstore_semantic_evidence"
    assert specification.layout_coordinate_path == "reports/figures/data/common/jpetstore_union_positions.csv"
    assert specification.edge_category_data_path == "reports/figures/data/stage3/jpetstore_semantic_edge_categories.csv"


def test_formal_graph_scope_and_edge_category_invariants(prepared) -> None:
    _config, data = prepared
    counts = Counter(edge.edge_category for edge in data.edges)
    assert len(data.nodes) == EXPECTED_CLASS_COUNT
    assert len(data.edges) == EXPECTED_UNION_EDGES
    assert counts == {
        "structural_only": EXPECTED_STRUCTURAL_ONLY,
        "overlap": EXPECTED_OVERLAP,
        "semantic_only": EXPECTED_SEMANTIC_ONLY,
    }
    assert counts["structural_only"] + counts["overlap"] == EXPECTED_STRUCTURAL_EDGES
    assert counts["semantic_only"] + counts["overlap"] == EXPECTED_SEMANTIC_EDGES
    pairs = [(edge.source_class_id, edge.target_class_id) for edge in data.edges]
    assert len(pairs) == len(set(pairs))
    assert all(source < target for source, target in pairs)
    assert all(source != target for source, target in pairs)
    semantic_degree = Counter(
        class_id
        for edge in data.edges if edge.edge_category in {"semantic_only", "overlap"}
        for class_id in (edge.source_class_id, edge.target_class_id)
    )
    assert set(semantic_degree) == {node.class_id for node in data.nodes}


def test_edge_category_csv_is_complete_relative_and_deterministic(prepared) -> None:
    _config, data = prepared
    text = edge_category_csv(data)
    assert text == edge_category_csv(data)
    assert text.endswith("\n")
    rows = list(csv.DictReader(StringIO(text)))
    assert len(rows) == EXPECTED_UNION_EDGES
    assert Counter(row["edge_category"] for row in rows) == {
        "structural_only": 28, "overlap": 25, "semantic_only": 22,
    }
    assert all(row["source_class_id"] < row["target_class_id"] for row in rows)
    assert "/Users/" not in text and str(ROOT) not in text
    assert all(not (row["structural_weight"] and row["semantic_similarity"])
               for row in rows if row["edge_category"] != "overlap")


def test_initial_layout_is_unweighted_category_neutral_and_deterministic(prepared) -> None:
    config, data = prepared
    dot = initial_layout_dot(config, data)
    assert dot == initial_layout_dot(config, data)
    assert "start=42" in dot
    assert "raw_weight" not in dot and "similarity" not in dot
    assert "edge_category" not in dot and "structural_only" not in dot and "semantic_only" not in dot
    assert "color=" not in dot and "penwidth=" not in dot and "style=" not in dot
    assert len(re.findall(r'^  ".+" -- ".+";$', dot, flags=re.MULTILINE)) == EXPECTED_UNION_EDGES


def test_master_coordinates_are_complete_finite_and_deterministic(tmp_path: Path, prepared) -> None:
    config, data = prepared
    first = generate_master_positions(config, data, tmp_path / "first.dot")
    second = generate_master_positions(config, data, tmp_path / "second.dot")
    assert first == second
    assert len(first) == EXPECTED_CLASS_COUNT
    assert len({position.class_id for position in first}) == EXPECTED_CLASS_COUNT
    assert [position.canonical_order for position in first] == list(range(1, EXPECTED_CLASS_COUNT + 1))
    assert all(math.isfinite(position.x) and math.isfinite(position.y) for position in first)
    for index, left in enumerate(first):
        for right in first[index + 1:]:
            assert (
                abs(left.x - right.x) >= (left.width_pt + right.width_pt) / 2 + 1.9
                or abs(left.y - right.y) >= (left.height_pt + right.height_pt) / 2 + 1.9
            )
    text = master_position_csv(first)
    assert text == master_position_csv(second)
    assert len(text.splitlines()) == EXPECTED_CLASS_COUNT + 1
    assert "/Users/" not in text and str(ROOT) not in text


def test_two_panels_share_relative_coordinates_and_required_edges(positioned) -> None:
    config, data, positions = positioned
    dot = evidence_dot(config, data, positions)
    assert dot == evidence_dot(config, data, positions)
    offset = float(config.style["semantic_evidence_comparison"]["panel_offset_pt"])
    coordinates: dict[tuple[str, str], tuple[float, float]] = {}
    for panel, node, x, y in re.findall(r'^  "([ab])_(n\d+)" \[.*pos="([0-9.eE+-]+),([0-9.eE+-]+)!"', dot, re.MULTILINE):
        coordinates[(panel, node)] = (float(x), float(y))
    assert len(coordinates) == EXPECTED_CLASS_COUNT * 2
    for index in range(1, EXPECTED_CLASS_COUNT + 1):
        lower = coordinates[("b", f"n{index:02d}")]
        upper = coordinates[("a", f"n{index:02d}")]
        assert upper[0] == pytest.approx(lower[0])
        assert upper[1] - lower[1] == pytest.approx(offset)
    assert len(re.findall(r'^  "a_n\d+" -- "a_n\d+" ', dot, re.MULTILINE)) == EXPECTED_STRUCTURAL_EDGES
    assert len(re.findall(r'^  "b_n\d+" -- "b_n\d+" ', dot, re.MULTILINE)) == EXPECTED_SEMANTIC_EDGES


def test_category_membership_styles_and_uniform_nodes(positioned) -> None:
    config, data, positions = positioned
    dot = evidence_dot(config, data, positions)
    for edge in data.edges:
        source = next(node.canonical_order for node in data.nodes if node.class_id == edge.source_class_id)
        target = next(node.canonical_order for node in data.nodes if node.class_id == edge.target_class_id)
        a = f'"a_n{source:02d}" -- "a_n{target:02d}"'
        b = f'"b_n{source:02d}" -- "b_n{target:02d}"'
        assert (a in dot, b in dot) == {
            "structural_only": (True, False),
            "overlap": (True, True),
            "semantic_only": (False, True),
        }[edge.edge_category]
    category_styles = config.style["edge_categories"]
    assert f'style="{category_styles["structural"]["style"]}"' in dot
    assert f'style="{category_styles["semantic_only"]["style"]}"' in dot
    assert f'style="{category_styles["structural_semantic_overlap"]["style"]}"' in dot
    assert 'node [color=' in dot
    assert "partition" not in dot.lower()


def test_real_neato_fixed_render_and_relative_provenance(tmp_path: Path) -> None:
    outputs = build_figure(
        load_visualization_config(), output_root=tmp_path, generated_at=FIXED_TIME,
        git_commit="abc123", git_dirty=True,
    )
    assert outputs["svg"].read_text(encoding="utf-8").lstrip().startswith("<?xml")
    assert outputs["pdf"].read_bytes().startswith(b"%PDF")
    assert len(outputs["categories"].read_text(encoding="utf-8").splitlines()) == 76
    assert len(outputs["positions"].read_text(encoding="utf-8").splitlines()) == 25
    provenance = json.loads(outputs["provenance"].read_text(encoding="utf-8"))
    assert provenance["graphviz_engine"] == "neato"
    assert all(command[:2] == ["neato", "-n2"] for command in provenance["render_command"])
    text = outputs["provenance"].read_text(encoding="utf-8")
    assert str(tmp_path) not in text and "/Users/" not in text and "/tmp/" not in text


def test_render_failure_publishes_neither_entry_nor_outputs(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema_version": 1, "figures": {"stage3_four_to_three_projection": {}}}\n')
    original = manifest.read_bytes()

    def fail(_request):
        raise GraphvizError("synthetic semantic-evidence render failure")

    with pytest.raises(GraphvizError, match="synthetic semantic-evidence render failure"):
        build_figure(load_visualization_config(), output_root=tmp_path, manifest_path=manifest, renderer=fail)
    assert manifest.read_bytes() == original
    assert not (tmp_path / "source/stage3/jpetstore_semantic_evidence_comparison.dot").exists()
    assert not (tmp_path / "data/common/jpetstore_union_positions.csv").exists()


def test_temporary_generation_does_not_modify_formal_inputs_or_existing_figures(tmp_path: Path) -> None:
    protected = [
        ROOT / "data/extracted/jpetstore/class_nodes.csv",
        ROOT / "results/stage1/subjects/jpetstore/leiden_baseline/raw_reference_leiden/graph/stage1_edges.csv",
        ROOT / "data/semantic_graphs/declaration_method_body/jpetstore/semantic_edges.csv",
        ROOT / "data/semantic_graphs/declaration_method_body/jpetstore/class_mapping.csv",
        ROOT / "data/semantic_graphs/declaration_method_body/jpetstore/graph_metadata.json",
    ]
    existing = [
        path for path in (ROOT / "reports/figures").rglob("*")
        if path.is_file() and ("daytrader_partition_transition" in path.name or "stage3_four_to_three_projection" in path.name)
    ]
    before = {path: _hash(path) for path in (*protected, *existing)}
    build_figure(
        load_visualization_config(), output_root=tmp_path, generated_at=FIXED_TIME,
        git_commit="abc123", git_dirty=True, renderer=_fake_renderer,
    )
    assert {path: _hash(path) for path in before} == before
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["figures"]) == {FIGURE_ID}
