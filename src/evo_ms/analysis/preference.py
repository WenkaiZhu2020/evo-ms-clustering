"""Final-only preference-response analysis policy."""

from __future__ import annotations

FINAL_STAGE_LABELS = ("stage2", "stage3")


def validate_stage_labels(labels: list[str]) -> None:
    unexpected = sorted(set(labels) - set(FINAL_STAGE_LABELS))
    if unexpected:
        raise ValueError(f"preference analysis contains obsolete stages: {unexpected}")
