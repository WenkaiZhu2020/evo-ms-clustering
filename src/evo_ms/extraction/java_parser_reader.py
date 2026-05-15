"""Legacy optional adapter for parser-derived Java class facts."""

from pathlib import Path


def read_class_facts(path: str | Path):
    """Load parser-derived class facts from CSV.

    Soot is the planned main extractor for Stage 1. This reader remains optional
    for older parser exports.
    """
    import pandas as pd

    # TODO: Keep only if older parser exports are needed for comparison.
    return pd.read_csv(path)
