"""JPetStore structural-versus-semantic evidence comparison."""

from __future__ import annotations

from collections.abc import Callable
import csv
from dataclasses import dataclass
from io import StringIO
import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

import pandas as pd

from evo_ms.visualization.dot import dot_quote, format_number, stable_attributes, write_dot
from evo_ms.visualization.layout import GraphvizError, find_graphviz, render_graphviz
from evo_ms.visualization.model import GraphvizRenderRequest, GraphvizRenderResult, VisualizationConfig
from evo_ms.visualization.provenance import build_provenance, sha256_file, write_json_atomic, write_provenance


FIGURE_ID = "stage3_jpetstore_semantic_evidence_comparison"
STAGE_DIRECTORY = "stage3"
BASENAME = "jpetstore_semantic_evidence_comparison"
EXPECTED_CLASS_COUNT = 24
EXPECTED_STRUCTURAL_EDGES = 53
EXPECTED_SEMANTIC_EDGES = 47
EXPECTED_STRUCTURAL_ONLY = 28
EXPECTED_OVERLAP = 25
EXPECTED_SEMANTIC_ONLY = 22
EXPECTED_UNION_EDGES = 75


@dataclass(frozen=True)
class EvidenceNode:
    class_id: str
    display_name: str
    canonical_order: int


@dataclass(frozen=True)
class EvidenceEdge:
    source_class_id: str
    target_class_id: str
    source_display_name: str
    target_display_name: str
    structural_weight: float | None
    semantic_similarity: float | None
    edge_category: str


@dataclass(frozen=True)
class MasterPosition:
    class_id: str
    display_name: str
    x: float
    y: float
    canonical_order: int
    width_pt: float
    height_pt: float


@dataclass(frozen=True)
class EvidenceData:
    nodes: tuple[EvidenceNode, ...]
    edges: tuple[EvidenceEdge, ...]


def _canonical_pair(source: object, target: object) -> tuple[str, str]:
    left, right = str(source), str(target)
    if left == right:
        raise ValueError(f"self-loop is forbidden: {left}")
    return (left, right) if left < right else (right, left)


def _edge_map(frame: pd.DataFrame, source: str, target: str, weight: str, label: str) -> dict[tuple[str, str], float]:
    result: dict[tuple[str, str], float] = {}
    for row in frame.itertuples(index=False):
        pair = _canonical_pair(getattr(row, source), getattr(row, target))
        if pair in result:
            raise ValueError(f"duplicate undirected {label} edge: {pair[0]} -- {pair[1]}")
        value = float(getattr(row, weight))
        if not math.isfinite(value):
            raise ValueError(f"non-finite {label} edge value: {pair[0]} -- {pair[1]}")
        result[pair] = value
    return result


