"""Two deterministic summary-profile Xerces-J appendix figures."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd

from evo_ms.visualization.figures.stage123_daytrader_clusters import (
    BoundaryAggregate,
    BoundaryConnection,
    ClusterProfile,
    FigureData,
    _canonical_partition,
    _format_metric,
    _relative,
    profiles_csv,
    selected_csv,
)
from evo_ms.visualization.model import VisualizationConfig
from evo_ms.visualization.operating_preference import (
    balance_partition_medoid,
    fixed_balance_selection,
    representative_provenance,
)
from evo_ms.visualization.provenance import sha256_file, write_json_atomic

FIGURE_IDS = {
    "stage13": "stage13_xerces_balance_highest_lowest_clusters",
    "stage2": "stage2_xerces_highest_lowest_clusters",
}
BASENAMES = {
    "stage13": "xerces_stage13_balance_highest_lowest_clusters",
    "stage2": "xerces_stage2_highest_lowest_clusters",
}
EXPECTED = {
    1: (42, "stage1_seed42", "C11", 118, 624, "C07", 1, 12),
    2: (21, "seed21_solution022", "C13", 115, 570, "C27", 2, 16),
    3: (5, "seed5_solution019", "C13", 118, 624, "C06", 3, 15),
}
DIRECTORY = "cross_stage"
FIGURE_SIZE = (11.1, 7.3)
TOP_RELATION_COUNT = 5
TOP_BOUNDARY_COUNT = 5


@dataclass(frozen=True)
class PackageProfile:
    package_id: str
    package_name: str
    member_classes: tuple[str, ...]
    within_edge_count: int
    within_weight: float


@dataclass(frozen=True)
class PackageRelation:
    source_package: str
    target_package: str
    class_edge_count: int
    aggregated_weight: float


@dataclass(frozen=True)
class BoundaryProfile:
    external_cluster_id: str
    external_classes: tuple[str, ...]
    boundary_edge_count: int
    aggregated_weight: float


@dataclass(frozen=True)
class CompositeData:
    page: str
    stage_label: str
    high: ClusterProfile
    low: ClusterProfile
    packages: tuple[PackageProfile, ...]
    package_order: tuple[str, ...]
    relations: tuple[PackageRelation, ...]
    boundaries: tuple[BoundaryProfile, ...]
    class_to_package: tuple[tuple[str, str], ...]


def _partitions(root: Path, stages: tuple[int, ...]):
    partitions = []
    if 1 in stages:
        stage1_path = (
            "results/stage1/subjects/xerces-j/leiden_baseline/raw_reference_leiden/"
            "clustering/stage1_clusters.csv"
        )
        stage1 = pd.read_csv(root / stage1_path)
        stage1_modularity = float(
            pd.read_csv(
                root
                / "results/stage1/subjects/xerces-j/leiden_baseline/"
                "raw_reference_leiden/metrics/stage1_metrics.csv"
            ).iloc[0].modularity
        )
        partitions.append(
            (1, 42, "stage1_seed42", stage1_path, stage1, stage1_modularity)
        )
    if 2 in stages:
        stage2 = fixed_balance_selection(root, "xerces", "stage2", 21)
        if stage2.solution_id != "seed21_solution022":
            raise ValueError(
                "expected Xerces-J Stage 2 primary Balance-preference representative changed"
            )
        partitions.append((
            2,
            stage2.seed,
            stage2.solution_id,
            stage2.partition_source,
            stage2.partition,
            stage2.weighted_modularity,
        ))
    if 3 in stages:
        stage3 = balance_partition_medoid(root, "xerces", "stage3")
        if (stage3.seed, stage3.solution_id) != (5, "seed5_solution019"):
            raise ValueError("expected Xerces-J Stage 3 primary Balance-preference medoid changed")
        partitions.append((
            3,
            stage3.seed,
            stage3.solution_id,
            stage3.partition_source,
            stage3.partition,
            stage3.weighted_modularity,
        ))
    return tuple(partitions)


def prepare_figure_data(
    config: VisualizationConfig, stages: tuple[int, ...] = (1, 2, 3)
) -> FigureData:
    if not stages or not set(stages).issubset({1, 2, 3}):
        raise ValueError(f"invalid Xerces-J stage scope: {stages}")
    root = config.repository_root
    nodes = pd.read_csv(root / "data/extracted/xerces-j/class_nodes.csv")
    expected_classes = set(nodes.class_id.astype(str))
    if len(nodes) != 814 or len(expected_classes) != 814:
        raise ValueError("Xerces-J scope must contain 814 unique classes")
    edges = pd.read_csv(
        root
        / "results/stage1/subjects/xerces-j/leiden_baseline/"
        "raw_reference_leiden/graph/stage1_edges.csv"
    )
    pairs = [tuple(sorted((str(edge.source), str(edge.target)))) for edge in edges.itertuples()]
    if any(source == target for source, target in pairs) or len(pairs) != len(set(pairs)):
        raise ValueError("Xerces-J raw graph has invalid undirected edges")
    total_weight = float(edges.raw_weight.sum())
    degree = {class_id: 0.0 for class_id in expected_classes}
    for edge in edges.itertuples():
        degree[str(edge.source)] += float(edge.raw_weight)
        degree[str(edge.target)] += float(edge.raw_weight)

    profiles: list[ClusterProfile] = []
    formal_modularity = []
    for stage, seed, solution, source_path, raw, formal_value in _partitions(
        root, stages
    ):
        class_ids = raw.class_id.astype(str)
        if (
            len(class_ids) != 814
            or class_ids.duplicated().any()
            or set(class_ids) != expected_classes
        ):
            raise ValueError(f"Xerces-J Stage {stage} scope changed")
        partition = _canonical_partition(raw)
        cluster_by_class = dict(
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
                source = str(edge.source)
                target = str(edge.target)
                weight = float(edge.raw_weight)
                if source in member_set and target in member_set:
                    internal.append((min(source, target), max(source, target), weight))
                elif (source in member_set) ^ (target in member_set):
                    boundary.append((min(source, target), max(source, target), weight))
            grouped: dict[str, list[tuple[str, str, float]]] = {}
            for source, target, weight in boundary:
                focal, outside = (
                    (source, target) if source in member_set else (target, source)
                )
                grouped.setdefault(cluster_by_class[outside], []).append(
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
                        tuple(
                            sorted(
                                {outside for outside, _weight in by_focal[focal]}
                            )
                        ),
                        len(by_focal[focal]),
                        sum(weight for _outside, weight in by_focal[focal]),
                    )
                    for focal in sorted(by_focal)
                )
                aggregates.append(
                    BoundaryAggregate(
                        destination,
                        tuple(
                            sorted(
                                {
                                    outside
                                    for _focal, outside, _weight in records
                                }
                            )
                        ),
                        len(records),
                        sum(weight for _focal, _outside, weight in records),
                        tuple(sorted(by_focal)),
                        connections,
                    )
                )
            internal_weight = sum(weight for _a, _b, weight in internal)
            boundary_weight = sum(weight for _a, _b, weight in boundary)
            strength = sum(degree[class_id] for class_id in members)
            contribution = internal_weight / total_weight - (
                strength / (2 * total_weight)
            ) ** 2
            external = tuple(
                sorted(
                    {
                        endpoint
                        for source, target, _weight in boundary
                        for endpoint in (source, target)
                    }
                    - member_set
                )
            )
            profiles.append(
                ClusterProfile(
                    stage,
                    seed,
                    solution,
                    source_path,
                    str(cluster_id),
                    members,
                    tuple(sorted(internal)),
                    tuple(sorted(boundary)),
                    external,
                    internal_weight,
                    boundary_weight,
                    strength,
                    contribution,
                    tuple(aggregates),
                )
            )
        reconstructed = sum(
            profile.contribution for profile in profiles if profile.stage == stage
        )
        if not math.isclose(reconstructed, formal_value, abs_tol=1e-12):
            raise ValueError(f"Xerces-J Stage {stage} modularity reconstruction failed")
        formal_modularity.append((stage, formal_value))

    selected = []
    for stage in stages:
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
    data = FigureData(tuple(profiles), tuple(selected), tuple(formal_modularity))
    for stage in stages:
        expected = EXPECTED[stage]
        seed, solution, high_id, high_n, high_edges, low_id, low_n, destinations = expected
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
    return data


def _selected(data: FigureData, stage: int, role: str) -> ClusterProfile:
    return next(
        profile
        for selected_role, profile in data.selected
        if selected_role == role and profile.stage == stage
    )


def prepare_composite_data(
    config: VisualizationConfig, data: FigureData, page: str
) -> CompositeData:
    if page not in FIGURE_IDS:
        raise ValueError(f"unknown Xerces-J page: {page}")
    stage = 3 if page == "stage13" else 2
    stage_label = "stage3_balance" if page == "stage13" else "stage2"
    high = _selected(data, stage, "highest")
    low = _selected(data, stage, "lowest")
    nodes = pd.read_csv(
        config.repository_root / "data/extracted/xerces-j/class_nodes.csv"
    )
    package_by_class = dict(
        zip(nodes.class_id.astype(str), nodes.package.astype(str), strict=True)
    )
    canonical_packages = sorted(
        {package_by_class[class_id] for class_id in high.members}
    )
    package_id = {
        package_name: f"P{index:02d}"
        for index, package_name in enumerate(canonical_packages, 1)
    }
    members: dict[str, list[str]] = {
        package_name: [] for package_name in canonical_packages
    }
    for class_id in high.members:
        members[package_by_class[class_id]].append(class_id)
    within_count: defaultdict[str, int] = defaultdict(int)
    within_weight: defaultdict[str, float] = defaultdict(float)
    pair_values: dict[tuple[str, str], list[float]] = {
        (package_name, package_name): [0.0, 0.0]
        for package_name in canonical_packages
    }
    for source, target, weight in high.internal_edges:
        source_package = package_by_class[source]
        target_package = package_by_class[target]
        pair = tuple(sorted((source_package, target_package)))
        record = pair_values.setdefault(pair, [0.0, 0.0])
        record[0] += 1
        record[1] += weight
        if source_package == target_package:
            within_count[source_package] += 1
            within_weight[source_package] += weight
    profiles = tuple(
        PackageProfile(
            package_id[name],
            name,
            tuple(sorted(members[name])),
            within_count[name],
            within_weight[name],
        )
        for name in canonical_packages
    )
    package_order = tuple(
        profile.package_id
        for profile in sorted(
            profiles,
            key=lambda profile: (-len(profile.member_classes), profile.package_name),
        )
    )
    relations = tuple(
        PackageRelation(
            package_id[source],
            package_id[target],
            int(values[0]),
            float(values[1]),
        )
        for (source, target), values in sorted(pair_values.items())
    )
    boundaries = tuple(
        BoundaryProfile(
            aggregate.external_cluster_id,
            aggregate.external_classes,
            aggregate.boundary_edge_count,
            aggregate.boundary_weight,
        )
        for aggregate in sorted(
            high.boundary_aggregates,
            key=lambda aggregate: (
                -aggregate.boundary_weight,
                aggregate.external_cluster_id,
            ),
        )
    )
    composite = CompositeData(
        page,
        stage_label,
        high,
        low,
        profiles,
        package_order,
        relations,
        boundaries,
        tuple(
            sorted(
                (
                    class_id,
                    package_id[package_by_class[class_id]],
                )
                for class_id in high.members
            )
        ),
    )
    validate_composite_data(composite)
    return composite


def interaction_matrix(composite: CompositeData) -> np.ndarray:
    index = {
        package_id: position
        for position, package_id in enumerate(composite.package_order)
    }
    matrix = np.zeros((len(index), len(index)), dtype=float)
    for relation in composite.relations:
        source = index[relation.source_package]
        target = index[relation.target_package]
        matrix[source, target] = relation.aggregated_weight
        matrix[target, source] = relation.aggregated_weight
    return matrix


def top_internal_relations(composite: CompositeData) -> tuple[PackageRelation, ...]:
    """Return the five strongest between-package relations deterministically."""
    return tuple(
        sorted(
            (
                relation
                for relation in composite.relations
                if relation.source_package != relation.target_package
            ),
            key=lambda relation: (
                -relation.aggregated_weight,
                relation.source_package,
                relation.target_package,
            ),
        )[:TOP_RELATION_COUNT]
    )


def boundary_display_rows(composite: CompositeData) -> tuple[dict[str, object], ...]:
    """Return the five strongest destinations plus a deterministic remainder."""
    top = composite.boundaries[:TOP_BOUNDARY_COUNT]
    rows: list[dict[str, object]] = [
        {
            "label": f"External {boundary.external_cluster_id}",
            "external_cluster_id": boundary.external_cluster_id,
            "destination_cluster_count": 1,
            "external_class_count": len(boundary.external_classes),
            "aggregated_boundary_weight": boundary.aggregated_weight,
        }
        for boundary in top
    ]
    remainder = composite.boundaries[TOP_BOUNDARY_COUNT:]
    if remainder:
        rows.append(
            {
                "label": "Other external clusters",
                "external_cluster_id": "OTHER",
                "destination_cluster_count": len(remainder),
                "external_class_count": sum(
                    len(boundary.external_classes) for boundary in remainder
                ),
                "aggregated_boundary_weight": sum(
                    boundary.aggregated_weight for boundary in remainder
                ),
            }
        )
    return tuple(rows)


def validate_composite_data(composite: CompositeData) -> None:
    high = composite.high
    assigned = [class_id for class_id, _package_id in composite.class_to_package]
    if assigned != sorted(high.members) or len(set(assigned)) != len(high.members):
        raise ValueError("focal class-to-package assignment is incomplete")
    if sum(len(profile.member_classes) for profile in composite.packages) != len(
        high.members
    ):
        raise ValueError("package composition does not reconcile focal classes")
    if len(composite.packages) != 10:
        raise ValueError("accepted Xerces-J focal cluster must contain 10 packages")
    if sum(relation.class_edge_count for relation in composite.relations) != len(
        high.internal_edges
    ):
        raise ValueError("package matrix does not reconcile internal edge count")
    if not math.isclose(
        sum(relation.aggregated_weight for relation in composite.relations),
        high.internal_weight,
    ):
        raise ValueError("package matrix does not reconstruct W_in")
    if sum(boundary.boundary_edge_count for boundary in composite.boundaries) != len(
        high.boundary_edges
    ):
        raise ValueError("boundary profile does not reconcile boundary edge count")
    if not math.isclose(
        sum(boundary.aggregated_weight for boundary in composite.boundaries),
        high.boundary_weight,
    ):
        raise ValueError("boundary profile does not reconstruct W_boundary")
    matrix = interaction_matrix(composite)
    if not np.array_equal(matrix, matrix.T):
        raise ValueError("plotted package matrix is not symmetric")
    reconstructed = float(np.triu(matrix).sum())
    if not math.isclose(reconstructed, high.internal_weight):
        raise ValueError("symmetric package matrix does not reconstruct W_in")
    top_relations = top_internal_relations(composite)
    if len(top_relations) != min(
        TOP_RELATION_COUNT,
        sum(
            relation.source_package != relation.target_package
            for relation in composite.relations
        ),
    ):
        raise ValueError("top internal package relations are incomplete")
    displayed_boundary_weight = sum(
        float(row["aggregated_boundary_weight"])
        for row in boundary_display_rows(composite)
    )
    if not math.isclose(displayed_boundary_weight, high.boundary_weight):
        raise ValueError("displayed boundary summary does not reconstruct W_boundary")


def _csv(fields: Iterable[str], rows: Iterable[dict[str, object]]) -> str:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def membership_csv(composite: CompositeData) -> str:
    profile_by_id = {
        profile.package_id: profile for profile in composite.packages
    }
    return _csv(
        ("stage", "focal_cluster_id", "class_id", "fully_qualified_name", "package"),
        (
            {
                "stage": composite.stage_label,
                "focal_cluster_id": composite.high.cluster_id,
                "class_id": class_id,
                "fully_qualified_name": class_id,
                "package": profile_by_id[package_id].package_name,
            }
            for class_id, package_id in composite.class_to_package
        ),
    )


def package_profiles_csv(composite: CompositeData) -> str:
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
        ),
        (
            {
                "stage": composite.stage_label,
                "focal_cluster_id": composite.high.cluster_id,
                "package_id": profile.package_id,
                "package_name": profile.package_name,
                "class_count": len(profile.member_classes),
                "member_classes": json.dumps(
                    profile.member_classes, separators=(",", ":")
                ),
                "within_package_edge_count": profile.within_edge_count,
                "within_package_weight": format(profile.within_weight, ".12g"),
            }
            for profile in composite.packages
        ),
    )


def package_relations_csv(composite: CompositeData) -> str:
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
                "stage": composite.stage_label,
                "focal_cluster_id": composite.high.cluster_id,
                "source_package": relation.source_package,
                "target_package": relation.target_package,
                "class_edge_count": relation.class_edge_count,
                "aggregated_internal_weight": format(
                    relation.aggregated_weight, ".12g"
                ),
            }
            for relation in composite.relations
        ),
    )


def boundary_profile_csv(composite: CompositeData) -> str:
    return _csv(
        (
            "stage",
            "focal_cluster_id",
            "external_cluster_id",
            "external_class_count",
            "external_classes",
            "boundary_edge_count",
            "aggregated_boundary_weight",
        ),
        (
            {
                "stage": composite.stage_label,
                "focal_cluster_id": composite.high.cluster_id,
                "external_cluster_id": boundary.external_cluster_id,
                "external_class_count": len(boundary.external_classes),
                "external_classes": json.dumps(
                    boundary.external_classes, separators=(",", ":")
                ),
                "boundary_edge_count": boundary.boundary_edge_count,
                "aggregated_boundary_weight": format(
                    boundary.aggregated_weight, ".12g"
                ),
            }
            for boundary in composite.boundaries
        ),
    )


def top_internal_relations_csv(composite: CompositeData) -> str:
    by_id = {profile.package_id: profile for profile in composite.packages}
    return _csv(
        (
            "stage",
            "focal_cluster_id",
            "rank",
            "source_package_id",
            "source_package_name",
            "target_package_id",
            "target_package_name",
            "class_edge_count",
            "aggregated_internal_weight",
        ),
        (
            {
                "stage": composite.stage_label,
                "focal_cluster_id": composite.high.cluster_id,
                "rank": rank,
                "source_package_id": relation.source_package,
                "source_package_name": by_id[relation.source_package].package_name,
                "target_package_id": relation.target_package,
                "target_package_name": by_id[relation.target_package].package_name,
                "class_edge_count": relation.class_edge_count,
                "aggregated_internal_weight": format(
                    relation.aggregated_weight, ".12g"
                ),
            }
            for rank, relation in enumerate(top_internal_relations(composite), 1)
        ),
    )


def top_boundary_destinations_csv(composite: CompositeData) -> str:
    return _csv(
        (
            "stage",
            "focal_cluster_id",
            "rank",
            "display_label",
            "external_cluster_id",
            "destination_cluster_count",
            "external_class_count",
            "aggregated_boundary_weight",
        ),
        (
            {
                "stage": composite.stage_label,
                "focal_cluster_id": composite.high.cluster_id,
                "rank": rank,
                "display_label": row["label"],
                "external_cluster_id": row["external_cluster_id"],
                "destination_cluster_count": row["destination_cluster_count"],
                "external_class_count": row["external_class_count"],
                "aggregated_boundary_weight": format(
                    float(row["aggregated_boundary_weight"]), ".12g"
                ),
            }
            for rank, row in enumerate(boundary_display_rows(composite), 1)
        ),
    )


def lowest_profile_csv(composite: CompositeData) -> str:
    low = composite.low
    rows = []
    if low.boundary_aggregates:
        for aggregate in sorted(
            low.boundary_aggregates,
            key=lambda item: (-item.boundary_weight, item.external_cluster_id),
        ):
            rows.append(
                {
                    "stage": composite.stage_label,
                    "cluster_id": low.cluster_id,
                    "class_count": len(low.members),
                    "member_classes": json.dumps(low.members, separators=(",", ":")),
                    "q_c": format(low.contribution, ".12g"),
                    "internal_weight": format(low.internal_weight, ".12g"),
                    "boundary_weight": format(low.boundary_weight, ".12g"),
                    "external_cluster_id": aggregate.external_cluster_id,
                    "external_class_count": len(aggregate.external_classes),
                    "aggregated_boundary_weight": format(
                        aggregate.boundary_weight, ".12g"
                    ),
                }
            )
    else:
        rows.append(
            {
                "stage": composite.stage_label,
                "cluster_id": low.cluster_id,
                "class_count": len(low.members),
                "member_classes": json.dumps(low.members, separators=(",", ":")),
                "q_c": format(low.contribution, ".12g"),
                "internal_weight": format(low.internal_weight, ".12g"),
                "boundary_weight": format(low.boundary_weight, ".12g"),
                "external_cluster_id": "",
                "external_class_count": 0,
                "aggregated_boundary_weight": 0,
            }
        )
    return _csv(
        (
            "stage",
            "cluster_id",
            "class_count",
            "member_classes",
            "q_c",
            "internal_weight",
            "boundary_weight",
            "external_cluster_id",
            "external_class_count",
            "aggregated_boundary_weight",
        ),
        rows,
    )


def class_edges_csv(
    composite: CompositeData, edge_kind: str
) -> str:
    edges = (
        composite.high.internal_edges
        if edge_kind == "internal"
        else composite.high.boundary_edges
    )
    return _csv(
        (
            "stage",
            "focal_cluster_id",
            "source_class",
            "target_class",
            "weight",
        ),
        (
            {
                "stage": composite.stage_label,
                "focal_cluster_id": composite.high.cluster_id,
                "source_class": source,
                "target_class": target,
                "weight": format(weight, ".12g"),
            }
            for source, target, weight in edges
        ),
    )


def _abbreviation(package_name: str) -> str:
    prefix = "org.apache.xerces."
    return package_name[len(prefix) :] if package_name.startswith(prefix) else package_name


def _style_axis(axis) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["left", "bottom"]].set_color("#A7A7A7")
    axis.tick_params(colors="#3F3F3F", labelsize=7)
    axis.grid(axis="x", color="#E5E5E5", linewidth=0.6)
    axis.set_axisbelow(True)


def _draw_header(axis, composite: CompositeData) -> None:
    axis.set_gid("header")
    axis.axis("off")
    high = composite.high
    axis.add_patch(
        plt.Rectangle(
            (0, 0.04),
            1,
            0.92,
            transform=axis.transAxes,
            facecolor="#F2F6FA",
            edgecolor="#315A7D",
            linewidth=1.2,
        )
    )
    axis.text(
        0.02,
        0.72,
        f"{high.cluster_id} - Highest-contributing focal cluster",
        transform=axis.transAxes,
        fontsize=14,
        fontweight="bold",
        color="#17365D",
        va="center",
    )
    axis.text(
        0.02,
        0.38,
        (
            f"{len(high.members)} classes in {len(composite.packages)} packages     "
            f"q_c = {_format_metric(high.contribution)}     W_in = {high.internal_weight:.0f}     "
            f"W_boundary = {high.boundary_weight:.0f}"
        ),
        transform=axis.transAxes,
        fontsize=9.5,
        color="#263746",
        va="center",
    )
    if composite.page == "stage13":
        axis.text(
            0.98,
            0.72,
            "Stage 3 medoid under the primary Balance preference (seed 5)",
            transform=axis.transAxes,
            fontsize=9.5,
            fontweight="bold",
            ha="right",
            color="#315A7D",
            va="center",
        )
        axis.text(
            0.98,
            0.18,
            "Stage 1 context: highest membership retained; lowest changes from C07 (1 class) to C06 (3 classes).",
            transform=axis.transAxes,
            fontsize=7.5,
            ha="right",
            color="#4C4C4C",
            va="center",
        )


def _draw_composition(axis, composite: CompositeData) -> None:
    axis.set_gid("composition")
    by_id = {profile.package_id: profile for profile in composite.packages}
    profiles = [by_id[package_id] for package_id in composite.package_order]
    values = [len(profile.member_classes) for profile in profiles]
    positions = np.arange(len(profiles))
    axis.barh(positions, values, color="#587FA4", height=0.62)
    axis.set_yticks(
        positions,
        [_abbreviation(profile.package_name) for profile in profiles],
        fontsize=7,
    )
    axis.invert_yaxis()
    axis.set_xlabel("Number of focal classes", fontsize=8)
    axis.set_title(
        f"Composition of {composite.high.cluster_id}\n"
        "Packages are internal subdivisions of the focal cluster.",
        loc="left",
        fontsize=10,
        fontweight="bold",
        pad=8,
    )
    maximum = max(values)
    axis.set_xlim(0, maximum * 1.18)
    for position, value in zip(positions, values, strict=True):
        axis.text(
            value + maximum * 0.025,
            position,
            str(value),
            va="center",
            fontsize=7,
            color="#2F2F2F",
        )
    _style_axis(axis)


def _draw_structural_summary(axis, composite: CompositeData) -> None:
    axis.set_gid("structural")
    by_id = {profile.package_id: profile for profile in composite.packages}
    relations = top_internal_relations(composite)
    axis.set_facecolor("#F8FAFC")
    for spine in axis.spines.values():
        spine.set_color("#B8C4CE")
        spine.set_linewidth(0.8)
    axis.set_xticks([])
    axis.set_yticks([])
    axis.set_title(
        "Structural summary",
        loc="left",
        fontsize=10,
        fontweight="bold",
        pad=7,
    )
    metrics = (
        ("Local modularity contribution", _format_metric(composite.high.contribution)),
        ("Internal structural weight", f"{composite.high.internal_weight:.0f}"),
        ("Boundary structural weight", f"{composite.high.boundary_weight:.0f}"),
    )
    for index, (label, value) in enumerate(metrics):
        left = 0.025 + index * 0.325
        axis.add_patch(
            plt.Rectangle(
                (left, 0.67), 0.305, 0.28,
                transform=axis.transAxes,
                facecolor="white",
                edgecolor="#CBD5DE",
                linewidth=0.7,
            )
        )
        axis.text(left + 0.015, 0.89, label, transform=axis.transAxes,
                  fontsize=5.9, color="#4A5966", va="top")
        axis.text(left + 0.015, 0.69, value, transform=axis.transAxes,
                  fontsize=10, fontweight="bold", color="#17365D", va="bottom")
    chart = axis.inset_axes([0.035, 0.13, 0.93, 0.42])
    values = [relation.aggregated_weight for relation in relations]
    labels = []
    for relation in relations:
        source = _abbreviation(by_id[relation.source_package].package_name)
        target = _abbreviation(by_id[relation.target_package].package_name)
        separator = "\n↔ " if len(source) + len(target) > 31 else " ↔ "
        labels.append(f"{source}{separator}{target}")
    positions = np.arange(len(relations))
    chart.barh(positions, values, color="#6689A8", height=0.56)
    chart.set_yticks(positions, labels, fontsize=6.4)
    chart.invert_yaxis()
    chart.set_title("Five strongest between-package relations", loc="left", fontsize=7.5, pad=4)
    maximum = max(values)
    chart.set_xlim(0, maximum * 1.18)
    chart.set_xticks([])
    for position, value in zip(positions, values, strict=True):
        chart.text(value + maximum * 0.02, position, f"{value:.0f}", va="center", fontsize=6.4)
    _style_axis(chart)
    axis.text(
        0.035, 0.025,
        "Complete package-interaction data are available in the companion CSV.",
        transform=axis.transAxes, fontsize=6.3, color="#59636B", va="bottom",
    )


def _draw_boundary(axis, composite: CompositeData) -> None:
    axis.set_gid("boundary")
    rows = boundary_display_rows(composite)
    values = [float(row["aggregated_boundary_weight"]) for row in rows]
    labels = []
    for row in rows:
        if row["external_cluster_id"] == "OTHER":
            labels.append(
                f"Other external clusters ({row['destination_cluster_count']} clusters)"
            )
        else:
            labels.append(f"{row['label']} ({row['external_class_count']} classes)")
    positions = np.arange(len(rows))
    axis.barh(positions, values, color="#7C8D92", height=0.62)
    axis.set_yticks(positions, labels, fontsize=6.3)
    axis.invert_yaxis()
    axis.set_xlabel("Aggregated boundary weight", fontsize=8)
    axis.set_title(
        "Strongest external destinations\nTop five plus deterministic remainder",
        loc="left",
        fontsize=10,
        fontweight="bold",
        pad=8,
    )
    maximum = max(values)
    axis.set_xlim(0, maximum * 1.23)
    axis.xaxis.set_major_locator(MaxNLocator(nbins=6, prune="upper"))
    for position, value in zip(positions, values, strict=True):
        axis.text(
            value + maximum * 0.025,
            position,
            f"{value:.0f}",
            va="center",
            fontsize=6.6,
            color="#2F2F2F",
        )
    _style_axis(axis)


def _draw_lowest(axis, composite: CompositeData) -> None:
    axis.set_gid("lowest")
    low = composite.low
    axis.set_facecolor("#F8F8F8")
    for spine in axis.spines.values():
        spine.set_color("#B5B5B5")
        spine.set_linewidth(0.8)
    axis.set_xticks([])
    axis.set_yticks([])
    members = [class_id.rsplit(".", 1)[-1] for class_id in low.members]
    if composite.page == "stage13":
        members = [member.replace("$", "\n$", 1) for member in members]
    axis.text(
        0.04,
        0.86,
        f"{low.cluster_id} - Lowest-contributing\ncluster",
        transform=axis.transAxes,
        fontsize=9,
        fontweight="bold",
        color="#333333",
        va="top",
    )
    axis.text(
        0.40 if composite.page == "stage13" else 0.42,
        0.72 if composite.page == "stage13" else 0.5,
        "\n".join(members),
        transform=axis.transAxes,
        fontsize=6.5 if composite.page == "stage13" else 7.5,
        color="#315A7D",
        va="top",
    )
    axis.text(
        0.04,
        0.43 if composite.page == "stage13" else 0.5,
        (
            f"{len(low.members)} {'class' if len(low.members) == 1 else 'classes'}   "
            f"q_c = {_format_metric(low.contribution)}\n"
            f"W_in = {low.internal_weight:.0f}   "
            f"W_boundary = {low.boundary_weight:.0f}"
        ),
        transform=axis.transAxes,
        fontsize=7.2,
        color="#404040",
        va="top",
        ha="left",
    )
    if not low.boundary_aggregates:
        axis.text(
            0.72,
            0.5,
            "Isolated singleton\nNo internal or\nboundary relations",
            transform=axis.transAxes,
            fontsize=7.5,
            color="#555555",
            va="top",
        )
        return
    summary = sorted(
        low.boundary_aggregates,
        key=lambda item: (-item.boundary_weight, item.external_cluster_id),
    )
    inset = axis.inset_axes(
        [0.75, 0.12, 0.20, 0.62]
        if composite.page == "stage13"
        else [0.70, 0.12, 0.27, 0.62]
    )
    values = [item.boundary_weight for item in summary]
    labels = [
        item.external_cluster_id
        if composite.page == "stage13"
        else f"External {item.external_cluster_id}"
        for item in summary
    ]
    positions = np.arange(len(summary))
    inset.barh(positions, values, color="#9AA8AC", height=0.55)
    inset.set_yticks(positions, labels, fontsize=6)
    inset.invert_yaxis()
    inset.tick_params(axis="x", labelsize=5.5)
    inset.spines[["top", "right"]].set_visible(False)
    inset.set_title("Boundary summary", fontsize=6.5, loc="left", pad=3)
    maximum = max(values)
    inset.set_xlim(0, maximum * 1.25)
    for position, value in zip(positions, values, strict=True):
        inset.text(
            value + maximum * 0.03,
            position,
            f"{value:.0f}",
            va="center",
            fontsize=5.8,
        )


def create_figure(composite: CompositeData) -> Figure:
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.titlecolor": "#252525",
            "axes.labelcolor": "#353535",
            "svg.hashsalt": "evo-ms-xerces-summary-v1",
            "pdf.fonttype": 42,
        }
    ):
        figure = plt.figure(figsize=FIGURE_SIZE, facecolor="white")
        outer = figure.add_gridspec(
            2,
            1,
            height_ratios=(0.15, 0.85),
            left=0.095,
            right=0.98,
            top=0.965,
            bottom=0.075,
            hspace=0.2,
        )
        header = figure.add_subplot(outer[0])
        content = outer[1].subgridspec(1, 2, width_ratios=(0.43, 0.57), wspace=0.35)
        composition = figure.add_subplot(content[0, 0])
        summary = content[0, 1].subgridspec(
            3, 1, height_ratios=(0.43, 0.34, 0.23), hspace=0.48,
        )
        structural = figure.add_subplot(summary[0, 0])
        boundary = figure.add_subplot(summary[1, 0])
        lowest = figure.add_subplot(summary[2, 0])
        _draw_header(header, composite)
        _draw_composition(composition, composite)
        _draw_structural_summary(structural, composite)
        _draw_boundary(boundary, composite)
        _draw_lowest(lowest, composite)
        return figure


def _save_figure(figure: Figure, path: Path, output_format: str) -> None:
    metadata = {
        "Title": figure._suptitle.get_text() if figure._suptitle else "Xerces-J cluster contribution",
        "Creator": "evo-ms-clustering Matplotlib visualisation pipeline",
    }
    if output_format == "pdf":
        metadata.update({"CreationDate": None, "ModDate": None})
    else:
        metadata["Date"] = None
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "svg.hashsalt": "evo-ms-xerces-summary-v1",
            "pdf.fonttype": 42,
        }
    ):
        figure.savefig(
            path,
            format=output_format,
            dpi=150,
            facecolor="white",
            metadata=metadata,
        )
    if output_format == "svg":
        normalized = "\n".join(
            line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()
        )
        path.write_text(normalized + "\n", encoding="utf-8", newline="\n")


def _targets(config: VisualizationConfig, page: str, output_root: Path | None):
    basename = BASENAMES[page]
    prefix = "xerces_stage13" if page == "stage13" else "xerces_stage2"
    summary_prefix = (
        "xerces_stage13_balance" if page == "stage13" else "xerces_stage2"
    )
    if output_root is None:
        data_root = config.output.data / DIRECTORY
        targets = {
            "profiles": data_root / f"{summary_prefix}_cluster_profiles.csv",
            "selected": data_root / f"{summary_prefix}_highest_lowest_clusters.csv",
            "membership": data_root / f"{prefix}_class_membership.csv",
            "package_profiles": data_root / f"{prefix}_package_profiles.csv",
            "package_relations": data_root / f"{prefix}_package_relations.csv",
            "boundary_profile": data_root / f"{prefix}_boundary_profile.csv",
            "top_internal_relations": data_root / f"{prefix}_top_internal_relations.csv",
            "top_boundary_destinations": data_root / f"{prefix}_top_boundary_destinations.csv",
            "lowest_profile": data_root / f"{prefix}_lowest_cluster_profile.csv",
            "internal_edges": data_root / f"{prefix}_class_internal_edges.csv",
            "boundary_edges": data_root / f"{prefix}_class_boundary_edges.csv",
            "svg": config.output.svg / DIRECTORY / f"{basename}.svg",
            "pdf": config.output.pdf / DIRECTORY / f"{basename}.pdf",
            "provenance": data_root / f"{basename}.provenance.json",
        }
        return targets, config.repository_root / "reports/figures/manifest.json", None
    root = output_root.resolve()
    data_root = root / "data" / DIRECTORY
    targets = {
        "profiles": data_root / f"{summary_prefix}_cluster_profiles.csv",
        "selected": data_root / f"{summary_prefix}_highest_lowest_clusters.csv",
        "membership": data_root / f"{prefix}_class_membership.csv",
        "package_profiles": data_root / f"{prefix}_package_profiles.csv",
        "package_relations": data_root / f"{prefix}_package_relations.csv",
        "boundary_profile": data_root / f"{prefix}_boundary_profile.csv",
        "top_internal_relations": data_root / f"{prefix}_top_internal_relations.csv",
        "top_boundary_destinations": data_root / f"{prefix}_top_boundary_destinations.csv",
        "lowest_profile": data_root / f"{prefix}_lowest_cluster_profile.csv",
        "internal_edges": data_root / f"{prefix}_class_internal_edges.csv",
        "boundary_edges": data_root / f"{prefix}_class_boundary_edges.csv",
        "svg": root / "preview" / DIRECTORY / f"{basename}.svg",
        "pdf": root / "pdf" / DIRECTORY / f"{basename}.pdf",
        "provenance": data_root / f"{basename}.provenance.json",
    }
    return targets, root / "manifest.json", root


def _git_state(repository_root: Path) -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(repository_root), "status", "--porcelain=v1"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return commit, bool(status.strip())


def _provenance(
    config: VisualizationConfig,
    figure_id: str,
    targets: dict[str, Path],
    staged: dict[str, Path],
    artifact_root: Path | None,
    generated_at: str | None,
    git_commit: str | None,
    git_dirty: bool | None,
) -> dict[str, object]:
    specification = config.figures[figure_id]
    actual_commit, actual_dirty = (
        _git_state(config.repository_root)
        if git_commit is None or git_dirty is None
        else (git_commit, git_dirty)
    )
    timestamp = generated_at or (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    return {
        "schema_version": 1,
        "figure_id": figure_id,
        "stage": specification.stage,
        "generator": "src/"
        + specification.generator.replace(".", "/")
        + ".py",
        "renderer": "matplotlib",
        "renderer_version": matplotlib.__version__,
        "git_commit": actual_commit if git_commit is None else git_commit,
        "git_dirty": actual_dirty if git_dirty is None else git_dirty,
        "input_files": list(specification.inputs),
        "input_sha256": {
            path: sha256_file(config.repository_root / path)
            for path in specification.inputs
        },
        "config_files": [
            config.figures_config_path.relative_to(config.repository_root).as_posix(),
            config.style_config_path.relative_to(config.repository_root).as_posix(),
        ],
        "config_sha256": {
            path.relative_to(config.repository_root).as_posix(): sha256_file(path)
            for path in (config.figures_config_path, config.style_config_path)
        },
        "render_command": [
            ["matplotlib", "savefig", "--format", output_format]
            for output_format in ("svg", "pdf")
        ],
        "generated_outputs": sorted(
            _relative(path, config.repository_root, artifact_root)
            for path in targets.values()
        ),
        "generated_at": timestamp,
        "sha256": {
            name: sha256_file(path)
            for name, path in sorted(staged.items())
            if name != "provenance"
        },
    }


def build_figure(
    config: VisualizationConfig,
    *,
    figure_id: str,
    output_root: str | Path | None = None,
    manifest_path: str | Path | None = None,
    generated_at: str | None = None,
    git_commit: str | None = None,
    git_dirty: bool | None = None,
    renderer: Callable[[Figure, Path, str], None] = _save_figure,
) -> dict[str, Path]:
    page = next(
        (candidate for candidate, registered in FIGURE_IDS.items() if registered == figure_id),
        None,
    )
    specification = config.figures.get(figure_id)
    if page is None or specification is None or not specification.enabled:
        raise ValueError(f"Xerces-J figure is not registered: {figure_id}")
    if specification.formats != ("svg", "pdf"):
        raise ValueError("Xerces-J summary figures must use SVG and PDF only")
    data = prepare_figure_data(config, (1, 3) if page == "stage13" else (2,))
    composite = prepare_composite_data(config, data, page)
    targets, default_manifest, artifact_root = _targets(
        config, page, None if output_root is None else Path(output_root)
    )
    manifest = default_manifest if manifest_path is None else Path(manifest_path)
    for path in (*targets.values(), manifest):
        path.parent.mkdir(parents=True, exist_ok=True)
    staging_parent = artifact_root or config.repository_root / "reports/figures"
    with tempfile.TemporaryDirectory(
        prefix=f".{figure_id}.", dir=staging_parent
    ) as temporary:
        root = Path(temporary)
        staged = {name: root / f"figure.{name}" for name in targets}
        staged["provenance"] = root / "figure.provenance.json"
        staged["profiles"].write_text(
            profiles_csv(data), encoding="utf-8", newline="\n"
        )
        staged["selected"].write_text(
            selected_csv(data), encoding="utf-8", newline="\n"
        )
        staged["membership"].write_text(
            membership_csv(composite), encoding="utf-8", newline="\n"
        )
        staged["package_profiles"].write_text(
            package_profiles_csv(composite), encoding="utf-8", newline="\n"
        )
        staged["package_relations"].write_text(
            package_relations_csv(composite), encoding="utf-8", newline="\n"
        )
        staged["boundary_profile"].write_text(
            boundary_profile_csv(composite), encoding="utf-8", newline="\n"
        )
        staged["top_internal_relations"].write_text(
            top_internal_relations_csv(composite), encoding="utf-8", newline="\n"
        )
        staged["top_boundary_destinations"].write_text(
            top_boundary_destinations_csv(composite), encoding="utf-8", newline="\n"
        )
        staged["lowest_profile"].write_text(
            lowest_profile_csv(composite), encoding="utf-8", newline="\n"
        )
        staged["internal_edges"].write_text(
            class_edges_csv(composite, "internal"), encoding="utf-8", newline="\n"
        )
        staged["boundary_edges"].write_text(
            class_edges_csv(composite, "boundary"), encoding="utf-8", newline="\n"
        )
        figure = create_figure(composite)
        try:
            for output_format in ("svg", "pdf"):
                renderer(figure, staged[output_format], output_format)
        finally:
            plt.close(figure)
        for name, path in staged.items():
            if name == "provenance":
                continue
            if not path.is_file() or not path.stat().st_size:
                raise ValueError(f"missing staged {name}")
        provenance = _provenance(
            config,
            figure_id,
            targets,
            staged,
            artifact_root,
            generated_at,
            git_commit,
            git_dirty,
        )
        representative = (
            fixed_balance_selection(config.repository_root, "xerces", "stage2", 21)
            if page == "stage2"
            else balance_partition_medoid(config.repository_root, "xerces", "stage3")
        )
        provenance["operating_profile_representatives"] = representative_provenance(
            representative
        )
        write_json_atomic(staged["provenance"], provenance)
        document = (
            json.loads(manifest.read_text(encoding="utf-8"))
            if manifest.exists()
            else {"schema_version": 1, "figures": {}}
        )
        if document.get("schema_version") != 1 or not isinstance(
            document.get("figures"), dict
        ):
            raise ValueError("invalid figure manifest")
        document["figures"][figure_id] = {
            "destination": specification.destination,
            "formats": list(specification.formats),
            "generated_at": provenance["generated_at"],
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
        staged_manifest = root / "manifest.json"
        write_json_atomic(staged_manifest, document)
        for name in targets:
            os.replace(staged[name], targets[name])
        os.replace(staged_manifest, manifest)
    return targets
