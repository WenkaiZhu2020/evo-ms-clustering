from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


DEFAULT_EXPECTED_EXTRACTED_EVIDENCE_WEIGHTS: dict[str, float] = {
    "type_dependency": 1.0,
    "method_call": 2.0,
    "return_value_flow": 3.0,
    "argument_passing_flow": 3.0,
}


def expected_extracted_evidence_weights(config: Mapping[str, object]) -> dict[str, float]:
    values = config.get("expected_extracted_evidence_weights")
    if values is None:
        return dict(DEFAULT_EXPECTED_EXTRACTED_EVIDENCE_WEIGHTS)
    if not isinstance(values, Mapping):
        raise ValueError("expected_extracted_evidence_weights must be a mapping")
    expected = dict(DEFAULT_EXPECTED_EXTRACTED_EVIDENCE_WEIGHTS)
    for key, value in values.items():
        if key not in expected:
            allowed = ", ".join(sorted(expected))
            raise ValueError(
                f"unsupported expected evidence weight key: {key}; expected one of: {allowed}"
            )
        expected[key] = _as_float(value, key)
    return expected


def validate_extracted_evidence_weights(
    structural_dependencies: pd.DataFrame,
    ssa_flow_edges: pd.DataFrame,
    expected_weights: Mapping[str, object],
    subject: str | None = None,
) -> None:
    """Verify embedded extracted CSV row weights without changing them."""
    expected = {
        key: _as_float(value, key)
        for key, value in expected_weights.items()
    }
    missing = sorted(set(DEFAULT_EXPECTED_EXTRACTED_EVIDENCE_WEIGHTS) - set(expected))
    if missing:
        raise ValueError(f"expected evidence weights missing keys: {', '.join(missing)}")

    errors: list[str] = []
    _validate_channel(
        structural_dependencies,
        selector_column="dependency_type",
        selector_value="type",
        weight_column="weight",
        expected=expected["type_dependency"],
        label="type_dependency",
        errors=errors,
    )
    _validate_channel(
        structural_dependencies,
        selector_column="dependency_type",
        selector_value="call",
        weight_column="weight",
        expected=expected["method_call"],
        label="method_call",
        errors=errors,
    )
    _validate_channel(
        ssa_flow_edges,
        selector_column="flow_type",
        selector_value="return_value_flow",
        weight_column="weight",
        expected=expected["return_value_flow"],
        label="return_value_flow",
        errors=errors,
    )
    _validate_channel(
        ssa_flow_edges,
        selector_column="flow_type",
        selector_value="argument_passing_flow",
        weight_column="weight",
        expected=expected["argument_passing_flow"],
        label="argument_passing_flow",
        errors=errors,
    )
    if errors:
        prefix = f"{subject}: " if subject else ""
        raise ValueError(prefix + "unexpected extracted evidence row weights: " + "; ".join(errors))


def _validate_channel(
    frame: pd.DataFrame,
    selector_column: str,
    selector_value: str,
    weight_column: str,
    expected: float,
    label: str,
    errors: list[str],
) -> None:
    if selector_column not in frame.columns:
        errors.append(f"{label} missing {selector_column} column")
        return
    if weight_column not in frame.columns:
        errors.append(f"{label} missing {weight_column} column")
        return
    row_mask = frame[selector_column].astype(str).eq(selector_value)
    weights = pd.to_numeric(frame.loc[row_mask, weight_column], errors="coerce")
    if weights.empty:
        return
    if weights.isna().any():
        errors.append(f"{label} has non-numeric weights")
        return
    observed = sorted({float(value) for value in weights.tolist()})
    if observed != [expected]:
        errors.append(f"{label} expected {expected}, observed {observed}")


def _as_float(value: object, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
