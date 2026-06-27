"""Summarize class membership for generated Leiden clusters."""

import pandas as pd


def summarize_clusters(clusters: pd.DataFrame) -> pd.DataFrame:
    """Return cluster sizes and class-name lists for reportable CSV summaries."""
    _validate_clusters(clusters)
    summary = (
        clusters.assign(class_name=clusters["class_name"].astype(str))
        .groupby("cluster_id", as_index=False)
        .agg(
            cluster_size=("class_id", "count"),
            class_names=("class_name", lambda names: ";".join(sorted(names))),
        )
    )
    return summary.loc[:, ["cluster_id", "cluster_size", "class_names"]].sort_values(
        "cluster_id",
    ).reset_index(drop=True)


def _validate_clusters(clusters: pd.DataFrame) -> None:
    missing = [column for column in ["class_id", "class_name", "cluster_id"] if column not in clusters.columns]
    if missing:
        raise ValueError(f"clusters is missing required columns: {', '.join(missing)}")
