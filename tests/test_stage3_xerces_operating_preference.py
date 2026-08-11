from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from evo_ms.visualization.config import load_visualization_config
from evo_ms.visualization.figures.stage3_xerces_operating_preference import (
    FIGURE_ID,
    build_figure,
    create_figure,
    figure_data_csv,
    prepare_figure_data,
)


def test_authoritative_summary_and_p0_p4_selections() -> None:
    config = load_visualization_config()
    summary, per_seed = prepare_figure_data(config)
    assert summary.profile_id.tolist() == ["P0", "P1", "P2", "P3", "P4"]
    assert per_seed.seed.nunique() == 30
    assert per_seed.groupby("profile_id").size().to_dict() == {
        "P0": 30, "P1": 30, "P2": 30, "P3": 30, "P4": 30,
    }
    assert per_seed.relative_modularity_loss.max() <= 0.05 + 1e-12
    assert len(figure_data_csv(summary).splitlines()) == 21
    assert figure_data_csv(summary) == figure_data_csv(summary)


def test_plot_uses_four_actual_metric_panels_and_common_profile_labels() -> None:
    summary, _per_seed = prepare_figure_data(load_visualization_config())
    figure = create_figure(summary)
    try:
        assert len(figure.axes) == 4
        assert [axis.get_title(loc="left") for axis in figure.axes] == [
            "(a) Imbalance",
            "(b) Cohesion",
            r"(c) $f_{semantic}$",
            "(d) Relative modularity loss",
        ]
        expected = ["MAX-Q", "BALANCE", "COUPLING", "COHESION", "SEMANTIC"]
        assert all([tick.get_text() for tick in axis.get_xticklabels()] == expected for axis in figure.axes)
    finally:
        plt.close(figure)


def test_outputs_and_provenance_are_deterministic(tmp_path: Path) -> None:
    config = load_visualization_config()
    first = build_figure(
        config, output_root=tmp_path / "a", generated_at="fixed",
        git_commit="abc", git_dirty=True,
    )
    second = build_figure(
        config, output_root=tmp_path / "b", generated_at="fixed",
        git_commit="abc", git_dirty=True,
    )
    for kind in ("data", "svg", "pdf"):
        assert first[kind].read_bytes() == second[kind].read_bytes()
    provenance = json.loads(first["provenance"].read_text())
    assert provenance["profile_count"] == 5
    assert provenance["panel_metrics"] == [
        "imbalance", "cohesion", "f_semantic", "relative_modularity_loss",
    ]
    assert provenance["selected_count_per_profile"] == {
        "P0": 30, "P1": 30, "P2": 30, "P3": 30, "P4": 30,
    }
    assert len(provenance["authoritative_source_commit"]) == 40
    assert set(json.loads((tmp_path / "a/manifest.json").read_text())["figures"]) == {FIGURE_ID}
