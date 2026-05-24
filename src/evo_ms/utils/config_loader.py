from pathlib import Path
from typing import Any


def load_yaml(path: str | Path) -> dict[str, Any]:
    import yaml

    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
