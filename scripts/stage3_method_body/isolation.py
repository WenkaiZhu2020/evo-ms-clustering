"""Path, representation, and cache guards for the Stage 3B branch.

This module contains routing policy only.  It does not load embeddings,
construct graphs, or run an optimizer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Any


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ID = "stage3_declaration_method_body"
REPRESENTATION_ID = "declaration_method_body_v1"
STAGE3B_CONFIG = ROOT / "configs/experiments/05_stage3_declaration_method_body.yml"

STAGE3A_RESULT_PART = "04_stage3_semantic"
STAGE3B_RESULT_PART = "05_stage3_declaration_method_body"
STAGE3A_REPORT_ROOT = ROOT / "reports/stage3"
STAGE3B_REPORT_ROOT = ROOT / "reports/stage3_method_body"
STAGE3A_DECLARATION_ROOT = ROOT / "data/semantic_inputs"
STAGE3B_TEXT_ROOT = ROOT / "data/semantic_text/declaration_method_body"
STAGE3B_EMBEDDING_ROOT = ROOT / "data/embeddings/declaration_method_body"
STAGE3B_GRAPH_ROOT = ROOT / "data/semantic_graphs/declaration_method_body"

SUBJECTS = ("jpetstore", "daytrader", "xerces")
DECLARATION_FILENAMES = {
    "jpetstore": "jpetstore_class_declarations.csv",
    "daytrader": "daytrader_class_declarations.csv",
    "xerces": "xerces-j_class_declarations.csv",
}


class Stage3BIsolationError(ValueError):
    """Raised when a Stage 3B operation crosses the Stage 3A boundary."""


def _resolved(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def _inside(path: Path, root: Path) -> bool:
    try:
        _resolved(path).relative_to(_resolved(root))
    except ValueError:
        return False
    return True


def stage3b_result_root(subject: str) -> Path:
    if subject not in SUBJECTS:
        raise Stage3BIsolationError(f"unknown Stage 3B subject: {subject}")
    return ROOT / "results" / subject / STAGE3B_RESULT_PART


def stage3b_paths(subject: str) -> dict[str, Path]:
    """Return explicit Stage 3B artifact paths for one subject."""
    if subject not in SUBJECTS:
        raise Stage3BIsolationError(f"unknown Stage 3B subject: {subject}")
    return {
        "semantic_text": STAGE3B_TEXT_ROOT / f"{subject}_semantic_inputs.csv",
        "embeddings": STAGE3B_EMBEDDING_ROOT / subject,
        "semantic_graph": STAGE3B_GRAPH_ROOT / subject,
        "results": stage3b_result_root(subject),
        "report": STAGE3B_REPORT_ROOT / subject,
        "log": STAGE3B_REPORT_ROOT / "logs" / subject,
    }


def declaration_source_path(subject: str) -> Path:
    """Return the only Stage 3A path that Stage 3B input construction may read."""
    if subject not in DECLARATION_FILENAMES:
        raise Stage3BIsolationError(f"unknown declaration subject: {subject}")
    return STAGE3A_DECLARATION_ROOT / DECLARATION_FILENAMES[subject]


def assert_declaration_source(path: Path, subject: str) -> Path:
    expected = declaration_source_path(subject)
    if _resolved(path) != _resolved(expected):
        raise Stage3BIsolationError(
            "Stage 3B declaration input must use the explicit frozen declaration "
            f"source {expected}; got {path}"
        )
    return expected


def assert_stage3b_write_path(path: Path, *, kind: str | None = None) -> Path:
    """Reject writes into any Stage 3A report/result namespace."""
    candidate = _resolved(path)
    if _inside(candidate, STAGE3A_REPORT_ROOT):
        raise Stage3BIsolationError(f"Stage 3B write under frozen Stage 3A reports: {candidate}")
    for subject in SUBJECTS:
        stage3a_result = ROOT / "results" / subject / STAGE3A_RESULT_PART
        if _inside(candidate, stage3a_result):
            raise Stage3BIsolationError(
                f"Stage 3B write under frozen Stage 3A results: {candidate}"
            )
    allowed_roots = (STAGE3B_REPORT_ROOT, STAGE3B_TEXT_ROOT, STAGE3B_EMBEDDING_ROOT, STAGE3B_GRAPH_ROOT)
    allowed = any(_inside(candidate, root) for root in allowed_roots)
    if not allowed:
        allowed = any(_inside(candidate, stage3b_result_root(subject)) for subject in SUBJECTS)
    if not allowed:
        raise Stage3BIsolationError(
            f"Stage 3B {kind or 'artifact'} path is outside its explicit namespace: {candidate}"
        )
    return candidate


def assert_representation(metadata: Mapping[str, Any]) -> None:
    actual = metadata.get("representation_id")
    if actual != REPRESENTATION_ID:
        raise Stage3BIsolationError(
            f"expected representation_id={REPRESENTATION_ID!r}, got {actual!r}; "
            "Stage 3A artifacts cannot be used as Stage 3B artifacts"
        )
    if metadata.get("experiment_id") not in {None, EXPERIMENT_ID}:
        raise Stage3BIsolationError(
            f"metadata belongs to a different experiment: {metadata.get('experiment_id')!r}"
        )


def validate_cache_metadata(
    metadata: Mapping[str, Any],
    *,
    subject: str,
    input_hash: str,
    model_identity: str | None = None,
    class_mapping_hash: str | None = None,
) -> None:
    """Require all identity fields before a Stage 3B cache is reused."""
    assert_representation(metadata)
    if metadata.get("subject") != subject:
        raise Stage3BIsolationError("cached artifact subject does not match Stage 3B request")
    if metadata.get("input_hash") != input_hash:
        raise Stage3BIsolationError("cached artifact input hash does not match Stage 3B input")
    if model_identity is not None and metadata.get("model_identity") != model_identity:
        raise Stage3BIsolationError("cached artifact model identity does not match Stage 3B request")
    if class_mapping_hash is not None and metadata.get("class_mapping_hash") != class_mapping_hash:
        raise Stage3BIsolationError("cached artifact class mapping does not match Stage 3B request")


def reject_stage3a_artifact(metadata: Mapping[str, Any]) -> None:
    """Alias used at embedding/graph/result boundaries for clear failures."""
    assert_representation(metadata)
