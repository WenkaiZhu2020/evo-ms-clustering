"""Placeholder reader for Soot-produced Stage 1 extraction outputs.

The planned Stage 1 extractor is Soot/Shimple. This module will later load
normalized CSV outputs such as class nodes, structural dependencies, and scoped
SSA flow edges. It does not perform Java bytecode analysis itself.
"""

from pathlib import Path


def read_normalized_csv(path: str | Path):
    """Load a Soot-produced normalized CSV artifact."""
    import pandas as pd

    # TODO: Add schema-specific validators for class_nodes, structural
    # dependencies, and scoped SSA flow edges.
    return pd.read_csv(path)
