"""Cross-stage DayTrader local weighted-modularity cluster comparison."""

from __future__ import annotations

from collections.abc import Callable
import csv
from dataclasses import dataclass
from io import StringIO
import json
import math
import os
from pathlib import Path
import re
import tempfile

import pandas as pd

from evo_ms.visualization.dot import dot_quote, stable_attributes, write_dot
from evo_ms.visualization.layout import render_graphviz
from evo_ms.visualization.model import GraphvizRenderRequest, GraphvizRenderResult, VisualizationConfig
from evo_ms.visualization.operating_preference import (
    balance_partition_medoid,
    fixed_balance_selection,
    representative_provenance,
)
from evo_ms.visualization.provenance import build_provenance, sha256_file, write_json_atomic

FIGURE_ID = "stage123_daytrader_highest_lowest_clusters"
BASENAME = "daytrader_highest_lowest_clusters"
DIRECTORY = "cross_stage"
EXPECTED_CLASSES = 53
STAGE2_SEED = 25
STAGE2_SOLUTION = "seed25_solution047"
STAGE3_SEED = 25
STAGE3_SOLUTION = "seed25_solution026"


def _format_metric(value: float) -> str:
    """Format figure metrics without hiding meaningful small non-zero values."""

    if value != 0.0 and abs(value) < 0.0005:
        return f"{value:.2e}".replace("e-0", "e-").replace("e+0", "e+")
    return f"{value:.3f}"


@dataclass(frozen=True)
class ClusterProfile:
    stage: int
    seed: int
    solution_id: str
    partition_source: str
    cluster_id: str
    members: tuple[str, ...]
    internal_edges: tuple[tuple[str, str, float], ...]
    boundary_edges: tuple[tuple[str, str, float], ...]
    external: tuple[str, ...]
    internal_weight: float
    boundary_weight: float
    degree_sum: float
    contribution: float
    boundary_aggregates: tuple["BoundaryAggregate", ...]

    @property
    def rank_key(self) -> tuple[str, ...]:
        return self.members


@dataclass(frozen=True)
class FigureData:
    profiles: tuple[ClusterProfile, ...]
    selected: tuple[tuple[str, ClusterProfile], ...]
    formal_modularity: tuple[tuple[int, float], ...]


@dataclass(frozen=True)
class CompactPanel:
    """One focal structure, potentially shared by several stages."""

    role: str
    profiles: tuple[ClusterProfile, ...]

    @property
    def profile(self) -> ClusterProfile:
        return self.profiles[0]

    @property
    def stages(self) -> tuple[int, ...]:
        return tuple(profile.stage for profile in self.profiles)


@dataclass(frozen=True)
class BoundaryConnection:
    focal_class: str
    external_classes: tuple[str, ...]
    boundary_edge_count: int
    boundary_weight: float


@dataclass(frozen=True)
class BoundaryAggregate:
    external_cluster_id: str
    external_classes: tuple[str, ...]
    boundary_edge_count: int
    boundary_weight: float
    connected_focal_classes: tuple[str, ...]
    connections: tuple[BoundaryConnection, ...]


def _relative(path: Path, root: Path, artifact_root: Path | None = None) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(root):
        return resolved.relative_to(root).as_posix()
    if artifact_root is not None and resolved.is_relative_to(artifact_root):
        return resolved.relative_to(artifact_root).as_posix()
    raise ValueError(f"path outside repository/artifact root: {path}")


def _canonical_partition(frame: pd.DataFrame) -> pd.DataFrame:
    groups = sorted(tuple(sorted(group.class_id.astype(str))) for _, group in frame.groupby("cluster_id"))
    canonical = {class_id: f"C{index:02d}" for index, members in enumerate(groups, 1) for class_id in members}
    output = frame[["class_id", "class_name"]].copy()
    output["cluster_id"] = output.class_id.astype(str).map(canonical)
    return output.sort_values("class_id").reset_index(drop=True)


