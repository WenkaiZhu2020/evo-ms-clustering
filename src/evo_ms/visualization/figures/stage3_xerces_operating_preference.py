"""Xerces-J Stage 3 operating-profile comparison."""

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
from matplotlib.ticker import PercentFormatter
import pandas as pd

from evo_ms.visualization.figures.stage123_daytrader_clusters import _relative
from evo_ms.visualization.model import VisualizationConfig
from evo_ms.visualization.operating_preference import authoritative_source_commit
from evo_ms.visualization.provenance import sha256_file, write_json_atomic


FIGURE_ID = "stage3_xerces_operating_preference_sensitivity"
BASENAME = "xerces_operating_preference_sensitivity"
DIRECTORY = "stage3"
PROFILES = (
    ("P0", "MODULARITY_ANCHOR", "MAX-Q"),
    ("P1", "BALANCE", "BALANCE"),
    ("P2", "COUPLING", "COUPLING"),
    ("P3", "COHESION", "COHESION"),
    ("P4", "SEMANTIC", "SEMANTIC"),
)
METRICS = (
    ("imbalance", "Imbalance", "lower is preferred"),
    ("cohesion", "Cohesion", "higher is preferred"),
    ("f_semantic", r"$f_{semantic}$", "lower is preferred"),
    ("relative_modularity_loss", "Relative modularity loss", r"from $Q_{best}$; lower is preferred"),
)


