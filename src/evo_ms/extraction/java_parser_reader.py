"""Read parser-derived Java class facts for graph construction."""

from pathlib import Path


def read_class_facts(path: str | Path):
    """Load parser-derived class facts from CSV."""
    import pandas as pd

    # TODO: Replace this with the final Java parser output schema.
    return pd.read_csv(path)
