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
    boundary_csv,
    build_figure,
    figure_dot,
    focal_node_map,
    node_map_csv,
    prepare_figure_data,
)
from evo_ms.visualization.layout import GraphvizError
from evo_ms.visualization.model import GraphvizRenderResult

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def prepared():
    config=load_visualization_config();return config,prepare_figure_data(config)


def _hash(path: Path): return hashlib.sha256(path.read_bytes()).hexdigest()


def _fake_renderer(request):
    request.output_path.parent.mkdir(parents=True,exist_ok=True);request.output_path.write_bytes(b"<svg/>\n" if request.output_format=="svg" else b"%PDF-1.4\n%%EOF\n")
    return GraphvizRenderResult(request.output_path.resolve(),"neato","neato test",("neato","-n2",f"-T{request.output_format}",str(request.dot_path),"-o",str(request.output_path)))


def test_exactly_eight_figures_and_three_xerces_appendix_registrations() -> None:
    config=load_visualization_config();assert len(config.figures)==8
    for stage,figure_id in FIGURE_IDS.items():
        spec=config.figures[figure_id];assert spec.stage==f"stage{stage}" and spec.destination=="appendix"
        assert spec.formats==("dot","svg","pdf") and spec.generator=="evo_ms.visualization.figures.stage123_xerces_clusters"


def test_scope_modularity_representatives_and_accepted_clusters(prepared) -> None:
    _config,data=prepared
    for stage,formal in data.formal_modularity:
        profiles=[p for p in data.profiles if p.stage==stage]
        assert sum(len(p.members) for p in profiles)==814 and len({c for p in profiles for c in p.members})==814
        assert sum(p.contribution for p in profiles)==pytest.approx(formal,abs=1e-12)
        chosen={role:p for role,p in data.selected if p.stage==stage};high,low=chosen["highest"],chosen["lowest"]
        seed,solution,hcid,hn,he,lcid,ln,destinations=EXPECTED[stage]
        assert (high.seed,high.solution_id,high.cluster_id,len(high.members),len(high.internal_edges))==(seed,solution,hcid,hn,he)
        assert (low.cluster_id,len(low.members),len(high.boundary_aggregates))==(lcid,ln,destinations)
    assert [(p.stage,len(p.members),len(p.internal_edges)) for role,p in data.selected if role=="highest"]==[(1,118,624),(2,115,570),(3,118,624)]


def test_short_ids_are_one_to_one_deterministic_and_packages_complete(prepared) -> None:
    config,data=prepared
    for stage in (1,2,3):
        high=next(p for role,p in data.selected if role=="highest" and p.stage==stage)
        first=focal_node_map(config,stage,high);second=focal_node_map(config,stage,high)
        assert first==second and len(first)==len(high.members)
        assert [r["short_id"] for r in first]==[f"F{i:03d}" for i in range(1,len(first)+1)]
        assert [r["class_id"] for r in first]==sorted(high.members)
        assert len({r["class_id"] for r in first})==len(first) and all(r["package"] for r in first)
        text=node_map_csv(first);assert text==node_map_csv(second) and text.endswith("\n") and "/Users/" not in text


def test_boundary_aggregation_reconciles_counts_and_weights(prepared) -> None:
    _config,data=prepared
    for stage in (1,2,3):
        selected=tuple((role,p) for role,p in data.selected if p.stage==stage)
        text=boundary_csv(stage,selected);assert text==boundary_csv(stage,selected) and text.endswith("\n")
        for _role,profile in selected:
            assert sum(a.boundary_edge_count for a in profile.boundary_aggregates)==len(profile.boundary_edges)
            assert sum(a.boundary_weight for a in profile.boundary_aggregates)==pytest.approx(profile.boundary_weight)
            assert {c for a in profile.boundary_aggregates for c in a.external_classes}==set(profile.external)
        high=next(p for role,p in selected if role=="highest");assert len(high.boundary_aggregates)=={1:12,2:16,3:12}[stage]


def test_dot_is_deterministic_complete_landscape_and_has_correct_inset(prepared) -> None:
    config,data=prepared
    for stage in (1,2,3):
        chosen={role:p for role,p in data.selected if p.stage==stage};high,low=chosen["highest"],chosen["lowest"]
        mapping=focal_node_map(config,stage,high);dot=figure_dot(config,stage,high,low,mapping)
        assert dot==figure_dot(config,stage,high,low,mapping) and 'size="11.111,7.5!"' in dot
        assert len(re.findall(r'^  "f_F\d{3}" \[',dot,re.MULTILINE))==len(high.members)
        assert len(re.findall(r'^  "f_F\d{3}" -- "f_F\d{3}" ',dot,re.MULTILINE))==len(high.internal_edges)
        assert "Lowest-contributing cluster" in dot
        if stage in (1,3): assert "Isolated singleton" in dot
        else: assert "Isolated singleton" not in dot and '"l_F001"' in dot and '"l_F002"' in dot


def test_three_real_landscape_renders_relative_provenance_and_manifest(tmp_path: Path) -> None:
    config=load_visualization_config()
    for figure_id in FIGURE_IDS.values():
        outputs=build_figure(config,figure_id=figure_id,output_root=tmp_path,generated_at="2026-08-06T23:00:00Z",git_commit="abc",git_dirty=True)
        assert outputs["svg"].read_text().lstrip().startswith("<?xml") and outputs["pdf"].read_bytes().startswith(b"%PDF")
        provenance=json.loads(outputs["provenance"].read_text());assert provenance["graphviz_engine"]=="neato"
        assert all(command[:2]==["neato","-n2"] for command in provenance["render_command"])
        assert "/Users/" not in outputs["provenance"].read_text() and "/tmp/" not in outputs["provenance"].read_text()
    assert set(json.loads((tmp_path/"manifest.json").read_text())["figures"])==set(FIGURE_IDS.values())


def test_render_failure_is_atomic(tmp_path: Path) -> None:
    manifest=tmp_path/"manifest.json";manifest.write_text('{"schema_version":1,"figures":{}}\n');before=manifest.read_bytes()
    def fail(_request): raise GraphvizError("synthetic Xerces render failure")
    with pytest.raises(GraphvizError,match="synthetic Xerces render failure"):
        build_figure(load_visualization_config(),figure_id=FIGURE_IDS[1],output_root=tmp_path,manifest_path=manifest,renderer=fail)
    assert manifest.read_bytes()==before and not (tmp_path/"source/cross_stage/xerces_stage1_highest_lowest_clusters.dot").exists()


def test_temporary_build_preserves_formal_inputs_and_existing_five_figures(tmp_path: Path) -> None:
    config=load_visualization_config();protected=[ROOT/path for path in config.figures[FIGURE_IDS[1]].inputs]
    existing=[path for path in (ROOT/"reports/figures").rglob("*") if path.is_file() and "xerces_stage" not in path.name]
    before={path:_hash(path) for path in (*protected,*existing)}
    for figure_id in FIGURE_IDS.values(): build_figure(config,figure_id=figure_id,output_root=tmp_path,generated_at="fixed",git_commit="abc",git_dirty=True,renderer=_fake_renderer)
    assert {path:_hash(path) for path in before}==before
