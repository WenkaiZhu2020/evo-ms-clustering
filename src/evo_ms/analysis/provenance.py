"""Deterministic artifact inventories for final Stage 3 provenance."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact_inventory(root: str | Path) -> list[dict[str, object]]:
    base = Path(root)
    rows = []
    for path in sorted(p for p in base.rglob("*") if p.is_file()):
        rows.append({"path": str(path.relative_to(base)), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return rows
