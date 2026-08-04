from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from evo_ms.analysis.stage3_reporting import (
    ACTIVE_STAGE2_PROFILE,
    EXPECTED_PAIRS,
    PROJECTED_HV_SOURCE,
    _validate_pairs,
    build_formal_tests,
    build_input_control_summary,
    build_partition_similarity,
    build_selected_fsemantic_pairs,
    canonical_partition_key,
    holm_adjust,
    load_active_stage2_profile,
    load_projected_hv_pairs,
    paired_wilcoxon,
    rank_biserial,
    reporting_outputs,
)
from evo_ms.evaluation.partition_ops import changed_partition_ratio


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def selected_pairs() -> pd.DataFrame:
    return build_selected_fsemantic_pairs(ROOT)


@pytest.fixture(scope="module")
def formal_tests(selected_pairs: pd.DataFrame) -> pd.DataFrame:
    return build_formal_tests(ROOT, selected_pairs)


def test_active_stage2_profile_is_exact_five_percent_source() -> None:
    frame = load_active_stage2_profile(ROOT)
    assert len(frame) == 90
    assert set(zip(frame["subject"], frame["seed"], strict=True)) == EXPECTED_PAIRS
    assert set(frame["budget"]) == {0.05}
    assert frame["canonical_operating_profile"].all()
    assert ACTIVE_STAGE2_PROFILE.as_posix() == (
        "results/stage2/cross_subject/operating_profile/"
        "canonical_operating_solution_per_seed.csv"
    )


def test_projected_hv_loader_reads_only_accepted_pair_columns() -> None:
    frame = load_projected_hv_pairs(ROOT)
    assert list(frame.columns) == [
        "subject",
        "seed",
        "stage2_hv",
        "stage3_projected_hv",
    ]
    assert len(frame) == 90
    assert PROJECTED_HV_SOURCE.as_posix().endswith("stage2_comparison/paired_per_seed.csv")


def test_selected_fsemantic_is_recomputed_for_all_paired_seeds(
    selected_pairs: pd.DataFrame,
) -> None:
    assert len(selected_pairs) == 90
    assert set(zip(selected_pairs["subject"], selected_pairs["seed"], strict=True)) == EXPECTED_PAIRS
    assert set(selected_pairs["stage2_profile_id"]) == {"stage2_5pct_modularity_band"}
    assert set(selected_pairs["stage3_profile_id"]) == {
        "stage3_final_projected_front_operating_selector"
    }
    sources = " ".join(selected_pairs["stage3_profile_source"])
    assert "results/stage3/subjects/" in sources
    assert "stage3a" not in sources.lower()
    assert "04_stage3_semantic" not in sources.lower()


