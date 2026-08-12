"""Stage 1 SSA partition movement relative to Leiden seed variation."""

from __future__ import annotations

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
import numpy as np
import pandas as pd
import yaml

from evo_ms.visualization.model import VisualizationConfig
from evo_ms.visualization.provenance import sha256_file, write_json_atomic


FIGURE_ID = "stage1_ssa_seed_robustness"
BASENAME = "stage1_ssa_seed_robustness"
DIRECTORY = "stage1"
FIGURE_SIZE = (10.4, 4.8)
SUBJECTS = ("jpetstore", "daytrader", "xerces-j")
DISPLAY_NAMES = {"jpetstore": "JPetStore", "daytrader": "DayTrader", "xerces-j": "Xerces-J"}


@dataclass(frozen=True)
class Observation:
    subject: str
    comparison_type: str
    observation_id: str
    ari: float
    partition_distance: float


@dataclass(frozen=True)
class SubjectSummary:
    subject: str
    ssa_mean: float
    ssa_sd: float
    seed_noise_mean: float
    seed_noise_sd: float
    raw_distinct_partitions: int
    within_seed_variation: bool | None
    interpretation: str


@dataclass(frozen=True)
class RobustnessData:
    observations: tuple[Observation, ...]
    summaries: tuple[SubjectSummary, ...]


def _paths(root: Path, subject: str) -> dict[str, Path]:
    directory = root / f"results/stage1/subjects/{subject}/seed_robustness"
    return {name: directory / filename for name, filename in {
        "seed_noise": "seed_noise_ari.csv", "ssa_effect": "ssa_effect_ari.csv",
        "summary": "robustness_summary.csv", "metadata": "robustness_metadata.yml",
    }.items()}


def _verify_metadata_hashes(root: Path, subject: str, metadata: dict) -> None:
    source = Path(str(metadata["source_extracted_data"]))
    for filename, expected in sorted(metadata["extracted_input_sha256"].items()):
        path = root / source / filename
        if sha256_file(path) != str(expected):
            raise ValueError(f"{subject} robustness source hash changed: {path.relative_to(root)}")


def prepare_robustness_data(config: VisualizationConfig) -> RobustnessData:
    observations: list[Observation] = []
    summaries: list[SubjectSummary] = []
    for subject in SUBJECTS:
        paths = _paths(config.repository_root, subject)
        seed = pd.read_csv(paths["seed_noise"])
        ssa = pd.read_csv(paths["ssa_effect"])
        formal = pd.read_csv(paths["summary"])
        metadata = yaml.safe_load(paths["metadata"].read_text(encoding="utf-8"))
        if len(seed) != 435 or len(ssa) != 30 or len(formal) != 1:
            raise ValueError(f"{subject} robustness row counts changed")
        if list(metadata["seeds"]) != list(range(30)) or metadata["subject"] != subject:
            raise ValueError(f"{subject} robustness metadata seed scope changed")
        _verify_metadata_hashes(config.repository_root, subject, metadata)
        seed_ari = seed["ari_raw_i_vs_raw_j"].astype(float)
        ssa_ari = ssa["ari_raw_vs_ssa"].astype(float)
        for row in seed.itertuples(index=False):
            ari = float(row.ari_raw_i_vs_raw_j)
            observations.append(Observation(subject, "seed_variation", f"seed_{int(row.seed_i):02d}_vs_{int(row.seed_j):02d}", ari, 1.0 - ari))
        for row in ssa.itertuples(index=False):
            ari = float(row.ari_raw_vs_ssa)
            observations.append(Observation(subject, "ssa_effect", f"seed_{int(row.seed):02d}", ari, 1.0 - ari))
        seed_dist = 1.0 - seed_ari
        ssa_dist = 1.0 - ssa_ari
        record = formal.iloc[0]
        values = {
            "ssa_effect_dist_mean": float(ssa_dist.mean()),
            "ssa_effect_dist_std": float(ssa_dist.std(ddof=1)),
            "seed_noise_dist_mean": float(seed_dist.mean()),
            "seed_noise_dist_std": float(seed_dist.std(ddof=1)),
        }
        for column, recomputed in values.items():
            if not math.isclose(float(record[column]), recomputed, abs_tol=1e-12):
                raise ValueError(f"{subject} saved robustness summary disagrees for {column}")
        distinct = int(record["distinct_raw_partitions_across_seeds"])
        if subject == "jpetstore":
            if not bool((seed_dist == 0).all()) or distinct != 1:
                raise ValueError("JPetStore raw Leiden baseline is no longer seed-invariant")
            within = None
            interpretation = "Seed-invariant raw baseline; noise-band comparison: N/A"
        else:
            within = str(record["ssa_effect_dist_in_seed_noise_band"]).lower() == "true"
            if not within:
                raise ValueError(f"{subject} accepted within-seed-variation interpretation changed")
            interpretation = "SSA mean within observed seed-variation band"
        summaries.append(SubjectSummary(subject, values["ssa_effect_dist_mean"], values["ssa_effect_dist_std"],
                                        values["seed_noise_dist_mean"], values["seed_noise_dist_std"],
                                        distinct, within, interpretation))
    return RobustnessData(tuple(observations), tuple(summaries))