def _partitions(root: Path) -> tuple[tuple[int, int, str, str, pd.DataFrame, float], ...]:
    stage1_path = "results/stage1/subjects/daytrader/leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv"
    stage1 = pd.read_csv(root / stage1_path)
    q1 = float(pd.read_csv(root / "results/stage1/subjects/daytrader/leiden_baseline/raw_reference_leiden/metrics/stage1_metrics.csv").iloc[0].modularity)
    stage2 = fixed_balance_selection(root, "daytrader", "stage2", STAGE2_SEED)
    stage3 = balance_partition_medoid(root, "daytrader", "stage3")
    if stage2.solution_id != STAGE2_SOLUTION:
        raise ValueError("expected DayTrader Stage 2 primary Balance-preference representative changed")
    if (stage3.seed, stage3.solution_id) != (STAGE3_SEED, STAGE3_SOLUTION):
        raise ValueError("expected DayTrader Stage 3 primary Balance-preference medoid changed")
    return ((1, 42, "stage1_seed42", stage1_path, stage1, q1),
            (2, stage2.seed, stage2.solution_id, stage2.partition_source, stage2.partition, stage2.weighted_modularity),
            (3, stage3.seed, stage3.solution_id, stage3.partition_source, stage3.partition, stage3.weighted_modularity))


def prepare_figure_data(config: VisualizationConfig) -> FigureData:
    root = config.repository_root
    nodes = pd.read_csv(root / "data/extracted/daytrader/class_nodes.csv")
    expected = set(nodes.class_id.astype(str))
    if len(nodes) != EXPECTED_CLASSES or len(expected) != EXPECTED_CLASSES:
        raise ValueError("DayTrader scope must contain exactly 53 unique classes")
    edges = pd.read_csv(root / "results/stage1/subjects/daytrader/leiden_baseline/raw_reference_leiden/graph/stage1_edges.csv")
    pairs = [tuple(sorted((str(row.source), str(row.target)))) for row in edges.itertuples()]
    if any(a == b for a, b in pairs) or len(pairs) != len(set(pairs)):
        raise ValueError("raw graph contains a self-loop or duplicate undirected edge")
    total = float(edges.raw_weight.sum())
    degree = {class_id: 0.0 for class_id in expected}
    for row in edges.itertuples():
        degree[str(row.source)] += float(row.raw_weight)
        degree[str(row.target)] += float(row.raw_weight)
    profiles = []
    formal = []
    for stage, seed, solution, source, raw_partition, formal_q in _partitions(root):
        ids = raw_partition.class_id.astype(str)
        if ids.duplicated().any() or set(ids) != expected:
            raise ValueError(f"Stage {stage} partition does not cover all 53 classes exactly once")
        partition = _canonical_partition(raw_partition)
        cluster_by_class = dict(zip(partition.class_id.astype(str), partition.cluster_id.astype(str), strict=True))
        if not partition.equals(_canonical_partition(raw_partition.sample(frac=1, random_state=42))):
            raise ValueError("cluster canonicalisation is not deterministic")
        for cluster_id, group in partition.groupby("cluster_id", sort=True):
            members = tuple(sorted(group.class_id.astype(str)))
            member_set = set(members)
            internal = tuple(sorted((min(str(e.source), str(e.target)), max(str(e.source), str(e.target)), float(e.raw_weight))
                                    for e in edges.itertuples() if str(e.source) in member_set and str(e.target) in member_set))
            boundary = tuple(sorted((min(str(e.source), str(e.target)), max(str(e.source), str(e.target)), float(e.raw_weight))
                                    for e in edges.itertuples() if (str(e.source) in member_set) ^ (str(e.target) in member_set)))
            external = tuple(sorted({node for left, right, _ in boundary for node in (left, right)} - member_set))
            iw = sum(edge[2] for edge in internal); bw = sum(edge[2] for edge in boundary)
            strength = sum(degree[class_id] for class_id in members)
            q = iw / total - (strength / (2.0 * total)) ** 2
            grouped: dict[str, list[tuple[str, str, float]]] = {}
            for left, right, weight in boundary:
                focal, outside = (left, right) if left in member_set else (right, left)
                grouped.setdefault(cluster_by_class[outside], []).append((focal, outside, weight))
            aggregates = []
            for external_cluster_id in sorted(grouped):
                records = grouped[external_cluster_id]
                by_focal: dict[str, list[tuple[str, float]]] = {}
                for focal, outside, weight in records:
                    by_focal.setdefault(focal, []).append((outside, weight))
                connections = tuple(
                    BoundaryConnection(
                        focal,
                        tuple(sorted({outside for outside, _weight in by_focal[focal]})),
                        len(by_focal[focal]),
                        sum(weight for _outside, weight in by_focal[focal]),
                    )
                    for focal in sorted(by_focal)
                )
                aggregates.append(BoundaryAggregate(
                    external_cluster_id,
                    tuple(sorted({outside for _focal, outside, _weight in records})),
                    len(records),
                    sum(weight for _focal, _outside, weight in records),
                    tuple(sorted(by_focal)),
                    connections,
                ))
            profiles.append(ClusterProfile(stage, seed, solution, source, str(cluster_id), members, internal, boundary,
                                           external, iw, bw, strength, q, tuple(aggregates)))
        stage_profiles = [profile for profile in profiles if profile.stage == stage]
        reconstructed = sum(profile.contribution for profile in stage_profiles)
        if abs(reconstructed - formal_q) > 1e-12:
            raise ValueError(f"Stage {stage} local contributions do not reconstruct formal modularity")
        formal.append((stage, formal_q))
    selected = []
    for stage in (1, 2, 3):
        candidates = [profile for profile in profiles if profile.stage == stage]
        selected.append(("highest", sorted(candidates, key=lambda p: (-p.contribution, p.rank_key))[0]))
        selected.append(("lowest", sorted(candidates, key=lambda p: (p.contribution, p.rank_key))[0]))
    return FigureData(tuple(profiles), tuple(selected), tuple(formal))


