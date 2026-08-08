"""Deterministic whole-partition overview for the three primary subjects."""

from __future__ import annotations

from collections.abc import Callable, Iterable
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np
import pandas as pd

from evo_ms.evaluation.partition_metrics import partition_similarity
from evo_ms.visualization.model import VisualizationConfig
from evo_ms.visualization.provenance import sha256_file, write_json_atomic


FIGURE_ID = "cross_stage_partition_overview"
BASENAME = "cross_stage_partition_overview"
DIRECTORY = "cross_stage"
FIGURE_SIZE = (8.15, 9.0)
SUBJECTS = ("jpetstore", "daytrader", "xerces-j")
DISPLAY_NAMES = {"jpetstore": "JPetStore", "daytrader": "DayTrader", "xerces-j": "Xerces-J"}
EXPECTED_CLASSES = {"jpetstore": 24, "daytrader": 53, "xerces-j": 814}
REPRESENTATIVES = {
    "jpetstore": {
        1: (42, "raw_reference_leiden", "results/stage1/subjects/jpetstore/leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv"),
        2: (1, "seed1_solution007", "results/stage2/subjects/jpetstore/nsga/robustness_final_30seeds/seed_01/pareto_labels.csv.xz"),
        3: (0, "seed0_solution000", "results/stage3/subjects/jpetstore/declaration_method_body/validation/seed_00/selected_partition.csv"),
    },
    "daytrader": {
        1: (42, "raw_reference_leiden", "results/stage1/subjects/daytrader/leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv"),
        2: (25, "seed25_solution047", "results/stage2/subjects/daytrader/nsga/robustness_final_30seeds/seed_25/pareto_labels.csv.xz"),
        3: (16, "seed16_solution036", "results/stage3/subjects/daytrader/declaration_method_body/formal/seed_16/selected_partition.csv"),
    },
    "xerces-j": {
        1: (42, "raw_reference_leiden", "results/stage1/subjects/xerces-j/leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv"),
        2: (21, "seed21_solution022", "results/stage2/subjects/xerces-j/nsga/robustness_final_30seeds/seed_21/pareto_labels.csv.xz"),
        3: (22, "seed22_solution015", "results/stage3/subjects/xerces-j/declaration_method_body/formal/seed_22/selected_partition.csv"),
    },
}


@dataclass(frozen=True)
class ClusterSegment:
    subject: str
    stage: int
    seed: int
    solution_id: str
    source_path: str
    cluster_id: str
    signature: str
    members: tuple[str, ...]
    class_fraction: float
    size_rank: int


@dataclass(frozen=True)
class Similarity:
    subject: str
    partition_a: str
    partition_b: str
    ari: float
    nmi: float


@dataclass(frozen=True)
class OverviewData:
    segments: tuple[ClusterSegment, ...]
    similarities: tuple[Similarity, ...]


def _signature(members: tuple[str, ...]) -> str:
    return hashlib.sha256("\0".join(members).encode("utf-8")).hexdigest()


def _load_partition(root: Path, subject: str, stage: int) -> pd.DataFrame:
    seed, solution_id, source_path = REPRESENTATIVES[subject][stage]
    frame = pd.read_csv(root / source_path)
    if stage == 2:
        if "solution_id" not in frame:
            raise ValueError(f"{subject} Stage 2 labels have no solution_id")
        frame = frame.loc[frame.solution_id.astype(str) == solution_id].copy()
    if not {"class_id", "cluster_id"}.issubset(frame.columns):
        raise ValueError(f"{subject} Stage {stage} partition schema changed")
    return frame[[column for column in ("class_id", "class_name", "cluster_id") if column in frame]].copy()


