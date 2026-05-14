"""Compute basic metrics for cluster partitions."""

from collections import Counter
from collections.abc import Hashable


def partition_size_metrics(partition: dict[Hashable, int]) -> dict[str, float]:
    """Return simple size metrics for a partition."""
    sizes = Counter(partition.values())
    if not sizes:
        return {"clusters": 0, "average_cluster_size": 0.0}
    return {
        "clusters": len(sizes),
        "average_cluster_size": len(partition) / len(sizes),
    }
