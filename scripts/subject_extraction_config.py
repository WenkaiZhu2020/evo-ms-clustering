#!/usr/bin/env python3
"""Convert subject YAML scope settings into Soot extractor CLI arguments."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex

import yaml


def load_extraction_cli_args(root: Path, subject: str) -> list[str]:
    """Return the normalized Java extractor arguments for one configured subject."""
    config_path = root / "configs" / "subjects" / f"{subject}.yml"
    if not config_path.is_file():
        raise FileNotFoundError(f"missing subject config: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    configured_subject = _required_text(config, "subject")
    if configured_subject != subject:
        raise ValueError(
            f"subject config mismatch: requested {subject}, found {configured_subject}"
        )

    project_root = Path(_required_text(config, "project_root"))
    classes_dir = _project_path(project_root, _required_text(config, "classes_dir"))
    output_dir = Path(_required_text(config, "extracted_output_path"))
    app_packages = _string_list(config, "app_packages", required=True)
    exclude_packages = _string_list(config, "exclude_packages")
    classpath_entries = _string_list(config, "classpath_entries", required=True)
    classpath = os.pathsep.join(
        str(_project_path(project_root, entry)) for entry in classpath_entries
    )

    args = [
        "--subject",
        configured_subject,
        "--classes-dir",
        str(classes_dir),
        "--classpath",
        classpath,
        "--app-packages",
        ",".join(app_packages),
    ]
    if exclude_packages:
        args.extend(["--exclude-packages", ",".join(exclude_packages)])
    args.extend(["--out-dir", str(output_dir)])
    return args


def _project_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def _required_text(config: dict, key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"subject config must define non-empty {key}")
    return value.strip()


def _string_list(config: dict, key: str, required: bool = False) -> list[str]:
    value = config.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"subject config {key} must be a list")
    normalized = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"subject config {key} must contain non-empty strings")
        normalized.append(item.strip())
    if required and not normalized:
        raise ValueError(f"subject config must define non-empty {key}")
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print normalized Soot extractor CLI arguments from a subject config."
    )
    parser.add_argument("--subject", required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    try:
        cli_args = load_extraction_cli_args(args.root, args.subject)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))

    print(shlex.join(cli_args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
