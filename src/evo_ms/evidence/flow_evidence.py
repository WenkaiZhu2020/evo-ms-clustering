"""Collect scoped SSA flow evidence for G_ssa graph construction."""

from collections.abc import Iterable

ALLOWED_SSA_FLOW_TYPES = frozenset({"return_value_flow", "argument_passing_flow"})


def validate_ssa_flow_type(flow_type: str) -> str:
    """Validate a scoped SSA flow type."""
    if flow_type not in ALLOWED_SSA_FLOW_TYPES:
        allowed = ", ".join(sorted(ALLOWED_SSA_FLOW_TYPES))
        raise ValueError(f"unsupported SSA flow type: {flow_type}; expected one of: {allowed}")
    return flow_type


def collect_flow_edges(class_names: Iterable[str]) -> list[tuple[str, str, str]]:
    """Placeholder for Soot/Shimple-derived class-level SSA flow evidence."""
    # TODO: Load return-value and argument-passing flow from normalized Soot outputs.
    _ = list(class_names)
    return []