def prepare_figure_data(config: VisualizationConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    root = config.repository_root
    summary = pd.read_csv(
        root
        / "results/stage3/cross_subject/operating_preference_analysis/"
        "05_profile_summary.csv"
    )
    summary = summary.loc[
        (summary["subject"] == "xerces") & (summary["stage"] == "stage3")
    ].copy()
    order = {profile_id: index for index, (profile_id, _profile, _label) in enumerate(PROFILES)}
    summary["profile_order"] = summary["profile_id"].map(order)
    summary = summary.sort_values("profile_order").reset_index(drop=True)
    expected = [(profile_id, profile) for profile_id, profile, _label in PROFILES]
    if list(zip(summary["profile_id"], summary["profile"], strict=True)) != expected:
        raise ValueError("Xerces-J Stage 3 summary must contain authoritative P0-P4 profiles")
    if not (summary["n_seeds"] == 30).all():
        raise ValueError("every Xerces-J Stage 3 profile summary must represent 30 seeds")

    per_seed = pd.read_csv(
        root
        / "results/stage3/cross_subject/operating_preference_analysis/"
        "04_selected_profiles_per_seed.csv"
    )
    per_seed = per_seed.loc[
        (per_seed["subject"] == "xerces") & (per_seed["stage"] == "stage3")
    ].sort_values(["profile_id", "seed"]).reset_index(drop=True)
    counts = per_seed.groupby("profile_id").size().to_dict()
    if counts != {profile_id: 30 for profile_id, _profile, _label in PROFILES}:
        raise ValueError("Xerces-J Stage 3 P0-P4 selections must contain 30 rows per profile")
    for profile_id, profile, _label in PROFILES:
        rows = per_seed.loc[per_seed["profile_id"] == profile_id]
        if rows["seed"].astype(int).tolist() != list(range(30)) or not (rows["profile"] == profile).all():
            raise ValueError(f"{profile_id}/{profile} does not contain exactly seeds 0-29")

    for metric, _label, _direction in METRICS:
        summary_median = summary.set_index("profile_id")[f"median_{metric}"]
        retained_median = per_seed.groupby("profile_id")[metric].median()
        if not summary_median.index.equals(retained_median.index) or not (
            (summary_median - retained_median).abs() <= 1e-12
        ).all():
            raise ValueError(f"retained per-seed {metric} values disagree with 05_profile_summary.csv")

    relative = per_seed.groupby("profile_id")["relative_modularity_loss"].quantile([0.25, 0.75]).unstack()
    summary["q1_relative_modularity_loss"] = summary["profile_id"].map(relative[0.25])
    summary["q3_relative_modularity_loss"] = summary["profile_id"].map(relative[0.75])
    summary["iqr_relative_modularity_loss"] = (
        summary["q3_relative_modularity_loss"] - summary["q1_relative_modularity_loss"]
    )
    return summary, per_seed


def figure_data_csv(summary: pd.DataFrame) -> str:
    labels = {profile_id: label for profile_id, _profile, label in PROFILES}
    rows = []
    for metric, _metric_label, direction in METRICS:
        for row in summary.itertuples():
            rows.append(
                {
                    "subject": row.subject,
                    "stage": row.stage,
                    "profile_id": row.profile_id,
                    "profile": row.profile,
                    "display_label": labels[row.profile_id],
                    "metric": metric,
                    "preferred_direction": direction,
                    "n_seeds": row.n_seeds,
                    "median": getattr(row, f"median_{metric}"),
                    "q1": getattr(row, f"q1_{metric}"),
                    "q3": getattr(row, f"q3_{metric}"),
                    "iqr": getattr(row, f"iqr_{metric}"),
                }
            )
    return pd.DataFrame(rows).to_csv(index=False, lineterminator="\n")


def create_figure(summary: pd.DataFrame) -> Figure:
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.2,
            "pdf.fonttype": 42,
            "svg.hashsalt": "evo-ms-xerces-operating-preference-v2",
        }
    ):
        figure, axes = plt.subplots(2, 2, figsize=(7.1, 5.15), facecolor="white")
        labels = [label for _profile_id, _profile, label in PROFILES]
        x = list(range(len(labels)))
        for panel_label, axis, (metric, title, direction) in zip(
            ("a", "b", "c", "d"), axes.flat, METRICS, strict=True
        ):
            medians = summary[f"median_{metric}"].astype(float).to_numpy()
            q1 = summary[f"q1_{metric}"].astype(float).to_numpy()
            q3 = summary[f"q3_{metric}"].astype(float).to_numpy()
            axis.errorbar(
                x,
                medians,
                yerr=[medians - q1, q3 - medians],
                fmt="D",
                markersize=5.2,
                markerfacecolor="#1F4E79",
                markeredgecolor="white",
                markeredgewidth=0.55,
                color="#5B6B78",
                ecolor="#8796A3",
                elinewidth=2.1,
                capsize=4,
                capthick=1.0,
                zorder=3,
            )
            axis.set_title(f"({panel_label}) {title}", loc="left", fontsize=10, fontweight="bold", pad=7)
            axis.text(
                1.0,
                0.985 if metric == "relative_modularity_loss" else 1.025,
                direction,
                transform=axis.transAxes,
                ha="right",
                va="top" if metric == "relative_modularity_loss" else "bottom",
                fontsize=7.3,
                color="#555555",
            )
            axis.set_xticks(x, labels)
            axis.tick_params(axis="x", labelsize=7.1, pad=3)
            axis.tick_params(axis="y", labelsize=7.5)
            axis.grid(axis="y", color="#E2E5E8", linewidth=0.6)
            axis.set_axisbelow(True)
            axis.spines[["top", "right"]].set_visible(False)
            axis.margins(x=0.09, y=0.20)
            if metric == "relative_modularity_loss":
                axis.yaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=1))
                value_labels = [f"{value * 100:.2f}%" for value in medians]
            else:
                value_labels = [f"{value:.3f}" for value in medians]
            span = max(float(q3.max() - q1.min()), 1e-9)
            for xpos, median, value_label in zip(x, medians, value_labels, strict=True):
                axis.annotate(
                    value_label,
                    (xpos, median),
                    xytext=(0, 7),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=6.7,
                    color="#1D2A35",
                    clip_on=False,
                )
            lower = min(float(q1.min()), float(medians.min()))
            upper = max(float(q3.max()), float(medians.max()))
            axis.set_ylim(lower - 0.11 * span, upper + 0.30 * span)
        figure.suptitle(
            "Xerces-J Stage 3: operating-profile sensitivity",
            x=0.08,
            y=0.99,
            ha="left",
            fontsize=12,
            fontweight="bold",
        )
        figure.text(
            0.08,
            0.952,
            "Points show medians across 30 seeds; vertical intervals show the interquartile range.",
            ha="left",
            va="top",
            fontsize=7.7,
            color="#4A4A4A",
        )
        figure.subplots_adjust(left=0.08, right=0.985, bottom=0.085, top=0.87, hspace=0.48, wspace=0.24)
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
            "svg.hashsalt": "evo-ms-xerces-operating-preference-v2",
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
    summary, per_seed = prepare_figure_data(config)
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
            figure_data_csv(summary), encoding="utf-8", newline="\n"
        )
        figure = create_figure(summary)
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
            "profile_count": len(summary),
            "seed_count": per_seed["seed"].nunique(),
            "selected_count_per_profile": {
                profile_id: int((per_seed["profile_id"] == profile_id).sum())
                for profile_id, _profile, _label in PROFILES
            },
            "panel_metrics": [metric for metric, _label, _direction in METRICS],
            "summary_source": "results/stage3/cross_subject/operating_preference_analysis/05_profile_summary.csv",
            "relative_modularity_loss_iqr_source": "results/stage3/cross_subject/operating_preference_analysis/04_selected_profiles_per_seed.csv",
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
