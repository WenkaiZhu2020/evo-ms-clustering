from pathlib import Path


def read_depends_edges(path: str | Path):
    import pandas as pd

    return pd.read_csv(path)
