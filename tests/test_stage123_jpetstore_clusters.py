from __future__ import annotations

import csv
import hashlib
from io import StringIO
import json
from pathlib import Path
import re

import pytest

from evo_ms.visualization.config import load_visualization_config
from evo_ms.visualization.figures.stage123_daytrader_clusters import boundary_aggregation_csv, figure_dot, profiles_csv, selected_csv
from evo_ms.visualization.figures.stage123_jpetstore_clusters import (
    FIGURE_ID,
    STAGE2_SEED,
    STAGE2_SOLUTION,
    STAGE3_SEED,
    STAGE3_SOLUTION,
    build_figure,
    prepare_figure_data,
)
from evo_ms.visualization.layout import GraphvizError
from evo_ms.visualization.model import GraphvizRenderResult

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def prepared():
    config=load_visualization_config(); return config,prepare_figure_data(config)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fake_renderer(request) -> GraphvizRenderResult:
    request.output_path.parent.mkdir(parents=True,exist_ok=True)
    request.output_path.write_bytes(b"<svg/>\n" if request.output_format=="svg" else b"%PDF-1.4\n%%EOF\n")
    return GraphvizRenderResult(request.output_path.resolve(),"neato","neato test",("neato","-n2",f"-T{request.output_format}",str(request.dot_path),"-o",str(request.output_path)))


def test_appendix_registration_and_exactly_nine_figures() -> None:
    config=load_visualization_config(); assert len(config.figures)==9 and FIGURE_ID in config.figures
    spec=config.figures[FIGURE_ID]
    assert spec.destination=="appendix" and spec.formats==("dot","svg","pdf")
    assert spec.metadata["stage2_representative"]=="seed 1 / seed1_solution007"
    assert spec.metadata["stage3_representative"]=="seed 0 / seed0_solution000"


def test_complete_scope_representatives_modularity_and_selections(prepared) -> None:
    _config,data=prepared
    for stage,formal in data.formal_modularity:
        profiles=[profile for profile in data.profiles if profile.stage==stage]
        assert sum(len(profile.members) for profile in profiles)==24
        assert len({member for profile in profiles for member in profile.members})==24
        assert sum(profile.contribution for profile in profiles)==pytest.approx(formal,abs=1e-12)
    assert [(profile.stage,profile.seed,profile.solution_id) for role,profile in data.selected if role=="highest"]==[
        (1,42,"stage1_seed42"),(2,STAGE2_SEED,STAGE2_SOLUTION),(3,STAGE3_SEED,STAGE3_SOLUTION)]
    assert [(profile.cluster_id,len(profile.members)) for _role,profile in data.selected]==[
        ("C01",7),("C04",6),("C01",6),("C03",6),("C01",7),("C04",6)]


def test_csvs_and_aggregation_are_complete_and_deterministic(prepared) -> None:
    _config,data=prepared
    assert prepare_figure_data(_config)==data
    assert len(list(csv.DictReader(StringIO(selected_csv(data)))))==6
    assert profiles_csv(data).endswith("\n") and selected_csv(data).endswith("\n")
    aggregation=boundary_aggregation_csv(data)
    assert aggregation==boundary_aggregation_csv(data) and aggregation.endswith("\n")
    for _role,profile in data.selected:
        assert sum(a.boundary_edge_count for a in profile.boundary_aggregates)==len(profile.boundary_edges)
        assert sum(a.boundary_weight for a in profile.boundary_aggregates)==pytest.approx(profile.boundary_weight)
        assert {item for a in profile.boundary_aggregates for item in a.external_classes}==set(profile.external)


def test_dot_preserves_internal_edges_aggregates_and_three_by_two_structure(prepared) -> None:
    config,data=prepared
    dot=figure_dot(config,data,figure_id=FIGURE_ID,comparison_note="Stage 1 and Stage 3 select the same highest and lowest clusters.")
    assert dot==figure_dot(config,data,figure_id=FIGURE_ID,comparison_note="Stage 1 and Stage 3 select the same highest and lowest clusters.")
    assert len(re.findall(r'^  "p[123][hl]_panel" ',dot,re.MULTILINE))==6
    for role,profile in data.selected:
        prefix=f"p{profile.stage}{role[0]}"; ids={member:f"{prefix}_f{i:03d}" for i,member in enumerate(profile.members,1)}
        for member in profile.members: assert f'"{ids[member]}" [' in dot
        for left,right,_weight in profile.internal_edges: assert f'"{ids[left]}" -- "{ids[right]}"' in dot
        for aggregate in profile.boundary_aggregates: assert f'"{prefix}_x{aggregate.external_cluster_id}" [' in dot


def test_real_svg_pdf_relative_provenance_and_atomic_manifest(tmp_path: Path) -> None:
    outputs=build_figure(load_visualization_config(),output_root=tmp_path,generated_at="2026-08-06T22:00:00Z",git_commit="abc",git_dirty=True)
    assert outputs["svg"].read_text().lstrip().startswith("<?xml") and outputs["pdf"].read_bytes().startswith(b"%PDF")
    provenance=json.loads(outputs["provenance"].read_text()); assert provenance["graphviz_engine"]=="neato"
    assert all(command[:2]==["neato","-n2"] for command in provenance["render_command"])
    assert "/Users/" not in outputs["provenance"].read_text() and "/tmp/" not in outputs["provenance"].read_text()
    assert set(json.loads((tmp_path/"manifest.json").read_text())["figures"])=={FIGURE_ID}


def test_render_failure_publishes_nothing(tmp_path: Path) -> None:
    manifest=tmp_path/"manifest.json"; manifest.write_text('{"schema_version":1,"figures":{}}\n'); before=manifest.read_bytes()
    def fail(_request): raise GraphvizError("synthetic JPetStore cluster failure")
    with pytest.raises(GraphvizError,match="synthetic JPetStore cluster failure"):
        build_figure(load_visualization_config(),output_root=tmp_path,manifest_path=manifest,renderer=fail)
    assert manifest.read_bytes()==before and not (tmp_path/"source/cross_stage/jpetstore_highest_lowest_clusters.dot").exists()


def test_temporary_build_preserves_formal_inputs_and_existing_four_figures(tmp_path: Path) -> None:
    config=load_visualization_config(); protected=[ROOT/path for path in config.figures[FIGURE_ID].inputs]
    existing=[path for path in (ROOT/"reports/figures").rglob("*") if path.is_file() and "jpetstore_highest_lowest" not in path.name]
    before={path:_hash(path) for path in (*protected,*existing)}
    build_figure(config,output_root=tmp_path,generated_at="fixed",git_commit="abc",git_dirty=True,renderer=_fake_renderer)
    assert {path:_hash(path) for path in before}==before
