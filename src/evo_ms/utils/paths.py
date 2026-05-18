from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def config_path(*parts: str) -> Path:
    return repo_root() / "configs" / Path(*parts)