def _validate_representatives(root: Path) -> None:
    canonical = pd.read_csv(root / "results/stage2/cross_subject/operating_profile/canonical_operating_solution_per_seed.csv")
    for subject in SUBJECTS:
        seed, solution, _path = REPRESENTATIVES[subject][2]
        row = canonical.loc[(canonical.subject == subject) & (canonical.seed == seed)]
        if len(row) != 1 or str(row.iloc[0].solution_id) != solution:
            raise ValueError(f"{subject} Stage 2 representative changed")
        seed3, solution3, path3 = REPRESENTATIVES[subject][3]
        selected_path = root / Path(path3).with_name("selected_solution.json")
        selected = json.loads(selected_path.read_text(encoding="utf-8"))
        selected_id = selected["selected_four_objective_row"]["solution_id"]
        if int(selected["seed"]) != seed3 or selected_id != solution3:
            raise ValueError(f"{subject} Stage 3 representative changed")


def prepare_overview_data(config: VisualizationConfig) -> OverviewData:
    root = config.repository_root
    _validate_representatives(root)
    segments: list[ClusterSegment] = []
    similarities: list[Similarity] = []
    for subject in SUBJECTS:
        nodes = pd.read_csv(root / f"data/extracted/{subject}/class_nodes.csv")
        expected = set(nodes.class_id.astype(str))
        if len(nodes) != EXPECTED_CLASSES[subject] or len(expected) != EXPECTED_CLASSES[subject]:
            raise ValueError(f"{subject} class scope changed")
        partitions: dict[int, pd.DataFrame] = {}
        for stage in (1, 2, 3):
            frame = _load_partition(root, subject, stage)
            ids = frame.class_id.astype(str)
            if len(ids) != len(expected) or ids.duplicated().any() or set(ids) != expected:
                raise ValueError(f"{subject} Stage {stage} does not cover its complete class set")
            partitions[stage] = frame
            grouped = []
            for cluster_id, group in frame.groupby("cluster_id", sort=False):
                members = tuple(sorted(group.class_id.astype(str)))
                grouped.append((str(cluster_id), members, _signature(members)))
            ordered = sorted(grouped, key=lambda item: (-len(item[1]), item[2]))
            seed, solution, source_path = REPRESENTATIVES[subject][stage]
            for rank, (cluster_id, members, signature) in enumerate(ordered, 1):
                segments.append(
                    ClusterSegment(subject, stage, seed, solution, source_path, cluster_id,
                                   signature, members, len(members) / len(expected), rank)
                )
        for left, right in ((1, 2), (2, 3), (1, 3)):
            ari, nmi = partition_similarity(nodes, partitions[left], partitions[right])
            similarities.append(Similarity(subject, f"Stage {left}", f"Stage {right}", ari, nmi))
    return OverviewData(tuple(segments), tuple(similarities))


def _csv(fields: Iterable[str], rows: Iterable[dict[str, object]]) -> str:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def overview_csv(data: OverviewData) -> str:
    return _csv(
        ("subject", "stage", "representative_seed", "representative_solution_id", "source_path",
         "cluster_id", "canonical_member_signature", "class_count", "class_fraction", "size_rank"),
        ({
            "subject": segment.subject, "stage": segment.stage,
            "representative_seed": segment.seed, "representative_solution_id": segment.solution_id,
            "source_path": segment.source_path, "cluster_id": segment.cluster_id,
            "canonical_member_signature": segment.signature, "class_count": len(segment.members),
            "class_fraction": format(segment.class_fraction, ".12g"), "size_rank": segment.size_rank,
        } for segment in data.segments),
    )


def similarity_csv(data: OverviewData) -> str:
    return _csv(
        ("subject", "partition_a", "partition_b", "ari", "nmi"),
        ({"subject": row.subject, "partition_a": row.partition_a, "partition_b": row.partition_b,
          "ari": format(row.ari, ".12g"), "nmi": format(row.nmi, ".12g")}
         for row in data.similarities),
    )


