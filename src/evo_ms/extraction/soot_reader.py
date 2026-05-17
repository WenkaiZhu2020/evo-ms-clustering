"""Reader helpers for Soot-produced Stage 1 extraction outputs.

The planned Stage 1 extractor is Soot/Shimple. This module will later load
normalized CSV outputs such as class nodes, structural dependencies, and scoped
SSA flow edges. It does not perform Java bytecode analysis itself.
"""

from pathlib import Path

from evo_ms.extraction.dependency_extractor import load_extracted_subject


def read_normalized_csv(path: str | Path):
    """Load a Soot-produced normalized CSV artifact."""
    import pandas as pd

    return pd.read_csv(path)


def read_extracted_subject(extracted_dir: str | Path):
    """Load and validate all normalized Soot CSV files for one subject."""
    return load_extracted_subject(extracted_dir)
