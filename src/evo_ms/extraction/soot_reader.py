from pathlib import Path

from evo_ms.extraction.dependency_extractor import load_extracted_subject


def read_normalized_csv(path: str | Path):
    import pandas as pd

    return pd.read_csv(path)


def read_extracted_subject(extracted_dir: str | Path):
    return load_extracted_subject(extracted_dir)
