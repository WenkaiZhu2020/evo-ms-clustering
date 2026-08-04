"""Deterministic artifact inventories for final Stage 3 provenance."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


GRAPH_COMPATIBILITY_FIELDS = (
    "contract_version",
    "experiment_name",
    "representation_id",
    "class_scope_digest",
    "semantic_input_aggregate_sha256",
    "embedding_aggregate_sha256",
    "model_name",
    "model_revision",
    "tokenizer_name",
    "tokenizer_revision",
    "tokenizer_max_sequence_length",
    "tokenizer_truncation",
    "pooling",
    "pooling_source",
    "l2_normalize",
    "storage_dtype",
    "similarity",
    "similarity_implementation",
    "top_k",
    "directed_selection_count_per_node",
    "candidate_policy",
    "tie_break",
    "symmetrisation",
    "reciprocal_edge_policy",
    "self_loop_policy",
    "duplicate_edge_policy",
    "edge_weight_rule",
    "edge_weight_threshold",
    "edge_serialization_precision",
)


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact_inventory(root: str | Path) -> list[dict[str, object]]:
    base = Path(root)
    rows = []
    for path in sorted(p for p in base.rglob("*") if p.is_file()):
        rows.append({"path": str(path.relative_to(base)), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return rows


def normalized_graph_compatibility_contract(
    values: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep only scientifically relevant graph-regeneration parameters."""
    missing = [field for field in GRAPH_COMPATIBILITY_FIELDS if field not in values]
    if missing:
        raise ValueError(f"graph compatibility contract is missing fields: {', '.join(missing)}")
    return {field: values[field] for field in GRAPH_COMPATIBILITY_FIELDS}


def graph_compatibility_digest(values: Mapping[str, Any]) -> str:
    """Hash a normalized graph contract, excluding history and machine paths."""
    contract = normalized_graph_compatibility_contract(values)
    payload = json.dumps(
        contract,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
