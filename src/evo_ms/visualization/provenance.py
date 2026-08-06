"""Deterministic and machine-independent figure provenance records."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from collections.abc import Iterable, Sequence

from .model import ProvenanceRecord


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _safe_relative_text(value: str, label: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be a safe relative path: {value}")
    return path.as_posix()


def _relative_path(path: Path, repository_root: Path, artifact_root: Path | None) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(repository_root):
        return resolved.relative_to(repository_root).as_posix()
    if artifact_root is not None and resolved.is_relative_to(artifact_root):
        return resolved.relative_to(artifact_root).as_posix()
    raise ValueError(f"provenance path is outside the repository and artifact root: {path}")


def _git_state(repository_root: Path) -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(repository_root), "status", "--porcelain=v1", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return commit, bool(status.strip())


def _normalise_command(
    command: Sequence[str], repository_root: Path, artifact_root: Path | None
) -> tuple[str, ...]:
    normalized: list[str] = []
    for index, token in enumerate(command):
        candidate = Path(token)
        if index == 0:
            normalized.append(candidate.name)
        elif candidate.is_absolute():
            normalized.append(_relative_path(candidate, repository_root, artifact_root))
        else:
            normalized.append(token)
    return tuple(normalized)


def build_provenance(
    *,
    figure_id: str,
    stage: str,
    generator: str,
    repository_root: str | Path,
    input_files: Iterable[str | Path],
    config_files: Iterable[str | Path],
    dot_path: str | Path,
    graphviz_engine: str,
    graphviz_version: str,
    render_commands: Iterable[Sequence[str]],
    generated_outputs: Iterable[str | Path],
    artifact_root: str | Path | None = None,
    generated_at: str | None = None,
    git_commit: str | None = None,
    git_dirty: bool | None = None,
) -> ProvenanceRecord:
    root = Path(repository_root).resolve()
    artifacts = None if artifact_root is None else Path(artifact_root).resolve()
    actual_commit, actual_dirty = _git_state(root) if git_commit is None or git_dirty is None else (git_commit, git_dirty)
    commit = actual_commit if git_commit is None else git_commit
    dirty = actual_dirty if git_dirty is None else git_dirty

    inputs = sorted((Path(path) for path in input_files), key=lambda path: _relative_path(path, root, artifacts))
    configs = sorted((Path(path) for path in config_files), key=lambda path: _relative_path(path, root, artifacts))
    input_rows = tuple((_relative_path(path, root, artifacts), sha256_file(path)) for path in inputs)
    config_rows = tuple((_relative_path(path, root, artifacts), sha256_file(path)) for path in configs)
    outputs = tuple(sorted(_relative_path(Path(path), root, artifacts) for path in generated_outputs))
    commands = tuple(
        sorted(
            (_normalise_command(command, root, artifacts) for command in render_commands),
            key=lambda command: tuple(command),
        )
    )
    timestamp = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return ProvenanceRecord(
        figure_id=figure_id,
        stage=stage,
        generator=_safe_relative_text(generator, "generator"),
        git_commit=commit,
        git_dirty=dirty,
        input_files=tuple(path for path, _digest in input_rows),
        input_sha256=input_rows,
        config_files=tuple(path for path, _digest in config_rows),
        config_sha256=config_rows,
        dot_sha256=sha256_file(dot_path),
        graphviz_engine=graphviz_engine,
        graphviz_version=graphviz_version,
        render_command=commands,
        generated_outputs=outputs,
        generated_at=timestamp,
    )


def provenance_json(record: ProvenanceRecord) -> str:
    return json.dumps(record.as_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_provenance(path: str | Path, record: ProvenanceRecord) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(provenance_json(record))
        os.replace(temporary_name, output)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise
    return output
