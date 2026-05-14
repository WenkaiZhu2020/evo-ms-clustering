"""Coordinate extraction of class-level dependency facts from subject systems."""

from pathlib import Path
from typing import Any


def extract_dependencies(project_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Placeholder extraction entry point for a Java subject system."""
    # TODO: Invoke the selected dependency analyzer and Java parser.
    return {
        "project_dir": str(project_dir),
        "output_dir": str(output_dir),
        "status": "not_implemented",
    }