def _csv(fields: Iterable[str], rows: Iterable[dict[str, object]]) -> str:
    buffer = StringIO(newline=""); writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader(); writer.writerows(rows); return buffer.getvalue()


def observations_csv(data: RobustnessData) -> str:
    return _csv(("subject", "comparison_type", "observation_id", "ari", "partition_distance"),
                ({"subject": row.subject, "comparison_type": row.comparison_type,
                  "observation_id": row.observation_id, "ari": format(row.ari, ".12g"),
                  "partition_distance": format(row.partition_distance, ".12g")}
                 for row in data.observations))


def summary_csv(data: RobustnessData) -> str:
    return _csv(("subject", "ssa_mean", "ssa_sd", "seed_noise_mean", "seed_noise_sd",
                 "raw_distinct_partitions", "within_seed_variation", "interpretation"),
                ({"subject": row.subject, "ssa_mean": format(row.ssa_mean, ".12g"),
                  "ssa_sd": format(row.ssa_sd, ".12g"), "seed_noise_mean": format(row.seed_noise_mean, ".12g"),
                  "seed_noise_sd": format(row.seed_noise_sd, ".12g"),
                  "raw_distinct_partitions": row.raw_distinct_partitions,
                  "within_seed_variation": "" if row.within_seed_variation is None else str(row.within_seed_variation).lower(),
                  "interpretation": row.interpretation} for row in data.summaries))


def create_figure(data: RobustnessData) -> Figure:
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 8, "svg.hashsalt": "ssa-robustness-v1", "pdf.fonttype": 42}):
        figure, axes = plt.subplots(1, 3, figsize=FIGURE_SIZE, sharey=True, facecolor="white")
        figure.subplots_adjust(left=0.085, right=0.98, top=0.83, bottom=0.20, wspace=0.27)
        figure.suptitle("SSA-induced partition change relative to Leiden seed variation",
                        x=0.085, y=0.94, ha="left", fontsize=14, fontweight="bold", color="#17365D")
        figure.text(0.085, 0.875, "Partition distance = 1 - ARI; higher values indicate greater partition movement.",
                    fontsize=8, color="#46535C")
        maximum = max(row.partition_distance for row in data.observations)
        upper = max(0.5, math.ceil((maximum + 0.04) * 10) / 10)
        for axis, subject in zip(axes, SUBJECTS, strict=True):
            summary = next(row for row in data.summaries if row.subject == subject)
            seed = np.array([row.partition_distance for row in data.observations if row.subject == subject and row.comparison_type == "seed_variation"])
            ssa = np.array([row.partition_distance for row in data.observations if row.subject == subject and row.comparison_type == "ssa_effect"])
            if subject != "jpetstore":
                low = max(0.0, summary.seed_noise_mean - 2 * summary.seed_noise_sd)
                high = min(upper, summary.seed_noise_mean + 2 * summary.seed_noise_sd)
                axis.axhspan(low, high, color="#DCE6EC", alpha=0.75, zorder=0, label="Seed mean ± 2 SD")
            axis.boxplot([seed], positions=[0], widths=0.34, patch_artist=True, showfliers=True,
                         boxprops={"facecolor": "#93B7C8", "edgecolor": "#456878"},
                         medianprops={"color": "#17365D", "linewidth": 1.2},
                         whiskerprops={"color": "#456878"}, capprops={"color": "#456878"},
                         flierprops={"marker": ".", "markersize": 2.5, "markerfacecolor": "#6B7D85", "markeredgecolor": "none", "alpha": 0.5})
            jitter = np.linspace(-0.115, 0.115, len(ssa))
            axis.scatter(1 + jitter, ssa, s=16, color="#6C8797", alpha=0.5, edgecolors="none", zorder=3)
            axis.scatter([1], [summary.ssa_mean], marker="D", s=54, color="#B44D3A", edgecolor="white", linewidth=0.7, zorder=4)
            axis.set_title(DISPLAY_NAMES[subject], fontsize=11, fontweight="bold", pad=8)
            axis.set_xlim(-0.48, 1.48); axis.set_ylim(0, upper)
            axis.set_xticks((0, 1), ("Seed variation\n435 pairs", "SSA effect\n30 seeds"), fontsize=7.5)
            axis.grid(axis="y", color="#E1E5E8", linewidth=0.6); axis.set_axisbelow(True)
            axis.spines[["top", "right"]].set_visible(False)
            axis.spines[["left", "bottom"]].set_color("#A7A7A7")
            axis.text(0.5, 0.96, summary.interpretation.replace("; ", "\n"), transform=axis.transAxes,
                      ha="center", va="top", fontsize=7.2, color="#334A5A",
                      bbox={"boxstyle": "round,pad=0.28", "facecolor": "white", "edgecolor": "#B8C4CB", "linewidth": 0.6})
        axes[0].set_ylabel("Partition distance (1 - ARI)", fontsize=8.5)
        figure.text(0.085, 0.055, "Diamonds show mean SSA-effect distance; faint points show all 30 SSA observations. Shading is descriptive only.",
                    fontsize=7.2, color="#526069")
        return figure


