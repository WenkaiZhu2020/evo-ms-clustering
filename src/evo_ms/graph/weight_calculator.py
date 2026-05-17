"""Calculate Stage 1 edge weights for G_raw and G_ssa class graphs."""

from collections.abc import Mapping
import math

DEFAULT_EVIDENCE_WEIGHTS: dict[str, float] = {
    "type": 1.0,
    "call": 2.0,
    "return_value_flow": 3.0,
    "argument_passing_flow": 3.0,
}


def calculate_raw_weight(type_weight: object = 0.0, call_weight: object = 0.0) -> float:
    """Return the structural G_raw edge weight."""
    return _validated_weight(type_weight, "type_weight") + _validated_weight(
        call_weight,
        "call_weight",
    )


def calculate_ssa_flow_weight(
    return_flow_weight: object = 0.0,
    argument_flow_weight: object = 0.0,
) -> float:
    """Return the class-level Soot/Shimple-derived SSA flow weight."""
    return _validated_weight(return_flow_weight, "return_flow_weight") + _validated_weight(
        argument_flow_weight,
        "argument_flow_weight",
    )


def calculate_g_ssa_weight(
    type_weight: object = 0.0,
    call_weight: object = 0.0,
    return_flow_weight: object = 0.0,
    argument_flow_weight: object = 0.0,
) -> float:
    """Return the total G_ssa edge weight."""
    return calculate_raw_weight(type_weight, call_weight) + calculate_ssa_flow_weight(
        return_flow_weight,
        argument_flow_weight,
    )


def calculate_stage1_edge_weights(weights: Mapping[str, object]) -> dict[str, float]:
    """Calculate all Stage 1 edge weight columns from component weights.

    Missing component weights are treated as zero. The current Stage 1 design
    uses only structural type/call evidence and return/argument SSA flow
    evidence; no shared-domain component is required.
    """
    raw_weight = calculate_raw_weight(
        weights.get("type_weight", 0.0),
        weights.get("call_weight", 0.0),
    )
    ssa_flow_weight = calculate_ssa_flow_weight(
        weights.get("return_flow_weight", 0.0),
        weights.get("argument_flow_weight", 0.0),
    )
    return {
        "raw_weight": raw_weight,
        "ssa_flow_weight": ssa_flow_weight,
        "g_ssa_weight": raw_weight + ssa_flow_weight,
    }


def calculate_edge_weight(
    evidence_types: list[str] | tuple[str, ...],
    weights: dict[str, float] | None = None,
) -> float:
    """Return the additive edge weight for a collection of evidence types."""
    active_weights = weights or DEFAULT_EVIDENCE_WEIGHTS
    total = 0.0
    for evidence_type in evidence_types:
        if evidence_type not in active_weights:
            allowed = ", ".join(sorted(active_weights))
            raise ValueError(f"unsupported evidence type: {evidence_type}; expected one of: {allowed}")
        total += _validated_weight(active_weights[evidence_type], evidence_type)
    return total


def normalize_weight(weight: float, maximum: float) -> float:
    """Normalize a positive weight by a positive maximum value."""
    if maximum <= 0:
        raise ValueError("maximum must be positive")
    return float(weight / maximum)


def _validated_weight(value: object, name: str) -> float:
    """Return a numeric non-negative weight, treating missing values as zero."""
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
