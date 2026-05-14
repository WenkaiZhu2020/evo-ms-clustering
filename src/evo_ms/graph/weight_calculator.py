"""Calculate edge weights for raw and enriched class dependency graphs."""

DEFAULT_EVIDENCE_WEIGHTS: dict[str, float] = {
    "dependency": 1.0,
    "call": 1.0,
    "inheritance": 1.5,
    "field_access": 0.75,
    "flow": 1.25,
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
