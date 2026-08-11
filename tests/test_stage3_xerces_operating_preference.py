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


def test_authoritative_candidate_pool_and_p0_p4_selections() -> None:
    config = load_visualization_config()
    candidates, selected = prepare_figure_data(config)
    assert len(candidates) == 147 and candidates.seed.nunique() == 30
    assert selected.groupby("profile_id").size().to_dict() == {
        "P0": 30, "P1": 30, "P2": 30, "P3": 30, "P4": 30,
    }
    assert candidates.relative_modularity_loss.max() <= 0.05 + 1e-12
    assert figure_data_csv(candidates, selected) == figure_data_csv(candidates, selected)


def test_plot_uses_imbalance_and_cohesion_and_is_compact() -> None:
    candidates, selected = prepare_figure_data(load_visualization_config())
    figure = create_figure(candidates, selected)
    try:
        assert len(figure.axes) == 1
        axis = figure.axes[0]
        assert axis.get_xlabel() == "Imbalance (lower is preferred)"
        assert axis.get_ylabel() == "Cohesion (higher is preferred)"
        legend = [text.get_text() for text in axis.get_legend().get_texts()]
        assert all(any(item.startswith(profile) for item in legend) for profile in ("P0", "P1", "P2", "P3", "P4"))
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
    assert provenance["candidate_count"] == 147
    assert provenance["selected_count_per_profile"] == {
        "P0": 30, "P1": 30, "P2": 30, "P3": 30, "P4": 30,
    }
    assert len(provenance["authoritative_source_commit"]) == 40
    assert set(json.loads((tmp_path / "a/manifest.json").read_text())["figures"]) == {FIGURE_ID}