def test_seed_alignment_fails_on_missing_or_duplicate_rows() -> None:
    complete = pd.DataFrame(sorted(EXPECTED_PAIRS), columns=["subject", "seed"])
    with pytest.raises(ValueError, match="seed alignment failed"):
        _validate_pairs(complete.iloc[:-1], "missing seed")
    duplicated = pd.concat([complete, complete.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        _validate_pairs(duplicated, "duplicate seed")


def test_confirmatory_family_is_exactly_six_unique_rows(formal_tests: pd.DataFrame) -> None:
    expected = {
        (subject, metric)
        for subject in ("jpetstore", "daytrader", "xerces")
        for metric in ("projected_hypervolume", "selected_f_semantic")
    }
    assert len(formal_tests) == 6
    assert set(zip(formal_tests["subject"], formal_tests["metric"], strict=True)) == expected
    assert set(formal_tests["correction_family"]) == {"six confirmatory rows only"}
    assert set(formal_tests["n_pairs"]) == {30}


def test_holm_adjustment_covers_only_the_six_formal_p_values(
    formal_tests: pd.DataFrame,
) -> None:
    expected = holm_adjust(formal_tests["raw_p_value"].tolist())
    assert formal_tests["holm_adjusted_p_value"].tolist() == pytest.approx(expected)
    assert len(expected) == 6


def test_formal_p_values_and_effect_sizes_match_frozen_inputs(
    formal_tests: pd.DataFrame,
) -> None:
    indexed = formal_tests.set_index(["subject", "metric"])
    expected = {
        ("jpetstore", "projected_hypervolume"): (
            9.220093488693237e-06,
            4.6100467443466187e-05,
            -0.8451612903225807,
        ),
        ("jpetstore", "selected_f_semantic"): (
            0.136610162687313,
            0.546440650749252,
            -0.30752688172043013,
        ),
        ("daytrader", "projected_hypervolume"): (
            0.40449450351297855,
            0.8089890070259571,
            0.17849462365591398,
        ),
        ("daytrader", "selected_f_semantic"): (
            0.23665234446525574,
            0.7099570333957672,
            -0.25161290322580643,
        ),
        ("xerces", "projected_hypervolume"): (
            0.8393927440047264,
            0.8393927440047264,
            0.04516129032258064,
        ),
        ("xerces", "selected_f_semantic"): (
            1.862645149230957e-09,
            1.1175870895385742e-08,
            -1.0,
        ),
    }
    for key, values in expected.items():
        row = indexed.loc[key]
        assert (
            row["raw_p_value"],
            row["holm_adjusted_p_value"],
            row["rank_biserial"],
        ) == pytest.approx(values)


def test_wilcoxon_zero_handling_and_rank_biserial_are_explicit() -> None:
    assert paired_wilcoxon([0.0, 0.0]) == (0.0, 1.0)
    statistic, p_value = paired_wilcoxon([0.0, 1.0, -2.0])
    assert statistic >= 0.0
    assert 0.0 <= p_value <= 1.0
    assert rank_biserial([0.0, 1.0, 2.0]) == 1.0
    assert rank_biserial([0.0, -1.0, -2.0]) == -1.0
    assert rank_biserial([0.0, 0.0]) == 0.0


def test_better_tie_worse_counts_follow_metric_direction(
    formal_tests: pd.DataFrame,
) -> None:
    hv = formal_tests.loc[
        (formal_tests["subject"] == "jpetstore")
        & (formal_tests["metric"] == "projected_hypervolume")
    ].iloc[0]
    semantic = formal_tests.loc[
        (formal_tests["subject"] == "xerces")
        & (formal_tests["metric"] == "selected_f_semantic")
    ].iloc[0]
    assert (hv["better_count"], hv["tie_count"], hv["worse_count"]) == (4, 0, 26)
    assert hv["comparison_direction"] == "higher_is_better"
    assert (semantic["better_count"], semantic["tie_count"], semantic["worse_count"]) == (
        30,
        0,
        0,
    )
    assert semantic["comparison_direction"] == "lower_is_better"


def test_partition_similarity_terms_are_distinct() -> None:
    nodes = pd.DataFrame(
        {
            "class_id": ["a", "b", "c", "d"],
            "class_name": ["a", "b", "c", "d"],
        }
    )
    left = pd.DataFrame({"class_id": ["a", "b", "c", "d"], "cluster_id": [0, 0, 1, 1]})
    right = pd.DataFrame({"class_id": ["a", "b", "c", "d"], "cluster_id": [7, 7, 8, 9]})
    changed_count, class_level_ratio = changed_partition_ratio(nodes, left, right)
    exact_identical = canonical_partition_key(left) == canonical_partition_key(right)
    non_identical_pair_proportion = float(not exact_identical)
    ari = adjusted_rand_score(left["cluster_id"], right["cluster_id"])
    nmi = normalized_mutual_info_score(left["cluster_id"], right["cluster_id"])
    assert exact_identical is False
    assert non_identical_pair_proportion == 1.0
    assert changed_count == 2
    assert class_level_ratio == 0.5
    assert ari != non_identical_pair_proportion
    assert nmi != non_identical_pair_proportion


def test_partition_reporting_uses_non_identical_pair_name() -> None:
    per_seed, summary = build_partition_similarity(ROOT)
    assert "non_identical_pair_proportion" in summary.columns
    assert "changed_ratio" not in summary.columns
    assert "changed_partition_ratio" in per_seed.columns
    assert set(summary["exact_identical_count"]) == {0}
    assert set(summary["non_identical_pair_proportion"]) == {1.0}


def test_model_truncation_and_body_budget_are_separate() -> None:
    controls = build_input_control_summary(ROOT).set_index("subject")
    assert set(controls["embedding_model_max_tokens"]) == {32768}
    assert set(controls["model_tokenizer_truncation_count"]) == {0}
    assert set(controls["embedding_context_limit_exceeded_count"]) == {0}
    assert controls["body_budget_capped_classes"].to_dict() == {
        "jpetstore": 0,
        "daytrader": 1,
        "xerces": 7,
    }
    assert controls["body_tokens_removed_by_budget"].to_dict() == {
        "jpetstore": 0,
        "daytrader": 31,
        "xerces": 753,
    }


def test_report_regeneration_is_deterministic_in_memory() -> None:
    first = reporting_outputs(ROOT)
    second = reporting_outputs(ROOT)
    assert first.keys() == second.keys()
    assert all(first[path] == second[path] for path in first)
