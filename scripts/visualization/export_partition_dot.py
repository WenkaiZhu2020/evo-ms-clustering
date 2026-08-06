#!/usr/bin/env python3
"""Export a class partition and its raw graph as a deterministic Graphviz DOT file."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


NODE_COLUMNS = ("class_id", "class_name", "package", "class_file_path")
EDGE_COLUMNS = ("source", "target", "type_weight", "call_weight", "raw_weight")
PARTITION_COLUMNS = ("class_id", "class_name", "cluster_id")
LABEL_MODES = ("simple_class", "short_package_class", "fully_qualified")
PALETTE = (
    "#DDEBF7",
    "#E2F0D9",
    "#FFF2CC",
    "#FCE4D6",
    "#E4DFEC",
    "#C9DAF8",
    "#D9EAD3",
    "#F4CCCC",
    "#D0E0E3",
    "#EADCF8",
    "#FCE5CD",
    "#D9D2E9",
)
EXTRA_PALETTE = (
    "#CFE2F3",
    "#D9EAD3",
    "#F9CB9C",
    "#D9D2E9",
    "#F4CCCC",
    "#D0E0E3",
)


@dataclass(frozen=True)
class Node:
    class_id: str
    class_name: str
    package: str


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    raw_weight: float


def read_csv(path: Path, required_columns: Iterable[str], kind: str) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError(f"{kind} CSV is empty: {path}")
            missing = [column for column in required_columns if column not in reader.fieldnames]
            if missing:
                raise ValueError(f"{kind} CSV missing required columns {missing}: {path}")
            return list(reader)
    except OSError as error:
        raise ValueError(f"Cannot read {kind} CSV {path}: {error}") from error


def display_label(class_name: str, package: str, mode: str) -> str:
    if mode == "fully_qualified":
        return class_name
    simple_name = class_name.rsplit(".", 1)[-1]
    if mode == "simple_class":
        return simple_name
    if mode == "short_package_class":
        package_tail = package.rsplit(".", 1)[-1] if package else ""
        return f"{package_tail}.{simple_name}" if package_tail else simple_name
    raise ValueError(f"Unsupported label mode: {mode}")


def dot_quote(value: object) -> str:
    text = str(value)
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def format_weight(value: float) -> str:
    return format(value, ".12g")


def edge_widths(edges: list[Edge]) -> list[float]:
    weights = [edge.raw_weight for edge in edges]
    if not weights:
        return []
    low, high = min(weights), max(weights)
    if math.isclose(low, high):
        return [2.5] * len(edges)
    return [1.0 + 3.0 * (weight - low) / (high - low) for weight in weights]


def cluster_signatures(cluster_by_class: dict[str, str]) -> dict[str, tuple[str, ...]]:
    members_by_raw_cluster: dict[str, list[str]] = {}
    for class_name, raw_cluster_id in cluster_by_class.items():
        members_by_raw_cluster.setdefault(raw_cluster_id, []).append(class_name)
    return {raw_cluster_id: tuple(sorted(members)) for raw_cluster_id, members in members_by_raw_cluster.items()}


def canonical_clusters(cluster_by_class: dict[str, str], prefix: str = "C") -> dict[str, str]:
    """Return stable labels based only on each cluster's class membership."""
    signatures_by_raw_cluster = cluster_signatures(cluster_by_class)
    canonical_by_signature = {
        signature: f"{prefix}{index}"
        for index, signature in enumerate(sorted(signatures_by_raw_cluster.values()), start=1)
    }
    return {
        class_name: canonical_by_signature[signatures_by_raw_cluster[raw_cluster_id]]
        for class_name, raw_cluster_id in cluster_by_class.items()
    }


def validate_partition_rows(
    partition_rows: list[dict[str, str]], node_names: set[str], kind: str
) -> dict[str, str]:
    partition_names = [row["class_name"] for row in partition_rows]
    if len(set(partition_names)) != len(partition_names):
        raise ValueError(f"{kind} CSV has duplicate class assignments")
    partition_set = set(partition_names)
    missing = sorted(node_names - partition_set)
    extra = sorted(partition_set - node_names)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing nodes: {', '.join(missing)}")
        if extra:
            details.append(f"unknown nodes: {', '.join(extra)}")
        raise ValueError(f"{kind} class scope does not match nodes CSV (" + "; ".join(details) + ")")
    return {row["class_name"]: row["cluster_id"] for row in partition_rows}


