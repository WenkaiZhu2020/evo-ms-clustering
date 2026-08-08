from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

import pytest

from evo_ms.visualization.config import load_visualization_config
from evo_ms.visualization.figures.stage3_projection import FIGURE_ID, build_figure, projection_dot
from evo_ms.visualization.layout import GraphvizError
from evo_ms.visualization.model import GraphvizRenderResult


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"
CLI = ROOT / "scripts/visualization/build_figures.py"
FIXED_TIME = "2026-08-06T12:00:00Z"


def test_figure_registration_loads_correctly() -> None:
    config = load_visualization_config()
    assert set(config.figures) == {
        "cross_stage_partition_overview",
        "stage123_daytrader_highest_lowest_clusters",
        "stage123_jpetstore_highest_lowest_clusters",
        FIGURE_ID,
        "stage2_daytrader_partition_transition",
        "stage3_jpetstore_semantic_evidence_comparison",
        "stage13_xerces_shared_highest_lowest_clusters",
        "stage2_xerces_highest_lowest_clusters",
    }
    specification = config.figures[FIGURE_ID]
    assert specification.stage == "stage3"
    assert specification.destination == "main_text"
    assert specification.layout_profile == "hierarchical"
    assert specification.formats == ("dot", "svg", "pdf")
    assert specification.generator == "evo_ms.visualization.figures.stage3_projection"
    assert specification.inputs == ("experiments/05_stage3_declaration_method_body/run.py",)


def test_projection_dot_is_deterministic() -> None:
    config = load_visualization_config()
    assert projection_dot(config) == projection_dot(config)


def test_expected_conceptual_nodes_and_objective_spaces_appear_once() -> None:
    dot = projection_dot(load_visualization_config())
    expected = (
        "Stage 3 four-objective Pareto set",
        "Project onto the structural objectives",
        "Recompute non-dominance in 3D",
        "Remove exact duplicate triples",
        "Projected Stage 3 front",
        "Common structural comparison",
        "Stage 2 front vs projected Stage 3 front",
    )
    assert all(dot.count(label) == 1 for label in expected)
    assert dot.count("(coupling, −cohesion, imbalance, <I>f</I><SUB>sem</SUB>)") == 1
    assert dot.count("(coupling, −cohesion, imbalance)") == 2


def test_implementation_wording_is_absent_and_semantic_objective_is_subscripted() -> None:
    dot = projection_dot(load_visualization_config())
    forbidden = (
        "stable solution-ID survivor",
        "Remove f_sem from comparison coordinates",
        "Reapply three-objective non-dominated filtering",
        "Compare with the Stage 2 three-objective front",
    )
    assert all(phrase not in dot for phrase in forbidden)
    assert "f_sem" not in dot
    assert dot.count("<I>f</I><SUB>sem</SUB>") == 1


def test_combined_normalization_operations_preserve_scientific_order() -> None:
    dot = projection_dot(load_visualization_config())
    assert dot.index("Recompute non-dominance in 3D") < dot.index("Remove exact duplicate triples")


def test_node_and_edge_counts_are_stable() -> None:
    dot = projection_dot(load_visualization_config())
    assert len(re.findall(r'^  "n[1-5]" \[', dot, flags=re.MULTILINE)) == 5
    assert len(re.findall(r'^  "n[1-5]" -> "n[1-5]" ', dot, flags=re.MULTILINE)) == 4


def test_two_row_rank_structure_and_flow_are_explicit() -> None:
    dot = projection_dot(load_visualization_config())
    assert 'subgraph "top_row" { rank=same; "n1"; "n2"; "n3"; }' in dot
    assert 'subgraph "bottom_row" { rank=same; "n4"; "n5"; }' in dot
    for source, target in (("n1", "n2"), ("n2", "n3"), ("n3", "n4"), ("n4", "n5")):
        assert dot.count(f'"{source}" -> "{target}"') == 1


def test_dot_renders_svg_pdf_and_relative_provenance(tmp_path: Path) -> None:
    outputs = build_figure(
        load_visualization_config(),
        output_root=tmp_path,
        generated_at=FIXED_TIME,
        git_commit="abc123",
        git_dirty=True,
    )
    assert outputs["dot"].read_text(encoding="utf-8").endswith("\n")
    assert outputs["svg"].read_text(encoding="utf-8").lstrip().startswith("<?xml")
    assert outputs["pdf"].read_bytes().startswith(b"%PDF")
    document = json.loads(outputs["provenance"].read_text(encoding="utf-8"))
    assert document["input_files"] == ["experiments/05_stage3_declaration_method_body/run.py"]
    assert document["generated_at"] == FIXED_TIME
    text = outputs["provenance"].read_text(encoding="utf-8")
    assert str(tmp_path) not in text
    assert "/Users/" not in text and "/private/" not in text and "/tmp/" not in text


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


def test_manifest_entry_is_deterministic_with_fixed_timestamp(tmp_path: Path) -> None:
    config = load_visualization_config()
    first_root = tmp_path / "one"
    second_root = tmp_path / "two"
    build_figure(
        config,
        output_root=first_root,
        generated_at=FIXED_TIME,
        git_commit="abc123",
        git_dirty=True,
        renderer=_deterministic_renderer,
    )
    build_figure(
        config,
        output_root=second_root,
        generated_at=FIXED_TIME,
        git_commit="abc123",
        git_dirty=True,
        renderer=_deterministic_renderer,
    )
    assert (first_root / "manifest.json").read_bytes() == (second_root / "manifest.json").read_bytes()
    entry = json.loads((first_root / "manifest.json").read_text(encoding="utf-8"))["figures"]
    assert set(entry) == {FIGURE_ID}


def test_unknown_figure_id_fails_clearly() -> None:
    completed = subprocess.run(
        [str(PYTHON), str(CLI), "--figure", "unknown_figure"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "unknown figure ID" in completed.stderr


def test_render_failure_does_not_create_manifest_entry(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema_version": 1, "figures": {}}\n', encoding="utf-8")
    original = manifest.read_bytes()

    def fail(_request):
        raise GraphvizError("synthetic PDF failure")

    with pytest.raises(GraphvizError, match="synthetic PDF failure"):
        build_figure(
            load_visualization_config(),
            output_root=tmp_path,
            manifest_path=manifest,
            generated_at=FIXED_TIME,
            git_commit="abc123",
            git_dirty=True,
            renderer=fail,
        )
    assert manifest.read_bytes() == original
    assert not any(path.suffix in {".dot", ".svg", ".pdf"} for path in tmp_path.rglob("*"))


def test_no_other_formal_figure_is_generated(tmp_path: Path) -> None:
    outputs = build_figure(
        load_visualization_config(),
        output_root=tmp_path,
        generated_at=FIXED_TIME,
        git_commit="abc123",
        git_dirty=True,
        renderer=_deterministic_renderer,
    )
    expected = {path.resolve() for path in outputs.values()} | {(tmp_path / "manifest.json").resolve()}
    observed = {path.resolve() for path in tmp_path.rglob("*") if path.is_file()}
    assert observed == expected
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["figures"]) == {FIGURE_ID}