def create_figure(data: OverviewData) -> Figure:
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 8, "svg.hashsalt": "partition-overview-v1", "pdf.fonttype": 42}):
        figure = plt.figure(figsize=FIGURE_SIZE, facecolor="white")
        grid = figure.add_gridspec(3, 1, left=0.12, right=0.79, top=0.91, bottom=0.105, hspace=0.48)
        figure.suptitle("Cross-stage partition profiles for the three primary subjects",
                        x=0.12, y=0.97, ha="left", fontsize=14, fontweight="bold", color="#17365D")
        for row_index, subject in enumerate(SUBJECTS):
            axis = figure.add_subplot(grid[row_index])
            axis.set_title(DISPLAY_NAMES[subject], loc="left", fontsize=11, fontweight="bold", pad=7)
            axis.set_xlim(0, 1.0)
            axis.set_ylim(-1.0, 2.65)
            axis.set_yticks((2, 1, 0), ("Stage 1", "Stage 2", "Stage 3"), fontsize=8)
            axis.set_xticks(np.linspace(0, 1, 5), ("0%", "25%", "50%", "75%", "100%"), fontsize=7)
            axis.grid(axis="x", color="#E3E6E8", linewidth=0.6)
            axis.set_axisbelow(True)
            axis.spines[["top", "right", "left"]].set_visible(False)
            axis.spines["bottom"].set_color("#A7A7A7")
            axis.tick_params(axis="y", length=0)
            for stage, y in ((1, 2), (2, 1), (3, 0)):
                stage_segments = [s for s in data.segments if s.subject == subject and s.stage == stage]
                left = 0.0
                colors = plt.cm.Blues(np.linspace(0.38, 0.84, max(len(stage_segments), 2)))
                for segment, color in zip(stage_segments, colors, strict=False):
                    axis.barh(y, segment.class_fraction, left=left, height=0.52, color=color,
                              edgecolor="white", linewidth=0.45)
                    left += segment.class_fraction
                largest = stage_segments[0].class_fraction
                axis.annotate(f"k = {len(stage_segments)}   largest = {largest:.1%}",
                              xy=(1, y), xytext=(8, 0), textcoords="offset points",
                              ha="left", va="center", fontsize=7.2, color="#34495E", annotation_clip=False)
            subject_similarity = [s for s in data.similarities if s.subject == subject]
            text = "   |   ".join(
                f"{item.partition_a.replace('Stage ', 'S')}-{item.partition_b.replace('Stage ', 'S')}: "
                f"ARI {item.ari:.3f}, NMI {item.nmi:.3f}"
                for item in subject_similarity
            )
            axis.text(0, -0.72, text, fontsize=7.2, color="#3E4A52", va="center")
        figure.text(0.12, 0.035,
                    "Clusters are ordered by size within each stage; segment position does not represent cluster identity across stages.",
                    fontsize=7.3, color="#4E5960")
        return figure


def _save_figure(figure: Figure, path: Path, output_format: str) -> None:
    metadata = {"Title": "Cross-stage partition profiles for the three primary subjects",
                "Creator": "evo-ms-clustering Matplotlib visualisation pipeline"}
    metadata.update({"CreationDate": None, "ModDate": None} if output_format == "pdf" else {"Date": None})
    with plt.rc_context({"svg.hashsalt": "partition-overview-v1", "pdf.fonttype": 42}):
        figure.savefig(path, format=output_format, dpi=150, facecolor="white", metadata=metadata)
    if output_format == "svg":
        path.write_text("\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()) + "\n",
                        encoding="utf-8", newline="\n")


def _relative(path: Path, repository_root: Path, artifact_root: Path | None) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(repository_root):
        return resolved.relative_to(repository_root).as_posix()
    if artifact_root is not None and resolved.is_relative_to(artifact_root):
        return resolved.relative_to(artifact_root).as_posix()
    raise ValueError(f"path outside repository/artifact root: {path}")


