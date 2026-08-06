"""Two package-level Xerces-J cluster-contribution appendix pages."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
import csv
from dataclasses import dataclass
from io import StringIO
import json
import math
import os
from pathlib import Path
import tempfile

import pandas as pd

from evo_ms.visualization.dot import dot_quote, stable_attributes, write_dot
from evo_ms.visualization.figures.stage123_daytrader_clusters import (
    BoundaryAggregate,
    BoundaryConnection,
    ClusterProfile,
    FigureData,
    _canonical_partition,
    _relative,
    profiles_csv,
    selected_csv,
)
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

FIGURE_IDS = {
    "stage13": "stage13_xerces_shared_highest_lowest_clusters",
    "stage2": "stage2_xerces_highest_lowest_clusters",
}
BASENAMES = {
    "stage13": "xerces_stage13_shared_highest_lowest_clusters",
    "stage2": "xerces_stage2_highest_lowest_clusters",
}
EXPECTED = {
    1: (42, "stage1_seed42", "C11", 118, 624, "C07", 1, 12),
    2: (21, "seed21_solution022", "C13", 115, 570, "C27", 2, 16),
    3: (22, "seed22_solution015", "C11", 118, 624, "C07", 1, 12),
}
DIRECTORY = "cross_stage"


@dataclass(frozen=True)
class PackageProfile:
    package_id: str
    package_name: str
    member_classes: tuple[str, ...]
    within_edge_count: int
    within_weight: float
    weighted_degree: float


@dataclass(frozen=True)
class PackageRelation:
    source_package: str
    target_package: str
    class_edge_count: int
    aggregated_weight: float


@dataclass(frozen=True)
class PackageBoundaryRelation:
    source_package: str
    external_cluster_id: str
    external_classes: tuple[str, ...]
    boundary_edge_count: int
    aggregated_weight: float


@dataclass(frozen=True)
class PackageAggregation:
    stage_label: str
    focal_cluster_id: str
    profiles: tuple[PackageProfile, ...]
    relations: tuple[PackageRelation, ...]
    boundary_relations: tuple[PackageBoundaryRelation, ...]
    class_to_package: tuple[tuple[str, str], ...]


def _partitions(root: Path):
    p1 = "results/stage1/subjects/xerces-j/leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv"
    p2 = "results/stage2/subjects/xerces-j/nsga/robustness_final_30seeds/seed_21/pareto_labels.csv.xz"
    p3 = "results/stage3/subjects/xerces-j/declaration_method_body/formal/seed_22/selected_partition.csv"
    stage1 = pd.read_csv(root / p1)
    q1 = float(
        pd.read_csv(
            root
            / "results/stage1/subjects/xerces-j/leiden_baseline/raw_reference_leiden/metrics/stage1_metrics.csv"
        ).iloc[0].modularity
    )
    canonical = pd.read_csv(
        root
        / "results/stage2/cross_subject/operating_profile/canonical_operating_solution_per_seed.csv"
    )
    record = canonical.loc[(canonical.subject == "xerces-j") & (canonical.seed == 21)]
    if len(record) != 1 or str(record.iloc[0].solution_id) != "seed21_solution022":
        raise ValueError("Xerces-J Stage 2 representative changed")
    labels = pd.read_csv(root / p2)
    stage2 = labels.loc[
        labels.solution_id == "seed21_solution022",
        ["class_id", "class_name", "cluster_id"],
    ].copy()
    payload = json.loads(
        (
            root
            / "results/stage3/subjects/xerces-j/declaration_method_body/formal/seed_22/selected_solution.json"
        ).read_text()
    )
    if (
        int(payload["seed"]) != 22
        or payload["selected_four_objective_row"]["solution_id"]
        != "seed22_solution015"
    ):
        raise ValueError("Xerces-J Stage 3 representative changed")
    stage3 = pd.read_csv(root / p3)
    posthoc = pd.read_csv(
        root
        / "results/stage3/subjects/xerces-j/declaration_method_body/formal/seed_22/posthoc_metrics.csv"
    )
    q3 = posthoc.loc[
        posthoc.solution_id == "seed22_solution015", "weighted_modularity"
    ]
    if len(q3) != 1:
        raise ValueError("Xerces-J Stage 3 modularity is not unique")
    return (
        (1, 42, "stage1_seed42", p1, stage1, q1),
        (
            2,
            21,
            "seed21_solution022",
            p2,
            stage2,
            float(record.iloc[0].weighted_modularity),
        ),
        (3, 22, "seed22_solution015", p3, stage3, float(q3.iloc[0])),
    )


def prepare_figure_data(config: VisualizationConfig) -> FigureData:
    root = config.repository_root
    nodes = pd.read_csv(root / "data/extracted/xerces-j/class_nodes.csv")
    expected = set(nodes.class_id.astype(str))
    if len(nodes) != 814 or len(expected) != 814:
        raise ValueError("Xerces-J scope must contain 814 unique classes")
    edges = pd.read_csv(
        root
        / "results/stage1/subjects/xerces-j/leiden_baseline/raw_reference_leiden/graph/stage1_edges.csv"
    )
    pairs = [tuple(sorted((str(e.source), str(e.target)))) for e in edges.itertuples()]
    if any(a == b for a, b in pairs) or len(pairs) != len(set(pairs)):
        raise ValueError("Xerces-J raw graph has invalid undirected edges")
    total = float(edges.raw_weight.sum())
    degree = {class_id: 0.0 for class_id in expected}
    for edge in edges.itertuples():
        degree[str(edge.source)] += float(edge.raw_weight)
        degree[str(edge.target)] += float(edge.raw_weight)
    profiles: list[ClusterProfile] = []
    formal = []
    for stage, seed, solution, source, raw, formal_q in _partitions(root):
        ids = raw.class_id.astype(str)
        if len(ids) != 814 or ids.duplicated().any() or set(ids) != expected:
            raise ValueError(f"Xerces-J Stage {stage} scope changed")
        partition = _canonical_partition(raw)
        cluster_map = dict(
            zip(
                partition.class_id.astype(str),
                partition.cluster_id.astype(str),
                strict=True,
            )
        )
        for cluster_id, group in partition.groupby("cluster_id", sort=True):
            members = tuple(sorted(group.class_id.astype(str)))
            member_set = set(members)
            internal = []
            boundary = []
            for edge in edges.itertuples():
                a, b, weight = (
                    str(edge.source),
                    str(edge.target),
                    float(edge.raw_weight),
                )
                if a in member_set and b in member_set:
                    internal.append((min(a, b), max(a, b), weight))
                elif (a in member_set) ^ (b in member_set):
                    boundary.append((min(a, b), max(a, b), weight))
            grouped: dict[str, list[tuple[str, str, float]]] = {}
            for a, b, weight in boundary:
                focal, outside = (a, b) if a in member_set else (b, a)
                grouped.setdefault(cluster_map[outside], []).append(
                    (focal, outside, weight)
                )
            aggregates = []
            for destination in sorted(grouped):
                records = grouped[destination]
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
                aggregates.append(
                    BoundaryAggregate(
                        destination,
                        tuple(sorted({outside for _focal, outside, _weight in records})),
                        len(records),
                        sum(weight for _focal, _outside, weight in records),
                        tuple(sorted(by_focal)),
                        connections,
                    )
                )
            internal_weight = sum(edge[2] for edge in internal)
            boundary_weight = sum(edge[2] for edge in boundary)
            strength = sum(degree[class_id] for class_id in members)
            contribution = internal_weight / total - (strength / (2 * total)) ** 2
            profiles.append(
                ClusterProfile(
                    stage,
                    seed,
                    solution,
                    source,
                    str(cluster_id),
                    members,
                    tuple(sorted(internal)),
                    tuple(sorted(boundary)),
                    tuple(
                        sorted(
                            {value for a, b, _weight in boundary for value in (a, b)}
                            - member_set
                        )
                    ),
                    internal_weight,
                    boundary_weight,
                    strength,
                    contribution,
                    tuple(aggregates),
                )
            )
        if (
            abs(
                sum(profile.contribution for profile in profiles if profile.stage == stage)
                - formal_q
            )
            > 1e-12
        ):
            raise ValueError(
                f"Xerces-J Stage {stage} modularity reconstruction failed"
            )
        formal.append((stage, formal_q))
    selected = []
    for stage in (1, 2, 3):
        candidates = [profile for profile in profiles if profile.stage == stage]
        selected.extend(
            (
                (
                    "highest",
                    sorted(
                        candidates,
                        key=lambda profile: (-profile.contribution, profile.rank_key),
                    )[0],
                ),
                (
                    "lowest",
                    sorted(
                        candidates,
                        key=lambda profile: (profile.contribution, profile.rank_key),
                    )[0],
                ),
            )
        )
    data = FigureData(tuple(profiles), tuple(selected), tuple(formal))
    for stage, expected_values in EXPECTED.items():
        seed, solution, high_id, high_n, high_edges, low_id, low_n, destinations = (
            expected_values
        )
        chosen = {
            role: profile
            for role, profile in data.selected
            if profile.stage == stage
        }
        high = chosen["highest"]
        low = chosen["lowest"]
        actual = (
            high.seed,
            high.solution_id,
            high.cluster_id,
            len(high.members),
            len(high.internal_edges),
            low.cluster_id,
            len(low.members),
            len(high.boundary_aggregates),
        )
        if actual != (
            seed,
            solution,
            high_id,
            high_n,
            high_edges,
            low_id,
            low_n,
            destinations,
        ):
            raise ValueError(f"accepted Xerces-J Stage {stage} selection changed")
    stage1_high = next(
        profile
        for role, profile in data.selected
        if role == "highest" and profile.stage == 1
    )
    stage3_high = next(
        profile
        for role, profile in data.selected
        if role == "highest" and profile.stage == 3
    )
    stage1_low = next(
        profile
        for role, profile in data.selected
        if role == "lowest" and profile.stage == 1
    )
    stage3_low = next(
        profile
        for role, profile in data.selected
        if role == "lowest" and profile.stage == 3
    )
    if stage1_high.members != stage3_high.members or stage1_low.members != stage3_low.members:
        raise ValueError("Xerces-J Stage 1 and Stage 3 selected memberships diverged")
    return data


def _csv(fields: Iterable[str], rows: Iterable[dict[str, object]]) -> str:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def package_aggregation(
    config: VisualizationConfig,
    stage_label: str,
    profile: ClusterProfile,
) -> PackageAggregation:
    nodes = pd.read_csv(
        config.repository_root / "data/extracted/xerces-j/class_nodes.csv"
    )
    package_by_class = dict(
        zip(nodes.class_id.astype(str), nodes.package.astype(str), strict=True)
    )
    package_names = sorted({package_by_class[class_id] for class_id in profile.members})
    package_ids = {
        package_name: f"P{index:02d}"
        for index, package_name in enumerate(package_names, 1)
    }
    members_by_package: dict[str, list[str]] = {name: [] for name in package_names}
    for class_id in profile.members:
        members_by_package[package_by_class[class_id]].append(class_id)

    within_count: defaultdict[str, int] = defaultdict(int)
    within_weight: defaultdict[str, float] = defaultdict(float)
    weighted_degree: defaultdict[str, float] = defaultdict(float)
    between: dict[tuple[str, str], list[float]] = {}
    for source, target, weight in profile.internal_edges:
        source_package = package_by_class[source]
        target_package = package_by_class[target]
        weighted_degree[source_package] += weight
        weighted_degree[target_package] += weight
        if source_package == target_package:
            within_count[source_package] += 1
            within_weight[source_package] += weight
        else:
            pair = tuple(sorted((source_package, target_package)))
            record = between.setdefault(pair, [0.0, 0.0])
            record[0] += 1
            record[1] += weight

    boundary: dict[tuple[str, str], dict[str, object]] = {}
    member_set = set(profile.members)
    destination_by_class = {
        outside: aggregate.external_cluster_id
        for aggregate in profile.boundary_aggregates
        for outside in aggregate.external_classes
    }
    for source, target, weight in profile.boundary_edges:
        focal, outside = (source, target) if source in member_set else (target, source)
        key = (package_by_class[focal], destination_by_class[outside])
        record = boundary.setdefault(
            key, {"count": 0, "weight": 0.0, "classes": set()}
        )
        record["count"] = int(record["count"]) + 1
        record["weight"] = float(record["weight"]) + weight
        classes = record["classes"]
        assert isinstance(classes, set)
        classes.add(outside)

    profiles = tuple(
        PackageProfile(
            package_ids[name],
            name,
            tuple(sorted(members_by_package[name])),
            within_count[name],
            within_weight[name],
            weighted_degree[name],
        )
        for name in package_names
    )
    relations = tuple(
        PackageRelation(
            package_ids[source],
            package_ids[target],
            int(values[0]),
            values[1],
        )
        for (source, target), values in sorted(between.items())
    )
    boundary_relations = tuple(
        PackageBoundaryRelation(
            package_ids[source],
            destination,
            tuple(sorted(record["classes"])),
            int(record["count"]),
            float(record["weight"]),
        )
        for (source, destination), record in sorted(boundary.items())
    )
    aggregation = PackageAggregation(
        stage_label,
        profile.cluster_id,
        profiles,
        relations,
        boundary_relations,
        tuple(
            sorted(
                (class_id, package_ids[package_by_class[class_id]])
                for class_id in profile.members
            )
        ),
    )
    _validate_aggregation(profile, aggregation)
    return aggregation


def _validate_aggregation(
    profile: ClusterProfile, aggregation: PackageAggregation
) -> None:
    assigned = [class_id for class_id, _package_id in aggregation.class_to_package]
    if assigned != sorted(profile.members) or len(set(assigned)) != len(profile.members):
        raise ValueError("focal class-to-package assignment is incomplete")
    internal_count = sum(item.within_edge_count for item in aggregation.profiles) + sum(
        item.class_edge_count for item in aggregation.relations
    )
    internal_weight = sum(item.within_weight for item in aggregation.profiles) + sum(
        item.aggregated_weight for item in aggregation.relations
    )
    if internal_count != len(profile.internal_edges) or not math.isclose(
        internal_weight, profile.internal_weight
    ):
        raise ValueError("package relations do not reconcile internal edges")
    if sum(item.boundary_edge_count for item in aggregation.boundary_relations) != len(
        profile.boundary_edges
    ) or not math.isclose(
        sum(item.aggregated_weight for item in aggregation.boundary_relations),
        profile.boundary_weight,
    ):
        raise ValueError("package boundary relations do not reconcile boundary edges")


def class_membership_csv(aggregation: PackageAggregation) -> str:
    profile_by_id = {profile.package_id: profile for profile in aggregation.profiles}
    return _csv(
        (
            "stage",
            "focal_cluster_id",
            "class_id",
            "fully_qualified_name",
            "simple_name",
            "package_id",
            "package_name",
        ),
        (
            {
                "stage": aggregation.stage_label,
                "focal_cluster_id": aggregation.focal_cluster_id,
                "class_id": class_id,
                "fully_qualified_name": class_id,
                "simple_name": class_id.rsplit(".", 1)[-1],
                "package_id": package_id,
                "package_name": profile_by_id[package_id].package_name,
            }
            for class_id, package_id in aggregation.class_to_package
        ),
    )


def package_profiles_csv(aggregation: PackageAggregation) -> str:
    return _csv(
        (
            "stage",
            "focal_cluster_id",
            "package_id",
            "package_name",
            "class_count",
            "member_classes",
            "within_package_edge_count",
            "within_package_weight",
            "weighted_degree_within_focal_cluster",
        ),
        (
            {
                "stage": aggregation.stage_label,
                "focal_cluster_id": aggregation.focal_cluster_id,
                "package_id": profile.package_id,
                "package_name": profile.package_name,
                "class_count": len(profile.member_classes),
                "member_classes": json.dumps(profile.member_classes, separators=(",", ":")),
                "within_package_edge_count": profile.within_edge_count,
                "within_package_weight": format(profile.within_weight, ".12g"),
                "weighted_degree_within_focal_cluster": format(
                    profile.weighted_degree, ".12g"
                ),
            }
            for profile in aggregation.profiles
        ),
    )


def package_relations_csv(aggregation: PackageAggregation) -> str:
    return _csv(
        (
            "stage",
            "focal_cluster_id",
            "source_package",
            "target_package",
            "class_edge_count",
            "aggregated_internal_weight",
        ),
        (
            {
                "stage": aggregation.stage_label,
                "focal_cluster_id": aggregation.focal_cluster_id,
                "source_package": relation.source_package,
                "target_package": relation.target_package,
                "class_edge_count": relation.class_edge_count,
                "aggregated_internal_weight": format(
                    relation.aggregated_weight, ".12g"
                ),
            }
            for relation in aggregation.relations
        ),
    )


def package_boundary_csv(aggregation: PackageAggregation) -> str:
    external_counts: defaultdict[str, set[str]] = defaultdict(set)
    for relation in aggregation.boundary_relations:
        external_counts[relation.external_cluster_id].update(relation.external_classes)
    return _csv(
        (
            "stage",
            "focal_cluster_id",
            "source_package",
            "external_cluster_id",
            "external_class_count",
            "external_classes",
            "boundary_edge_count",
            "aggregated_boundary_weight",
        ),
        (
            {
                "stage": aggregation.stage_label,
                "focal_cluster_id": aggregation.focal_cluster_id,
                "source_package": relation.source_package,
                "external_cluster_id": relation.external_cluster_id,
                "external_class_count": len(
                    external_counts[relation.external_cluster_id]
                ),
                "external_classes": json.dumps(
                    relation.external_classes, separators=(",", ":")
                ),
                "boundary_edge_count": relation.boundary_edge_count,
                "aggregated_boundary_weight": format(
                    relation.aggregated_weight, ".12g"
                ),
            }
            for relation in aggregation.boundary_relations
        ),
    )


def class_edges_csv(
    stage_label: str, role: str, profile: ClusterProfile, edge_kind: str
) -> str:
    edges = profile.internal_edges if edge_kind == "internal" else profile.boundary_edges
    return _csv(
        (
            "stage",
            "rank_role",
            "focal_cluster_id",
            "source_class",
            "target_class",
            "weight",
        ),
        (
            {
                "stage": stage_label,
                "rank_role": role,
                "focal_cluster_id": profile.cluster_id,
                "source_class": source,
                "target_class": target,
                "weight": format(weight, ".12g"),
            }
            for source, target, weight in edges
        ),
    )


def _package_label(package_name: str) -> str:
    prefix = "org.apache.xerces."
    return package_name[len(prefix) :] if package_name.startswith(prefix) else package_name


def _width(value: float, maximum: float, minimum: float = 0.7, top: float = 4.0) -> float:
    if maximum <= 0:
        return minimum
    return minimum + (top - minimum) * math.sqrt(value / maximum)


def _profile_for_page(data: FigureData, page: str, role: str) -> ClusterProfile:
    stage = 1 if page == "stage13" else 2
    return next(
        profile
        for selected_role, profile in data.selected
        if selected_role == role and profile.stage == stage
    )


def figure_dot(
    config: VisualizationConfig,
    page: str,
    high: ClusterProfile,
    low: ClusterProfile,
    aggregation: PackageAggregation,
) -> str:
    spec = config.figures[FIGURE_IDS[page]]
    package_names = {
        profile.package_id: profile.package_name for profile in aggregation.profiles
    }
    external_classes: defaultdict[str, set[str]] = defaultdict(set)
    for relation in aggregation.boundary_relations:
        external_classes[relation.external_cluster_id].update(relation.external_classes)
    max_internal = max(
        (relation.aggregated_weight for relation in aggregation.relations), default=1.0
    )
    max_boundary = max(
        (relation.aggregated_weight for relation in aggregation.boundary_relations),
        default=1.0,
    )
    frame_label = (
        f"{high.cluster_id} - Highest-contributing focal cluster\n"
        f"{len(high.members)} classes aggregated into {len(aggregation.profiles)} package nodes\n"
        f"q_c = {high.contribution:.6f}    W_in = {high.internal_weight:.0f}    "
        f"W_boundary = {high.boundary_weight:.0f}"
    )
    low_label = (
        f"{low.cluster_id} - Lowest-contributing cluster\n"
        f"{len(low.members)} {'class' if len(low.members) == 1 else 'classes'}    "
        f"q_c = {low.contribution:.6f}    W_in = {low.internal_weight:.0f}    "
        f"W_boundary = {low.boundary_weight:.0f}"
    )
    lines = [
        f"digraph {dot_quote(spec.title)} {{",
        "  graph "
        + stable_attributes(
            {
                "bgcolor": "white",
                "compound": True,
                "concentrate": True,
                "fontname": "Helvetica",
                "fontsize": 11,
                "label": spec.title,
                "labelloc": "t",
                "margin": 0.05,
                "newrank": True,
                "nodesep": 0.28,
                "outputorder": "edgesfirst",
                "pad": 0.12,
                "rankdir": "LR",
                "ranksep": 0.55,
                "ratio": "fill",
                "size": "11.1,7.3!",
                "splines": "polyline",
            }
        )
        + ";",
        "  node "
        + stable_attributes(
            {
                "fontname": "Helvetica",
                "fontsize": 8.5,
                "margin": "0.08,0.05",
                "shape": "box",
                "style": "rounded,filled",
            }
        )
        + ";",
        "  edge "
        + stable_attributes({"fontname": "Helvetica", "fontsize": 7})
        + ";",
        "  subgraph cluster_focal {",
        "    graph "
        + stable_attributes(
            {
                "color": "#4472A5",
                "fillcolor": "#F8FBFE",
                "fontcolor": "#17365D",
                "fontname": "Helvetica-Bold",
                "fontsize": 11,
                "label": frame_label,
                "labeljust": "l",
                "labelloc": "t",
                "margin": 18,
                "penwidth": 1.8,
                "style": "rounded,filled",
                "tooltip": f"The entire framed region is focal cluster {high.cluster_id}",
            }
        )
        + ";",
        "    \"focal_note\" "
        + stable_attributes(
            {
                "color": "transparent",
                "fillcolor": "transparent",
                "fontcolor": "#35546F",
                "fontsize": 8,
                "label": "Package nodes are internal subdivisions of the framed focal cluster.",
                "shape": "plain",
                "style": "",
            }
        )
        + ";",
    ]
    for profile in aggregation.profiles:
        node_size = 0.55 + 0.035 * math.sqrt(len(profile.member_classes))
        lines.append(
            f"    {dot_quote('pkg_' + profile.package_id)} "
            + stable_attributes(
                {
                    "color": "#4472A5",
                    "fillcolor": "#DCEAF7",
                    "height": node_size,
                    "label": f"{_package_label(profile.package_name)}\n{len(profile.member_classes)} classes",
                    "penwidth": 1.0,
                    "tooltip": "; ".join(profile.member_classes),
                    "width": 1.35 + 0.025 * math.sqrt(len(profile.member_classes)),
                }
            )
            + ";"
        )
    focal_columns = [
        aggregation.profiles[index : index + 5]
        for index in range(0, len(aggregation.profiles), 5)
    ]
    for column_index, column in enumerate(focal_columns, 1):
        lines.append(f"    subgraph focal_rank_{column_index:02d} {{")
        lines.append("      rank=same;")
        for profile in column:
            lines.append(f"      {dot_quote('pkg_' + profile.package_id)};")
        lines.append("    }")
    if len(focal_columns) > 1:
        focal_leaders = ["pkg_" + column[0].package_id for column in focal_columns]
        lines.append(
            "    "
            + " -> ".join(dot_quote(leader) for leader in focal_leaders)
            + " "
            + stable_attributes({"style": "invis", "weight": 30})
            + ";"
        )
    for relation in aggregation.relations:
        lines.append(
            f"    {dot_quote('pkg_' + relation.source_package)} -> "
            f"{dot_quote('pkg_' + relation.target_package)} "
            + stable_attributes(
                {
                    "color": "#4D4D4D",
                    "constraint": False,
                    "dir": "none",
                    "penwidth": _width(relation.aggregated_weight, max_internal),
                    "style": "solid",
                    "tooltip": f"{relation.class_edge_count} internal class edges; weight {relation.aggregated_weight:g}",
                }
            )
            + ";"
        )
    lines.append("  }")
    external_ids = sorted(external_classes)
    external_column_size = math.ceil(len(external_ids) / 2)
    external_columns = [
        external_ids[index : index + external_column_size]
        for index in range(0, len(external_ids), external_column_size)
    ]
    for column_index, column in enumerate(external_columns, 1):
        lines.extend(
            [
                f"  subgraph external_rank_{column_index:02d} {{",
                "    rank=same;",
            ]
        )
        for cluster_id in column:
            classes = sorted(external_classes[cluster_id])
            lines.append(
                f"    {dot_quote('ext_' + cluster_id)} "
                + stable_attributes(
                    {
                        "color": "#888888",
                        "fillcolor": "#F2F2F2",
                        "fontcolor": "#4D4D4D",
                        "label": f"External {cluster_id}\n{len(classes)} classes",
                        "penwidth": 1.0,
                        "shape": "box",
                        "style": "rounded,dashed,filled",
                        "tooltip": "; ".join(classes),
                    }
                )
                + ";"
            )
        lines.append("  }")
    if external_columns:
        external_leaders = ["ext_" + column[0] for column in external_columns]
        lines.append(
            "  \"focal_note\" -> "
            + " -> ".join(dot_quote(leader) for leader in external_leaders)
            + " "
            + stable_attributes({"style": "invis", "weight": 20})
            + ";"
        )
    for relation in aggregation.boundary_relations:
        lines.append(
            f"  {dot_quote('pkg_' + relation.source_package)} -> "
            f"{dot_quote('ext_' + relation.external_cluster_id)} "
            + stable_attributes(
                {
                    "color": "#8A8A8A",
                    "constraint": False,
                    "dir": "none",
                    "penwidth": _width(
                        relation.aggregated_weight, max_boundary, 0.6, 2.6
                    ),
                    "style": "dashed",
                    "tooltip": f"{relation.boundary_edge_count} boundary class edges; weight {relation.aggregated_weight:g}",
                }
            )
            + ";"
        )
    lines.extend(
        [
            "  subgraph cluster_lowest {",
            "    graph "
            + stable_attributes(
                {
                    "color": "#A6A6A6",
                    "fontname": "Helvetica-Bold",
                    "fontsize": 9,
                    "label": low_label,
                    "labeljust": "l",
                    "labelloc": "t",
                    "margin": 14,
                    "penwidth": 1.1,
                    "style": "rounded",
                }
            )
            + ";",
        ]
    )
    low_member_ids = {
        class_id: f"low_{index:02d}"
        for index, class_id in enumerate(low.members, 1)
    }
    for class_id in low.members:
        lines.append(
            f"    {dot_quote(low_member_ids[class_id])} "
            + stable_attributes(
                {
                    "color": "#4472A5",
                    "fillcolor": "#DCEAF7",
                    "fontsize": 8,
                    "label": class_id.rsplit(".", 1)[-1],
                    "tooltip": class_id,
                }
            )
            + ";"
        )
    if len(low.members) == 1 and not low.boundary_edges:
        lines.append(
            "    \"isolated_note\" "
            + stable_attributes(
                {
                    "color": "transparent",
                    "fillcolor": "transparent",
                    "fontcolor": "#555555",
                    "fontsize": 8,
                    "label": "Isolated singleton\nNo internal or boundary relations",
                    "shape": "plain",
                    "style": "",
                }
            )
            + ";"
        )
        lines.append(
            "    \"low_01\" -> \"isolated_note\" "
            + stable_attributes({"style": "invis", "weight": 5})
            + ";"
        )
    else:
        low_member_set = set(low.members)
        for source, target, weight in low.internal_edges:
            lines.append(
                f"    {dot_quote(low_member_ids[source])} -> {dot_quote(low_member_ids[target])} "
                + stable_attributes(
                    {
                        "color": "#4D4D4D",
                        "dir": "none",
                        "penwidth": _width(weight, max(low.internal_weight, 1.0)),
                        "tooltip": f"internal structural weight {weight:g}",
                    }
                )
                + ";"
            )
        for aggregate in low.boundary_aggregates:
            node_id = "low_ext_" + aggregate.external_cluster_id
            lines.append(
                f"    {dot_quote(node_id)} "
                + stable_attributes(
                    {
                        "color": "#888888",
                        "fillcolor": "#F2F2F2",
                        "fontsize": 7.5,
                        "label": f"External {aggregate.external_cluster_id}\n{len(aggregate.external_classes)} classes",
                        "style": "rounded,dashed,filled",
                        "tooltip": "; ".join(aggregate.external_classes),
                    }
                )
                + ";"
            )
            for connection in aggregate.connections:
                if connection.focal_class not in low_member_set:
                    raise ValueError("lowest boundary connection has no focal endpoint")
                lines.append(
                    f"    {dot_quote(low_member_ids[connection.focal_class])} -> {dot_quote(node_id)} "
                    + stable_attributes(
                        {
                            "color": "#7A7A7A",
                            "dir": "none",
                            "penwidth": _width(
                                connection.boundary_weight,
                                max(low.boundary_weight, 1.0),
                                0.6,
                                2.2,
                            ),
                            "style": "dashed",
                            "tooltip": f"{connection.boundary_edge_count} boundary class edges; weight {connection.boundary_weight:g}",
                        }
                    )
                    + ";"
                )
    lines.extend(
        [
            "  }",
            "  subgraph cluster_legend {",
            "    graph "
            + stable_attributes(
                {
                    "color": "#D0D0D0",
                    "fontname": "Helvetica-Bold",
                    "fontsize": 8,
                    "label": "Legend",
                    "labeljust": "l",
                    "margin": 10,
                    "style": "rounded",
                }
            )
            + ";",
            "    \"legend_package\" "
            + stable_attributes(
                {
                    "color": "#4472A5",
                    "fillcolor": "#DCEAF7",
                    "fontsize": 7.5,
                    "label": "Focal package node\nsize = focal class count",
                }
            )
            + ";",
            "    \"legend_external\" "
            + stable_attributes(
                {
                    "color": "#888888",
                    "fillcolor": "#F2F2F2",
                    "fontsize": 7.5,
                    "label": "External cluster summary",
                    "style": "rounded,dashed,filled",
                }
            )
            + ";",
            "    \"legend_relations\" "
            + stable_attributes(
                {
                    "color": "transparent",
                    "fillcolor": "transparent",
                    "fontsize": 7.5,
                    "label": "Solid edge = aggregated internal structural weight\nDashed edge = aggregated boundary weight",
                    "shape": "plain",
                    "style": "",
                }
            )
            + ";",
            "  }",
        ]
    )
    if page == "stage13":
        lines.append(
            "  \"shared_note\" "
            + stable_attributes(
                {
                    "color": "transparent",
                    "fillcolor": "transparent",
                    "fontname": "Helvetica-Bold",
                    "fontsize": 9,
                    "label": "Stage 1 and Stage 3 select the same highest- and lowest-contributing clusters.",
                    "shape": "plain",
                    "style": "",
                }
            )
            + ";"
        )
    lines.append(
        "  \"audit_note\" "
        + stable_attributes(
            {
                "color": "transparent",
                "fillcolor": "transparent",
                "fontcolor": "#555555",
                "fontsize": 7.5,
                "label": "Complete class-level membership and edge data are provided in companion CSV files.",
                "shape": "plain",
                "style": "",
            }
        )
        + ";"
    )
    lines.append("}")
    return "\n".join(lines) + "\n"


def _targets(config: VisualizationConfig, page: str, output_root: Path | None):
    basename = BASENAMES[page]
    prefix = "xerces_stage13" if page == "stage13" else "xerces_stage2"
    if output_root is None:
        data_root = config.output.data / DIRECTORY
        targets = {
            "profiles": data_root / "xerces_cluster_profiles.csv",
            "selected": data_root / "xerces_highest_lowest_clusters.csv",
            "class_membership": data_root / f"{prefix}_class_membership.csv",
            "package_profiles": data_root / f"{prefix}_package_profiles.csv",
            "package_relations": data_root / f"{prefix}_package_relations.csv",
            "boundary_aggregation": data_root / f"{prefix}_boundary_aggregation.csv",
            "internal_edges": data_root / f"{prefix}_class_internal_edges.csv",
            "boundary_edges": data_root / f"{prefix}_class_boundary_edges.csv",
            "dot": config.output.dot / DIRECTORY / f"{basename}.dot",
            "svg": config.output.svg / DIRECTORY / f"{basename}.svg",
            "pdf": config.output.pdf / DIRECTORY / f"{basename}.pdf",
            "provenance": data_root / f"{basename}.provenance.json",
        }
        return targets, config.repository_root / "reports/figures/manifest.json", None
    root = output_root.resolve()
    data_root = root / "data" / DIRECTORY
    targets = {
        "profiles": data_root / "xerces_cluster_profiles.csv",
        "selected": data_root / "xerces_highest_lowest_clusters.csv",
        "class_membership": data_root / f"{prefix}_class_membership.csv",
        "package_profiles": data_root / f"{prefix}_package_profiles.csv",
        "package_relations": data_root / f"{prefix}_package_relations.csv",
        "boundary_aggregation": data_root / f"{prefix}_boundary_aggregation.csv",
        "internal_edges": data_root / f"{prefix}_class_internal_edges.csv",
        "boundary_edges": data_root / f"{prefix}_class_boundary_edges.csv",
        "dot": root / "source" / DIRECTORY / f"{basename}.dot",
        "svg": root / "preview" / DIRECTORY / f"{basename}.svg",
        "pdf": root / "pdf" / DIRECTORY / f"{basename}.pdf",
        "provenance": data_root / f"{basename}.provenance.json",
    }
    return targets, root / "manifest.json", root


def build_figure(
    config: VisualizationConfig,
    *,
    figure_id: str,
    output_root: str | Path | None = None,
    manifest_path: str | Path | None = None,
    generated_at: str | None = None,
    git_commit: str | None = None,
    git_dirty: bool | None = None,
    renderer: Callable[
        [GraphvizRenderRequest], GraphvizRenderResult
    ] = render_graphviz,
):
    page = next(
        (candidate for candidate, registered in FIGURE_IDS.items() if registered == figure_id),
        None,
    )
    specification = config.figures.get(figure_id)
    if page is None or specification is None or not specification.enabled:
        raise ValueError(f"Xerces-J figure is not registered: {figure_id}")
    data = prepare_figure_data(config)
    high = _profile_for_page(data, page, "highest")
    low = _profile_for_page(data, page, "lowest")
    stage_label = "stage1+stage3" if page == "stage13" else "stage2"
    aggregation = package_aggregation(config, stage_label, high)
    targets, default_manifest, artifact_root = _targets(
        config, page, None if output_root is None else Path(output_root)
    )
    manifest = default_manifest if manifest_path is None else Path(manifest_path)
    for path in (*targets.values(), manifest):
        path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{figure_id}.",
        dir=artifact_root or config.repository_root / "reports/figures",
    ) as temporary:
        temporary_root = Path(temporary)
        staged = {name: temporary_root / f"figure.{name}" for name in targets}
        staged["provenance"] = temporary_root / "figure.provenance.json"
        staged["profiles"].write_text(
            profiles_csv(data), encoding="utf-8", newline="\n"
        )
        staged["selected"].write_text(
            selected_csv(data), encoding="utf-8", newline="\n"
        )
        staged["class_membership"].write_text(
            class_membership_csv(aggregation), encoding="utf-8", newline="\n"
        )
        staged["package_profiles"].write_text(
            package_profiles_csv(aggregation), encoding="utf-8", newline="\n"
        )
        staged["package_relations"].write_text(
            package_relations_csv(aggregation), encoding="utf-8", newline="\n"
        )
        staged["boundary_aggregation"].write_text(
            package_boundary_csv(aggregation), encoding="utf-8", newline="\n"
        )
        staged["internal_edges"].write_text(
            class_edges_csv(stage_label, "highest", high, "internal"),
            encoding="utf-8",
            newline="\n",
        )
        staged["boundary_edges"].write_text(
            class_edges_csv(stage_label, "highest", high, "boundary"),
            encoding="utf-8",
            newline="\n",
        )
        write_dot(staged["dot"], figure_dot(config, page, high, low, aggregation))
        renders = [
            renderer(
                GraphvizRenderRequest(
                    staged["dot"], staged[output_format], output_format, "dot"
                )
            )
            for output_format in ("svg", "pdf")
        ]
        for name in targets:
            if name == "provenance":
                continue
            if not staged[name].is_file() or not staged[name].stat().st_size:
                raise ValueError(f"missing staged {name}")
        commands = tuple(
            (
                "dot",
                f"-T{output_format}",
                str(targets["dot"]),
                "-o",
                str(targets[output_format]),
            )
            for output_format in ("svg", "pdf")
        )
        record = build_provenance(
            figure_id=figure_id,
            stage=specification.stage,
            generator="src/" + specification.generator.replace(".", "/") + ".py",
            repository_root=config.repository_root,
            input_files=(
                config.repository_root / path for path in specification.inputs
            ),
            config_files=(config.figures_config_path, config.style_config_path),
            dot_path=staged["dot"],
            graphviz_engine="dot",
            graphviz_version=renders[0].version,
            render_commands=commands,
            generated_outputs=targets.values(),
            artifact_root=artifact_root,
            generated_at=generated_at,
            git_commit=git_commit,
            git_dirty=git_dirty,
        )
        write_provenance(staged["provenance"], record)
        document = (
            json.loads(manifest.read_text())
            if manifest.exists()
            else {"schema_version": 1, "figures": {}}
        )
        if document.get("schema_version") != 1 or not isinstance(
            document.get("figures"), dict
        ):
            raise ValueError("invalid figure manifest")
        for obsolete in (
            "stage1_xerces_highest_lowest_clusters",
            "stage2_xerces_highest_lowest_clusters",
            "stage3_xerces_highest_lowest_clusters",
        ):
            document["figures"].pop(obsolete, None)
        document["figures"][figure_id] = {
            "destination": specification.destination,
            "formats": list(specification.formats),
            "generated_at": record.generated_at,
            "generator": specification.generator,
            "inputs": list(specification.inputs),
            "metadata": dict(specification.metadata or {}),
            "outputs": {
                name: _relative(path, config.repository_root, artifact_root)
                for name, path in sorted(targets.items())
            },
            "sha256": {
                name: sha256_file(path) for name, path in sorted(staged.items())
            },
            "stage": specification.stage,
            "title": specification.title,
        }
        staged_manifest = temporary_root / "manifest.json"
        write_json_atomic(staged_manifest, document)
        for name in targets:
            os.replace(staged[name], targets[name])
        os.replace(staged_manifest, manifest)
    return targets
