"""DayTrader cluster-flow transition from Stage 1 Leiden to Stage 2."""

from __future__ import annotations

from collections.abc import Callable
import csv
from dataclasses import dataclass
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile

import pandas as pd

from evo_ms.evaluation.partition_metrics import partition_similarity
from evo_ms.optimization.selection import select_solution
from evo_ms.visualization.dot import dot_quote, stable_attributes, write_dot
from evo_ms.visualization.layout import render_graphviz
from evo_ms.visualization.model import GraphvizRenderRequest, GraphvizRenderResult, VisualizationConfig
from evo_ms.visualization.provenance import (
    build_provenance,
    sha256_file,
    write_json_atomic,
    write_provenance,
)


FIGURE_ID = "stage2_daytrader_partition_transition"
STAGE_DIRECTORY = "stage2"
BASENAME = "daytrader_partition_transition"
SUBJECT = "daytrader"
EXPECTED_CLASS_COUNT = 53
EXPECTED_REFERENCE_CLUSTERS = 11
EXPECTED_TARGET_CLUSTERS = 9
EXPECTED_FLOW_COUNT = 15
EXPECTED_MAX_FLOW = 13
EXPECTED_SINGLETON_FLOWS = 9
EXPECTED_CHANGED_CLASSES = 6


@dataclass(frozen=True)
class Cluster:
    display_id: str
    members: tuple[str, ...]
    display_order: int
    color: str
    aligned_reference: str | None = None


@dataclass(frozen=True)
class Flow:
    source: str
    target: str
    shared_classes: tuple[str, ...]
    penwidth: float

    @property
    def count(self) -> int:
        return len(self.shared_classes)


@dataclass(frozen=True)
class TransitionData:
    seed: int
    solution_id: str
    reference_path: str
    target_path: str
    class_count: int
    ari: float
    nmi: float
    changed_class_count: int
    reference_clusters: tuple[Cluster, ...]
    target_clusters: tuple[Cluster, ...]
    flows: tuple[Flow, ...]


def flow_penwidth(shared_count: int, maximum_shared_count: int, minimum: float, maximum: float) -> float:
    """Return the configured square-root-scaled flow width."""

    if shared_count <= 0 or maximum_shared_count <= 0:
        raise ValueError("flow counts must be positive")
    if shared_count > maximum_shared_count:
        raise ValueError("shared flow count cannot exceed the maximum flow count")
    if minimum <= 0 or maximum < minimum:
        raise ValueError("transition flow width bounds are invalid")
    return minimum + (maximum - minimum) * math.sqrt(shared_count / maximum_shared_count)


