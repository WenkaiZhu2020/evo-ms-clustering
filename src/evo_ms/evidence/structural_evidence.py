"""Collect structural evidence such as inheritance, calls, and field references."""

from collections.abc import Iterable


def collect_structural_edges(raw_edges: Iterable[tuple[str, str]]) -> list[tuple[str, str, str]]:
    """Convert raw class pairs into typed structural evidence edges."""
    # TODO: Preserve concrete dependency types from extraction outputs.
    return [(source, target, "dependency") for source, target in raw_edges]
