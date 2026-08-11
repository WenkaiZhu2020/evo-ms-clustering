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
        raise ValueError("authoritative DayTrader Stage 2 BALANCE representative changed")
    if (stage3.seed, stage3.solution_id) != (STAGE3_SEED, STAGE3_SOLUTION):
        raise ValueError("authoritative DayTrader Stage 3 BALANCE medoid changed")
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


def figure_dot(
    config: VisualizationConfig,
    data: FigureData,
    *,
    figure_id: str = FIGURE_ID,
    comparison_note: str | None = "Stage 2 and Stage 3 representatives use the authoritative BALANCE profile.",
) -> str:
    spec=config.figures[figure_id]; style=config.style["cluster_contribution_comparison"]; font=config.style["fonts"]["family"]
    x_centres={"highest":125.0,"lowest":375.0}; y_centres={1:600.0,2:385.0,3:170.0}
    lines=[f"graph {dot_quote(spec.title)} {{", "  graph "+stable_attributes({"bb":"0,0,500,730","bgcolor":"white","margin":0,"outputorder":"edgesfirst","overlap":True,"pad":0.02,"size":"6.944,10.139!","splines":"true","start":42})+";",
           "  node "+stable_attributes({"fontname":font,"fontsize":style["node_font_size"],"height":0.18,"margin":"0.025,0.012","shape":"box","style":"rounded,filled","width":0.1})+";",
           "  edge "+stable_attributes({"fontname":font,"fontsize":5})+";"]
    for panel_index,(role,profile) in enumerate(data.selected,1):
        cx=x_centres[role]; cy=y_centres[profile.stage]; prefix=f"p{profile.stage}{role[0]}"; local=_layout(profile)
        lines.append(f"  {dot_quote(prefix+'_panel')} "+stable_attributes({"color":"#B8B8B8","fixedsize":True,"height":style["panel_height_pt"]/72,"label":"","penwidth":0.8,"pos":f"{cx},{cy}!","shape":"box","style":"solid","width":style["panel_width_pt"]/72})+";")
        title=f"Stage {profile.stage}\n{role.capitalize()}-contributing cluster {profile.cluster_id}"
        metric=(f"n = {len(profile.members)}   q_c = {profile.contribution:.5f}\n"
                f"W_in = {profile.internal_weight:.0f}   W_boundary = {profile.boundary_weight:.0f}")
        plain={"color":"transparent","fillcolor":"transparent","fontname":font,"shape":"plain","style":""}
        lines.append(f"  {dot_quote(prefix+'_title')} "+stable_attributes({**plain,"fontsize":style["title_font_size"],"label":title,"pos":f"{cx},{cy+82}!"})+";")
        lines.append(f"  {dot_quote(prefix+'_metric')} "+stable_attributes({**plain,"fontsize":style["metric_font_size"],"label":metric,"pos":f"{cx},{cy+59}!"})+";")
        ids={class_id:f"{prefix}_f{i:03d}" for i,class_id in enumerate(profile.members,1)}
        summary_ids={aggregate.external_cluster_id:f"{prefix}_x{aggregate.external_cluster_id}" for aggregate in profile.boundary_aggregates}
        for class_id in profile.members:
            x,y=local[class_id]
            lines.append(f"  {dot_quote(ids[class_id])} "+stable_attributes({"color":style["focal_border"],"fillcolor":style["focal_fill"],"label":_wrapped_simple_name(class_id),"penwidth":1.1,"pos":f"{cx+x},{cy+y-12}!","tooltip":class_id})+";")
        for aggregate in profile.boundary_aggregates:
            x,y=local[aggregate.external_cluster_id]
            tooltip=(f"{aggregate.external_cluster_id}: {len(aggregate.external_classes)} external classes; "
                     f"{aggregate.boundary_edge_count} boundary edges; weight {aggregate.boundary_weight:g}; "
                     + "; ".join(aggregate.external_classes))
            label=f"External {aggregate.external_cluster_id}\n{len(aggregate.external_classes)} class{'es' if len(aggregate.external_classes) != 1 else ''}"
            lines.append(f"  {dot_quote(summary_ids[aggregate.external_cluster_id])} "+stable_attributes({"color":style["external_border"],"fillcolor":style["external_fill"],"label":label,"penwidth":0.8,"pos":f"{cx+x},{cy+y-12}!","shape":"box","style":"rounded,dashed,filled","tooltip":tooltip})+";")
        for left,right,_ in profile.internal_edges:
            lines.append(f"  {dot_quote(ids[left])} -- {dot_quote(ids[right])} "+stable_attributes({"color":style["internal_edge"],"penwidth":0.8,"style":"solid"})+";")
        connection_weights=[connection.boundary_weight for aggregate in profile.boundary_aggregates for connection in aggregate.connections]
        maximum_weight=max(connection_weights,default=0.0)
        for aggregate in profile.boundary_aggregates:
            for connection in aggregate.connections:
                width=boundary_penwidth(connection.boundary_weight,maximum_weight,float(style["boundary_width_min"]),float(style["boundary_width_max"]))
                tooltip=(f"{connection.boundary_edge_count} aggregated boundary edge(s); weight {connection.boundary_weight:g}; "
                         + "; ".join(connection.external_classes))
                lines.append(f"  {dot_quote(ids[connection.focal_class])} -- {dot_quote(summary_ids[aggregate.external_cluster_id])} "+stable_attributes({"color":style["boundary_edge"],"penwidth":width,"style":"dashed","tooltip":tooltip})+";")
        if not profile.internal_edges and not profile.boundary_edges:
            lines.append(f"  {dot_quote(prefix+'_isolated')} "+stable_attributes({**plain,"fontsize":6.2,"label":"Isolated singleton\nNo internal or boundary relations","pos":f"{cx},{cy-52}!"})+";")
    if comparison_note:
        lines.append('  "comparison_note" '+stable_attributes({"color":"transparent","fillcolor":"transparent","label":comparison_note,"pos":"250,57!","shape":"plain","style":"","fontsize":6.5})+";")
    lines.extend([
        '  "legend_focal" '+stable_attributes({"color":style["focal_border"],"fillcolor":style["focal_fill"],"label":"Focal-cluster class","pos":"60,29!"})+";",
        '  "legend_external" '+stable_attributes({"color":style["external_border"],"fillcolor":style["external_fill"],"label":"External-cluster summary","pos":"185,29!","shape":"box","style":"rounded,dashed,filled"})+";",
        '  "legend_i1" '+stable_attributes({"label":"","pos":"290,34!","shape":"point","width":0.04})+";",
        '  "legend_i2" '+stable_attributes({"label":"","pos":"320,34!","shape":"point","width":0.04})+";",
        '  "legend_b1" '+stable_attributes({"label":"","pos":"395,34!","shape":"point","width":0.04})+";",
        '  "legend_b2" '+stable_attributes({"label":"","pos":"425,34!","shape":"point","width":0.04})+";",
        '  "legend_internal" '+stable_attributes({"color":"transparent","fillcolor":"transparent","label":"Solid: internal","pos":"305,20!","shape":"plain","style":"","fontsize":6})+";",
        '  "legend_boundary" '+stable_attributes({"color":"transparent","fillcolor":"transparent","label":"Dashed: aggregated boundary\nwidth = boundary weight","pos":"410,17!","shape":"plain","style":"","fontsize":6})+";",
        '  "legend_i1" -- "legend_i2" '+stable_attributes({"color":style["internal_edge"],"style":"solid"})+";",
        '  "legend_b1" -- "legend_b2" '+stable_attributes({"color":style["boundary_edge"],"style":"dashed"})+";",
        "}"])
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
