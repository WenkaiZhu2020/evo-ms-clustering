"""Stage 3 four-objective to three-objective projection method figure."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from collections.abc import Callable

from evo_ms.visualization.dot import dot_quote, stable_attributes, write_dot
from evo_ms.visualization.layout import render_graphviz
from evo_ms.visualization.model import (
    GraphvizRenderRequest,
    GraphvizRenderResult,
    VisualizationConfig,
)
from evo_ms.visualization.provenance import (
    build_provenance,
    sha256_file,
    write_json_atomic,
    write_provenance,
)


FIGURE_ID = "stage3_four_to_three_projection"
STAGE_DIRECTORY = "stage3"


def _node_attributes(config: VisualizationConfig, role: str) -> dict[str, object]:
    style = config.style
    node = style["node"]
    workflow = style["workflow"][role]
    return {
        "color": workflow["color"],
        "fillcolor": workflow["fillcolor"],
        "fontname": style["fonts"]["family"],
        "fontsize": style["fonts"]["node_size"],
        "margin": "0.16,0.10",
        "penwidth": node["penwidth"],
        "shape": node["shape"],
        "style": node["style"],
    }


def _html_label(*lines: str) -> str:
    rows = "".join(f'<TR><TD ALIGN="CENTER">{line}</TD></TR>' for line in lines)
    return f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">{rows}</TABLE>>'


def _node_statement(
    node_id: str,
    attributes: dict[str, object],
    label: str,
) -> str:
    rendered = stable_attributes(attributes)
    return f"  {dot_quote(node_id)} {rendered[:-1]}, label={label}];"


def projection_dot(config: VisualizationConfig) -> str:
    """Return deterministic DOT matching the formal Stage 3 projection code."""

    specification = config.figures[FIGURE_ID]
    profile = config.layout_profiles[specification.layout_profile]
    page = config.style["page_profiles"][profile.page_profile]
    graph_style = config.style["graph"]
    edge_style = config.style["edge"]
    nodes = {
        "n1": (
            _node_attributes(config, "stage3_space"),
            _html_label(
                "Stage 3 four-objective Pareto set",
                "(coupling, −cohesion, imbalance, <I>f</I><SUB>sem</SUB>)",
            ),
        ),
        "n2": (
            _node_attributes(config, "operation"),
            _html_label("Project onto the structural objectives", "(coupling, −cohesion, imbalance)"),
        ),
        "n3": (
            _node_attributes(config, "operation"),
            _html_label("Recompute non-dominance in 3D", "Remove exact duplicate triples"),
        ),
        "n4": (
            _node_attributes(config, "common_space"),
            _html_label("Projected Stage 3 front", "(coupling, −cohesion, imbalance)"),
        ),
        "n5": (
            _node_attributes(config, "comparison"),
            _html_label("Common structural comparison", "Stage 2 front vs projected Stage 3 front"),
        ),
    }
    edge_attributes = {
        "arrowsize": 0.75,
        "color": edge_style["color"],
        "fontname": config.style["fonts"]["family"],
        "penwidth": edge_style["penwidth"],
        "style": edge_style["style"],
    }
    graph_attributes = {
        "bgcolor": graph_style["background"],
        "fontname": config.style["fonts"]["family"],
        "margin": graph_style["margin"],
        "nodesep": 0.28,
        "outputorder": "edgesfirst",
        "pad": graph_style["pad"],
        "rankdir": "TB",
        "ranksep": 0.55,
        "size": f"{page['width_in']},{page['height_in']}",
    }
    lines = [
        f"digraph {dot_quote(specification.title)} {{",
        f"  graph {stable_attributes(graph_attributes)};",
    ]
    lines.extend(_node_statement(node_id, *nodes[node_id]) for node_id in sorted(nodes))
    lines.extend(
        (
            "",
            '  subgraph "top_row" { rank=same; "n1"; "n2"; "n3"; }',
            '  subgraph "bottom_row" { rank=same; "n4"; "n5"; }',
            "",
        )
    )
    for source, target in (("n1", "n2"), ("n2", "n3"), ("n3", "n4"), ("n4", "n5")):
        lines.append(
            f"  {dot_quote(source)} -> {dot_quote(target)} {stable_attributes(edge_attributes)};"
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def _targets(config: VisualizationConfig, output_root: Path | None) -> tuple[dict[str, Path], Path, Path | None]:
    if output_root is None:
        targets = {
            "dot": config.output.dot / STAGE_DIRECTORY / f"{FIGURE_ID}.dot",
            "svg": config.output.svg / STAGE_DIRECTORY / f"{FIGURE_ID}.svg",
            "pdf": config.output.pdf / STAGE_DIRECTORY / f"{FIGURE_ID}.pdf",
            "provenance": config.output.data / STAGE_DIRECTORY / f"{FIGURE_ID}.provenance.json",
        }
        return targets, config.repository_root / "reports/figures/manifest.json", None
    root = output_root.resolve()
    targets = {
        "dot": root / "source" / STAGE_DIRECTORY / f"{FIGURE_ID}.dot",
        "svg": root / "preview" / STAGE_DIRECTORY / f"{FIGURE_ID}.svg",
        "pdf": root / "pdf" / STAGE_DIRECTORY / f"{FIGURE_ID}.pdf",
        "provenance": root / "data" / STAGE_DIRECTORY / f"{FIGURE_ID}.provenance.json",
    }
    return targets, root / "manifest.json", root


def _relative(path: Path, repository_root: Path, artifact_root: Path | None) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(repository_root):
        return resolved.relative_to(repository_root).as_posix()
    if artifact_root is not None and resolved.is_relative_to(artifact_root):
        return resolved.relative_to(artifact_root).as_posix()
    raise ValueError(f"figure path is outside the repository and artifact root: {path}")


def _manifest(
    manifest_path: Path,
    config: VisualizationConfig,
    targets: dict[str, Path],
    artifact_root: Path | None,
    generated_at: str,
) -> dict[str, object]:
    if manifest_path.exists():
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        document = {"schema_version": 1, "figures": {}}
    if document.get("schema_version") != 1 or not isinstance(document.get("figures"), dict):
        raise ValueError("figure manifest must be a schema-version 1 catalogue")
    specification = config.figures[FIGURE_ID]
    outputs = {
        name: _relative(path, config.repository_root, artifact_root)
        for name, path in sorted(targets.items())
    }
    document["figures"][FIGURE_ID] = {
        "destination": specification.destination,
        "formats": list(specification.formats),
        "generated_at": generated_at,
        "generator": specification.generator,
        "inputs": list(specification.inputs),
        "outputs": outputs,
        "sha256": {name: sha256_file(targets[name]) for name in sorted(targets)},
        "stage": specification.stage,
        "title": specification.title,
    }
    return document


def build_figure(
    config: VisualizationConfig,
    *,
    output_root: str | Path | None = None,
    manifest_path: str | Path | None = None,
    generated_at: str | None = None,
    git_commit: str | None = None,
    git_dirty: bool | None = None,
    renderer: Callable[[GraphvizRenderRequest], GraphvizRenderResult] = render_graphviz,
) -> dict[str, Path]:
    """Build only the registered Stage 3 projection figure."""

    specification = config.figures.get(FIGURE_ID)
    if specification is None:
        raise ValueError(f"figure is not registered: {FIGURE_ID}")
    if not specification.enabled:
        raise ValueError(f"figure is disabled: {FIGURE_ID}")
    if specification.formats != ("dot", "svg", "pdf"):
        raise ValueError(f"figure formats must be dot, svg, and pdf: {FIGURE_ID}")
    root_override = None if output_root is None else Path(output_root)
    targets, default_manifest, artifact_root = _targets(config, root_override)
    manifest = default_manifest if manifest_path is None else Path(manifest_path)
    for path in (*targets.values(), manifest):
        path.parent.mkdir(parents=True, exist_ok=True)

    staging_parent = artifact_root or (config.repository_root / "reports/figures")
    with tempfile.TemporaryDirectory(prefix=f".{FIGURE_ID}.", dir=staging_parent) as temporary:
        stage = Path(temporary)
        staged_dot = write_dot(stage / "figure.dot", projection_dot(config))
        render_results = []
        for output_format in ("svg", "pdf"):
            render_results.append(
                renderer(
                    GraphvizRenderRequest(
                        dot_path=staged_dot,
                        output_path=stage / f"figure.{output_format}",
                        output_format=output_format,
                        engine="dot",
                    )
                )
            )
        for name, staged in (
            ("dot", staged_dot),
            ("svg", stage / "figure.svg"),
            ("pdf", stage / "figure.pdf"),
        ):
            if not staged.is_file() or staged.stat().st_size == 0:
                raise ValueError(f"figure renderer did not create non-empty {name} output")
            os.replace(staged, targets[name])

    render_commands = (
        ("dot", "-Tsvg", str(targets["dot"]), "-o", str(targets["svg"])),
        ("dot", "-Tpdf", str(targets["dot"]), "-o", str(targets["pdf"])),
    )
    record = build_provenance(
        figure_id=FIGURE_ID,
        stage=specification.stage,
        generator="src/" + specification.generator.replace(".", "/") + ".py",
        repository_root=config.repository_root,
        input_files=(config.repository_root / path for path in specification.inputs),
        config_files=(config.figures_config_path, config.style_config_path),
        dot_path=targets["dot"],
        graphviz_engine="dot",
        graphviz_version=render_results[0].version,
        render_commands=render_commands,
        generated_outputs=targets.values(),
        artifact_root=artifact_root,
        generated_at=generated_at,
        git_commit=git_commit,
        git_dirty=git_dirty,
    )
    write_provenance(targets["provenance"], record)
    write_json_atomic(
        manifest,
        _manifest(manifest, config, targets, artifact_root, record.generated_at),
    )
    return targets
