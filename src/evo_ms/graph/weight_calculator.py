"""Calculate edge weights for G_raw and G_ssa class dependency graphs."""

DEFAULT_EVIDENCE_WEIGHTS: dict[str, float] = {
    "type": 1.0,
    "call": 1.0,
    "return_value_flow": 3.0,
    "argument_passing_flow": 3.0,
}


def calculate_edge_weight(
    evidence_types: list[str] | tuple[str, ...],
    weights: dict[str, float] | None = None,
) -> float:
    """Return the additive edge weight for a collection of evidence types."""
    active_weights = weights or DEFAULT_EVIDENCE_WEIGHTS
    return float(sum(active_weights.get(evidence_type, 1.0) for evidence_type in evidence_types))


def normalize_weight(weight: float, maximum: float) -> float:
    """Normalize a positive weight by a positive maximum value."""
    if maximum <= 0:
        raise ValueError("maximum must be positive")
    return float(weight / maximum)
