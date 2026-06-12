from collections.abc import Mapping
import math

DEFAULT_EVIDENCE_WEIGHTS: dict[str, float] = {
    "type": 1.0,
    "call": 2.0,
    "return_value_flow": 3.0,
    "argument_passing_flow": 3.0,
}


def calculate_raw_weight(type_weight: object = 0.0, call_weight: object = 0.0) -> float:
    return _validated_weight(type_weight, "type_weight") + _validated_weight(
        call_weight,
        "call_weight",
    )


def calculate_ssa_flow_weight(
    return_flow_weight: object = 0.0,
    argument_flow_weight: object = 0.0,
    ssa_lambda: object = 1.0,
) -> float:
    """Return the lambda-scaled SSA contribution stored as ssa_flow_weight."""
    raw_ssa_flow_weight = (
        _validated_weight(return_flow_weight, "return_flow_weight")
        + _validated_weight(
            argument_flow_weight,
            "argument_flow_weight",
        )
    )
    return _validated_weight(ssa_lambda, "ssa_lambda") * raw_ssa_flow_weight


def calculate_g_ssa_weight(
    type_weight: object = 0.0,
    call_weight: object = 0.0,
    return_flow_weight: object = 0.0,
    argument_flow_weight: object = 0.0,
    ssa_lambda: object = 1.0,
) -> float:
    return calculate_raw_weight(type_weight, call_weight) + calculate_ssa_flow_weight(
        return_flow_weight,
        argument_flow_weight,
        ssa_lambda,
    )


def calculate_stage1_edge_weights(
    weights: Mapping[str, object],
    ssa_lambda: object = 1.0,
) -> dict[str, float]:
    """Return raw weight, scaled SSA contribution, and total G_ssa weight."""
    raw_weight = calculate_raw_weight(
        weights.get("type_weight", 0.0),
        weights.get("call_weight", 0.0),
    )
    scaled_ssa_flow_weight = calculate_ssa_flow_weight(
        weights.get("return_flow_weight", 0.0),
        weights.get("argument_flow_weight", 0.0),
        ssa_lambda,
    )
    return {
        "raw_weight": raw_weight,
        "ssa_flow_weight": scaled_ssa_flow_weight,
        "g_ssa_weight": raw_weight + scaled_ssa_flow_weight,
    }


def calculate_edge_weight(
    evidence_types: list[str] | tuple[str, ...],
    weights: dict[str, float] | None = None,
) -> float:
    active_weights = weights or DEFAULT_EVIDENCE_WEIGHTS
    total = 0.0
    for evidence_type in evidence_types:
        if evidence_type not in active_weights:
            allowed = ", ".join(sorted(active_weights))
            raise ValueError(f"unsupported evidence type: {evidence_type}; expected one of: {allowed}")
        total += _validated_weight(active_weights[evidence_type], evidence_type)
    return total


def normalize_weight(weight: float, maximum: float) -> float:
    if maximum <= 0:
        raise ValueError("maximum must be positive")
    return float(weight / maximum)


def _validated_weight(value: object, name: str) -> float:
    if value is None:
        return 0.0
    if isinstance(value, str) and value.strip() == "":
        return 0.0
    try:
        weight = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if math.isnan(weight):
        return 0.0
    if weight < 0:
        raise ValueError(f"{name} must be non-negative")
    return weight
