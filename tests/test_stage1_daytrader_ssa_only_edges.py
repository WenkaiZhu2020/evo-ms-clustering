from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
import re

import pytest

from evo_ms.visualization.config import load_visualization_config
from evo_ms.visualization.figures.stage1_daytrader_ssa_only_edges import (
    comparison_dot,
    nodes_csv,
    overlay_dot,
    prepare_figure_data,
    raw_edges_csv,
    ssa_only_edges_csv,
    summary,
)


def test_frozen_pair_counts_local_scopes_and_cluster_split(tmp_path: Path) -> None:
    config = load_visualization_config()
    data = prepare_figure_data(config, tmp_path)
    assert summary(data) == {
        "cross_cluster_ssa_only": 4,
        "full_induced_raw_edges": 149,
        "intra_cluster_ssa_only": 4,
        "overlap_pairs": 53,
        "raw_pairs": 161,
        "reduced_induced_raw_edges": 131,
        "reduced_nodes": 32,
        "ssa_only_pairs": 8,
        "ssa_pairs": 61,
        "v_fig": 41,
        "v_hop1_context": 30,
        "v_hop1_inclusive": 38,
        "v_new": 11,
    }


def test_source_data_is_complete_and_deterministic(tmp_path: Path) -> None:
    config = load_visualization_config()
    data = prepare_figure_data(config, tmp_path / "one")
    again = prepare_figure_data(config, tmp_path / "two")
    assert nodes_csv(data) == nodes_csv(again)
    assert raw_edges_csv(data) == raw_edges_csv(again)
    assert ssa_only_edges_csv(data) == ssa_only_edges_csv(again)
    rows = list(csv.DictReader(StringIO(ssa_only_edges_csv(data))))
    assert len(rows) == 8
    assert {row["flow_types"] for row in rows} == {"argument_passing_flow+return_value_flow"}
    assert sum(row["cross_cluster"] == "true" for row in rows) == 4
    assert all(float(row["scaled_contribution"]) == 0.25 * float(row["w_flow"]) for row in rows)


def test_panels_reuse_positions_and_only_right_adds_eight_edges(tmp_path: Path) -> None:
    config = load_visualization_config()
    data = prepare_figure_data(config, tmp_path)
    dot = comparison_dot(config, data.reduced, data.ssa_only_edges)
    positions = {}
    for panel, node, x, y in re.findall(
        r'^  "([ab])_(n\d+)" \[.*pos="([0-9.eE+-]+),([0-9.eE+-]+)!"', dot, re.MULTILINE
    ):
        positions[(panel, node)] = (float(x), float(y))
    assert len(positions) == 64
    offsets = [positions[("b", f"n{index:02d}")][0] - positions[("a", f"n{index:02d}")][0] for index in range(1, 33)]
    assert offsets == pytest.approx([offsets[0]] * 32)
    assert offsets[0] > 0
    assert [positions[("a", f"n{index:02d}")][1] for index in range(1, 33)] == pytest.approx(
        [positions[("b", f"n{index:02d}")][1] for index in range(1, 33)]
    )
    assert len(re.findall(r'^  "a_n\d+" -- "a_n\d+" ', dot, re.MULTILINE)) == 131
    assert len(re.findall(r'^  "b_n\d+" -- "b_n\d+" ', dot, re.MULTILINE)) == 139
    assert dot.count('style="dashed"') >= 8


def test_recommended_overlay_contains_one_node_set_and_both_edge_categories(tmp_path: Path) -> None:
    config = load_visualization_config()
    data = prepare_figure_data(config, tmp_path)
    dot = overlay_dot(config, data.reduced, data.ssa_only_edges)
    assert len(re.findall(r'^  "n\d+" \[', dot, re.MULTILINE)) == 32
    assert len(re.findall(r'^  "n\d+" -- "n\d+" ', dot, re.MULTILINE)) == 139
    assert len(re.findall(r'^  "n\d+" -- "n\d+" .*style="dashed"', dot, re.MULTILINE)) == 8
    assert "(a)" not in dot and "(b)" not in dot