def hungarian_min_cost(cost: list[list[int]]) -> list[int]:
    """Return a deterministic minimum-cost assignment for a square matrix."""
    size = len(cost)
    potentials_u = [0] * (size + 1)
    potentials_v = [0] * (size + 1)
    matching = [0] * (size + 1)
    predecessor = [0] * (size + 1)
    for row in range(1, size + 1):
        matching[0] = row
        column = 0
        minimum = [math.inf] * (size + 1)
        used = [False] * (size + 1)
        while True:
            used[column] = True
            current_row = matching[column]
            delta = math.inf
            next_column = 0
            for candidate in range(1, size + 1):
                if used[candidate]:
                    continue
                reduced_cost = cost[current_row - 1][candidate - 1] - potentials_u[current_row] - potentials_v[candidate]
                if reduced_cost < minimum[candidate]:
                    minimum[candidate] = reduced_cost
                    predecessor[candidate] = column
                if minimum[candidate] < delta:
                    delta = minimum[candidate]
                    next_column = candidate
            for candidate in range(size + 1):
                if used[candidate]:
                    potentials_u[matching[candidate]] += delta
                    potentials_v[candidate] -= delta
                else:
                    minimum[candidate] -= delta
            column = next_column
            if matching[column] == 0:
                break
        while True:
            previous_column = predecessor[column]
            matching[column] = matching[previous_column]
            column = previous_column
            if column == 0:
                break
    assignment = [-1] * size
    for column in range(1, size + 1):
        assignment[matching[column] - 1] = column - 1
    return assignment


def maximum_overlap_matching(
    target_by_class: dict[str, str], reference_by_class: dict[str, str]
) -> dict[str, str | None]:
    """Match target raw clusters to reference raw clusters by maximum member overlap."""
    reference_signatures = cluster_signatures(reference_by_class)
    target_signatures = cluster_signatures(target_by_class)
    reference_raw = sorted(reference_signatures, key=lambda raw: reference_signatures[raw])
    target_raw = sorted(target_signatures, key=lambda raw: target_signatures[raw])
    size = max(len(reference_raw), len(target_raw))
    overlap = [[0] * size for _ in range(size)]
    for reference_index, reference_cluster in enumerate(reference_raw):
        reference_members = set(reference_signatures[reference_cluster])
        for target_index, target_cluster in enumerate(target_raw):
            overlap[reference_index][target_index] = len(reference_members & set(target_signatures[target_cluster]))
    maximum = max((value for row in overlap for value in row), default=0)
    assignment = hungarian_min_cost([[maximum - value for value in row] for row in overlap])
    matched_reference_by_target_raw: dict[str, str | None] = {raw: None for raw in target_raw}
    for reference_index, target_index in enumerate(assignment):
        if reference_index < len(reference_raw) and target_index < len(target_raw) and overlap[reference_index][target_index] > 0:
            matched_reference_by_target_raw[target_raw[target_index]] = reference_raw[reference_index]
    return matched_reference_by_target_raw


def reference_alignment(
    target_by_class: dict[str, str], reference_by_class: dict[str, str]
) -> tuple[dict[str, str], dict[str, str | None]]:
    """Assign target cluster colors by deterministic maximum overlap with reference clusters."""
    reference_display = canonical_clusters(reference_by_class, "C")
    target_display = canonical_clusters(target_by_class, "T")
    target_signatures = cluster_signatures(target_by_class)
    reference_signatures = cluster_signatures(reference_by_class)
    reference_raw = sorted(reference_signatures, key=lambda raw: reference_signatures[raw])
    target_raw = sorted(target_signatures, key=lambda raw: target_signatures[raw])
    matched_raw_by_target_raw = maximum_overlap_matching(target_by_class, reference_by_class)
    reference_label_by_raw = {
        raw_cluster: reference_display[next(class_name for class_name, cluster in reference_by_class.items() if cluster == raw_cluster)]
        for raw_cluster in reference_raw
    }
    aligned_reference_by_target_raw = {
        target_raw_cluster: None if reference_raw_cluster is None else reference_label_by_raw[reference_raw_cluster]
        for target_raw_cluster, reference_raw_cluster in matched_raw_by_target_raw.items()
    }
    reference_colors = {
        f"C{index}": PALETTE[(index - 1) % len(PALETTE)]
        for index in range(1, len(reference_raw) + 1)
    }
    used_reference_colors = set(reference_colors.values())
    available_extra_colors = [color for color in EXTRA_PALETTE if color not in used_reference_colors]
    if not available_extra_colors:
        available_extra_colors = ["#B7B7B7"]
    colors_by_target_raw: dict[str, str] = {}
    extra_index = 0
    for raw_cluster in target_raw:
        aligned_reference = aligned_reference_by_target_raw[raw_cluster]
        if aligned_reference is None:
            colors_by_target_raw[raw_cluster] = available_extra_colors[extra_index % len(available_extra_colors)]
            extra_index += 1
        else:
            colors_by_target_raw[raw_cluster] = reference_colors[aligned_reference]
    return (
        {class_name: colors_by_target_raw[raw_cluster] for class_name, raw_cluster in target_by_class.items()},
        {class_name: aligned_reference_by_target_raw[raw_cluster] for class_name, raw_cluster in target_by_class.items()},
    )


