"""Central path helpers for repository-local experiment assets."""

from pathlib import Path


def repo_root() -> Path:
    """Return the repository root based on this module location."""
    return Path(__file__).resolve().parents[3]


def config_path(*parts: str) -> Path:
    """Return a path under the repository config directory."""
    return repo_root() / "configs" / Path(*parts)
