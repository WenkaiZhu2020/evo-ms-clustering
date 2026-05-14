"""Read class dependency exports produced by external dependency analyzers."""

from pathlib import Path


def read_depends_edges(path: str | Path):
    """Load a Depends-style edge table from CSV.

    The exact schema will be finalized after the subject extraction pipeline is chosen.
    """
    import pandas as pd

    # TODO: Validate required columns once the Depends export format is fixed.
    return pd.read_csv(path)