PROFILE_FIELDS = ("stage", "cluster_id", "class_count", "member_classes", "internal_edge_count", "internal_edges", "internal_weight",
                  "boundary_edge_count", "boundary_weight", "weighted_degree_sum", "local_modularity_contribution",
                  "boundary_edges", "external_classes", "representative_seed", "representative_solution_id", "partition_source")


def _row(profile: ClusterProfile) -> dict[str, object]:
    return {"stage": profile.stage, "cluster_id": profile.cluster_id, "class_count": len(profile.members),
            "member_classes": json.dumps(profile.members, separators=(",", ":")), "internal_edge_count": len(profile.internal_edges),
            "internal_edges": json.dumps(profile.internal_edges, separators=(",", ":")),
            "internal_weight": format(profile.internal_weight, ".12g"), "boundary_edge_count": len(profile.boundary_edges),
            "boundary_weight": format(profile.boundary_weight, ".12g"), "weighted_degree_sum": format(profile.degree_sum, ".12g"),
            "local_modularity_contribution": format(profile.contribution, ".12g"),
            "boundary_edges": json.dumps(profile.boundary_edges, separators=(",", ":")),
            "external_classes": json.dumps(profile.external, separators=(",", ":")), "representative_seed": profile.seed,
            "representative_solution_id": profile.solution_id, "partition_source": profile.partition_source}


def profiles_csv(data: FigureData) -> str:
    buffer = StringIO(newline=""); writer = csv.DictWriter(buffer, fieldnames=PROFILE_FIELDS, lineterminator="\n")
    writer.writeheader()
    for profile in sorted(data.profiles, key=lambda p: (p.stage, p.cluster_id)):
        writer.writerow(_row(profile))
    return buffer.getvalue()


def selected_csv(data: FigureData) -> str:
    fields = ("stage", "rank_role", *PROFILE_FIELDS[1:])
    buffer = StringIO(newline=""); writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for role, profile in data.selected:
        writer.writerow({"rank_role": role, **_row(profile)})
    return buffer.getvalue()


AGGREGATION_FIELDS = ("stage", "rank_role", "focal_cluster_id", "external_cluster_id",
                      "external_class_count", "external_classes", "boundary_edge_count", "boundary_weight",
                      "connected_focal_classes")