def _historical_exporter(repository_root: Path):
    path = repository_root / "scripts/visualization/export_partition_dot.py"
    specification = importlib.util.spec_from_file_location("partition_dot_for_transition", path)
    if specification is None or specification.loader is None:
        raise ImportError(f"cannot load deterministic partition exporter: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def _relative(path: Path, repository_root: Path, artifact_root: Path | None = None) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(repository_root):
        return resolved.relative_to(repository_root).as_posix()
    if artifact_root is not None and resolved.is_relative_to(artifact_root):
        return resolved.relative_to(artifact_root).as_posix()
    raise ValueError(f"figure path is outside the repository and artifact root: {path}")


def _cluster_members(display_by_class: dict[str, str]) -> dict[str, tuple[str, ...]]:
    members: dict[str, list[str]] = {}
    for class_id, display_id in display_by_class.items():
        members.setdefault(display_id, []).append(class_id)
    return {display_id: tuple(sorted(values)) for display_id, values in members.items()}


def prepare_transition_data(config: VisualizationConfig) -> TransitionData:
    """Read and validate the formal DayTrader partitions and their overlaps."""

    specification = config.figures[FIGURE_ID]
    if specification.representative_seed != 25 or specification.representative_solution != "seed25_solution047":
        raise ValueError("DayTrader transition must use the approved seed 25 representative")
    root = config.repository_root
    canonical_path = root / "results/stage2/cross_subject/operating_profile/canonical_operating_solution_per_seed.csv"
    nodes_path = root / "data/extracted/daytrader/class_nodes.csv"
    reference_path = root / "results/stage1/subjects/daytrader/leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv"
    front_path = root / "results/stage2/subjects/daytrader/nsga/robustness_final_30seeds/seed_25/pareto_front.csv"
    target_path = front_path.with_name("pareto_labels.csv.xz")

    canonical = pd.read_csv(canonical_path)
    canonical = canonical.loc[(canonical["subject"] == SUBJECT) & (canonical["seed"] == 25)]
    if len(canonical) != 1 or str(canonical.iloc[0]["solution_id"]) != specification.representative_solution:
        raise ValueError("canonical Stage 2 record does not select seed25_solution047")

    front = pd.read_csv(front_path)
    selected = select_solution(front.to_dict("records"), front.to_dict("records"))
    if selected["solution_id"] != specification.representative_solution:
        raise ValueError("current selector disagrees with the canonical DayTrader representative")
    selected_front = front.loc[front["solution_id"] == specification.representative_solution]
    if len(selected_front) != 1:
        raise ValueError("approved solution is not unique in the seed-25 Pareto front")

    nodes = pd.read_csv(nodes_path)
    reference = pd.read_csv(reference_path)
    labels = pd.read_csv(target_path, compression="xz")
    target = labels.loc[
        labels["solution_id"] == specification.representative_solution,
        ["class_id", "class_name", "cluster_id"],
    ].copy()
    if len(nodes) != EXPECTED_CLASS_COUNT:
        raise ValueError(f"DayTrader class scope must contain {EXPECTED_CLASS_COUNT} classes")
    expected = set(nodes["class_id"].astype(str))
    for name, frame in (("Leiden", reference), ("Stage 2", target)):
        class_ids = frame["class_id"].astype(str)
        if class_ids.duplicated().any() or set(class_ids) != expected:
            raise ValueError(f"{name} partition does not cover each DayTrader class exactly once")

    exporter = _historical_exporter(root)
    reference_raw = dict(zip(reference["class_id"].astype(str), reference["cluster_id"].astype(str), strict=True))
    target_raw = dict(zip(target["class_id"].astype(str), target["cluster_id"].astype(str), strict=True))
    reference_display = exporter.canonical_clusters(reference_raw, "L")
    target_display = exporter.canonical_clusters(target_raw, "S")
    reference_members = _cluster_members(reference_display)
    target_members = _cluster_members(target_display)
    if len(reference_members) != EXPECTED_REFERENCE_CLUSTERS or len(target_members) != EXPECTED_TARGET_CLUSTERS:
        raise ValueError("DayTrader transition cluster counts changed from the approved 11-to-9 scope")

    matched_raw = exporter.maximum_overlap_matching(target_raw, reference_raw)
    reference_display_by_raw = {
        raw_id: reference_display[next(class_id for class_id, value in reference_raw.items() if value == raw_id)]
        for raw_id in sorted(set(reference_raw.values()))
    }
    target_display_by_raw = {
        raw_id: target_display[next(class_id for class_id, value in target_raw.items() if value == raw_id)]
        for raw_id in sorted(set(target_raw.values()))
    }
    aligned_reference = {
        target_display_by_raw[target_raw_id]: (
            None if reference_raw_id is None else reference_display_by_raw[reference_raw_id]
        )
        for target_raw_id, reference_raw_id in matched_raw.items()
    }
    changed = sum(
        matched_raw[target_raw[class_id]] != reference_raw[class_id]
        for class_id in sorted(expected)
    )

    shared: dict[tuple[str, str], list[str]] = {}
    for class_id in sorted(expected):
        key = (reference_display[class_id], target_display[class_id])
        shared.setdefault(key, []).append(class_id)
    maximum_shared = max(len(values) for values in shared.values())
    widths = config.style["transition_flow"]
    minimum_width = float(widths["line_width_min"])
    maximum_width = float(widths["line_width_max"])

    source_order = {display_id: int(display_id[1:]) for display_id in reference_members}
    target_barycentres = {
        display_id: sum(
            source_order[source] * len(classes)
            for (source, target_id), classes in shared.items()
            if target_id == display_id
        ) / len(target_members[display_id])
        for display_id in target_members
    }
    ordered_targets = sorted(
        target_members,
        key=lambda display_id: (
            target_barycentres[display_id],
            target_members[display_id],
        ),
    )
    target_order = {display_id: index for index, display_id in enumerate(ordered_targets, start=1)}

    palette = tuple(config.style["cluster_palette"])
    if len(palette) < EXPECTED_REFERENCE_CLUSTERS:
        raise ValueError("cluster palette must provide a distinct entry for every Leiden cluster")
    source_colors = {f"L{index}": palette[index - 1] for index in range(1, EXPECTED_REFERENCE_CLUSTERS + 1)}
    unused_colors = [color for color in palette if color not in source_colors.values()]
    extra_index = 0
    target_colors: dict[str, str] = {}
    for display_id in sorted(target_members):
        aligned = aligned_reference[display_id]
        if aligned is not None:
            target_colors[display_id] = source_colors[aligned]
        else:
            if not unused_colors:
                raise ValueError("no stable unused cluster colour remains for an unmatched target cluster")
            target_colors[display_id] = unused_colors[extra_index]
            extra_index += 1

    reference_clusters = tuple(
        Cluster(display_id, reference_members[display_id], source_order[display_id], source_colors[display_id])
        for display_id in sorted(reference_members, key=source_order.get)
    )
    target_clusters = tuple(
        Cluster(
            display_id,
            target_members[display_id],
            target_order[display_id],
            target_colors[display_id],
            aligned_reference[display_id],
        )
        for display_id in ordered_targets
    )
    flows = tuple(
        Flow(
            source,
            target_id,
            tuple(sorted(classes)),
            flow_penwidth(len(classes), maximum_shared, minimum_width, maximum_width),
        )
        for (source, target_id), classes in sorted(
            shared.items(), key=lambda item: (source_order[item[0][0]], target_order[item[0][1]])
        )
    )
    ari, nmi = partition_similarity(nodes, target, reference)
    if (
        len(flows) != EXPECTED_FLOW_COUNT
        or maximum_shared != EXPECTED_MAX_FLOW
        or sum(flow.count == 1 for flow in flows) != EXPECTED_SINGLETON_FLOWS
        or changed != EXPECTED_CHANGED_CLASSES
    ):
        raise ValueError("DayTrader transition overlap invariants changed from the approved audit")
    return TransitionData(
        seed=25,
        solution_id=specification.representative_solution,
        reference_path=_relative(reference_path, root),
        target_path=_relative(target_path, root),
        class_count=EXPECTED_CLASS_COUNT,
        ari=ari,
        nmi=nmi,
        changed_class_count=changed,
        reference_clusters=reference_clusters,
        target_clusters=target_clusters,
        flows=flows,
    )


def transition_csv(data: TransitionData) -> str:
    """Serialize deterministic figure-specific flow data."""

    source = {cluster.display_id: cluster for cluster in data.reference_clusters}
    target = {cluster.display_id: cluster for cluster in data.target_clusters}
    fieldnames = (
        "subject", "seed", "solution_id", "class_count", "reference_partition",
        "target_partition", "reference_cluster_count", "target_cluster_count", "ari", "nmi",
        "changed_class_count", "non_zero_flow_count", "edge_width_meaning", "source_cluster",
        "target_cluster", "shared_class_count", "shared_classes", "source_cluster_size",
        "target_cluster_size", "source_canonical_signature", "target_canonical_signature",
        "source_display_order", "target_display_order", "target_aligned_reference", "flow_penwidth",
    )
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for flow in data.flows:
        source_cluster = source[flow.source]
        target_cluster = target[flow.target]
        writer.writerow({
            "subject": SUBJECT,
            "seed": data.seed,
            "solution_id": data.solution_id,
            "class_count": data.class_count,
            "reference_partition": data.reference_path,
            "target_partition": data.target_path,
            "reference_cluster_count": len(data.reference_clusters),
            "target_cluster_count": len(data.target_clusters),
            "ari": format(data.ari, ".12g"),
            "nmi": format(data.nmi, ".12g"),
            "changed_class_count": data.changed_class_count,
            "non_zero_flow_count": len(data.flows),
            "edge_width_meaning": "shared_class_count",
            "source_cluster": flow.source,
            "target_cluster": flow.target,
            "shared_class_count": flow.count,
            "shared_classes": json.dumps(flow.shared_classes, separators=(",", ":")),
            "source_cluster_size": len(source_cluster.members),
            "target_cluster_size": len(target_cluster.members),
            "source_canonical_signature": json.dumps(source_cluster.members, separators=(",", ":")),
            "target_canonical_signature": json.dumps(target_cluster.members, separators=(",", ":")),
            "source_display_order": source_cluster.display_order,
            "target_display_order": target_cluster.display_order,
            "target_aligned_reference": target_cluster.aligned_reference or "",
            "flow_penwidth": format(flow.penwidth, ".12g"),
        })
    return buffer.getvalue()


def transition_dot(config: VisualizationConfig, data: TransitionData) -> str:
    """Return deterministic DOT for the complete 15-flow transition."""

    specification = config.figures[FIGURE_ID]
    style = config.style
    node_style = style["node"]
    flow_style = style["transition_flow"]
    graph_style = style["graph"]
    font = style["fonts"]["family"]
    page = style["page_profiles"][specification.destination]
    lines = [
        f"digraph {dot_quote(specification.title)} {{",
        "  graph " + stable_attributes({
            "bgcolor": graph_style["background"],
            "fontname": font,
            "fontsize": style["fonts"]["edge_size"],
            "label": "Edge width represents shared class count (1-13 classes)",
            "labelloc": "b",
            "margin": graph_style["margin"],
            "nodesep": 0.03,
            "outputorder": "edgesfirst",
            "pad": graph_style["pad"],
            "rankdir": "LR",
            "ranksep": 3.0,
            "size": f"{page['width_in']},{page['height_in']}",
            "splines": "spline",
        }) + ";",
        "  node " + stable_attributes({
            "fillcolor": node_style["fillcolor"],
            "fontname": font,
            "fontsize": style["fonts"]["node_size"] - 1,
            "height": 0.34,
            "margin": "0.08,0.03",
            "penwidth": 1.5,
            "shape": node_style["shape"],
            "style": node_style["style"],
            "width": 1.05,
        }) + ";",
        "",
        '  "reference_header" ' + stable_attributes({
            "color": "transparent", "fillcolor": "transparent", "fontname": font,
            "fontsize": style["fonts"]["title_size"] - 1,
            "label": "Leiden baseline\n11 clusters", "shape": "plain", "style": "",
        }) + ";",
        '  "target_header" ' + stable_attributes({
            "color": "transparent", "fillcolor": "transparent", "fontname": font,
            "fontsize": style["fonts"]["title_size"] - 1,
            "label": "Stage 2 representative\n9 clusters - seed 25", "shape": "plain", "style": "",
        }) + ";",
    ]
    for cluster in data.reference_clusters:
        lines.append(
            f"  {dot_quote(cluster.display_id)} " + stable_attributes({
                "color": cluster.color,
                "label": (
                    f"{cluster.display_id}\n{len(cluster.members)} "
                    f"class{'es' if len(cluster.members) != 1 else ''}"
                ),
                "tooltip": "; ".join(cluster.members),
            }) + ";"
        )
    for cluster in data.target_clusters:
        lines.append(
            f"  {dot_quote(cluster.display_id)} " + stable_attributes({
                "color": cluster.color,
                "label": (
                    f"{cluster.display_id}\n{len(cluster.members)} "
                    f"class{'es' if len(cluster.members) != 1 else ''}"
                ),
                "tooltip": "; ".join(cluster.members),
            }) + ";"
        )
    reference_order = ["reference_header", *(cluster.display_id for cluster in data.reference_clusters)]
    target_order = ["target_header", *(cluster.display_id for cluster in data.target_clusters)]
    lines.extend((
        "",
        "  { rank=same; " + "; ".join(dot_quote(node) for node in reference_order) + "; }",
        "  { rank=same; " + "; ".join(dot_quote(node) for node in target_order) + "; }",
        "",
    ))
    invisible = stable_attributes({"arrowhead": "none", "style": "invis", "weight": 100})
    for order in (reference_order, target_order):
        for left, right in zip(order, order[1:]):
            lines.append(f"  {dot_quote(left)} -> {dot_quote(right)} {invisible};")
    lines.append("")
    for flow in data.flows:
        tooltip = f"{flow.count} shared class{'es' if flow.count != 1 else ''}: " + "; ".join(flow.shared_classes)
        lines.append(
            f"  {dot_quote(flow.source)} -> {dot_quote(flow.target)} " + stable_attributes({
                "arrowhead": "none",
                "color": flow_style["color"],
                "penwidth": flow.penwidth,
                "tooltip": tooltip,
            }) + ";"
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def _targets(config: VisualizationConfig, output_root: Path | None) -> tuple[dict[str, Path], Path, Path | None]:
    if output_root is None:
        targets = {
            "data": config.output.data / STAGE_DIRECTORY / f"{BASENAME}.csv",
            "dot": config.output.dot / STAGE_DIRECTORY / f"{BASENAME}.dot",
            "svg": config.output.svg / STAGE_DIRECTORY / f"{BASENAME}.svg",
            "pdf": config.output.pdf / STAGE_DIRECTORY / f"{BASENAME}.pdf",
            "provenance": config.output.data / STAGE_DIRECTORY / f"{BASENAME}.provenance.json",
        }
        return targets, config.repository_root / "reports/figures/manifest.json", None
    root = output_root.resolve()
    targets = {
        "data": root / "data" / STAGE_DIRECTORY / f"{BASENAME}.csv",
        "dot": root / "source" / STAGE_DIRECTORY / f"{BASENAME}.dot",
        "svg": root / "preview" / STAGE_DIRECTORY / f"{BASENAME}.svg",
        "pdf": root / "pdf" / STAGE_DIRECTORY / f"{BASENAME}.pdf",
        "provenance": root / "data" / STAGE_DIRECTORY / f"{BASENAME}.provenance.json",
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
    if manifest_path.exists():
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        document = {"schema_version": 1, "figures": {}}
    if document.get("schema_version") != 1 or not isinstance(document.get("figures"), dict):
        raise ValueError("figure manifest must be a schema-version 1 catalogue")
    specification = config.figures[FIGURE_ID]
    document["figures"][FIGURE_ID] = {
        "destination": specification.destination,
        "formats": list(specification.formats),
        "generated_at": generated_at,
        "generator": specification.generator,
        "inputs": list(specification.inputs),
        "outputs": {
            name: _relative(path, config.repository_root, artifact_root)
            for name, path in sorted(targets.items())
        },
        "representative_seed": specification.representative_seed,
        "representative_solution": specification.representative_solution,
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
    """Build only the registered DayTrader Stage 2 transition figure."""

    specification = config.figures.get(FIGURE_ID)
    if specification is None or not specification.enabled:
        raise ValueError(f"figure is not registered and enabled: {FIGURE_ID}")
    if specification.formats != ("dot", "svg", "pdf"):
        raise ValueError(f"figure formats must be dot, svg, and pdf: {FIGURE_ID}")
    root_override = None if output_root is None else Path(output_root)
    targets, default_manifest, artifact_root = _targets(config, root_override)
    manifest = default_manifest if manifest_path is None else Path(manifest_path)
    for path in (*targets.values(), manifest):
        path.parent.mkdir(parents=True, exist_ok=True)
    data = prepare_transition_data(config)

    staging_parent = artifact_root or (config.repository_root / "reports/figures")
    with tempfile.TemporaryDirectory(prefix=f".{FIGURE_ID}.", dir=staging_parent) as temporary:
        stage = Path(temporary)
        staged = {
            "data": stage / "figure.csv",
            "dot": stage / "figure.dot",
            "svg": stage / "figure.svg",
            "pdf": stage / "figure.pdf",
            "provenance": stage / "figure.provenance.json",
        }
        staged["data"].write_text(transition_csv(data), encoding="utf-8", newline="\n")
        write_dot(staged["dot"], transition_dot(config, data))
        render_results = [
            renderer(GraphvizRenderRequest(staged["dot"], staged[output_format], output_format, "dot"))
            for output_format in ("svg", "pdf")
        ]
        for name in ("data", "dot", "svg", "pdf"):
            if not staged[name].is_file() or staged[name].stat().st_size == 0:
                raise ValueError(f"figure build did not create non-empty {name} output")
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
            dot_path=staged["dot"],
            graphviz_engine="dot",
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
        for name in ("data", "dot", "svg", "pdf", "provenance"):
            os.replace(staged[name], targets[name])
        os.replace(staged_manifest, manifest)
    return targets
