"""DayTrader local G_raw versus G_ssa comparison for SSA-only edges."""

from __future__ import annotations

from collections import defaultdict
import csv
from dataclasses import dataclass
from io import StringIO
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

import pandas as pd

from evo_ms.evidence.ssa_flow_evidence import aggregate_ssa_flow_weights
from evo_ms.graph.raw_graph_builder import build_raw_edges
from evo_ms.visualization.dot import dot_quote, format_number, stable_attributes, write_dot
from evo_ms.visualization.layout import find_graphviz, render_graphviz
from evo_ms.visualization.model import GraphvizRenderRequest, VisualizationConfig
from evo_ms.visualization.provenance import (
    build_provenance,
    sha256_file,
    write_json_atomic,
    write_provenance,
)


FIGURE_ID = "stage1_daytrader_ssa_only_edge_comparison"
STAGE_DIRECTORY = "stage1"
BASENAME = "daytrader_ssa_only_edge_comparison"
FULL_BASENAME = f"{BASENAME}_full"
LAMBDA = 0.25
EXPECTED_RAW_PAIRS = 161
EXPECTED_SSA_PAIRS = 61
EXPECTED_OVERLAP = 53
EXPECTED_SSA_ONLY = 8

INPUTS = (
    "data/extracted/daytrader/class_nodes.csv",
    "data/extracted/daytrader/structural_dependencies.csv",
    "data/extracted/daytrader/ssa_flow_edges.csv",
    "results/stage1/subjects/daytrader/leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv",
    "results/stage1/subjects/daytrader/leiden_baseline/raw_reference_leiden/graph/stage1_edges.csv",
    "results/stage1/subjects/daytrader/seed_robustness/robustness_metadata.yml",
)


@dataclass(frozen=True)
class NodeRecord:
    class_id: str
    display_name: str
    cluster_id: int
    role: str


@dataclass(frozen=True)
class RawEdgeRecord:
    source: str
    target: str
    type_weight: float
    call_weight: float
    raw_weight: float


@dataclass(frozen=True)
class SSAOnlyEdgeRecord:
    source: str
    target: str
    flow_types: tuple[str, ...]
    method_record_count: int
    method_count: int
    return_flow_weight: float
    argument_flow_weight: float
    w_flow: float
    scaled_contribution: float
    source_cluster: int
    target_cluster: int

    @property
    def cross_cluster(self) -> bool:
        return self.source_cluster != self.target_cluster


@dataclass(frozen=True)
class VariantData:
    name: str
    nodes: tuple[NodeRecord, ...]
    raw_edges: tuple[RawEdgeRecord, ...]
    positions: tuple[tuple[str, float, float], ...]


@dataclass(frozen=True)
class FigureData:
    full: VariantData
    reduced: VariantData
    ssa_only_edges: tuple[SSAOnlyEdgeRecord, ...]
    raw_pair_count: int
    ssa_pair_count: int
    overlap_count: int
    hop1_inclusive_count: int
    hop1_context_count: int


def _canonical_pair(source: object, target: object) -> tuple[str, str]:
    left, right = str(source), str(target)
    if left == right:
        raise ValueError(f"self-loop is not a class-pair edge: {left}")
    return (left, right) if left < right else (right, left)


def _display_names(class_ids: set[str]) -> dict[str, str]:
    simple = {class_id: class_id.rsplit(".", 1)[-1] for class_id in class_ids}
    duplicates: dict[str, list[str]] = defaultdict(list)
    for class_id, name in simple.items():
        duplicates[name].append(class_id)
    result = dict(simple)
    for name, members in duplicates.items():
        if len(members) > 1:
            for class_id in members:
                result[class_id] = ".".join(class_id.rsplit(".", 2)[-2:])
    if len(set(result.values())) != len(result):
        raise ValueError("short DayTrader labels remain ambiguous after package qualification")
    return result


def _layout_label(display_name: str, cluster_id: int) -> str:
    if "." in display_name:
        prefix, name = display_name.split(".", 1)
        return f"{prefix}.{name}\nC{cluster_id}"
    capitals = [index for index, char in enumerate(display_name) if index and char.isupper()]
    if len(display_name) > 17 and capitals:
        split = min(capitals, key=lambda index: abs(index - len(display_name) / 2))
        return f"{display_name[:split]}\n{display_name[split:]} (C{cluster_id})"
    return f"{display_name}\nC{cluster_id}"


