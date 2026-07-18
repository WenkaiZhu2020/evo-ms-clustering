"""Representation-independent input and provenance helpers."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping


REPRESENTATION_ID = "declaration_method_body_v1"
EXPERIMENT_ID = "stage3_declaration_method_body"


def canonical_text_hash(semantic_text: str) -> str:
    """Hash the exact UTF-8 semantic text bytes used by the embedding stage."""
    return hashlib.sha256(semantic_text.encode("utf-8")).hexdigest()


def aggregate_input_hash(rows: Iterable[Mapping[str, str]]) -> str:
    """Hash sorted ``class_id<TAB>input_hash<LF>`` rows."""
    payload = "".join(
        f"{row['class_id']}\t{row['input_hash']}\n"
        for row in sorted(rows, key=lambda row: str(row["class_id"]))
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_identity(metadata: Mapping[str, object]) -> None:
    if metadata.get("experiment_id") not in {None, EXPERIMENT_ID}:
        raise ValueError("artifact belongs to a different experiment")
    if metadata.get("representation_id") != REPRESENTATION_ID:
        raise ValueError("artifact does not belong to the final Stage 3 representation")
