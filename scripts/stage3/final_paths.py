"""Final Stage 3 identity and artifact-path guards."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ID = "stage3_declaration_method_body"
REPRESENTATION_ID = "declaration_method_body_v1"
STAGE3_CONFIG = ROOT / "configs/experiments/05_stage3_declaration_method_body.yml"
STAGE3_RESULT_PART = "05_stage3_declaration_method_body"
STAGE3_REPORT_ROOT = ROOT / "reports/stage3"
STAGE3_TEXT_ROOT = ROOT / "data/semantic_text/declaration_method_body"
STAGE3_EMBEDDING_ROOT = ROOT / "data/embeddings/declaration_method_body"
STAGE3_GRAPH_ROOT = ROOT / "data/semantic_graphs/declaration_method_body"
SUBJECTS = ("jpetstore", "daytrader", "xerces")


class FinalStage3PathError(ValueError):
    """Raised when a final Stage 3 operation uses an invalid namespace."""


def _resolved(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def _inside(path: Path, root: Path) -> bool:
    try:
        _resolved(path).relative_to(_resolved(root))
    except ValueError:
        return False
    return True


def stage3_result_root(subject: str) -> Path:
    if subject not in SUBJECTS:
        raise FinalStage3PathError(f"unknown subject: {subject}")
    return ROOT / "results" / subject / STAGE3_RESULT_PART


def stage3_paths(subject: str) -> dict[str, Path]:
    if subject not in SUBJECTS:
        raise FinalStage3PathError(f"unknown subject: {subject}")
    return {
        "semantic_text": STAGE3_TEXT_ROOT / subject / "class_semantic_inputs.csv",
        "embeddings": STAGE3_EMBEDDING_ROOT / subject,
        "semantic_graph": STAGE3_GRAPH_ROOT / subject,
        "results": stage3_result_root(subject),
        "report": STAGE3_REPORT_ROOT,
    }


def assert_write_path(path: Path, *, kind: str = "artifact") -> Path:
    candidate = _resolved(path)
    allowed_roots = (STAGE3_REPORT_ROOT, STAGE3_TEXT_ROOT, STAGE3_EMBEDDING_ROOT, STAGE3_GRAPH_ROOT)
    allowed = any(_inside(candidate, root) for root in allowed_roots)
    allowed = allowed or any(_inside(candidate, stage3_result_root(subject)) for subject in SUBJECTS)
    if not allowed:
        raise FinalStage3PathError(f"final Stage 3 {kind} path is outside the accepted namespace: {candidate}")
    return candidate


assert_stage3_write_path = assert_write_path


def assert_temporary_path(path: Path) -> Path:
    candidate = _resolved(path)
    if _inside(candidate, ROOT):
        raise FinalStage3PathError("reproducibility output must be outside the repository")
    if candidate == Path("/"):
        raise FinalStage3PathError("refusing to use filesystem root as temporary output")
    return candidate


def assert_representation(metadata: Mapping[str, Any]) -> None:
    if metadata.get("representation_id") != REPRESENTATION_ID:
        raise FinalStage3PathError(f"expected representation_id={REPRESENTATION_ID!r}")
    if metadata.get("experiment_id") not in {None, EXPERIMENT_ID}:
        raise FinalStage3PathError(f"metadata belongs to another experiment: {metadata.get('experiment_id')!r}")


def validate_cache_metadata(
    metadata: Mapping[str, Any],
    *,
    subject: str,
    input_hash: str,
    model_identity: str | None = None,
    class_mapping_hash: str | None = None,
) -> None:
    assert_representation(metadata)
    if metadata.get("subject") != subject:
        raise FinalStage3PathError("cached artifact subject mismatch")
    if metadata.get("input_hash") != input_hash:
        raise FinalStage3PathError("cached artifact input hash mismatch")
    if model_identity is not None and metadata.get("model_identity") != model_identity:
        raise FinalStage3PathError("cached model identity mismatch")
    if class_mapping_hash is not None and metadata.get("class_mapping_hash") != class_mapping_hash:
        raise FinalStage3PathError("cached class mapping mismatch")
