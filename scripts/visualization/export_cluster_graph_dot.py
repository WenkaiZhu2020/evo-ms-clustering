#!/usr/bin/env python3
"""Export a partition as a deterministic cluster-level Graphviz graph."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from export_partition_dot import (
    EDGE_COLUMNS,
    NODE_COLUMNS,
    PARTITION_COLUMNS,
    canonical_clusters,
    cluster_signatures,
    maximum_overlap_matching,
    read_csv,
    validate_and_load,
    validate_partition_rows,
)


# Fixed, unique, pale colors.  This palette is intentionally longer than the
# Xerces reference partition so no cluster needs a repeated fill color.
CLUSTER_PALETTE = (
    "#ECCACA", "#ECCFCA", "#ECD4CA", "#ECDACA", "#ECDFCA",
    "#ECE4CA", "#ECE9CA", "#EBECCA", "#E6ECCA", "#E0ECCA",
    "#DBECCA", "#D6ECCA", "#D1ECCA", "#CCECCA", "#CAECCE",
    "#CAECD3", "#CAECD8", "#CAECDD", "#CAECE2", "#CAECE7",
    "#CAECEC", "#CAE7EC", "#CAE2EC", "#CADDEC", "#CAD8EC",
    "#CAD3EC", "#CACEEC", "#CCCAEC", "#D1CAEC", "#D6CAEC",
    "#DBCAEC", "#E0CAEC", "#E6CAEC", "#EBCAEC", "#ECCAE9",
    "#ECCAE4", "#ECCADF", "#ECCADA", "#ECCAD4", "#ECCACF",
)


@dataclass
class ClusterRecord:
    raw_id: str
    visual_id: str
    members: tuple[str, ...]
    class_count: int
    internal_edge_count: int = 0
    internal_raw_weight: float = 0.0
    isolated_class_count: int = 0
    aligned_reference_cluster: str = ""
    color: str = ""


@dataclass
class AggregateEdge:
    source: str
    target: str
    class_edge_count: int = 0
    type_weight: float = 0.0
    call_weight: float = 0.0
    raw_weight: float = 0.0


def _unique_palette() -> tuple[str, ...]:
    colors = tuple(dict.fromkeys(CLUSTER_PALETTE))
    if len(colors) < 40:
        raise ValueError("cluster palette must contain at least 40 unique colors")
    return colors


def _number(value: str, field: str, edge: str) -> float:
    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(f"{field} is not numeric for edge {edge}") from error
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field} must be a non-negative finite number for edge {edge}")
    return number


def _cluster_order(cluster_by_class: dict[str, str], prefix: str = "C") -> tuple[list[str], dict[str, str], dict[str, tuple[str, ...]]]:
    signatures_by_raw = cluster_signatures(cluster_by_class)
    ordered_raw = sorted(signatures_by_raw, key=lambda raw: signatures_by_raw[raw])
    raw_to_visual = {raw: f"{prefix}{index}" for index, raw in enumerate(ordered_raw, start=1)}
    return ordered_raw, raw_to_visual, signatures_by_raw


def _parse_positions(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Cannot read positioned DOT {path}: {error}") from error
    positions: dict[str, str] = {}
    for match in re.finditer(r"^[ \t]*(n\d+)[ \t]+\[(.*?)\];", text, flags=re.DOTALL | re.MULTILINE):
        position = re.search(r'\bpos="([^"]+)"', match.group(2))
        if position:
            positions[match.group(1)] = position.group(1)
    return positions


def _scale(value: float, low: float, high: float, out_low: float, out_high: float) -> float:
    if math.isclose(low, high):
        return (out_low + out_high) / 2
    return out_low + (out_high - out_low) * (value - low) / (high - low)


def _sqrt_scale(values: list[float], out_low: float, out_high: float) -> list[float]:
    transformed = [math.sqrt(max(0.0, value)) for value in values]
    if not transformed:
        return []
    return [_scale(value, min(transformed), max(transformed), out_low, out_high) for value in transformed]


def _log_scale(values: list[float], out_low: float, out_high: float) -> list[float]:
    transformed = [math.log1p(max(0.0, value)) for value in values]
    if not transformed:
        return []
    return [_scale(value, min(transformed), max(transformed), out_low, out_high) for value in transformed]


def _quote(value: object) -> str:
    text = str(value)
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _weight(value: float) -> str:
    return format(value, ".12g")


def aggregate(
    nodes_path: Path,
    edges_path: Path,
    partition_path: Path,
    reference_partition_path: Path | None = None,
) -> tuple[list[ClusterRecord], list[AggregateEdge], dict[str, int]]:
    # Cluster-level output does not display class labels, so Xerces simple-name
    # collisions must not reject an otherwise valid fully qualified input.
    nodes, _validated_edges, cluster_by_class = validate_and_load(nodes_path, edges_path, partition_path, "fully_qualified")
    node_names = {node.class_name for node in nodes}
    edge_rows = read_csv(edges_path, EDGE_COLUMNS, "edges")
    partition_rows = read_csv(partition_path, PARTITION_COLUMNS, "partition")
    cluster_by_class = validate_partition_rows(partition_rows, node_names, "partition")
    target_prefix = "T" if reference_partition_path is not None else "C"
    ordered_raw, raw_to_visual, signatures_by_raw = _cluster_order(cluster_by_class, target_prefix)
    endpoint_names = {endpoint for row in edge_rows for endpoint in (row["source"], row["target"])}
    records = [
        ClusterRecord(
            raw_id=raw,
            visual_id=raw_to_visual[raw],
            members=signatures_by_raw[raw],
            class_count=len(signatures_by_raw[raw]),
            isolated_class_count=sum(member not in endpoint_names for member in signatures_by_raw[raw]),
        )
        for raw in ordered_raw
    ]
    by_raw = {record.raw_id: record for record in records}
    aggregate_edges: dict[tuple[str, str], AggregateEdge] = {}
    for row in edge_rows:
        source, target = row["source"], row["target"]
        if source not in node_names or target not in node_names:
            unknown = source if source not in node_names else target
            raise ValueError(f"edge references class not present in nodes CSV: {unknown}")
        if source == target:
            raise ValueError(f"self-loop is not allowed: {source}")
        raw_weight = _number(row["raw_weight"], "raw_weight", f"{source} -- {target}")
        type_weight = _number(row["type_weight"], "type_weight", f"{source} -- {target}")
        call_weight = _number(row["call_weight"], "call_weight", f"{source} -- {target}")
        left, right = cluster_by_class[source], cluster_by_class[target]
        if left == right:
            record = by_raw[left]
            record.internal_edge_count += 1
            record.internal_raw_weight += raw_weight
            continue
        visual_left, visual_right = raw_to_visual[left], raw_to_visual[right]
        pair = tuple(sorted((visual_left, visual_right)))
        edge = aggregate_edges.setdefault(pair, AggregateEdge(pair[0], pair[1]))
        edge.class_edge_count += 1
        edge.type_weight += type_weight
        edge.call_weight += call_weight
        edge.raw_weight += raw_weight
    reference_by_class = None
    if reference_partition_path is not None:
        reference_rows = read_csv(reference_partition_path, PARTITION_COLUMNS, "reference partition")
        reference_by_class = validate_partition_rows(reference_rows, node_names, "reference partition")
        ref_ordered, ref_to_visual, _ = _cluster_order(reference_by_class, "C")
        matched_raw = maximum_overlap_matching(cluster_by_class, reference_by_class)
        target_ref = {raw: matched_raw.get(raw) for raw in ordered_raw}
        for record in records:
            ref_raw = target_ref[record.raw_id]
            record.aligned_reference_cluster = "" if ref_raw is None else ref_to_visual[ref_raw]
    colors = _unique_palette()
    reference_colors: dict[str, str] = {}
    if reference_by_class is None:
        for index, record in enumerate(records):
            record.color = colors[index]
    else:
        ref_ordered, ref_to_visual, _ = _cluster_order(reference_by_class, "C")
        for index, raw in enumerate(ref_ordered):
            reference_colors[raw] = colors[index]
        used = set(reference_colors.values())
        extras = [color for color in colors if color not in used]
        extra_index = 0
        matched_raw = maximum_overlap_matching(cluster_by_class, reference_by_class)
        for record in records:
            ref_raw = matched_raw.get(record.raw_id)
            if ref_raw is not None:
                record.color = reference_colors[ref_raw]
            else:
                record.color = extras[extra_index]
                extra_index += 1
    return records, sorted(aggregate_edges.values(), key=lambda edge: (edge.source, edge.target)), {
        "class_count": len(nodes),
        "raw_edge_count": len(edge_rows),
        "isolated_class_count": len(node_names - endpoint_names),
    }


def _write_audit(
    records: list[ClusterRecord], edges: list[AggregateEdge], nodes_path: Path | None, edges_path: Path | None
) -> None:
    if nodes_path is not None:
        nodes_path.parent.mkdir(parents=True, exist_ok=True)
        with nodes_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=("visual_cluster_id", "original_cluster_id", "class_count", "internal_edge_count", "internal_raw_weight", "isolated_class_count", "aligned_reference_cluster", "color"))
            writer.writeheader()
            for record in records:
                writer.writerow({"visual_cluster_id": record.visual_id, "original_cluster_id": record.raw_id, "class_count": record.class_count, "internal_edge_count": record.internal_edge_count, "internal_raw_weight": _weight(record.internal_raw_weight), "isolated_class_count": record.isolated_class_count, "aligned_reference_cluster": record.aligned_reference_cluster, "color": record.color})
    if edges_path is not None:
        edges_path.parent.mkdir(parents=True, exist_ok=True)
        with edges_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=("source_cluster", "target_cluster", "class_edge_count", "type_weight", "call_weight", "raw_weight"))
            writer.writeheader()
            for edge in edges:
                writer.writerow({"source_cluster": edge.source, "target_cluster": edge.target, "class_edge_count": edge.class_edge_count, "type_weight": _weight(edge.type_weight), "call_weight": _weight(edge.call_weight), "raw_weight": _weight(edge.raw_weight)})


def render_dot(
    records: list[ClusterRecord], edges: list[AggregateEdge], graph_name: str, positions_from: Path | None = None
) -> str:
    class_sizes = _sqrt_scale([record.class_count for record in records], 1.2, 2.8)
    edge_sizes = _log_scale([edge.raw_weight for edge in edges], 0.8, 5.0)
    positions = _parse_positions(positions_from) if positions_from is not None else {}
    if positions_from is not None and len(positions) < len(records):
        raise ValueError(f"positioned DOT has {len(positions)} node positions but {len(records)} are required")
    positions_by_visual: dict[str, str] = {}
    if positions_from is not None:
        for index, record in enumerate(records):
            if record.aligned_reference_cluster:
                reference_index = int(record.aligned_reference_cluster[1:]) - 1
                position_id = f"n{reference_index}"
            else:
                # Unmatched target clusters are deterministic but deliberately
                # offset from the corresponding reference slot, if available.
                position_id = f"n{index}"
            if position_id not in positions:
                raise ValueError(f"positioned DOT is missing node position: {position_id}")
            if record.aligned_reference_cluster:
                positions_by_visual[record.visual_id] = positions[position_id]
            else:
                base = positions[position_id]
                x, separator, y = base.partition(",")
                positions_by_visual[record.visual_id] = f"{float(x) + 1.5 + index * 0.1:g}{separator}{y}"
    lines = [
        f"graph {_quote(graph_name)} {{",
        "  graph [overlap=false, splines=true, outputorder=edgesfirst, bgcolor=\"white\"];",
        "  node [shape=box, style=\"rounded,filled\", fixedsize=true, fontname=\"Helvetica\", fontsize=10, margin=\"0.08,0.05\"];",
        "  edge [color=\"#B5B5B5\", fontname=\"Helvetica\"];",
        "",
    ]
    for record, size in zip(records, class_sizes):
        member_preview = list(record.members[:15])
        if len(record.members) > 15:
            member_preview.append(f"... and {len(record.members) - 15} more")
        alignment = ""
        if record.aligned_reference_cluster:
            alignment = f" | aligned to reference {record.aligned_reference_cluster}"
        tooltip = (
            f"cluster {record.visual_id}{alignment} | class_count={record.class_count} | "
            f"internal_edges={record.internal_edge_count} | internal_raw_weight={_weight(record.internal_raw_weight)} | "
            f"isolated_classes={record.isolated_class_count} | members: {'; '.join(member_preview)}"
        )
        attrs = [
            f"label={_quote(record.visual_id + '\n' + str(record.class_count) + ' classes')}",
            f"tooltip={_quote(tooltip)}",
            f"fillcolor={_quote(record.color)}",
            f"width={_weight(size)}",
            f"height={_weight(_scale(size, 1.2, 2.8, 0.55, 1.5))}",
            f"cluster_id={_quote(record.visual_id)}",
        ]
        if positions_from is not None:
            attrs.extend([f"pos={_quote(positions_by_visual[record.visual_id])}", "pin=true"])
        lines.append(f"  n{records.index(record)} [{', '.join(attrs)}];")
    lines.append("")
    for edge, width in zip(edges, edge_sizes):
        source = next(index for index, record in enumerate(records) if record.visual_id == edge.source)
        target = next(index for index, record in enumerate(records) if record.visual_id == edge.target)
        lines.append(f"  n{source} -- n{target} [penwidth={_weight(width)}, tooltip={_quote(f'class_edges={edge.class_edge_count} | raw_weight={_weight(edge.raw_weight)}')}];")
    lines.append("}")
    return "\n".join(lines) + "\n"


def export_cluster_dot(
    nodes: Path, edges: Path, partition: Path, output: Path, graph_name: str,
    reference_partition: Path | None = None, positions_from: Path | None = None,
    nodes_summary_output: Path | None = None, edges_summary_output: Path | None = None,
) -> dict[str, int]:
    records, aggregate_edges, summary = aggregate(nodes, edges, partition, reference_partition)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_dot(records, aggregate_edges, graph_name, positions_from), encoding="utf-8")
    _write_audit(records, aggregate_edges, nodes_summary_output, edges_summary_output)
    return {**summary, "cluster_nodes": len(records), "aggregate_edges": len(aggregate_edges), "internal_class_edges": sum(r.internal_edge_count for r in records), "cross_class_edges": sum(e.class_edge_count for e in aggregate_edges)}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", required=True, type=Path)
    parser.add_argument("--edges", required=True, type=Path)
    parser.add_argument("--partition", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--graph-name", default="G")
    parser.add_argument("--reference-partition", type=Path)
    parser.add_argument("--positions-from", type=Path)
    parser.add_argument("--nodes-summary-output", type=Path)
    parser.add_argument("--edges-summary-output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = export_cluster_dot(args.nodes, args.edges, args.partition, args.output, args.graph_name, args.reference_partition, args.positions_from, args.nodes_summary_output, args.edges_summary_output)
    except ValueError as error:
        print(f"Cluster DOT export failed: {error}", file=sys.stderr)
        return 2
    print("Cluster DOT export completed")
    for key in ("class_count", "raw_edge_count", "cluster_nodes", "aggregate_edges", "internal_class_edges", "cross_class_edges", "isolated_class_count"):
        print(f"{key}: {summary[key]}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
