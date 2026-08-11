"""Xerces-J operating-preference sensitivity within the 5% candidate bands."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import pandas as pd

from evo_ms.visualization.figures.stage123_daytrader_clusters import _relative
from evo_ms.visualization.model import VisualizationConfig
from evo_ms.visualization.operating_preference import authoritative_source_commit
from evo_ms.visualization.provenance import sha256_file, write_json_atomic


FIGURE_ID = "stage3_xerces_operating_preference_sensitivity"
BASENAME = "xerces_operating_preference_sensitivity"
DIRECTORY = "stage3"
PROFILES = (
    ("P0", "MODULARITY_ANCHOR", "selected_modularity_anchor", "x", "#202020"),
    ("P1", "BALANCE", "selected_balance", "o", "#0072B2"),
    ("P2", "COUPLING", "selected_coupling", "+", "#555555"),
    ("P3", "COHESION", "selected_cohesion", "s", "#D55E00"),
    ("P4", "SEMANTIC", "selected_semantic", "D", "#009E73"),
)


def prepare_figure_data(config: VisualizationConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    root = config.repository_root
    candidates = pd.read_csv(
        root
        / "results/stage3/cross_subject/operating_preference_analysis/"
        "15_figure_candidates_5pct.csv"
    )
    candidates = candidates.loc[
        (candidates["subject"] == "xerces") & (candidates["stage"] == "stage3")
    ].sort_values(["seed", "solution_id"]).reset_index(drop=True)
    if len(candidates) != 147 or candidates["seed"].nunique() != 30:
        raise ValueError("Xerces-J Stage 3 figure pool must contain 147 candidates across 30 seeds")
    if candidates["relative_modularity_loss"].min() < 0 or candidates["relative_modularity_loss"].max() > 0.05 + 1e-12:
        raise ValueError("figure candidate lies outside the seed-specific 5% modularity region")

    selected_rows = []
    for profile_id, profile, flag, _marker, _colour in PROFILES:
        selected = candidates.loc[candidates[flag].astype(bool)].copy()
        if len(selected) != 30 or selected["seed"].astype(int).tolist() != list(range(30)):
            raise ValueError(f"{profile_id}/{profile} must select exactly one candidate per seed")
        selected["profile_id"] = profile_id
        selected["profile"] = profile
        selected_rows.append(selected)
    selected = pd.concat(selected_rows, ignore_index=True)

    authoritative = pd.read_csv(
        root
        / "results/stage3/cross_subject/operating_preference_analysis/"
        "04_selected_profiles_per_seed.csv"
    )
    authoritative = authoritative.loc[
        (authoritative["subject"] == "xerces")
        & (authoritative["stage"] == "stage3")
    ]
    merged = selected.merge(
        authoritative[
            ["seed", "profile_id", "profile", "selected_solution_id"]
        ],
        on=["seed", "profile_id", "profile"],
        how="left",
        validate="one_to_one",
    )
    if merged["selected_solution_id"].isna().any() or not (
        merged["solution_id"] == merged["selected_solution_id"]
    ).all():
        raise ValueError("figure P0-P4 selections disagree with the authoritative profile table")
    return candidates, selected.sort_values(["profile_id", "seed"]).reset_index(drop=True)


def figure_data_csv(candidates: pd.DataFrame, selected: pd.DataFrame) -> str:
    selected_lookup = {
        (int(row.seed), str(row.solution_id)): [] for row in candidates.itertuples()
    }
    for row in selected.itertuples():
        selected_lookup[(int(row.seed), str(row.solution_id))].append(str(row.profile_id))
    output = candidates[
        [
            "subject",
            "seed",
            "stage",
            "solution_id",
            "weighted_modularity",
            "relative_modularity_loss",
            "coupling",
            "cohesion",
            "imbalance",
            "f_semantic",
            "cluster_count",
            "canonical_partition_sha256",
        ]
    ].copy()
    output["selected_profiles"] = [
        ";".join(selected_lookup[(int(row.seed), str(row.solution_id))])
        for row in candidates.itertuples()
    ]
    return output.to_csv(index=False, lineterminator="\n")


def create_figure(candidates: pd.DataFrame, selected: pd.DataFrame) -> Figure:
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "pdf.fonttype": 42,
            "svg.hashsalt": "evo-ms-xerces-operating-preference-v1",
        }
    ):
        figure, axis = plt.subplots(figsize=(7.2, 4.5), facecolor="white")
        axis.scatter(
            candidates["imbalance"],
            candidates["cohesion"],
            s=18,
            marker="o",
            facecolors="#D7D7D7",
            edgecolors="#8A8A8A",
            linewidths=0.35,
            alpha=0.65,
            label="5% candidates (147; 30 seed-specific pools)",
            zorder=1,
        )
        for profile_id, profile, _flag, marker, colour in PROFILES:
            rows = selected.loc[selected["profile_id"] == profile_id]
            if marker in {"x", "+"}:
                axis.scatter(
                    rows["imbalance"], rows["cohesion"], s=42, marker=marker,
                    color=colour, linewidths=1.1, label=f"{profile_id} {profile}", zorder=3,
                )
            else:
                axis.scatter(
                    rows["imbalance"], rows["cohesion"], s=34, marker=marker,
                    facecolors="none", edgecolors=colour, linewidths=1.0,
                    label=f"{profile_id} {profile}", zorder=3,
                )
            median_style = {
                "s": 80, "marker": marker, "color": colour,
                "linewidths": 1.5 if marker in {"x", "+"} else 0.7, "zorder": 4,
            }
            if marker not in {"x", "+"}:
                median_style["edgecolors"] = "white"
            axis.scatter(
                [rows["imbalance"].median()], [rows["cohesion"].median()],
                **median_style,
            )
        axis.set_title(
            "Xerces-J: operating preferences select different 5% candidates",
            loc="left",
            fontsize=11,
            fontweight="bold",
            pad=10,
        )
        axis.text(
            0.0,
            1.01,
            "Small markers: exact per-seed selections; large markers: profile medians",
            transform=axis.transAxes,
            fontsize=7.4,
            color="#4A4A4A",
            va="bottom",
        )
        axis.set_xlabel("Imbalance (lower is preferred)")
        axis.set_ylabel("Cohesion (higher is preferred)")
        axis.grid(True, color="#E4E4E4", linewidth=0.55)
        axis.set_axisbelow(True)
        axis.spines[["top", "right"]].set_visible(False)
        axis.legend(
            loc="lower left",
            bbox_to_anchor=(0.0, 1.10),
            ncol=3,
            frameon=False,
            fontsize=7,
            handletextpad=0.45,
            columnspacing=1.0,
        )
        axis.annotate(
            "P1: lower imbalance,\noften low cohesion",
            xy=(selected.loc[selected.profile_id == "P1", "imbalance"].median(),
                selected.loc[selected.profile_id == "P1", "cohesion"].median()),
            xytext=(0.03, 0.08),
            textcoords="axes fraction",
            fontsize=7,
            color="#222222",
            arrowprops={"arrowstyle": "-", "color": "#777777", "linewidth": 0.7},
        )
        axis.annotate(
            "P0/P2/P4 remain near the\nhigh-modularity/high-cohesion region",
            xy=(selected.loc[selected.profile_id == "P0", "imbalance"].median(),
                selected.loc[selected.profile_id == "P0", "cohesion"].median()),
            xytext=(0.55, 0.72),
            textcoords="axes fraction",
            fontsize=7,
            color="#222222",
            arrowprops={"arrowstyle": "-", "color": "#777777", "linewidth": 0.7},
        )
        figure.subplots_adjust(left=0.11, right=0.98, bottom=0.14, top=0.75)
        return figure


def _save_figure(figure: Figure, path: Path, output_format: str) -> None:
    metadata = {
        "Title": "Xerces-J operating-preference sensitivity",
        "Creator": "evo-ms-clustering Matplotlib visualisation pipeline",
    }
    if output_format == "pdf":
        metadata.update({"CreationDate": None, "ModDate": None})
    else:
        metadata["Date"] = None
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "pdf.fonttype": 42,
            "svg.hashsalt": "evo-ms-xerces-operating-preference-v1",
        }
    ):
        figure.savefig(
            path, format=output_format, dpi=150, facecolor="white", metadata=metadata
        )
    if output_format == "svg":
        path.write_text(
            "\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n",
            encoding="utf-8",
            newline="\n",
        )


def _targets(config: VisualizationConfig, output_root: Path | None):
    if output_root is None:
        data = config.output.data / DIRECTORY
        return {
            "data": data / f"{BASENAME}.csv",
            "svg": config.output.svg / DIRECTORY / f"{BASENAME}.svg",
            "pdf": config.output.pdf / DIRECTORY / f"{BASENAME}.pdf",
            "provenance": data / f"{BASENAME}.provenance.json",
        }, config.repository_root / "reports/figures/manifest.json", None
    root = output_root.resolve()
    return {
        "data": root / "data" / DIRECTORY / f"{BASENAME}.csv",
        "svg": root / "preview" / DIRECTORY / f"{BASENAME}.svg",
        "pdf": root / "pdf" / DIRECTORY / f"{BASENAME}.pdf",
        "provenance": root / "data" / DIRECTORY / f"{BASENAME}.provenance.json",
    }, root / "manifest.json", root


def _git_state(root: Path) -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1"], check=True,
        capture_output=True, text=True,
    ).stdout
    return commit, bool(status.strip())


def build_figure(
    config: VisualizationConfig,
    *,
    output_root: str | Path | None = None,
    manifest_path: str | Path | None = None,
    generated_at: str | None = None,
    git_commit: str | None = None,
    git_dirty: bool | None = None,
    renderer: Callable[[Figure, Path, str], None] = _save_figure,
) -> dict[str, Path]:
    specification = config.figures.get(FIGURE_ID)
    if specification is None or not specification.enabled or specification.formats != ("svg", "pdf"):
        raise ValueError(f"figure is not correctly registered: {FIGURE_ID}")
    candidates, selected = prepare_figure_data(config)
    targets, default_manifest, artifact_root = _targets(
        config, None if output_root is None else Path(output_root)
    )
    manifest = default_manifest if manifest_path is None else Path(manifest_path)
    for path in (*targets.values(), manifest):
        path.parent.mkdir(parents=True, exist_ok=True)
    staging_parent = artifact_root or config.repository_root / "reports/figures"
    with tempfile.TemporaryDirectory(prefix=f".{FIGURE_ID}.", dir=staging_parent) as temporary:
        temporary_root = Path(temporary)
        staged = {name: temporary_root / f"figure.{name}" for name in targets}
        staged["data"].write_text(
            figure_data_csv(candidates, selected), encoding="utf-8", newline="\n"
        )
        figure = create_figure(candidates, selected)
        try:
            for output_format in ("svg", "pdf"):
                renderer(figure, staged[output_format], output_format)
        finally:
            plt.close(figure)
        actual_commit, actual_dirty = (
            _git_state(config.repository_root)
            if git_commit is None or git_dirty is None
            else (git_commit, git_dirty)
        )
        timestamp = generated_at or datetime.now(timezone.utc).replace(
            microsecond=0
        ).isoformat().replace("+00:00", "Z")
        provenance = {
            "schema_version": 1,
            "figure_id": FIGURE_ID,
            "stage": "stage3",
            "generator": "src/evo_ms/visualization/figures/stage3_xerces_operating_preference.py",
            "renderer": "matplotlib",
            "renderer_version": matplotlib.__version__,
            "git_commit": actual_commit if git_commit is None else git_commit,
            "git_dirty": actual_dirty if git_dirty is None else git_dirty,
            "generated_at": timestamp,
            "authoritative_source_commit": authoritative_source_commit(config.repository_root),
            "subject": "xerces",
            "stage_filter": "stage3",
            "candidate_count": len(candidates),
            "seed_count": candidates["seed"].nunique(),
            "selected_count_per_profile": {
                profile_id: int((selected["profile_id"] == profile_id).sum())
                for profile_id, *_rest in PROFILES
            },
            "dimensions": {"x": "imbalance", "y": "cohesion"},
            "input_files": list(specification.inputs),
            "input_sha256": {
                path: sha256_file(config.repository_root / path)
                for path in specification.inputs
            },
            "config_files": [
                config.figures_config_path.relative_to(config.repository_root).as_posix(),
                config.style_config_path.relative_to(config.repository_root).as_posix(),
            ],
            "generated_outputs": sorted(
                _relative(path, config.repository_root, artifact_root)
                for path in targets.values()
            ),
            "sha256": {
                name: sha256_file(path)
                for name, path in staged.items()
                if name != "provenance"
            },
        }
        write_json_atomic(staged["provenance"], provenance)
        document = (
            json.loads(manifest.read_text())
            if manifest.exists()
            else {"schema_version": 1, "figures": {}}
        )
        for deprecated_id in (
            "cross_stage_partition_overview",
            "stage13_xerces_shared_highest_lowest_clusters",
        ):
            document["figures"].pop(deprecated_id, None)
        document["figures"][FIGURE_ID] = {
            "destination": specification.destination,
            "formats": list(specification.formats),
            "generated_at": timestamp,
            "generator": specification.generator,
            "inputs": list(specification.inputs),
            "metadata": dict(specification.metadata or {}),
            "outputs": {
                name: _relative(path, config.repository_root, artifact_root)
                for name, path in sorted(targets.items())
            },
            "sha256": {name: sha256_file(path) for name, path in staged.items()},
            "stage": specification.stage,
            "title": specification.title,
        }
        staged_manifest = temporary_root / "manifest.json"
        write_json_atomic(staged_manifest, document)
        for name, path in targets.items():
            os.replace(staged[name], path)
        os.replace(staged_manifest, manifest)
    return targets
