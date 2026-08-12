"""Stable public interfaces for dissertation figure infrastructure."""

from .config import load_visualization_config
from .dot import (
    content_sha256,
    dot_quote,
    render_directed_graph,
    render_undirected_graph,
    stable_attributes,
    write_dot,
)
from .layout import GraphvizError, find_graphviz, graphviz_version, render_graphviz
from .model import GraphvizRenderRequest, ProvenanceRecord, VisualizationConfig
from .provenance import build_provenance, provenance_json, sha256_file, write_provenance

__all__ = (
    "GraphvizError",
    "GraphvizRenderRequest",
    "ProvenanceRecord",
    "VisualizationConfig",
    "build_provenance",
    "content_sha256",
    "dot_quote",
    "find_graphviz",
    "graphviz_version",
    "load_visualization_config",
    "provenance_json",
    "render_graphviz",
    "render_directed_graph",
    "render_undirected_graph",
    "sha256_file",
    "stable_attributes",
    "write_dot",
    "write_provenance",
)