def changed_classes(target_by_class: dict[str, str], reference_by_class: dict[str, str]) -> set[str]:
    """Return classes outside the same alignment used for reference colors."""
    matched_raw_by_target = maximum_overlap_matching(target_by_class, reference_by_class)
    return {
        class_name
        for class_name, target_raw_cluster in target_by_class.items()
        if matched_raw_by_target[target_raw_cluster] != reference_by_class[class_name]
    }


def positions_from_dot(path: Path, class_names: set[str]) -> dict[str, str]:
    """Read Graphviz n0/n1... positions from a positioned DOT file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Cannot read positioned DOT {path}: {error}") from error
    positions: dict[str, str] = {}
    for match in re.finditer(r"^[ \t]*(n\d+)[ \t]+\[(.*?)\];", text, flags=re.DOTALL | re.MULTILINE):
        position = re.search(r'\bpos="([^"]+)"', match.group(2))
        if position is not None:
            positions[match.group(1)] = position.group(1)
    expected_ids = {f"n{index}" for index in range(len(class_names))}
    missing = sorted(expected_ids - set(positions))
    if missing:
        raise ValueError(f"positioned DOT is missing node positions: {', '.join(missing)}")
    return positions


def validate_and_load(
    nodes_path: Path, edges_path: Path, partition_path: Path, label_mode: str
) -> tuple[list[Node], list[Edge], dict[str, str]]:
    node_rows = read_csv(nodes_path, NODE_COLUMNS, "nodes")
    edge_rows = read_csv(edges_path, EDGE_COLUMNS, "edges")
    partition_rows = read_csv(partition_path, PARTITION_COLUMNS, "partition")

    nodes = sorted(
        (Node(row["class_id"], row["class_name"], row["package"]) for row in node_rows),
        key=lambda node: (node.class_name, node.class_id, node.package),
    )
    class_ids = [node.class_id for node in nodes]
    class_names = [node.class_name for node in nodes]
    if len(set(class_ids)) != len(class_ids):
        raise ValueError("nodes CSV has duplicate class_id values")
    if len(set(class_names)) != len(class_names):
        raise ValueError("nodes CSV has duplicate class_name values")
    if any(not name for name in class_names):
        raise ValueError("nodes CSV has an empty class_name")

    node_set = set(class_names)
    cluster_by_class = validate_partition_rows(partition_rows, node_set, "partition")
    labels = [display_label(node.class_name, node.package, label_mode) for node in nodes]
    if len(set(labels)) != len(labels):
        duplicates = sorted(label for label in set(labels) if labels.count(label) > 1)
        raise ValueError(f"label mode {label_mode} produces duplicate display labels: {', '.join(duplicates)}")

    edges: list[Edge] = []
    seen_pairs: set[frozenset[str]] = set()
    for row in edge_rows:
        source, target = row["source"], row["target"]
        if source not in node_set or target not in node_set:
            unknown = source if source not in node_set else target
            raise ValueError(f"edge references class not present in nodes CSV: {unknown}")
        if source == target:
            raise ValueError(f"self-loop is not allowed: {source}")
        pair = frozenset((source, target))
        if pair in seen_pairs:
            raise ValueError(f"duplicate undirected edge is not allowed: {source} -- {target}")
        seen_pairs.add(pair)
        try:
            raw_weight = float(row["raw_weight"])
        except ValueError as error:
            raise ValueError(f"raw_weight is not numeric for edge {source} -- {target}") from error
        if not math.isfinite(raw_weight) or raw_weight < 0:
            raise ValueError(f"raw_weight must be a non-negative finite number for edge {source} -- {target}")
        left, right = sorted((source, target))
        edges.append(Edge(left, right, raw_weight))
    edges.sort(key=lambda edge: (edge.source, edge.target, edge.raw_weight))
    return nodes, edges, cluster_by_class


def render_dot(
    nodes: list[Node], edges: list[Edge], cluster_by_class: dict[str, str], label_mode: str, graph_name: str,
    reference_by_class: dict[str, str] | None = None, highlight_reference_by_class: dict[str, str] | None = None,
    positions_by_id: dict[str, str] | None = None, changed_class_names: set[str] | None = None,
) -> str:
    if reference_by_class is None:
        canonical_by_class = canonical_clusters(cluster_by_class)
        cluster_ids = sorted(set(canonical_by_class.values()), key=lambda cluster_id: int(cluster_id[1:]))
        colors_by_class = {class_name: PALETTE[(int(cluster_id[1:]) - 1) % len(PALETTE)] for class_name, cluster_id in canonical_by_class.items()}
        alignment_by_class: dict[str, str | None] = {}
    else:
        canonical_by_class = canonical_clusters(cluster_by_class, "T")
        colors_by_class, alignment_by_class = reference_alignment(cluster_by_class, reference_by_class)
    ids = {node.class_name: f"n{index}" for index, node in enumerate(nodes)}
    edge_endpoints = {endpoint for edge in edges for endpoint in (edge.source, edge.target)}
    lines = [
        f"graph {dot_quote(graph_name)} {{",
        "  graph [overlap=false, splines=true, outputorder=edgesfirst, bgcolor=\"white\"];",
        "  node [shape=box, style=\"rounded,filled\", fontname=\"Helvetica\", fontsize=10, margin=\"0.08,0.05\"];",
        "  edge [color=\"#8A8A8A\", fontname=\"Helvetica\"];",
        "",
    ]
    for node in nodes:
        cluster_id = canonical_by_class[node.class_name]
        label = display_label(node.class_name, node.package, label_mode)
        if reference_by_class is None:
            tooltip = f"{node.class_name} | cluster {cluster_id}"
        elif alignment_by_class[node.class_name] is None:
            tooltip = f"{node.class_name} | target cluster {cluster_id} | unmatched"
        else:
            tooltip = f"{node.class_name} | target cluster {cluster_id} | aligned to reference {alignment_by_class[node.class_name]}"
        if highlight_reference_by_class is not None:
            change_status = "changed from reference" if node.class_name in changed_class_names else "unchanged from reference"
            tooltip = f"{tooltip} | {change_status}"
        node_attributes = ""
        if changed_class_names is not None and node.class_name in changed_class_names:
            node_attributes += ', color="#C00000", penwidth=3.0'
        if positions_by_id is not None:
            node_attributes += f", pos={dot_quote(positions_by_id[ids[node.class_name]])}, pin=true"
        lines.append(
            f"  {ids[node.class_name]} [label={dot_quote(label)}, tooltip={dot_quote(tooltip)}, "
            f"fillcolor={dot_quote(colors_by_class[node.class_name])}, cluster_id={dot_quote(cluster_id)}{node_attributes}];"
        )
    lines.append("")
    for edge, width in zip(edges, edge_widths(edges)):
        lines.append(
            f"  {ids[edge.source]} -- {ids[edge.target]} [penwidth={format_weight(width)}, "
            f"tooltip={dot_quote('raw_weight=' + format_weight(edge.raw_weight))}];"
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def export_dot(
    nodes_path: Path, edges_path: Path, partition_path: Path, output_path: Path, label_mode: str, graph_name: str,
    reference_partition_path: Path | None = None, highlight_changes_from_path: Path | None = None,
    positions_from_path: Path | None = None,
) -> dict[str, int]:
    nodes, edges, clusters = validate_and_load(nodes_path, edges_path, partition_path, label_mode)
    reference_clusters = None
    if reference_partition_path is not None:
        reference_rows = read_csv(reference_partition_path, PARTITION_COLUMNS, "reference partition")
        reference_clusters = validate_partition_rows(reference_rows, {node.class_name for node in nodes}, "reference partition")
    highlight_clusters = None
    if highlight_changes_from_path is not None:
        highlight_rows = read_csv(highlight_changes_from_path, PARTITION_COLUMNS, "highlight comparison partition")
        highlight_clusters = validate_partition_rows(highlight_rows, {node.class_name for node in nodes}, "highlight comparison partition")
    changed_class_names = set() if highlight_clusters is None else changed_classes(clusters, highlight_clusters)
    positions = None if positions_from_path is None else positions_from_dot(positions_from_path, {node.class_name for node in nodes})
    dot = render_dot(nodes, edges, clusters, label_mode, graph_name, reference_clusters, highlight_clusters, positions, changed_class_names)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dot, encoding="utf-8")
    endpoints = {endpoint for edge in edges for endpoint in (edge.source, edge.target)}
    return {"nodes": len(nodes), "edges": len(edges), "clusters": len(set(clusters.values())), "isolated_nodes": len(nodes) - len(endpoints)}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", required=True, type=Path)
    parser.add_argument("--edges", required=True, type=Path)
    parser.add_argument("--partition", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reference-partition", type=Path)
    parser.add_argument("--highlight-changes-from", type=Path)
    parser.add_argument("--positions-from", type=Path)
    parser.add_argument("--label-mode", choices=LABEL_MODES, default="simple_class")
    parser.add_argument("--graph-name", default="G")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = export_dot(args.nodes, args.edges, args.partition, args.output, args.label_mode, args.graph_name, args.reference_partition, args.highlight_changes_from, args.positions_from)
    except ValueError as error:
        print(f"DOT export failed: {error}", file=sys.stderr)
        return 2
    print("DOT export completed")
    for key in ("nodes", "edges", "clusters", "isolated_nodes"):
        print(f"{key}: {summary[key]}")
    print(f"label_mode: {args.label_mode}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
