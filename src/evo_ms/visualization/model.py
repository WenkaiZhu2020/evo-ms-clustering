"""Typed contracts for the common visualisation infrastructure."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class OutputPaths:
    data: Path
    dot: Path
    svg: Path
    pdf: Path

    def as_dict(self) -> dict[str, Path]:
        return {"data": self.data, "dot": self.dot, "svg": self.svg, "pdf": self.pdf}


@dataclass(frozen=True)
class LayoutProfile:
    name: str
    engine: str
    fixed_coordinates: bool
    seed: int
    page_profile: str


@dataclass(frozen=True)
class FigureSpecification:
    figure_id: str
    stage: str
    title: str
    destination: str
    inputs: tuple[str, ...]
    layout_profile: str
    enabled: bool
    formats: tuple[str, ...]
    generator: str
    representative_seed: int | None = None
    representative_solution: str | None = None
    layout_coordinate_path: str | None = None
    edge_category_data_path: str | None = None


@dataclass(frozen=True)
class VisualizationConfig:
    repository_root: Path
    schema_version: int
    allowed_stages: tuple[str, ...]
    allowed_output_formats: tuple[str, ...]
    output: OutputPaths
    figures: Mapping[str, FigureSpecification]
    layout_profiles: Mapping[str, LayoutProfile]
    style: Mapping[str, Any]
    figures_config_path: Path
    style_config_path: Path


@dataclass(frozen=True)
class GraphvizRenderRequest:
    dot_path: Path
    output_path: Path
    output_format: str
    engine: str
    fixed_coordinates: bool = False

    def __post_init__(self) -> None:
        if self.engine not in {"dot", "neato", "sfdp"}:
            raise ValueError(f"unsupported Graphviz engine: {self.engine}")
        if self.output_format not in {"svg", "pdf"}:
            raise ValueError(f"unsupported Graphviz output format: {self.output_format}")
        if self.fixed_coordinates and self.engine != "neato":
            raise ValueError("fixed-coordinate rendering requires the neato engine")


@dataclass(frozen=True)
class GraphvizRenderResult:
    output_path: Path
    engine: str
    version: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class ProvenanceRecord:
    figure_id: str
    stage: str
    generator: str
    git_commit: str
    git_dirty: bool
    input_files: tuple[str, ...]
    input_sha256: tuple[tuple[str, str], ...]
    config_files: tuple[str, ...]
    config_sha256: tuple[tuple[str, str], ...]
    dot_sha256: str
    graphviz_engine: str
    graphviz_version: str
    render_command: tuple[tuple[str, ...], ...]
    generated_outputs: tuple[str, ...]
    generated_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "figure_id": self.figure_id,
            "stage": self.stage,
            "generator": self.generator,
            "git_commit": self.git_commit,
            "git_dirty": self.git_dirty,
            "input_files": list(self.input_files),
            "input_sha256": dict(self.input_sha256),
            "config_files": list(self.config_files),
            "config_sha256": dict(self.config_sha256),
            "dot_sha256": self.dot_sha256,
            "graphviz_engine": self.graphviz_engine,
            "graphviz_version": self.graphviz_version,
            "render_command": [list(command) for command in self.render_command],
            "generated_outputs": list(self.generated_outputs),
            "generated_at": self.generated_at,
        }
