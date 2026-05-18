def compare_metric(metric_name: str, before: float, after: float) -> dict[str, float | str]:
    return {
        "metric": metric_name,
        "before": before,
        "after": after,
        "delta": after - before,
    }
