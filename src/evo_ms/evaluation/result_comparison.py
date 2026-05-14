"""Compare pre-experiment and Stage 1 baseline result summaries."""


def compare_metric(metric_name: str, before: float, after: float) -> dict[str, float | str]:
    """Return a small before-after comparison for one metric."""
    return {
        "metric": metric_name,
        "before": before,
        "after": after,
        "delta": after - before,
    }