def _validate_input_hashes(root: Path) -> None:
    import yaml

    metadata = yaml.safe_load(
        (root / "results/stage1/subjects/daytrader/seed_robustness/robustness_metadata.yml")
        .read_text(encoding="utf-8")
    )
    expected = metadata.get("extracted_input_sha256", {})
    for name in ("class_nodes.csv", "structural_dependencies.csv", "ssa_flow_edges.csv"):
        path = root / "data/extracted/daytrader" / name
        if expected.get(name) != sha256_file(path):
            raise ValueError(f"frozen Stage 1 input hash disagrees with robustness metadata: {name}")
    if float(metadata.get("ssa_ssa_lambda")) != LAMBDA:
        raise ValueError("frozen DayTrader SSA lambda is no longer 0.25")


def _initial_positions(
    config: VisualizationConfig,
    nodes: tuple[NodeRecord, ...],
    raw_edges: tuple[RawEdgeRecord, ...],
    ssa_edges: tuple[SSAOnlyEdgeRecord, ...],
    directory: Path,
) -> tuple[tuple[str, float, float], ...]:
    directory.mkdir(parents=True, exist_ok=True)
    dot_path = directory / "layout.dot"
    plain_path = directory / "layout.plain"
    node_ids = {node.class_id for node in nodes}
    lines = [
        'graph "DayTrader SSA-only local layout" {',
        '  graph [overlap=false, outputorder=edgesfirst, sep="+18", start=42];',
        '  node [fontname="Helvetica", fontsize=7, height=0.22, margin="0.025,0.014", shape=box];',
    ]
    for node in nodes:
        lines.append(f"  {dot_quote(node.class_id)} [label={dot_quote(_layout_label(node.display_name, node.cluster_id))}];")
    for edge in raw_edges:
        lines.append(f"  {dot_quote(edge.source)} -- {dot_quote(edge.target)};")
    for edge in ssa_edges:
        if edge.source in node_ids and edge.target in node_ids:
            lines.append(f"  {dot_quote(edge.source)} -- {dot_quote(edge.target)};")
    lines.append("}")
    write_dot(dot_path, "\n".join(lines) + "\n")
    executable = find_graphviz("neato")
    environment = {**os.environ, "SOURCE_DATE_EPOCH": "0"}
    completed = subprocess.run(
        [str(executable), "-Tplain", str(dot_path), "-o", str(plain_path)],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    if completed.returncode != 0:
        raise ValueError(f"neato layout failed: {(completed.stderr or completed.stdout).strip()}")
    positions: dict[str, tuple[float, float, float, float]] = {}
    for line in plain_path.read_text(encoding="utf-8").splitlines():
        fields = shlex.split(line)
        if fields and fields[0] == "node":
            positions[fields[1]] = (
                float(fields[2]), float(fields[3]), float(fields[4]), float(fields[5])
            )
    if set(positions) != node_ids:
        raise ValueError("neato layout did not return one position for every selected class")
    # Pack the force-directed order into a narrow deterministic grid.  The local
    # graph is too dense to shrink a free layout into two dissertation-width
    # side-by-side panels without shrinking node labels or reintroducing overlap.
    column_count = 3 if len(nodes) <= 32 else 4
    ordered = sorted(nodes, key=lambda node: (positions[node.class_id][0], node.class_id))
    base, remainder = divmod(len(ordered), column_count)
    columns: list[list[NodeRecord]] = []
    cursor = 0
    for column_index in range(column_count):
        size = base + (1 if column_index < remainder else 0)
        members = ordered[cursor:cursor + size]
        columns.append(sorted(members, key=lambda node: (positions[node.class_id][1], node.class_id)))
        cursor += size
    packed: dict[str, tuple[float, float]] = {}
    for column_index, members in enumerate(columns):
        x = column_index / (column_count - 1)
        for row_index, node in enumerate(members):
            y = (row_index + 0.5) / len(members)
            packed[node.class_id] = (x, y)
    return tuple((node.class_id, *packed[node.class_id]) for node in nodes)


def prepare_figure_data(config: VisualizationConfig, layout_root: Path) -> FigureData:
    """Recompute the audited local subgraphs from frozen extraction artefacts."""

    root = config.repository_root
    _validate_input_hashes(root)
    nodes_frame = pd.read_csv(root / INPUTS[0])
    dependencies = pd.read_csv(root / INPUTS[1])
    flows = pd.read_csv(root / INPUTS[2])
    clusters = pd.read_csv(root / INPUTS[3])
    frozen_raw = pd.read_csv(root / INPUTS[4])
    if len(nodes_frame) != 53 or nodes_frame["class_id"].astype(str).duplicated().any():
        raise ValueError("frozen DayTrader class scope must contain 53 unique classes")
    node_ids = set(nodes_frame["class_id"].astype(str))
    if set(clusters["class_id"].astype(str)) != node_ids or clusters["class_id"].astype(str).duplicated().any():
        raise ValueError("seed-42 raw Leiden partition does not cover the frozen DayTrader scope")

    raw_frame = build_raw_edges(nodes_frame, dependencies)
    raw_pairs = {_canonical_pair(row.source, row.target) for row in raw_frame.itertuples(index=False)}
    frozen_pairs = {_canonical_pair(row.source, row.target) for row in frozen_raw.itertuples(index=False)}
    if raw_pairs != frozen_pairs:
        raise ValueError("recomputed G_raw pairs disagree with the frozen Stage 1 graph")
    flow_aggregate = aggregate_ssa_flow_weights(nodes_frame, flows)
    ssa_pairs = {_canonical_pair(row.source, row.target) for row in flow_aggregate.itertuples(index=False)}
    overlap = raw_pairs & ssa_pairs
    ssa_only_pairs = sorted(ssa_pairs - raw_pairs)
    observed = (len(raw_pairs), len(ssa_pairs), len(overlap), len(ssa_only_pairs))
    expected = (EXPECTED_RAW_PAIRS, EXPECTED_SSA_PAIRS, EXPECTED_OVERLAP, EXPECTED_SSA_ONLY)
    if observed != expected:
        raise ValueError(f"DayTrader Stage 1 pair counts changed: observed {observed}, expected {expected}")

    cluster_by_id = {
        str(row.class_id): int(row.cluster_id) for row in clusters.itertuples(index=False)
    }
    aggregate_by_pair = {
        _canonical_pair(row.source, row.target): row for row in flow_aggregate.itertuples(index=False)
    }
    ssa_records: list[SSAOnlyEdgeRecord] = []
    for source, target in ssa_only_pairs:
        mask = (
            ((flows["source"].astype(str) == source) & (flows["target"].astype(str) == target))
            | ((flows["source"].astype(str) == target) & (flows["target"].astype(str) == source))
        )
        rows = flows.loc[mask]
        aggregate = aggregate_by_pair[(source, target)]
        return_weight = float(aggregate.return_flow_weight)
        argument_weight = float(aggregate.argument_flow_weight)
        w_flow = return_weight + argument_weight
        ssa_records.append(SSAOnlyEdgeRecord(
            source=source,
            target=target,
            flow_types=tuple(sorted(set(rows["flow_type"].astype(str)))),
            method_record_count=len(rows),
            method_count=rows["evidence_method"].astype(str).nunique(),
            return_flow_weight=return_weight,
            argument_flow_weight=argument_weight,
            w_flow=w_flow,
            scaled_contribution=LAMBDA * w_flow,
            source_cluster=cluster_by_id[source],
            target_cluster=cluster_by_id[target],
        ))

    v_new = {endpoint for pair in ssa_only_pairs for endpoint in pair}
    adjacency = {class_id: set() for class_id in node_ids}
    for source, target in raw_pairs:
        adjacency[source].add(target)
        adjacency[target].add(source)
    v_hop1 = {neighbour for class_id in v_new for neighbour in adjacency[class_id]}
    v_full = v_new | v_hop1
    bridge_context = {
        class_id for class_id in v_hop1 - v_new if len(adjacency[class_id] & v_new) >= 2
    }
    v_reduced = v_new | bridge_context
    if len(v_full) <= 25:
        raise ValueError("DayTrader local scope no longer triggers the specified reduced-variant rule")

    names = _display_names(v_full)
    raw_by_pair = {
        _canonical_pair(row.source, row.target): RawEdgeRecord(
            *_canonical_pair(row.source, row.target),
            float(row.type_weight), float(row.call_weight), float(row.raw_weight),
        )
        for row in raw_frame.itertuples(index=False)
    }

    def make_variant(name: str, selected: set[str]) -> VariantData:
        selected_nodes = tuple(
            NodeRecord(class_id, names[class_id], cluster_by_id[class_id], "ssa_endpoint" if class_id in v_new else "context")
            for class_id in sorted(selected)
        )
        selected_edges = tuple(
            raw_by_pair[pair] for pair in sorted(raw_pairs) if pair[0] in selected and pair[1] in selected
        )
        positions = _initial_positions(
            config, selected_nodes, selected_edges, tuple(ssa_records), layout_root / name
        )
        return VariantData(name, selected_nodes, selected_edges, positions)

    return FigureData(
        full=make_variant("full", v_full),
        reduced=make_variant("reduced", v_reduced),
        ssa_only_edges=tuple(ssa_records),
        raw_pair_count=len(raw_pairs),
        ssa_pair_count=len(ssa_pairs),
        overlap_count=len(overlap),
        hop1_inclusive_count=len(v_hop1),
        hop1_context_count=len(v_hop1 - v_new),
    )


def nodes_csv(data: FigureData) -> str:
    buffer = StringIO(newline="")
    fields = ("variant", "class_id", "display_name", "node_role", "seed42_raw_cluster_id", "layout_x", "layout_y")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for variant in (data.reduced, data.full):
        positions = {class_id: (x, y) for class_id, x, y in variant.positions}
        for node in variant.nodes:
            x, y = positions[node.class_id]
            writer.writerow({
                "variant": variant.name, "class_id": node.class_id, "display_name": node.display_name,
                "node_role": node.role, "seed42_raw_cluster_id": node.cluster_id,
                "layout_x": format(x, ".17g"), "layout_y": format(y, ".17g"),
            })
    return buffer.getvalue()


def raw_edges_csv(data: FigureData) -> str:
    buffer = StringIO(newline="")
    fields = ("variant", "source", "target", "type_weight", "call_weight", "raw_weight")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for variant in (data.reduced, data.full):
        for edge in variant.raw_edges:
            writer.writerow({
                "variant": variant.name, "source": edge.source, "target": edge.target,
                "type_weight": format(edge.type_weight, ".17g"),
                "call_weight": format(edge.call_weight, ".17g"),
                "raw_weight": format(edge.raw_weight, ".17g"),
            })
    return buffer.getvalue()


def ssa_only_edges_csv(data: FigureData) -> str:
    buffer = StringIO(newline="")
    fields = (
        "source", "target", "flow_types", "method_level_record_count", "distinct_evidence_method_count",
        "return_flow_weight", "argument_flow_weight", "w_flow", "lambda", "scaled_contribution",
        "source_seed42_raw_cluster_id", "target_seed42_raw_cluster_id", "cross_cluster",
    )
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for edge in data.ssa_only_edges:
        writer.writerow({
            "source": edge.source, "target": edge.target, "flow_types": "+".join(edge.flow_types),
            "method_level_record_count": edge.method_record_count,
            "distinct_evidence_method_count": edge.method_count,
            "return_flow_weight": format(edge.return_flow_weight, ".17g"),
            "argument_flow_weight": format(edge.argument_flow_weight, ".17g"),
            "w_flow": format(edge.w_flow, ".17g"), "lambda": format(LAMBDA, ".17g"),
            "scaled_contribution": format(edge.scaled_contribution, ".17g"),
            "source_seed42_raw_cluster_id": edge.source_cluster,
            "target_seed42_raw_cluster_id": edge.target_cluster,
            "cross_cluster": str(edge.cross_cluster).lower(),
        })
    return buffer.getvalue()


def _pale(hex_color: str, mix: float = 0.72) -> str:
    value = hex_color.lstrip("#")
    channels = [int(value[index:index + 2], 16) for index in (0, 2, 4)]
    mixed = [round(channel + (255 - channel) * mix) for channel in channels]
    return "#" + "".join(f"{channel:02X}" for channel in mixed)


def comparison_dot(config: VisualizationConfig, variant: VariantData, ssa_edges: tuple[SSAOnlyEdgeRecord, ...]) -> str:
    """Create two horizontally aligned panels from one normalized layout."""

    style = config.style
    font = style["fonts"]["family"]
    palette = tuple(style["cluster_palette"])
    # The reduced candidate targets the configured 9.2 x 7.0 inch appendix
    # profile in landscape orientation after Graphviz adds its small page pad.
    canvas_width = 650.0 if variant.name == "reduced" else 760.0
    canvas_height = 495.0 if variant.name == "reduced" else 540.0
    margin_x = 30.0
    gap = 44.0
    panel_width = (canvas_width - 2 * margin_x - gap) / 2
    plot_bottom = 54.0
    plot_top = canvas_height - 58.0
    plot_height = plot_top - plot_bottom
    left_origin = margin_x
    right_origin = margin_x + panel_width + gap
    positions = {class_id: (x, y) for class_id, x, y in variant.positions}
    node_by_id = {node.class_id: node for node in variant.nodes}
    ids = {class_id: f"n{index:02d}" for index, class_id in enumerate(sorted(node_by_id), start=1)}
    node_ids = set(node_by_id)
    lines = [
        f"graph {dot_quote('DayTrader G_raw versus G_ssa local comparison')} {{",
        "  graph " + stable_attributes({
            "bgcolor": style["graph"]["background"], "margin": 0.02, "notranslate": True,
            "outputorder": "edgesfirst", "overlap": True, "pad": 0.04, "splines": True,
        }) + ";",
        "  node " + stable_attributes({
            "fontname": font, "fontsize": style["semantic_evidence_comparison"]["node_font_size"],
            "height": 0.22, "margin": "0.025,0.014",
            "shape": "box", "style": "rounded,filled",
        }) + ";",
        "  edge " + stable_attributes({"dir": "none"}) + ";",
        "",
    ]
    for panel, origin in (("a", left_origin), ("b", right_origin)):
        for class_id in sorted(node_by_id):
            node = node_by_id[class_id]
            x, y = positions[class_id]
            px = origin + 10.0 + x * (panel_width - 20.0)
            py = plot_bottom + 10.0 + y * (plot_height - 20.0)
            lines.append(
                f"  {dot_quote(panel + '_' + ids[class_id])} " + stable_attributes({
                    "color": "#1F1F1F" if node.role == "ssa_endpoint" else "#777777",
                    "fillcolor": _pale(palette[node.cluster_id % len(palette)]),
                    "label": _layout_label(node.display_name, node.cluster_id), "pin": True,
                    "penwidth": 2.2 if node.role == "ssa_endpoint" else 0.75,
                    "pos": f"{format_number(px)},{format_number(py)}!", "tooltip": node.class_id,
                }) + ";"
            )
    structural = style["edge_categories"]["structural"]
    ssa_style = style["edge_categories"]["ssa_only"]
    for panel in ("a", "b"):
        for edge in variant.raw_edges:
            lines.append(
                f"  {dot_quote(panel + '_' + ids[edge.source])} -- {dot_quote(panel + '_' + ids[edge.target])} "
                + stable_attributes({
                    "color": "#888888", "penwidth": 0.55, "style": structural["style"],
                    "tooltip": f"{edge.source} -- {edge.target}: G_raw",
                }) + ";"
            )
    for edge in ssa_edges:
        if edge.source in node_ids and edge.target in node_ids:
            lines.append(
                f"  {dot_quote('b_' + ids[edge.source])} -- {dot_quote('b_' + ids[edge.target])} "
                + stable_attributes({
                    "color": ssa_style["color"], "penwidth": 1.8, "style": ssa_style["style"],
                    "tooltip": f"{edge.source} -- {edge.target}: SSA-only",
                }) + ";"
            )
    for node_id, x in (("title_a", left_origin + panel_width / 2), ("title_b", right_origin + panel_width / 2)):
        label = "(a) G_raw local view" if node_id.endswith("a") else "(b) G_ssa local view (+8 SSA-only pairs)"
        lines.append(
            f"  {dot_quote(node_id)} " + stable_attributes({
                "color": "transparent", "fillcolor": "transparent", "fontname": font,
                "fontcolor": "#111111", "fontsize": 10.0, "label": label, "pin": True,
                "pos": f"{format_number(x)},{format_number(canvas_height - 24)}!", "shape": "plain", "style": "",
            }) + ";"
        )
    legend_y = 24.0
    legend_items = (
        (55.0, "#888888", "solid", 0.8, "G_raw pair"),
        (190.0, ssa_style["color"], ssa_style["style"], 1.8, "SSA-only pair"),
    )
    for index, (x, color, edge_style, width, label) in enumerate(legend_items, start=1):
        for suffix, dx in (("l", 0.0), ("r", 20.0)):
            lines.append(
                f"  {dot_quote(f'legend_{index}_{suffix}')} " + stable_attributes({
                    "height": 0.01, "label": "", "pin": True,
                    "pos": f"{format_number(x + dx)},{format_number(legend_y)}!",
                    "shape": "point", "style": "invis", "width": 0.01,
                }) + ";"
            )
        lines.append(
            f"  {dot_quote(f'legend_{index}_l')} -- {dot_quote(f'legend_{index}_r')} "
            + stable_attributes({"color": color, "penwidth": width, "style": edge_style}) + ";"
        )
        lines.append(
            f"  {dot_quote(f'legend_{index}_label')} " + stable_attributes({
                "color": "transparent", "fillcolor": "transparent", "fontname": font,
                "fontcolor": "#111111", "fontsize": 7.0, "label": label, "pin": True,
                "pos": f"{format_number(x + 62)},{format_number(legend_y)}!", "shape": "plain", "style": "",
            }) + ";"
        )
    lines.append(
        f"  {dot_quote('legend_nodes')} " + stable_attributes({
            "color": "transparent", "fillcolor": "transparent", "fontname": font,
            "fontcolor": "#111111", "fontsize": 7.0,
            "label": "thick border = endpoint of an SSA-only pair; fill and Cn = seed-42 raw Leiden cluster",
            "pin": True, "pos": f"{format_number(canvas_width - 220)},{format_number(legend_y)}!",
            "shape": "plain", "style": "",
        }) + ";"
    )
    for name, x, y in (("anchor_ll", 0.0, 0.0), ("anchor_ur", canvas_width, canvas_height)):
        lines.append(
            f"  {dot_quote(name)} " + stable_attributes({
                "height": 0.01, "label": "", "pin": True, "pos": f"{x},{y}!",
                "shape": "point", "style": "invis", "width": 0.01,
            }) + ";"
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def overlay_dot(config: VisualizationConfig, variant: VariantData, ssa_edges: tuple[SSAOnlyEdgeRecord, ...]) -> str:
    """Create the recommended single-panel local evidence overlay."""

    style = config.style
    font = style["fonts"]["family"]
    palette = tuple(style["cluster_palette"])
    ssa_style = style["edge_categories"]["ssa_only"]
    canvas_width = 450.0
    canvas_height = 520.0
    plot_left = 34.0
    plot_right = canvas_width - 34.0
    plot_bottom = 54.0
    plot_top = canvas_height - 58.0
    positions = {class_id: (x, y) for class_id, x, y in variant.positions}
    node_by_id = {node.class_id: node for node in variant.nodes}
    ids = {class_id: f"n{index:02d}" for index, class_id in enumerate(sorted(node_by_id), start=1)}
    lines = [
        f"graph {dot_quote('DayTrader local structural and SSA-only evidence')} {{",
        "  graph " + stable_attributes({
            "bgcolor": style["graph"]["background"], "margin": 0.02, "notranslate": True,
            "outputorder": "edgesfirst", "overlap": True, "pad": 0.04, "splines": False,
        }) + ";",
        "  node " + stable_attributes({
            "fontname": font, "fontsize": style["semantic_evidence_comparison"]["node_font_size"],
            "height": 0.22, "margin": "0.025,0.014", "shape": "box", "style": "rounded,filled",
        }) + ";",
        "  edge " + stable_attributes({"dir": "none"}) + ";",
        "",
    ]
    for class_id in sorted(node_by_id):
        node = node_by_id[class_id]
        x, y = positions[class_id]
        px = plot_left + x * (plot_right - plot_left)
        py = plot_bottom + 10.0 + y * (plot_top - plot_bottom - 20.0)
        lines.append(
            f"  {dot_quote(ids[class_id])} " + stable_attributes({
                "color": "#1F1F1F" if node.role == "ssa_endpoint" else "#777777",
                "fillcolor": _pale(palette[node.cluster_id % len(palette)]),
                "label": _layout_label(node.display_name, node.cluster_id), "pin": True,
                "penwidth": 2.2 if node.role == "ssa_endpoint" else 0.75,
                "pos": f"{format_number(px)},{format_number(py)}!", "tooltip": node.class_id,
            }) + ";"
        )
    for edge in variant.raw_edges:
        lines.append(
            f"  {dot_quote(ids[edge.source])} -- {dot_quote(ids[edge.target])} "
            + stable_attributes({
                "color": "#888888", "penwidth": 0.55, "style": "solid",
                "tooltip": f"{edge.source} -- {edge.target}: G_raw",
            }) + ";"
        )
    for edge in ssa_edges:
        lines.append(
            f"  {dot_quote(ids[edge.source])} -- {dot_quote(ids[edge.target])} "
            + stable_attributes({
                "color": ssa_style["color"], "penwidth": 2.1, "style": ssa_style["style"],
                "tooltip": f"{edge.source} -- {edge.target}: SSA-only",
            }) + ";"
        )
    lines.append(
        f"  {dot_quote('title')} " + stable_attributes({
            "color": "transparent", "fillcolor": "transparent", "fontcolor": "#111111",
            "fontname": font, "fontsize": 10.0,
            "label": "DayTrader local evidence: raw structural edges and 8 SSA-only class pairs", "pin": True,
            "pos": f"{format_number(canvas_width / 2)},{format_number(canvas_height - 24)}!",
            "shape": "plain", "style": "",
        }) + ";"
    )
    legend_y = 24.0
    for index, (x, color, edge_style, width, label) in enumerate((
        (42.0, "#888888", "solid", 0.8, "raw structural edge"),
        (168.0, ssa_style["color"], ssa_style["style"], 2.1, "SSA-only pair"),
    ), start=1):
        for suffix, dx in (("l", 0.0), ("r", 20.0)):
            lines.append(
                f"  {dot_quote(f'legend_{index}_{suffix}')} " + stable_attributes({
                    "height": 0.01, "label": "", "pin": True,
                    "pos": f"{format_number(x + dx)},{format_number(legend_y)}!",
                    "shape": "point", "style": "invis", "width": 0.01,
                }) + ";"
            )
        lines.append(
            f"  {dot_quote(f'legend_{index}_l')} -- {dot_quote(f'legend_{index}_r')} "
            + stable_attributes({"color": color, "penwidth": width, "style": edge_style}) + ";"
        )
        lines.append(
            f"  {dot_quote(f'legend_{index}_label')} " + stable_attributes({
                "color": "transparent", "fillcolor": "transparent", "fontcolor": "#111111",
                "fontname": font, "fontsize": 7.0, "label": label, "pin": True,
                "pos": f"{format_number(x + 61)},{format_number(legend_y)}!",
                "shape": "plain", "style": "",
            }) + ";"
        )
    lines.append(
        f"  {dot_quote('legend_nodes')} " + stable_attributes({
            "color": "transparent", "fillcolor": "transparent", "fontcolor": "#111111",
            "fontname": font, "fontsize": 6.8,
            "label": "thick border = SSA-only endpoint; fill and Cn = seed-42 raw Leiden cluster",
            "pin": True, "pos": f"{format_number(canvas_width / 2)},{format_number(7)}!",
            "shape": "plain", "style": "",
        }) + ";"
    )
    for name, x, y in (("anchor_ll", 0.0, 0.0), ("anchor_ur", canvas_width, canvas_height)):
        lines.append(
            f"  {dot_quote(name)} " + stable_attributes({
                "height": 0.01, "label": "", "pin": True, "pos": f"{x},{y}!",
                "shape": "point", "style": "invis", "width": 0.01,
            }) + ";"
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def _targets(config: VisualizationConfig) -> dict[str, Path]:
    return {
        "nodes": config.output.data / STAGE_DIRECTORY / f"{BASENAME}_nodes.csv",
        "raw_edges": config.output.data / STAGE_DIRECTORY / f"{BASENAME}_raw_edges.csv",
        "ssa_only_edges": config.output.data / STAGE_DIRECTORY / f"{BASENAME}_ssa_only_edges.csv",
        "dot": config.output.dot / STAGE_DIRECTORY / f"{BASENAME}.dot",
        "full_dot": config.output.dot / STAGE_DIRECTORY / f"{FULL_BASENAME}.dot",
        "svg": config.output.svg / STAGE_DIRECTORY / f"{BASENAME}.svg",
        "full_svg": config.output.svg / STAGE_DIRECTORY / f"{FULL_BASENAME}.svg",
        "pdf": config.output.pdf / STAGE_DIRECTORY / f"{BASENAME}.pdf",
        "full_pdf": config.output.pdf / STAGE_DIRECTORY / f"{FULL_BASENAME}.pdf",
        "provenance": config.output.data / STAGE_DIRECTORY / f"{BASENAME}.provenance.json",
        "manifest_fragment": config.output.data / STAGE_DIRECTORY / f"{BASENAME}.manifest.json",
    }


def build_figure(
    config: VisualizationConfig,
    *,
    generated_at: str = "2026-08-13T00:00:00Z",
    git_commit: str | None = None,
    git_dirty: bool | None = None,
) -> dict[str, Path]:
    """Build both additive variants and publish the reduced variant as canonical."""

    targets = _targets(config)
    for path in targets.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    staging_parent = config.repository_root / "reports/figures"
    with tempfile.TemporaryDirectory(prefix=f".{FIGURE_ID}.", dir=staging_parent) as temporary:
        stage = Path(temporary)
        data = prepare_figure_data(config, stage / "layout")
        staged = {name: stage / path.name for name, path in targets.items()}
        staged["nodes"].write_text(nodes_csv(data), encoding="utf-8", newline="\n")
        staged["raw_edges"].write_text(raw_edges_csv(data), encoding="utf-8", newline="\n")
        staged["ssa_only_edges"].write_text(ssa_only_edges_csv(data), encoding="utf-8", newline="\n")
        write_dot(staged["dot"], overlay_dot(config, data.reduced, data.ssa_only_edges))
        write_dot(staged["full_dot"], comparison_dot(config, data.full, data.ssa_only_edges))
        render_results = []
        for prefix in ("", "full_"):
            for output_format in ("svg", "pdf"):
                name = prefix + output_format
                dot_name = prefix + "dot"
                render_results.append(render_graphviz(
                    GraphvizRenderRequest(staged[dot_name], staged[name], output_format, "neato", True)
                ))
        generated_for_provenance = tuple(targets[name] for name in targets if name not in {"manifest_fragment"})
        render_commands = (
            ("neato", "-n2", "-Tsvg", str(targets["dot"]), "-o", str(targets["svg"])),
            ("neato", "-n2", "-Tpdf", str(targets["dot"]), "-o", str(targets["pdf"])),
            ("neato", "-n2", "-Tsvg", str(targets["full_dot"]), "-o", str(targets["full_svg"])),
            ("neato", "-n2", "-Tpdf", str(targets["full_dot"]), "-o", str(targets["full_pdf"])),
        )
        provenance = build_provenance(
            figure_id=FIGURE_ID,
            stage=STAGE_DIRECTORY,
            generator="src/evo_ms/visualization/figures/stage1_daytrader_ssa_only_edges.py",
            repository_root=config.repository_root,
            input_files=(config.repository_root / path for path in INPUTS),
            config_files=(config.style_config_path,),
            dot_path=staged["dot"],
            graphviz_engine="neato",
            graphviz_version=render_results[0].version,
            render_commands=render_commands,
            generated_outputs=generated_for_provenance,
            generated_at=generated_at,
            git_commit=git_commit,
            git_dirty=git_dirty,
        )
        write_provenance(staged["provenance"], provenance)
        hashes = {
            name: sha256_file(staged[name])
            for name in sorted(staged)
            if name not in {"manifest_fragment"}
        }
        manifest = {
            "schema_version": 1,
            "figures": {
                FIGURE_ID: {
                    "destination": "main_text",
                    "formats": ["dot", "svg", "pdf"],
                    "generated_at": generated_at,
                    "generator": "evo_ms.visualization.figures.stage1_daytrader_ssa_only_edges",
                    "inputs": list(INPUTS),
                    "metadata": {
                        "subject": "daytrader", "lambda": LAMBDA,
                        "raw_pairs": data.raw_pair_count, "ssa_supported_pairs": data.ssa_pair_count,
                        "overlap_pairs": data.overlap_count, "ssa_only_pairs": len(data.ssa_only_edges),
                        "recommended_variant": "reduced single-panel overlay",
                        "reduced_rule": "V_new plus hop-1 context adjacent to at least two V_new classes",
                    },
                    "outputs": {
                        name: path.relative_to(config.repository_root).as_posix()
                        for name, path in sorted(targets.items())
                    },
                    "sha256": hashes,
                    "stage": STAGE_DIRECTORY,
                    "title": "DayTrader local evidence: raw structural edges and 8 SSA-only class pairs",
                }
            },
        }
        write_json_atomic(staged["manifest_fragment"], manifest)
        for name, target in targets.items():
            os.replace(staged[name], target)
    return targets


def summary(data: FigureData) -> dict[str, object]:
    return {
        "raw_pairs": data.raw_pair_count,
        "ssa_pairs": data.ssa_pair_count,
        "overlap_pairs": data.overlap_count,
        "ssa_only_pairs": len(data.ssa_only_edges),
        "v_new": sum(node.role == "ssa_endpoint" for node in data.full.nodes),
        "v_hop1_inclusive": data.hop1_inclusive_count,
        "v_hop1_context": data.hop1_context_count,
        "v_fig": len(data.full.nodes),
        "full_induced_raw_edges": len(data.full.raw_edges),
        "reduced_nodes": len(data.reduced.nodes),
        "reduced_induced_raw_edges": len(data.reduced.raw_edges),
        "intra_cluster_ssa_only": sum(not edge.cross_cluster for edge in data.ssa_only_edges),
        "cross_cluster_ssa_only": sum(edge.cross_cluster for edge in data.ssa_only_edges),
    }
