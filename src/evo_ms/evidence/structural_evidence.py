from collections.abc import Iterable


def collect_structural_edges(raw_edges: Iterable[tuple[str, str]]) -> list[tuple[str, str, str]]:
    return [(source, target, "dependency") for source, target in raw_edges]
