from collections.abc import Iterable

from evo_ms.evidence.ssa_flow_evidence import ALLOWED_SSA_FLOW_TYPES, validate_ssa_flow_type


def collect_flow_edges(class_names: Iterable[str]) -> list[tuple[str, str, str]]:
    _ = list(class_names)
    return []
