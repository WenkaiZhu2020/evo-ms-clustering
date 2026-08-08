#!/usr/bin/env python3
"""Validate, list, or smoke-test the common visualisation infrastructure."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.visualization import (
    GraphvizError,
    GraphvizRenderRequest,
    build_provenance,
    content_sha256,
    find_graphviz,
    graphviz_version,
    load_visualization_config,
    render_graphviz,
    render_undirected_graph,
    sha256_file,
    write_dot,
    write_provenance,
)


def _list_figures() -> int:
    config = load_visualization_config()
    if not config.figures:
        print("No formal figures registered.")
        return 0
    for figure_id in sorted(config.figures):
        figure = config.figures[figure_id]
        state = "enabled" if figure.enabled else "disabled"
        print(f"{figure.figure_id}\t{figure.stage}\t{state}\t{figure.title}")
    return 0


def _configured_engines(config) -> tuple[str, ...]:
    graphviz = config.style["graphviz"]
    return tuple(sorted(set(graphviz["default_engines"].values())))


def _validate_config() -> int:
    config = load_visualization_config()
    for engine in _configured_engines(config):
        executable = find_graphviz(engine)
        print(f"{engine}: {executable.name}: {graphviz_version(engine)}")
    print("Visualisation configuration is valid.")
    for name, path in config.output.as_dict().items():
        print(f"output.{name}: {path.relative_to(config.repository_root)}")
    return 0


def _build_registered_figure(figure_id: str) -> int:
    config = load_visualization_config()
    specification = config.figures.get(figure_id)
    if specification is None:
        raise ValueError(f"unknown figure ID: {figure_id}")
    if not specification.enabled:
        raise ValueError(f"figure is disabled: {figure_id}")
    if figure_id == "stage3_four_to_three_projection":
        from evo_ms.visualization.figures.stage3_projection import build_figure
    elif figure_id == "stage2_daytrader_partition_transition":
        from evo_ms.visualization.figures.stage2_daytrader_transition import build_figure
    elif figure_id == "stage3_jpetstore_semantic_evidence_comparison":
        from evo_ms.visualization.figures.stage3_jpetstore_semantic_evidence import build_figure
    elif figure_id == "stage123_daytrader_highest_lowest_clusters":
        from evo_ms.visualization.figures.stage123_daytrader_clusters import build_figure
    elif figure_id == "stage123_jpetstore_highest_lowest_clusters":
        from evo_ms.visualization.figures.stage123_jpetstore_clusters import build_figure
    elif figure_id in {
        "stage13_xerces_shared_highest_lowest_clusters",
        "stage2_xerces_highest_lowest_clusters",
    }:
        from evo_ms.visualization.figures.stage123_xerces_clusters import build_figure
    elif figure_id == "cross_stage_partition_overview":
        from evo_ms.visualization.figures.cross_stage_partition_overview import build_figure
    elif figure_id == "stage1_ssa_seed_robustness":
        from evo_ms.visualization.figures.stage1_ssa_seed_robustness import build_figure
    else:
        raise ValueError(f"no implemented generator for figure: {figure_id}")

    outputs = (
        build_figure(config, figure_id=figure_id)
        if "xerces" in figure_id and "highest_lowest_clusters" in figure_id
        else build_figure(config)
    )
    for name in sorted(outputs):
        path = outputs[name]
        print(f"{name}\t{path.relative_to(config.repository_root)}\t{path.stat().st_size}\t{sha256_file(path)}")
    return 0


def _smoke_output_directory(value: Path, config) -> Path:
    output = value.resolve()
    if output == config.repository_root or output.is_relative_to(config.repository_root):
        raise ValueError("--smoke-test output must be a temporary directory outside the repository")
    output.mkdir(parents=True, exist_ok=True)
    return output


def _smoke_test(output_value: Path) -> int:
    config = load_visualization_config()
    output = _smoke_output_directory(output_value, config)
    paths = {
        "dot": output / "synthetic.dot",
        "svg": output / "synthetic.svg",
        "pdf": output / "synthetic.pdf",
        "provenance": output / "synthetic.provenance.json",
    }
    existing = [path.name for path in paths.values() if path.exists()]
    if existing:
        raise ValueError(f"smoke-test outputs already exist: {', '.join(sorted(existing))}")

    styles = config.style["edge_categories"]
    nodes = {
        "gamma": {"label": "Gamma", "pin": True, "pos": "120,0!"},
        "alpha": {"label": "Alpha", "pin": True, "pos": "0,0!"},
        "beta": {"label": "Beta", "pin": True, "pos": "60,60!"},
    }
    edges = [
        ("gamma", "beta", {"color": styles["semantic_only"]["color"], "style": styles["semantic_only"]["style"]}),
        ("beta", "alpha", {"color": styles["structural"]["color"], "style": styles["structural"]["style"]}),
    ]
    dot = render_undirected_graph(
        "Synthetic visualisation smoke test",
        nodes,
        edges,
        graph_attributes={"outputorder": "edgesfirst", "overlap": False, "splines": True},
    )
    write_dot(paths["dot"], dot)
    if content_sha256(dot) != sha256_file(paths["dot"]):
        raise ValueError("synthetic DOT hash changed while writing")

    renders = []
    for output_format in ("svg", "pdf"):
        renders.append(
            render_graphviz(
                GraphvizRenderRequest(
                    dot_path=paths["dot"],
                    output_path=paths[output_format],
                    output_format=output_format,
                    engine="neato",
                    fixed_coordinates=True,
                )
            )
        )
    provenance = build_provenance(
        figure_id="synthetic-smoke-test",
        stage="synthetic",
        generator="scripts/visualization/build_figures.py",
        repository_root=config.repository_root,
        input_files=(),
        config_files=(config.figures_config_path, config.style_config_path),
        dot_path=paths["dot"],
        graphviz_engine="neato",
        graphviz_version=renders[0].version,
        render_commands=(result.command for result in renders),
        generated_outputs=paths.values(),
        artifact_root=output,
    )
    write_provenance(paths["provenance"], provenance)
    for name in ("dot", "svg", "pdf", "provenance"):
        path = paths[name]
        print(f"{path.name}\t{path.stat().st_size}\t{sha256_file(path)}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--list", action="store_true", dest="list_figures")
    operation.add_argument("--validate-config", action="store_true")
    operation.add_argument("--smoke-test", action="store_true")
    operation.add_argument("--figure")
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.list_figures:
            if args.output_dir is not None:
                raise ValueError("--output-dir is valid only with --smoke-test")
            return _list_figures()
        if args.validate_config:
            if args.output_dir is not None:
                raise ValueError("--output-dir is valid only with --smoke-test")
            return _validate_config()
        if args.figure is not None:
            if args.output_dir is not None:
                raise ValueError("--output-dir is valid only with --smoke-test")
            return _build_registered_figure(args.figure)
        if args.output_dir is None:
            raise ValueError("--smoke-test requires --output-dir")
        return _smoke_test(args.output_dir)
    except (GraphvizError, OSError, ValueError) as error:
        print(f"visualisation command failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
