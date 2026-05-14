"""Load YAML configuration files for subjects and experiments."""

from pathlib import Path
from typing import Any


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file and return an empty mapping for empty documents."""
    import yaml

    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
