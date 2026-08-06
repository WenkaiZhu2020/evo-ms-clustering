"""Small deterministic primitives for Graphviz DOT source generation."""

from __future__ import annotations

import hashlib
import math
import os
from collections.abc import Iterable, Mapping
from pathlib import Path
import tempfile
from typing import Any


def dot_quote(value: object) -> str:
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
    return f'"{escaped}"'


def format_number(value: int | float) -> str:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("DOT numeric values must be finite")
    if number == 0:
        return "0"
    return format(number, ".12g")


def _attribute_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return format_number(value)
    return dot_quote(value)


def stable_attributes(attributes: Mapping[str, Any]) -> str:
    return "[" + ", ".join(f"{key}={_attribute_value(attributes[key])}" for key in sorted(attributes)) + "]"


def _render_graph(
    graph_name: str,
    nodes: Mapping[str, Mapping[str, Any]],
    edges: Iterable[tuple[str, str, Mapping[str, Any]]],
    graph_attributes: Mapping[str, Any] | None = None,
    *,
    directed: bool,
) -> str:
    node_ids = set(nodes)
    canonical_edges: list[tuple[str, str, Mapping[str, Any]]] = []
    seen: set[tuple[str, str]] = set()
    for source, target, attributes in edges:
        if source not in node_ids or target not in node_ids:
            missing = source if source not in node_ids else target
            raise ValueError(f"edge references unknown node: {missing}")
        if source == target:
            raise ValueError(f"self-loop is not allowed: {source}")
        left, right = (source, target) if directed else tuple(sorted((source, target)))
        if (left, right) in seen:
            kind = "directed" if directed else "undirected"
            raise ValueError(f"duplicate {kind} edge is not allowed: {left} -- {right}")
        seen.add((left, right))
        canonical_edges.append((left, right, attributes))

    graph_keyword = "digraph" if directed else "graph"
    edge_operator = "->" if directed else "--"
    lines = [f"{graph_keyword} {dot_quote(graph_name)} {{"]
    if graph_attributes:
        lines.append(f"  graph {stable_attributes(graph_attributes)};")
    for node_id in sorted(nodes):
        lines.append(f"  {dot_quote(node_id)} {stable_attributes(nodes[node_id])};")
    if nodes and canonical_edges:
        lines.append("")
    for source, target, attributes in sorted(canonical_edges, key=lambda row: (row[0], row[1])):
        lines.append(
            f"  {dot_quote(source)} {edge_operator} {dot_quote(target)} {stable_attributes(attributes)};"
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_undirected_graph(
    graph_name: str,
    nodes: Mapping[str, Mapping[str, Any]],
    edges: Iterable[tuple[str, str, Mapping[str, Any]]],
    graph_attributes: Mapping[str, Any] | None = None,
) -> str:
    """Render a deterministic undirected graph with validated edge identity."""

    return _render_graph(graph_name, nodes, edges, graph_attributes, directed=False)


def render_directed_graph(
    graph_name: str,
    nodes: Mapping[str, Mapping[str, Any]],
    edges: Iterable[tuple[str, str, Mapping[str, Any]]],
    graph_attributes: Mapping[str, Any] | None = None,
) -> str:
    """Render a deterministic directed graph suitable for process diagrams."""

    return _render_graph(graph_name, nodes, edges, graph_attributes, directed=True)


def ensure_final_newline(text: str) -> str:
    return text.rstrip("\n") + "\n"


def write_dot(path: str | Path, text: str) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(ensure_final_newline(text))
        os.replace(temporary_name, output)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise
    return output


def content_sha256(text: str) -> str:
    return hashlib.sha256(ensure_final_newline(text).encode("utf-8")).hexdigest()
