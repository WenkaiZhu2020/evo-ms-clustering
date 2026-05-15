"""Legacy optional adapter for Depends-style dependency exports."""

from pathlib import Path


def read_depends_edges(path: str | Path):
    """Load a Depends-style edge table from CSV.

    Soot is the planned main extractor for Stage 1. This reader remains optional
    for older dependency export experiments.
    """
    import pandas as pd

    # TODO: Keep only if older dependency exports are needed for comparison.
    return pd.read_csv(path)
