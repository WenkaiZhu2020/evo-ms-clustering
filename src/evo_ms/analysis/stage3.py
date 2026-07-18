"""Final-only Stage 2 versus Stage 3 analysis boundaries."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


FINAL_STAGES = ("stage2", "stage3")


def ensure_final_stages(stages: Iterable[str]) -> tuple[str, ...]:
    observed = tuple(stages)
    if any(stage not in FINAL_STAGES for stage in observed):
        raise ValueError("analysis may compare only Stage 2 and final Stage 3")
    return observed


def ordered_rows(rows: Iterable[Mapping[str, object]], keys: tuple[str, ...] = ("subject", "seed")) -> list[Mapping[str, object]]:
    return sorted(rows, key=lambda row: tuple(str(row.get(key, "")) for key in keys))


def availability(rows: Iterable[Mapping[str, object]], field: str) -> dict[str, int]:
    """Count present and missing values for one saved-artifact field."""
    present = missing = 0
    for row in rows:
        if row.get(field) in (None, ""):
            missing += 1
        else:
            present += 1
    return {"present": present, "missing": missing, "total": present + missing}