def _targets(config: VisualizationConfig, output_root: Path | None):
    if output_root is None:
        data = config.output.data / DIRECTORY
        root = None
        manifest = config.repository_root / "reports/figures/manifest.json"
        svg = config.output.svg / DIRECTORY / f"{BASENAME}.svg"
        pdf = config.output.pdf / DIRECTORY / f"{BASENAME}.pdf"
    else:
        root = output_root.resolve(); data = root / "data" / DIRECTORY; manifest = root / "manifest.json"
        svg = root / "preview" / DIRECTORY / f"{BASENAME}.svg"; pdf = root / "pdf" / DIRECTORY / f"{BASENAME}.pdf"
    return ({"data": data / "cross_stage_partition_overview.csv",
             "similarity": data / "cross_stage_partition_similarity.csv",
             "svg": svg, "pdf": pdf,
             "provenance": data / "cross_stage_partition_overview.provenance.json"}, manifest, root)


def _git_state(root: Path) -> tuple[str, bool]:
    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    status = subprocess.run(["git", "-C", str(root), "status", "--porcelain=v1"], capture_output=True, text=True, check=True).stdout
    return commit, bool(status.strip())


def build_figure(config: VisualizationConfig, *, output_root: str | Path | None = None,
                 manifest_path: str | Path | None = None, generated_at: str | None = None,
                 git_commit: str | None = None, git_dirty: bool | None = None,
                 renderer: Callable[[Figure, Path, str], None] = _save_figure) -> dict[str, Path]:
    specification = config.figures.get(FIGURE_ID)
    if specification is None or not specification.enabled or specification.formats != ("svg", "pdf"):
        raise ValueError("cross-stage partition overview is not correctly registered")
    data = prepare_overview_data(config)
    targets, default_manifest, artifact_root = _targets(config, None if output_root is None else Path(output_root))
    manifest = default_manifest if manifest_path is None else Path(manifest_path)
    for path in (*targets.values(), manifest): path.parent.mkdir(parents=True, exist_ok=True)
    staging_parent = artifact_root or config.repository_root / "reports/figures"
    with tempfile.TemporaryDirectory(prefix=f".{FIGURE_ID}.", dir=staging_parent) as temporary:
        temp = Path(temporary); staged = {name: temp / f"figure.{name}" for name in targets}
        staged["data"].write_text(overview_csv(data), encoding="utf-8", newline="\n")
        staged["similarity"].write_text(similarity_csv(data), encoding="utf-8", newline="\n")
        figure = create_figure(data)
        try:
            for output_format in ("svg", "pdf"): renderer(figure, staged[output_format], output_format)
        finally: plt.close(figure)
        commit, dirty = _git_state(config.repository_root) if git_commit is None or git_dirty is None else (git_commit, git_dirty)
        provenance = {
            "schema_version": 1, "figure_id": FIGURE_ID, "stage": specification.stage,
            "generator": "src/evo_ms/visualization/figures/cross_stage_partition_overview.py",
            "renderer": "matplotlib", "renderer_version": matplotlib.__version__,
            "git_commit": commit, "git_dirty": dirty,
            "input_files": list(specification.inputs),
            "input_sha256": {path: sha256_file(config.repository_root / path) for path in specification.inputs},
            "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "note": "Clusters are size-ordered within each stage; segment position does not represent cross-stage identity.",
            "sha256": {name: sha256_file(path) for name, path in staged.items() if name != "provenance"},
        }
        write_json_atomic(staged["provenance"], provenance)
        document = json.loads(manifest.read_text()) if manifest.exists() else {"schema_version": 1, "figures": {}}
        document["figures"][FIGURE_ID] = {
            "destination": specification.destination, "formats": list(specification.formats),
            "generated_at": provenance["generated_at"], "generator": specification.generator,
            "inputs": list(specification.inputs), "metadata": dict(specification.metadata or {}),
            "outputs": {name: _relative(path, config.repository_root, artifact_root) for name, path in sorted(targets.items())},
            "sha256": {name: sha256_file(path) for name, path in sorted(staged.items())},
            "stage": specification.stage, "title": specification.title,
        }
        staged_manifest = temp / "manifest.json"; write_json_atomic(staged_manifest, document)
        for name in targets: os.replace(staged[name], targets[name])
        os.replace(staged_manifest, manifest)
    return targets
