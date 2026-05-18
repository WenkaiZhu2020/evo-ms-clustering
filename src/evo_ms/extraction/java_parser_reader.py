from pathlib import Path


def read_class_facts(path: str | Path):
    import pandas as pd

    return pd.read_csv(path)