def _save_figure(figure: Figure, path: Path, output_format: str) -> None:
    metadata = {"Title": "SSA-induced partition change relative to Leiden seed variation",
                "Creator": "evo-ms-clustering Matplotlib visualisation pipeline"}
    metadata.update({"CreationDate": None, "ModDate": None} if output_format == "pdf" else {"Date": None})
    with plt.rc_context({"svg.hashsalt": "ssa-robustness-v1", "pdf.fonttype": 42}):
        figure.savefig(path, format=output_format, dpi=150, facecolor="white", metadata=metadata)
    if output_format == "svg":
        path.write_text("\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8", newline="\n")


def _relative(path: Path, repository_root: Path, artifact_root: Path | None) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(repository_root): return resolved.relative_to(repository_root).as_posix()
    if artifact_root is not None and resolved.is_relative_to(artifact_root): return resolved.relative_to(artifact_root).as_posix()
    raise ValueError(f"path outside repository/artifact root: {path}")


def _targets(config: VisualizationConfig, output_root: Path | None):
    if output_root is None:
        data = config.output.data / DIRECTORY; root = None; manifest = config.repository_root / "reports/figures/manifest.json"
        svg = config.output.svg / DIRECTORY / f"{BASENAME}.svg"; pdf = config.output.pdf / DIRECTORY / f"{BASENAME}.pdf"
    else:
        root = output_root.resolve(); data = root / "data" / DIRECTORY; manifest = root / "manifest.json"
        svg = root / "preview" / DIRECTORY / f"{BASENAME}.svg"; pdf = root / "pdf" / DIRECTORY / f"{BASENAME}.pdf"
    return ({"data": data / "stage1_ssa_seed_robustness.csv", "summary": data / "stage1_ssa_seed_robustness_summary.csv",
             "svg": svg, "pdf": pdf, "provenance": data / "stage1_ssa_seed_robustness.provenance.json"}, manifest, root)


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
        raise ValueError("Stage 1 SSA robustness figure is not correctly registered")
    data = prepare_robustness_data(config)
    targets, default_manifest, artifact_root = _targets(config, None if output_root is None else Path(output_root))
    manifest = default_manifest if manifest_path is None else Path(manifest_path)
    for path in (*targets.values(), manifest): path.parent.mkdir(parents=True, exist_ok=True)
    staging_parent = artifact_root or config.repository_root / "reports/figures"
    with tempfile.TemporaryDirectory(prefix=f".{FIGURE_ID}.", dir=staging_parent) as temporary:
        temp = Path(temporary); staged = {name: temp / f"figure.{name}" for name in targets}
        staged["data"].write_text(observations_csv(data), encoding="utf-8", newline="\n")
        staged["summary"].write_text(summary_csv(data), encoding="utf-8", newline="\n")
        figure = create_figure(data)
        try:
            for output_format in ("svg", "pdf"): renderer(figure, staged[output_format], output_format)
        finally: plt.close(figure)
        commit, dirty = _git_state(config.repository_root) if git_commit is None or git_dirty is None else (git_commit, git_dirty)
        provenance = {
            "schema_version": 1, "figure_id": FIGURE_ID, "stage": specification.stage,
            "generator": "src/evo_ms/visualization/figures/stage1_ssa_seed_robustness.py",
            "renderer": "matplotlib", "renderer_version": matplotlib.__version__,
            "git_commit": commit, "git_dirty": dirty, "input_files": list(specification.inputs),
            "input_sha256": {path: sha256_file(config.repository_root / path) for path in specification.inputs},
            "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "method_note": "SSA partitions for all seeds were not persisted; SSA-effect ARIs are read from committed formal robustness results rather than independently reconstructed.",
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
