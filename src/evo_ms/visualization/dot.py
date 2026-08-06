"""Small deterministic primitives for Graphviz DOT source generation."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Mapping
from pathlib import Path
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


def render_undirected_graph(
    graph_name: str,
    nodes: Mapping[str, Mapping[str, Any]],
    edges: Iterable[tuple[str, str, Mapping[str, Any]]],
    graph_attributes: Mapping[str, Any] | None = None,
) -> str:
    """Render a deterministic undirected graph with validated edge identity."""

    node_ids = set(nodes)
    canonical_edges: list[tuple[str, str, Mapping[str, Any]]] = []
    seen: set[tuple[str, str]] = set()
    for source, target, attributes in edges:
        if source not in node_ids or target not in node_ids:
            missing = source if source not in node_ids else target
            raise ValueError(f"edge references unknown node: {missing}")
        if source == target:
            raise ValueError(f"self-loop is not allowed: {source}")
        left, right = sorted((source, target))
        if (left, right) in seen:
            raise ValueError(f"duplicate undirected edge is not allowed: {left} -- {right}")
        seen.add((left, right))
        canonical_edges.append((left, right, attributes))

    lines = [f"graph {dot_quote(graph_name)} {{"]
    if graph_attributes:
        lines.append(f"  graph {stable_attributes(graph_attributes)};")
    for node_id in sorted(nodes):
        lines.append(f"  {dot_quote(node_id)} {stable_attributes(nodes[node_id])};")
    if nodes and canonical_edges:
        lines.append("")
    for source, target, attributes in sorted(canonical_edges, key=lambda row: (row[0], row[1])):
        lines.append(f"  {dot_quote(source)} -- {dot_quote(target)} {stable_attributes(attributes)};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def ensure_final_newline(text: str) -> str:
    return text.rstrip("\n") + "\n"


def write_dot(path: str | Path, text: str) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(ensure_final_newline(text), encoding="utf-8", newline="\n")
    return output


def content_sha256(text: str) -> str:
    return hashlib.sha256(ensure_final_newline(text).encode("utf-8")).hexdigest()
