from evo_ms.analysis.stability import neighbour_retention_ratio
from evo_ms.analysis.stability import partition_change_fraction
from evo_ms.analysis.stability import summarize_retention
from evo_ms.analysis.statistics import conditional_summary
from evo_ms.analysis.statistics import paired_summary
from evo_ms.analysis.statistics import spearman_summary


def test_paired_summary_is_deterministic():
    rows = [{"left": 1, "right": 3}, {"left": 2, "right": 2}]
    assert paired_summary(rows, "left", "right")["mean_difference"] == 1.0


def test_conditional_summary_has_stable_group_order():
    rows = [
        {"group": "b", "value": 2},
        {"group": "a", "value": 1},
    ]
    assert [row["group"] for row in conditional_summary(rows, "group", "value")] == ["a", "b"]


def test_stability_summary_and_change_fraction():
    baseline = {"a": {"b", "c"}, "b": {"a"}}
    observed = {"a": {"b"}, "b": {"a"}}
    ratios = neighbour_retention_ratio(baseline, observed)
    assert summarize_retention(ratios)["mean"] == 0.75
    assert partition_change_fraction(baseline, observed) == 0.5


def test_spearman_reports_constant_input_without_warning_dependent_values():
    result = spearman_summary([1, 1], [1, 2])
    assert result["rho"] is None
    assert result["undefined_reason"] == "constant_input"
