"""Repository-root-safe loading and validation for visualisation configuration."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from evo_ms.repository_layout import REPOSITORY_ROOT
from evo_ms.utils.config_loader import load_yaml

from .model import FigureSpecification, LayoutProfile, OutputPaths, VisualizationConfig


PROTECTED_OUTPUT_ROOTS = (
    Path("data/semantic_graphs"),
    Path("results/stage1"),
    Path("results/stage2"),
    Path("results/stage3"),
)
REQUIRED_STYLE_KEYS = (
    "subjects",
    "fonts",
    "node",
    "edge",
    "changed_node",
    "edge_categories",
    "transition_flow",
    "graph",
    "page_profiles",
    "graphviz",
    "layout_profiles",
    "cluster_palette",
)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def _string_list(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{label} must be a non-empty list of strings")
    if len(set(value)) != len(value):
        raise ValueError(f"{label} contains duplicate values")
    return tuple(value)


def _path_within(root: Path, value: str | Path, label: str) -> tuple[Path, Path]:
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} must remain inside the repository: {value}") from error
    return resolved, relative


def _output_path(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty path string")
    resolved, relative = _path_within(root, value, label)
    for protected in PROTECTED_OUTPUT_ROOTS:
        if relative == protected or protected in relative.parents:
            raise ValueError(f"{label} cannot write into protected formal location: {relative}")
    return resolved


def _config_path(root: Path, value: str | Path | None, default: str) -> Path:
    path, _relative = _path_within(root, value or default, "configuration path")
    if not path.is_file():
        raise ValueError(f"configuration file does not exist: {path}")
    return path


def _load_document(path: Path, label: str) -> Mapping[str, Any]:
    try:
        document = load_yaml(path)
    except (OSError, ValueError) as error:
        raise ValueError(f"could not load {label} configuration {path}: {error}") from error
    return _mapping(document, f"{label} configuration")


def _layout_profiles(style: Mapping[str, Any]) -> Mapping[str, LayoutProfile]:
    page_profiles = _mapping(style["page_profiles"], "style.page_profiles")
    raw_profiles = _mapping(style["layout_profiles"], "style.layout_profiles")
    profiles: dict[str, LayoutProfile] = {}
    for name in sorted(raw_profiles):
        raw = _mapping(raw_profiles[name], f"layout profile {name}")
        missing = [key for key in ("engine", "fixed_coordinates", "seed", "page_profile") if key not in raw]
        if missing:
            raise ValueError(f"layout profile {name} is missing keys: {', '.join(missing)}")
        engine = raw["engine"]
        fixed = raw["fixed_coordinates"]
        seed = raw["seed"]
        page_profile = raw["page_profile"]
        if engine not in {"dot", "neato", "sfdp"}:
            raise ValueError(f"layout profile {name} has unsupported engine: {engine}")
        if not isinstance(fixed, bool):
            raise ValueError(f"layout profile {name}.fixed_coordinates must be boolean")
        if fixed and engine != "neato":
            raise ValueError(f"layout profile {name} requires neato for fixed coordinates")
        if not isinstance(seed, int):
            raise ValueError(f"layout profile {name}.seed must be an integer")
        if page_profile not in page_profiles:
            raise ValueError(f"layout profile {name} references unknown page profile: {page_profile}")
        profiles[name] = LayoutProfile(name, engine, fixed, seed, page_profile)
    if not profiles:
        raise ValueError("style.layout_profiles cannot be empty")
    return MappingProxyType(profiles)


def _figures(
    raw_figures: Mapping[str, Any],
    allowed_stages: tuple[str, ...],
    profiles: Mapping[str, LayoutProfile],
    page_profiles: Mapping[str, Any],
) -> Mapping[str, FigureSpecification]:
    figures: dict[str, FigureSpecification] = {}
    required = ("stage", "title", "destination", "inputs", "layout_profile", "enabled")
    for figure_id in sorted(raw_figures):
        if not isinstance(figure_id, str) or not figure_id:
            raise ValueError("figure IDs must be non-empty strings")
        raw = _mapping(raw_figures[figure_id], f"figure {figure_id}")
        missing = [key for key in required if key not in raw]
        if missing:
            raise ValueError(f"figure {figure_id} is missing keys: {', '.join(missing)}")
        if raw["stage"] not in allowed_stages:
            raise ValueError(f"figure {figure_id} has unsupported stage: {raw['stage']}")
        if raw["destination"] not in page_profiles:
            raise ValueError(f"figure {figure_id} has unknown destination: {raw['destination']}")
        if raw["layout_profile"] not in profiles:
            raise ValueError(f"figure {figure_id} has unknown layout profile: {raw['layout_profile']}")
        if not isinstance(raw["title"], str) or not raw["title"]:
            raise ValueError(f"figure {figure_id}.title must be a non-empty string")
        if not isinstance(raw["inputs"], list) or not all(isinstance(item, str) for item in raw["inputs"]):
            raise ValueError(f"figure {figure_id}.inputs must be a list of paths")
        if not isinstance(raw["enabled"], bool):
            raise ValueError(f"figure {figure_id}.enabled must be boolean")
        figures[figure_id] = FigureSpecification(
            figure_id=figure_id,
            stage=raw["stage"],
            title=raw["title"],
            destination=raw["destination"],
            inputs=tuple(sorted(raw["inputs"])),
            layout_profile=raw["layout_profile"],
            enabled=raw["enabled"],
        )
    return MappingProxyType(figures)


def load_visualization_config(
    repository_root: str | Path | None = None,
    figures_path: str | Path | None = None,
    style_path: str | Path | None = None,
) -> VisualizationConfig:
    """Load both visualisation configs independently of the process CWD."""

    root = Path(repository_root or REPOSITORY_ROOT).resolve()
    figures_file = _config_path(root, figures_path, "configs/visualization/figures.yml")
    style_file = _config_path(root, style_path, "configs/visualization/style.yml")
    catalogue = _load_document(figures_file, "figure catalogue")
    style = _load_document(style_file, "style")

    if catalogue.get("schema_version") != 1:
        raise ValueError("figure catalogue schema_version must be 1")
    if style.get("schema_version") != 1:
        raise ValueError("style schema_version must be 1")
    missing_style = [key for key in REQUIRED_STYLE_KEYS if key not in style]
    if missing_style:
        raise ValueError(f"style configuration is missing keys: {', '.join(missing_style)}")

    allowed_stages = _string_list(catalogue.get("allowed_stages"), "allowed_stages")
    formats = _string_list(catalogue.get("allowed_output_formats"), "allowed_output_formats")
    unsupported_formats = sorted(set(formats) - {"dot", "svg", "pdf"})
    if unsupported_formats:
        raise ValueError(f"unsupported output formats: {', '.join(unsupported_formats)}")

    output = _mapping(catalogue.get("output"), "output")
    missing_output = [key for key in ("data", "dot", "svg", "pdf") if key not in output]
    if missing_output:
        raise ValueError(f"output configuration is missing keys: {', '.join(missing_output)}")
    output_paths = OutputPaths(
        data=_output_path(root, output["data"], "output.data"),
        dot=_output_path(root, output["dot"], "output.dot"),
        svg=_output_path(root, output["svg"], "output.svg"),
        pdf=_output_path(root, output["pdf"], "output.pdf"),
    )

    subjects = _mapping(style["subjects"], "style.subjects")
    expected_subjects = {"jpetstore": "JPetStore", "daytrader": "DayTrader", "xerces-j": "Xerces-J"}
    if dict(subjects) != expected_subjects:
        raise ValueError("style.subjects must define the canonical dissertation display names")
    graphviz = _mapping(style["graphviz"], "style.graphviz")
    if graphviz.get("initial_layout_seed") != 42:
        raise ValueError("style.graphviz.initial_layout_seed must be 42")
    _mapping(graphviz.get("default_engines"), "style.graphviz.default_engines")

    page_profiles = _mapping(style["page_profiles"], "style.page_profiles")
    profiles = _layout_profiles(style)
    raw_figures = _mapping(catalogue.get("figures"), "figures")
    figures = _figures(raw_figures, allowed_stages, profiles, page_profiles)

    return VisualizationConfig(
        repository_root=root,
        schema_version=1,
        allowed_stages=allowed_stages,
        allowed_output_formats=formats,
        output=output_paths,
        figures=figures,
        layout_profiles=profiles,
        style=MappingProxyType(dict(style)),
        figures_config_path=figures_file,
        style_config_path=style_file,
    )