def prepare_evidence_data(config: VisualizationConfig) -> EvidenceData:
    """Read the formal graph inputs and validate the audited JPetStore scope."""

    root = config.repository_root
    nodes_path = root / "data/extracted/jpetstore/class_nodes.csv"
    structural_path = root / "results/stage1/subjects/jpetstore/leiden_baseline/raw_reference_leiden/graph/stage1_edges.csv"
    semantic_path = root / "data/semantic_graphs/declaration_method_body/jpetstore/semantic_edges.csv"
    mapping_path = root / "data/semantic_graphs/declaration_method_body/jpetstore/class_mapping.csv"
    metadata_path = root / "data/semantic_graphs/declaration_method_body/jpetstore/graph_metadata.json"

    node_frame = pd.read_csv(nodes_path)
    structural_frame = pd.read_csv(structural_path)
    semantic_frame = pd.read_csv(semantic_path)
    mapping = pd.read_csv(mapping_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if len(node_frame) != EXPECTED_CLASS_COUNT or node_frame["class_id"].astype(str).duplicated().any():
        raise ValueError("JPetStore formal node scope must contain 24 unique class IDs")
    if len(mapping) != EXPECTED_CLASS_COUNT:
        raise ValueError("JPetStore class mapping must contain exactly 24 records")
    for column in ("row_index", "class_id", "class_name"):
        if mapping[column].duplicated().any():
            raise ValueError(f"JPetStore class mapping is not one-to-one: duplicate {column}")

    node_ids = set(node_frame["class_id"].astype(str))
    mapping_ids = set(mapping["class_id"].astype(str))
    if node_ids != mapping_ids:
        raise ValueError("structural and semantic class scopes do not match")
    display_by_id = dict(zip(mapping["class_id"].astype(str), mapping["class_name"].astype(str), strict=True))
    for class_id, display_name in display_by_id.items():
        if class_id.rsplit(".", 1)[-1] != display_name:
            raise ValueError(f"class mapping display name does not resolve from class ID: {class_id}")

    structural = _edge_map(structural_frame, "source", "target", "raw_weight", "structural")
    semantic = _edge_map(semantic_frame, "class_id_a", "class_id_b", "weight", "semantic")
    if len(structural) != EXPECTED_STRUCTURAL_EDGES or len(semantic) != EXPECTED_SEMANTIC_EDGES:
        raise ValueError("JPetStore formal edge counts changed from 53 structural and 47 semantic")
    endpoints = {class_id for pair in (*structural.keys(), *semantic.keys()) for class_id in pair}
    if not endpoints <= node_ids:
        raise ValueError(f"graph edge endpoint is outside the formal class scope: {sorted(endpoints - node_ids)}")
    semantic_degree = {class_id: 0 for class_id in node_ids}
    for source, target in semantic:
        semantic_degree[source] += 1
        semantic_degree[target] += 1
    if any(degree == 0 for degree in semantic_degree.values()):
        raise ValueError("semantic graph contains an isolated formal class")
    if metadata.get("node_count") != EXPECTED_CLASS_COUNT or metadata.get("edge_count") != EXPECTED_SEMANTIC_EDGES:
        raise ValueError("semantic graph metadata disagrees with formal node or edge counts")

    structural_only = set(structural) - set(semantic)
    overlap = set(structural) & set(semantic)
    semantic_only = set(semantic) - set(structural)
    if (len(structural_only), len(overlap), len(semantic_only), len(set(structural) | set(semantic))) != (
        EXPECTED_STRUCTURAL_ONLY,
        EXPECTED_OVERLAP,
        EXPECTED_SEMANTIC_ONLY,
        EXPECTED_UNION_EDGES,
    ):
        raise ValueError("JPetStore evidence-category counts changed from the approved audit")

    nodes = tuple(
        EvidenceNode(class_id, display_by_id[class_id], order)
        for order, class_id in enumerate(sorted(node_ids), start=1)
    )
    edges: list[EvidenceEdge] = []
    for source, target in sorted(set(structural) | set(semantic)):
        if (source, target) in overlap:
            category = "overlap"
        elif (source, target) in structural_only:
            category = "structural_only"
        else:
            category = "semantic_only"
        edges.append(EvidenceEdge(
            source,
            target,
            display_by_id[source],
            display_by_id[target],
            structural.get((source, target)),
            semantic.get((source, target)),
            category,
        ))
    return EvidenceData(nodes, tuple(edges))


def edge_category_csv(data: EvidenceData) -> str:
    """Serialize the deterministic 75-edge union audit table."""

    buffer = StringIO(newline="")
    fields = (
        "source_class_id", "target_class_id", "source_display_name", "target_display_name",
        "structural_weight", "semantic_similarity", "edge_category",
    )
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for edge in data.edges:
        writer.writerow({
            "source_class_id": edge.source_class_id,
            "target_class_id": edge.target_class_id,
            "source_display_name": edge.source_display_name,
            "target_display_name": edge.target_display_name,
            "structural_weight": "" if edge.structural_weight is None else format(edge.structural_weight, ".17g"),
            "semantic_similarity": "" if edge.semantic_similarity is None else format(edge.semantic_similarity, ".17g"),
            "edge_category": edge.edge_category,
        })
    return buffer.getvalue()


def initial_layout_dot(config: VisualizationConfig, data: EvidenceData) -> str:
    """Return the category-neutral, unweighted union graph used only for layout."""

    style = config.style
    evidence_style = style["semantic_evidence_comparison"]
    lines = [
        f"graph {dot_quote('JPetStore unweighted structural-semantic union layout')} {{",
        "  graph " + stable_attributes({
            "overlap": False, "sep": "+15", "start": style["graphviz"]["initial_layout_seed"],
        }) + ";",
        "  node " + stable_attributes({
            "fontname": style["fonts"]["family"], "fontsize": evidence_style["node_font_size"],
            "height": evidence_style["node_height_in"], "margin": evidence_style["node_margin"],
            "shape": style["node"]["shape"],
        }) + ";",
    ]
    for node in data.nodes:
        lines.append(f"  {dot_quote(node.class_id)} {stable_attributes({'label': node.display_name})};")
    lines.append("")
    for edge in data.edges:
        lines.append(f"  {dot_quote(edge.source_class_id)} -- {dot_quote(edge.target_class_id)};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _plain_positions(text: str, expected: set[str]) -> dict[str, tuple[float, float, float, float]]:
    positions: dict[str, tuple[float, float, float, float]] = {}
    for line in text.splitlines():
        fields = shlex.split(line)
        if fields and fields[0] == "node":
            class_id = fields[1]
            positions[class_id] = (
                float(fields[2]), float(fields[3]), float(fields[4]) * 72, float(fields[5]) * 72,
            )
    if set(positions) != expected or not all(math.isfinite(value) for pair in positions.values() for value in pair):
        raise ValueError("neato did not return one finite coordinate for every formal class")
    return positions


def _remove_box_overlaps(
    nodes: tuple[EvidenceNode, ...],
    coordinates: dict[str, list[float]],
    dimensions: dict[str, tuple[float, float]],
    canvas_width: float,
    panel_height: float,
) -> None:
    """Deterministically separate normalized label boxes without graph evidence."""

    gap = 2.0
    boundary = 4.0
    ordered = [node.class_id for node in nodes]
    for _iteration in range(2000):
        moved = False
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1:]:
                left_x, left_y = coordinates[left]
                right_x, right_y = coordinates[right]
                left_width, left_height = dimensions[left]
                right_width, right_height = dimensions[right]
                overlap_x = (left_width + right_width) / 2 + gap - abs(left_x - right_x)
                overlap_y = (left_height + right_height) / 2 + gap - abs(left_y - right_y)
                if overlap_x <= 0 or overlap_y <= 0:
                    continue
                moved = True
                if overlap_x <= overlap_y:
                    direction = -1.0 if left_x <= right_x else 1.0
                    shift = overlap_x / 2 + 0.01
                    coordinates[left][0] += direction * shift
                    coordinates[right][0] -= direction * shift
                else:
                    direction = -1.0 if left_y <= right_y else 1.0
                    shift = overlap_y / 2 + 0.01
                    coordinates[left][1] += direction * shift
                    coordinates[right][1] -= direction * shift
                for class_id in (left, right):
                    width, height = dimensions[class_id]
                    coordinates[class_id][0] = min(
                        canvas_width - boundary - width / 2,
                        max(boundary + width / 2, coordinates[class_id][0]),
                    )
                    coordinates[class_id][1] = min(
                        panel_height - boundary - height / 2,
                        max(boundary + height / 2, coordinates[class_id][1]),
                    )
        if not moved:
            return
    raise ValueError("deterministic normalized JPetStore layout still contains overlapping node boxes")


def generate_master_positions(
    config: VisualizationConfig, data: EvidenceData, layout_dot_path: Path
) -> tuple[MasterPosition, ...]:
    """Run seeded neato once, then normalize its category-neutral coordinates."""

    write_dot(layout_dot_path, initial_layout_dot(config, data))
    executable = find_graphviz("neato")
    seed = int(config.style["graphviz"]["initial_layout_seed"])
    completed = subprocess.run(
        [str(executable), f"-Gstart={seed}", "-Tplain", str(layout_dot_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise GraphvizError(f"initial JPetStore neato layout failed: {completed.stderr.strip()}")
    raw = _plain_positions(completed.stdout, {node.class_id for node in data.nodes})
    xs = [pair[0] for pair in raw.values()]
    ys = [pair[1] for pair in raw.values()]
    raw_width = max(xs) - min(xs)
    raw_height = max(ys) - min(ys)
    if raw_width <= 0 or raw_height <= 0:
        raise ValueError("initial JPetStore union layout has zero extent")
    layout = config.style["semantic_evidence_comparison"]
    margin_x = float(layout["coordinate_margin_x_pt"])
    margin_y = float(layout["coordinate_margin_y_pt"])
    usable_width = float(layout["canvas_width_pt"]) - 2 * margin_x
    usable_height = float(layout["panel_height_pt"]) - 2 * margin_y
    scale_x = usable_width / raw_width
    scale_y = usable_height / raw_height
    coordinates = {
        node.class_id: [
            margin_x + (raw[node.class_id][0] - min(xs)) * scale_x,
            margin_y + (raw[node.class_id][1] - min(ys)) * scale_y,
        ]
        for node in data.nodes
    }
    dimensions = {node.class_id: (raw[node.class_id][2], raw[node.class_id][3]) for node in data.nodes}
    _remove_box_overlaps(
        data.nodes,
        coordinates,
        dimensions,
        float(layout["canvas_width_pt"]),
        float(layout["panel_height_pt"]),
    )
    return tuple(
        MasterPosition(
            node.class_id,
            node.display_name,
            coordinates[node.class_id][0],
            coordinates[node.class_id][1],
            node.canonical_order,
            dimensions[node.class_id][0],
            dimensions[node.class_id][1],
        )
        for node in data.nodes
    )


def master_position_csv(positions: tuple[MasterPosition, ...]) -> str:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(
        buffer, fieldnames=("class_id", "display_name", "x", "y", "canonical_order"), lineterminator="\n"
    )
    writer.writeheader()
    for position in positions:
        writer.writerow({
            "class_id": position.class_id,
            "display_name": position.display_name,
            "x": format(position.x, ".12g"),
            "y": format(position.y, ".12g"),
            "canonical_order": position.canonical_order,
        })
    return buffer.getvalue()


def evidence_dot(
    config: VisualizationConfig, data: EvidenceData, positions: tuple[MasterPosition, ...]
) -> str:
    """Return the two-panel fixed-coordinate comparison DOT."""

    style = config.style
    layout = style["semantic_evidence_comparison"]
    node_style = style["node"]
    categories = style["edge_categories"]
    font = style["fonts"]["family"]
    panel_offset = float(layout["panel_offset_pt"])
    panel_height = float(layout["panel_height_pt"])
    canvas_width = float(layout["canvas_width_pt"])
    position_by_id = {position.class_id: position for position in positions}
    if set(position_by_id) != {node.class_id for node in data.nodes} or len(position_by_id) != EXPECTED_CLASS_COUNT:
        raise ValueError("master coordinate scope does not match the formal class scope")

    lines = [
        f"graph {dot_quote(config.figures[FIGURE_ID].title)} {{",
        "  graph " + stable_attributes({
            "bgcolor": style["graph"]["background"], "margin": style["graph"]["margin"],
            "notranslate": True, "outputorder": "edgesfirst", "overlap": True,
            "pad": style["graph"]["pad"], "splines": True,
        }) + ";",
        "  node " + stable_attributes({
            "color": node_style["color"], "fillcolor": node_style["fillcolor"], "fontname": font,
            "fontsize": layout["node_font_size"], "height": layout["node_height_in"],
            "margin": layout["node_margin"], "penwidth": node_style["penwidth"],
            "shape": node_style["shape"], "style": node_style["style"],
        }) + ";",
        "  edge " + stable_attributes({"dir": "none"}) + ";",
        "",
    ]
    id_by_class = {node.class_id: f"n{node.canonical_order:02d}" for node in data.nodes}
    for prefix, offset in (("a", panel_offset), ("b", 0.0)):
        for position in positions:
            lines.append(
                f"  {dot_quote(prefix + '_' + id_by_class[position.class_id])} "
                + stable_attributes({
                    "label": position.display_name, "pin": True,
                    "pos": f"{format_number(position.x)},{format_number(position.y + offset)}!",
                    "tooltip": position.class_id,
                }) + ";"
            )
    lines.extend((
        "",
        f"  {dot_quote('title_a')} " + stable_attributes({
            "color": "transparent", "fillcolor": "transparent", "fontname": font,
            "fontsize": style["fonts"]["title_size"], "label": "(a) Structural evidence\n53 edges: 28 structural-only and 25 overlap",
            "pin": True, "pos": f"{format_number(canvas_width / 2)},{format_number(panel_offset + panel_height + 12)}!",
            "shape": "plain", "style": "",
        }) + ";",
        f"  {dot_quote('title_b')} " + stable_attributes({
            "color": "transparent", "fillcolor": "transparent", "fontname": font,
            "fontsize": style["fonts"]["title_size"], "label": "(b) Semantic evidence\n47 edges: 22 semantic-only and 25 overlap",
            "pin": True, "pos": f"{format_number(canvas_width / 2)},{format_number(panel_height + 12)}!",
            "shape": "plain", "style": "",
        }) + ";",
        "",
    ))

    category_keys = {
        "structural_only": "structural",
        "overlap": "structural_semantic_overlap",
        "semantic_only": "semantic_only",
    }
    for panel, included in (("a", ("structural_only", "overlap")), ("b", ("semantic_only", "overlap"))):
        for category in included:
            edge_style = categories[category_keys[category]]
            for edge in (edge for edge in data.edges if edge.edge_category == category):
                tooltip = f"{edge.source_display_name} -- {edge.target_display_name}: {category.replace('_', ' ')}"
                lines.append(
                    f"  {dot_quote(panel + '_' + id_by_class[edge.source_class_id])} -- "
                    f"{dot_quote(panel + '_' + id_by_class[edge.target_class_id])} "
                    + stable_attributes({
                        "color": edge_style["color"], "penwidth": edge_style["penwidth"],
                        "style": edge_style["style"], "tooltip": tooltip,
                    }) + ";"
                )

    legend_y = 5.0
    legend = (
        (10.0, 90.0, "structural_only", "Structural-only - 28"),
        (160.0, 275.0, "overlap", "Structural-semantic overlap - 25"),
        (375.0, 445.0, "semantic_only", "Semantic-only - 22"),
    )
    lines.append("")
    for index, (x, label_x, category, label) in enumerate(legend, start=1):
        edge_style = categories[category_keys[category]]
        for suffix, endpoint in (("l", x), ("r", x + 18)):
            lines.append(
                f"  {dot_quote(f'legend_{index}_{suffix}')} " + stable_attributes({
                    "height": 0.01, "label": "", "pin": True,
                    "pos": f"{format_number(endpoint)},{format_number(legend_y)}!",
                    "shape": "point", "style": "invis", "width": 0.01,
                }) + ";"
            )
        lines.append(
            f"  {dot_quote(f'legend_{index}_label')} " + stable_attributes({
                "color": "transparent", "fillcolor": "transparent", "fontname": font,
                "fontsize": style["fonts"]["edge_size"], "label": label, "pin": True,
                "pos": f"{format_number(label_x)},{format_number(legend_y)}!", "shape": "plain", "style": "",
            }) + ";"
        )
        lines.append(
            f"  {dot_quote(f'legend_{index}_l')} -- {dot_quote(f'legend_{index}_r')} "
            + stable_attributes({
                "color": edge_style["color"], "penwidth": edge_style["penwidth"],
                "style": edge_style["style"],
            }) + ";"
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def _relative(path: Path, repository_root: Path, artifact_root: Path | None = None) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(repository_root):
        return resolved.relative_to(repository_root).as_posix()
    if artifact_root is not None and resolved.is_relative_to(artifact_root):
        return resolved.relative_to(artifact_root).as_posix()
    raise ValueError(f"figure path is outside the repository and artifact root: {path}")


def _targets(config: VisualizationConfig, output_root: Path | None) -> tuple[dict[str, Path], Path, Path | None]:
    if output_root is None:
        targets = {
            "categories": config.output.data / STAGE_DIRECTORY / "jpetstore_semantic_edge_categories.csv",
            "positions": config.output.data / "common/jpetstore_union_positions.csv",
            "dot": config.output.dot / STAGE_DIRECTORY / f"{BASENAME}.dot",
            "svg": config.output.svg / STAGE_DIRECTORY / f"{BASENAME}.svg",
            "pdf": config.output.pdf / STAGE_DIRECTORY / f"{BASENAME}.pdf",
            "provenance": config.output.data / STAGE_DIRECTORY / f"{BASENAME}.provenance.json",
        }
        return targets, config.repository_root / "reports/figures/manifest.json", None
    root = output_root.resolve()
    targets = {
        "categories": root / "data/stage3/jpetstore_semantic_edge_categories.csv",
        "positions": root / "data/common/jpetstore_union_positions.csv",
        "dot": root / f"source/stage3/{BASENAME}.dot",
        "svg": root / f"preview/stage3/{BASENAME}.svg",
        "pdf": root / f"pdf/stage3/{BASENAME}.pdf",
        "provenance": root / f"data/stage3/{BASENAME}.provenance.json",
    }
    return targets, root / "manifest.json", root


def _manifest_document(
    manifest_path: Path,
    config: VisualizationConfig,
    targets: dict[str, Path],
    staged: dict[str, Path],
    artifact_root: Path | None,
    generated_at: str,
) -> dict[str, object]:
    document = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {
        "schema_version": 1, "figures": {},
    }
    if document.get("schema_version") != 1 or not isinstance(document.get("figures"), dict):
        raise ValueError("figure manifest must be a schema-version 1 catalogue")
    specification = config.figures[FIGURE_ID]
    document["figures"][FIGURE_ID] = {
        "destination": specification.destination,
        "edge_category_data_path": specification.edge_category_data_path,
        "formats": list(specification.formats),
        "generated_at": generated_at,
        "generator": specification.generator,
        "inputs": list(specification.inputs),
        "layout_coordinate_path": specification.layout_coordinate_path,
        "outputs": {name: _relative(path, config.repository_root, artifact_root) for name, path in sorted(targets.items())},
        "sha256": {name: sha256_file(staged[name]) for name in sorted(staged)},
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
    """Build only the registered fixed-coordinate semantic-evidence comparison."""

    specification = config.figures.get(FIGURE_ID)
    if specification is None or not specification.enabled:
        raise ValueError(f"figure is not registered and enabled: {FIGURE_ID}")
    if specification.formats != ("dot", "svg", "pdf") or specification.layout_profile != "fixed_comparison":
        raise ValueError(f"figure must use fixed-comparison DOT, SVG, and PDF rendering: {FIGURE_ID}")
    expected_positions = "reports/figures/data/common/jpetstore_union_positions.csv"
    expected_categories = "reports/figures/data/stage3/jpetstore_semantic_edge_categories.csv"
    if specification.layout_coordinate_path != expected_positions or specification.edge_category_data_path != expected_categories:
        raise ValueError("registered JPetStore intermediate-data paths changed")

    root_override = None if output_root is None else Path(output_root)
    targets, default_manifest, artifact_root = _targets(config, root_override)
    manifest = default_manifest if manifest_path is None else Path(manifest_path)
    for path in (*targets.values(), manifest):
        path.parent.mkdir(parents=True, exist_ok=True)
    data = prepare_evidence_data(config)
    staging_parent = artifact_root or (config.repository_root / "reports/figures")
    with tempfile.TemporaryDirectory(prefix=f".{FIGURE_ID}.", dir=staging_parent) as temporary:
        stage = Path(temporary)
        staged = {
            "categories": stage / "edge_categories.csv",
            "positions": stage / "positions.csv",
            "dot": stage / "figure.dot",
            "svg": stage / "figure.svg",
            "pdf": stage / "figure.pdf",
            "provenance": stage / "figure.provenance.json",
        }
        staged["categories"].write_text(edge_category_csv(data), encoding="utf-8", newline="\n")
        positions = generate_master_positions(config, data, stage / "initial_layout.dot")
        staged["positions"].write_text(master_position_csv(positions), encoding="utf-8", newline="\n")
        write_dot(staged["dot"], evidence_dot(config, data, positions))
        render_results = [
            renderer(GraphvizRenderRequest(staged["dot"], staged[output_format], output_format, "neato", True))
            for output_format in ("svg", "pdf")
        ]
        for name in ("categories", "positions", "dot", "svg", "pdf"):
            if not staged[name].is_file() or staged[name].stat().st_size == 0:
                raise ValueError(f"figure build did not create non-empty {name} output")
        render_commands = (
            ("neato", "-n2", "-Tsvg", str(targets["dot"]), "-o", str(targets["svg"])),
            ("neato", "-n2", "-Tpdf", str(targets["dot"]), "-o", str(targets["pdf"])),
        )
        record = build_provenance(
            figure_id=FIGURE_ID,
            stage=specification.stage,
            generator="src/" + specification.generator.replace(".", "/") + ".py",
            repository_root=config.repository_root,
            input_files=(config.repository_root / path for path in specification.inputs),
            config_files=(config.figures_config_path, config.style_config_path),
            dot_path=staged["dot"],
            graphviz_engine="neato",
            graphviz_version=render_results[0].version,
            render_commands=render_commands,
            generated_outputs=targets.values(),
            artifact_root=artifact_root,
            generated_at=generated_at,
            git_commit=git_commit,
            git_dirty=git_dirty,
        )
        write_provenance(staged["provenance"], record)
        staged_manifest = stage / "manifest.json"
        write_json_atomic(
            staged_manifest,
            _manifest_document(manifest, config, targets, staged, artifact_root, record.generated_at),
        )
        for name in ("categories", "positions", "dot", "svg", "pdf", "provenance"):
            os.replace(staged[name], targets[name])
        os.replace(staged_manifest, manifest)
    return targets
