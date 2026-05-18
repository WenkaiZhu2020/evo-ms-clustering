from collections import Counter
from collections.abc import Hashable


def summarize_partition(partition: dict[Hashable, int]) -> dict[str, int]:
    cluster_sizes = Counter(partition.values())
    return {
        "clusters": len(cluster_sizes),
        "nodes": len(partition),
        "largest_cluster_size": max(cluster_sizes.values(), default=0),
    }