def boundary_aggregation_csv(data: FigureData) -> str:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=AGGREGATION_FIELDS, lineterminator="\n")
    writer.writeheader()
    for role, profile in data.selected:
        for aggregate in profile.boundary_aggregates:
            writer.writerow({
                "stage": profile.stage,
                "rank_role": role,
                "focal_cluster_id": profile.cluster_id,
                "external_cluster_id": aggregate.external_cluster_id,
                "external_class_count": len(aggregate.external_classes),
                "external_classes": json.dumps(aggregate.external_classes, separators=(",", ":")),
                "boundary_edge_count": aggregate.boundary_edge_count,
                "boundary_weight": format(aggregate.boundary_weight, ".12g"),
                "connected_focal_classes": json.dumps(aggregate.connected_focal_classes, separators=(",", ":")),
            })
    return buffer.getvalue()


def _grid(items: tuple[str, ...], columns: tuple[float, ...]) -> dict[str, tuple[float, float]]:
    if not items:
        return {}
    rows = math.ceil(len(items) / len(columns))
    spacing = 16.0 if rows > 1 else 0.0
    top = spacing * (rows - 1) / 2
    return {item: (columns[index % len(columns)], top - spacing * (index // len(columns)))
            for index, item in enumerate(items)}


def _layout(profile: ClusterProfile, seed: int = 42) -> dict[str, tuple[float, float]]:
    """Return an algorithmic, non-edited comparison grid for fixed neato assembly."""

    if seed != 42:
        raise ValueError("formal panel layout seed must remain 42")
    if len(profile.members) == 1 and not profile.boundary_aggregates:
        return {profile.members[0]: (0.0, -8.0)}
    focal_columns = (-88.0, -45.0) if len(profile.members) > 7 else (-68.0,)
    summaries = tuple(aggregate.external_cluster_id for aggregate in profile.boundary_aggregates)
    external_columns = (55.0, 98.0) if len(summaries) > 3 else (78.0,)
    return {**_grid(profile.members, focal_columns), **_grid(summaries, external_columns)}


def boundary_penwidth(weight: float, maximum_weight: float, minimum: float, maximum: float) -> float:
    if weight <= 0 or maximum_weight <= 0 or weight > maximum_weight:
        raise ValueError("boundary weights must be positive and bounded by the panel maximum")
    if minimum <= 0 or maximum < minimum:
        raise ValueError("boundary width bounds are invalid")
    return minimum + (maximum - minimum) * math.sqrt(weight / maximum_weight)


def _wrapped_simple_name(class_id: str) -> str:
    simple = class_id.rsplit('.', 1)[-1]
    parts = re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+", simple) or [simple]
    lines: list[str] = []
    current = ""
    for part in parts:
        if current and len(current) + len(part) > 13:
            lines.append(current)
            current = part
        else:
            current += part
    if current:
        lines.append(current)
    return "\n".join(lines)


def _focal_structure_signature(profile: ClusterProfile) -> tuple[object, ...]:
    """Identify exactly repeatable focal content in the fixed raw graph.

    External clusters are deliberately not part of the signature: the compact
    figure reports the complete boundary edge set as one context summary rather
    than drawing stage-specific external-cluster subdivisions.
    """

    return (
        profile.members,
        profile.internal_edges,
        profile.boundary_edges,
        profile.internal_weight,
        profile.boundary_weight,
        profile.contribution,
    )


def compact_panels(data: FigureData) -> tuple[CompactPanel, ...]:
    panels: list[CompactPanel] = []
    for role in ("highest", "lowest"):
        groups: dict[tuple[object, ...], list[ClusterProfile]] = {}
        for selected_role, profile in data.selected:
            if selected_role == role:
                groups.setdefault(_focal_structure_signature(profile), []).append(profile)
        panels.extend(
            CompactPanel(role, tuple(profiles))
            for profiles in sorted(groups.values(), key=lambda values: values[0].stage)
        )
    return tuple(panels)


def _stage_label(stages: tuple[int, ...]) -> str:
    if stages == (1, 2, 3):
        return "Stages 1-3"
    if len(stages) == 2:
        return f"Stages {stages[0]} and {stages[1]}"
    return f"Stage {stages[0]}"


def _panel_geometry(panel_count: int) -> tuple[tuple[float, float], ...]:
    if panel_count == 1:
        return ((225.0, 335.0),)
    if panel_count == 2:
        return ((302.0, 176.0), (111.0, 174.0))
    raise ValueError("compact comparison supports one or two structures per role")


def _compact_node_layout(
    profile: ClusterProfile,
    *,
    centre_x: float,
    centre_y: float,
    panel_height: float,
) -> dict[str, tuple[float, float]]:
    members = profile.members
    columns = 2 if len(members) > 5 else 1
    rows = math.ceil(len(members) / columns)
    x_values = (-84.0, -30.0) if columns == 2 else (-49.0,)
    body_top = centre_y + panel_height / 2 - 72.0
    body_bottom = centre_y - panel_height / 2 + 28.0
    spacing = 0.0 if rows == 1 else min(25.0, (body_top - body_bottom) / (rows - 1))
    used_height = spacing * (rows - 1)
    start_y = centre_y + used_height / 2 - 8.0
    return {
        member: (centre_x + x_values[index % columns], start_y - spacing * (index // columns))
        for index, member in enumerate(members)
    }


def figure_dot(
    config: VisualizationConfig,
    data: FigureData,
    *,
    figure_id: str = FIGURE_ID,
    comparison_note: str | None = "Stage 2 and Stage 3 representatives use the primary Balance preference.",
) -> str:
    spec = config.figures[figure_id]
    style = config.style["cluster_contribution_comparison"]
    font = config.style["fonts"]["family"]
    x_centres = {"highest": 125.0, "lowest": 375.0}
    panels = compact_panels(data)
    by_role = {
        role: tuple(panel for panel in panels if panel.role == role)
        for role in ("highest", "lowest")
    }
    lines = [
        f"graph {dot_quote(spec.title)} {{",
        "  graph "
        + stable_attributes(
            {
                "bb": "0,0,500,460",
                "bgcolor": "white",
                "margin": 0,
                "outputorder": "edgesfirst",
                "overlap": True,
                "pad": 0.02,
                "size": "6.944,6.389!",
                "splines": "true",
                "start": 42,
            }
        )
        + ";",
        "  node "
        + stable_attributes(
            {
                "fontname": font,
                "fontsize": style["node_font_size"],
                "height": 0.20,
                "margin": "0.035,0.018",
                "shape": "box",
                "style": "rounded,filled",
                "width": 0.1,
            }
        )
        + ";",
        "  edge " + stable_attributes({"fontname": font, "fontsize": 6}) + ";",
    ]
    plain = {
        "color": "transparent",
        "fillcolor": "transparent",
        "fontname": font,
        "shape": "plain",
        "style": "",
    }
    for role, label in (("highest", "Highest-contributing cluster"), ("lowest", "Lowest-contributing cluster")):
        cx = x_centres[role]
        lines.append(
            f"  {dot_quote(role + '_column_title')} "
            + stable_attributes({**plain, "fontsize": 11, "fontname": f"{font} Bold", "label": label, "pos": f"{cx},444!"})
            + ";"
        )
        for group_index, (panel, (cy, panel_height)) in enumerate(
            zip(by_role[role], _panel_geometry(len(by_role[role])), strict=True), 1
        ):
            profile = panel.profile
            prefix = f"{role[0]}g{group_index}"
            lines.append(
                f"  {dot_quote(prefix + '_panel')} "
                + stable_attributes(
                    {
                        "color": "#B8B8B8",
                        "fixedsize": True,
                        "height": panel_height / 72,
                        "label": "",
                        "penwidth": 0.8,
                        "pos": f"{cx},{cy}!",
                        "shape": "box",
                        "style": "solid",
                        "width": 236 / 72,
                    }
                )
                + ";"
            )
            stages = _stage_label(panel.stages)
            shared = " - identical focal structure" if len(panel.stages) > 1 else ""
            title = f"{stages}{shared}\nCluster {profile.cluster_id}"
            metric = (
                f"n = {len(profile.members)}   q_c = {_format_metric(profile.contribution)}   "
                f"W_in = {profile.internal_weight:.0f}   W_boundary = {profile.boundary_weight:.0f}"
            )
            top = cy + panel_height / 2
            lines.append(
                f"  {dot_quote(prefix + '_title')} "
                + stable_attributes({**plain, "fontsize": style["title_font_size"], "label": title, "pos": f"{cx},{top - 18}!"})
                + ";"
            )
            lines.append(
                f"  {dot_quote(prefix + '_metric')} "
                + stable_attributes({**plain, "fontsize": style["metric_font_size"], "label": metric, "pos": f"{cx},{top - 45}!"})
                + ";"
            )
            positions = _compact_node_layout(
                profile, centre_x=cx, centre_y=cy, panel_height=panel_height
            )
            ids = {
                class_id: f"{prefix}_f{index:03d}"
                for index, class_id in enumerate(profile.members, 1)
            }
            for class_id in profile.members:
                x, y = positions[class_id]
                lines.append(
                    f"  {dot_quote(ids[class_id])} "
                    + stable_attributes(
                        {
                            "color": style["focal_border"],
                            "fillcolor": style["focal_fill"],
                            "label": _wrapped_simple_name(class_id),
                            "penwidth": 1.1,
                            "pos": f"{x},{y}!",
                            "tooltip": class_id,
                        }
                    )
                    + ";"
                )
            for left, right, _weight in profile.internal_edges:
                lines.append(
                    f"  {dot_quote(ids[left])} -- {dot_quote(ids[right])} "
                    + stable_attributes(
                        {"color": style["internal_edge"], "penwidth": 0.7, "style": "solid"}
                    )
                    + ";"
                )
            if profile.boundary_edges:
                summary = (
                    f"Boundary context\n{len(profile.external)} external classes\n"
                    f"{len(profile.boundary_edges)} edges"
                )
                tooltip = "; ".join(profile.external)
                lines.append(
                    f"  {dot_quote(prefix + '_boundary')} "
                    + stable_attributes(
                        {
                            "color": style["external_border"],
                            "fillcolor": style["external_fill"],
                            "fontsize": 6.6,
                            "label": summary,
                            "penwidth": 0.8,
                            "pos": f"{cx + 72},{cy - 7}!",
                            "shape": "box",
                            "style": "rounded,dashed,filled",
                            "tooltip": tooltip,
                        }
                    )
                    + ";"
                )
            elif not profile.internal_edges:
                lines.append(
                    f"  {dot_quote(prefix + '_isolated')} "
                    + stable_attributes(
                        {
                            **plain,
                            "fontsize": 7,
                            "label": "Isolated singleton\nNo internal or boundary relations",
                            "pos": f"{cx + 60},{cy - 7}!",
                        }
                    )
                    + ";"
                )
    if comparison_note:
        lines.append(
            '  "comparison_note" '
            + stable_attributes(
                {
                    **plain,
                    "label": comparison_note + " Repeated focal structures are drawn once.",
                    "pos": "250,414!",
                    "fontsize": 6.6,
                }
            )
            + ";"
        )
    lines.append("}")
    return "\n".join(lines)+"\n"


def _targets(config: VisualizationConfig, output_root: Path | None):
    if output_root is None:
        targets={"profiles":config.output.data/DIRECTORY/"daytrader_cluster_profiles.csv",
                 "selected":config.output.data/DIRECTORY/"daytrader_highest_lowest_clusters.csv",
                 "aggregation":config.output.data/DIRECTORY/"daytrader_boundary_aggregation.csv",
                 "dot":config.output.dot/DIRECTORY/f"{BASENAME}.dot","svg":config.output.svg/DIRECTORY/f"{BASENAME}.svg",
                 "pdf":config.output.pdf/DIRECTORY/f"{BASENAME}.pdf","provenance":config.output.data/DIRECTORY/f"{BASENAME}.provenance.json"}
        return targets, config.repository_root/"reports/figures/manifest.json", None
    root=output_root.resolve(); targets={"profiles":root/"data"/DIRECTORY/"daytrader_cluster_profiles.csv",
        "selected":root/"data"/DIRECTORY/"daytrader_highest_lowest_clusters.csv","aggregation":root/"data"/DIRECTORY/"daytrader_boundary_aggregation.csv","dot":root/"source"/DIRECTORY/f"{BASENAME}.dot",
        "svg":root/"preview"/DIRECTORY/f"{BASENAME}.svg","pdf":root/"pdf"/DIRECTORY/f"{BASENAME}.pdf",
        "provenance":root/"data"/DIRECTORY/f"{BASENAME}.provenance.json"}
    return targets,root/"manifest.json",root


def build_figure(config: VisualizationConfig, *, output_root: str|Path|None=None, manifest_path: str|Path|None=None,
                 generated_at: str|None=None, git_commit: str|None=None, git_dirty: bool|None=None,
                 renderer: Callable[[GraphvizRenderRequest],GraphvizRenderResult]=render_graphviz) -> dict[str,Path]:
    spec=config.figures.get(FIGURE_ID)
    if spec is None or not spec.enabled or spec.formats != ("dot","svg","pdf"):
        raise ValueError(f"figure is not correctly registered: {FIGURE_ID}")
    targets,default_manifest,artifact_root=_targets(config,None if output_root is None else Path(output_root)); manifest=default_manifest if manifest_path is None else Path(manifest_path)
    for path in (*targets.values(),manifest): path.parent.mkdir(parents=True,exist_ok=True)
    data=prepare_figure_data(config); staging_parent=artifact_root or config.repository_root/"reports/figures"
    with tempfile.TemporaryDirectory(prefix=f".{FIGURE_ID}.",dir=staging_parent) as temporary:
        stage=Path(temporary); staged={name:stage/f"figure.{name}" for name in targets}; staged["provenance"]=stage/"figure.provenance.json"
        staged["profiles"].write_text(profiles_csv(data),encoding="utf-8",newline="\n"); staged["selected"].write_text(selected_csv(data),encoding="utf-8",newline="\n")
        staged["aggregation"].write_text(boundary_aggregation_csv(data),encoding="utf-8",newline="\n")
        write_dot(staged["dot"],figure_dot(config,data))
        renders=[renderer(GraphvizRenderRequest(staged["dot"],staged[fmt],fmt,"neato",fixed_coordinates=True)) for fmt in ("svg","pdf")]
        for name in ("profiles","selected","aggregation","dot","svg","pdf"):
            if not staged[name].is_file() or not staged[name].stat().st_size: raise ValueError(f"missing staged {name}")
        commands=tuple(("neato","-n2",f"-T{fmt}",str(targets["dot"]),"-o",str(targets[fmt])) for fmt in ("svg","pdf"))
        record=build_provenance(figure_id=FIGURE_ID,stage=spec.stage,generator="src/"+spec.generator.replace(".","/")+".py",repository_root=config.repository_root,
            input_files=(config.repository_root/path for path in spec.inputs),config_files=(config.figures_config_path,config.style_config_path),dot_path=staged["dot"],
            graphviz_engine="neato",graphviz_version=renders[0].version,render_commands=commands,generated_outputs=targets.values(),artifact_root=artifact_root,
            generated_at=generated_at,git_commit=git_commit,git_dirty=git_dirty)
        write_json_atomic(staged["provenance"], {
            **record.as_dict(),
            "operating_profile_representatives": representative_provenance(
                fixed_balance_selection(config.repository_root, "daytrader", "stage2", STAGE2_SEED),
                balance_partition_medoid(config.repository_root, "daytrader", "stage3"),
            ),
        })
        document=json.loads(manifest.read_text()) if manifest.exists() else {"schema_version":1,"figures":{}}
        if document.get("schema_version")!=1 or not isinstance(document.get("figures"),dict): raise ValueError("invalid figure manifest")
        document["figures"][FIGURE_ID]={"destination":spec.destination,"formats":list(spec.formats),"generated_at":record.generated_at,"generator":spec.generator,
            "inputs":list(spec.inputs),"metadata":dict(spec.metadata or {}),"outputs":{n:_relative(p,config.repository_root,artifact_root) for n,p in sorted(targets.items())},
            "sha256":{n:sha256_file(p) for n,p in sorted(staged.items())},"stage":spec.stage,"title":spec.title}
        staged_manifest=stage/"manifest.json"; write_json_atomic(staged_manifest,document)
        for name in targets: os.replace(staged[name],targets[name])
        os.replace(staged_manifest,manifest)
    return targets
