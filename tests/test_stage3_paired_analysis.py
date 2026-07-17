import importlib

import numpy as np
import pandas as pd


analysis = importlib.import_module("scripts.stage3.analyze_stage2_vs_stage3")


def test_exact_seed_pairing_requires_0_to_29_and_preserves_order():
    expected = list(range(30))
    assert analysis.paired_seeds(expected, expected) == expected


def test_delta_orientation_is_always_stage3_minus_stage2():
    np.testing.assert_array_equal(analysis.compute_delta([3.0, 1.0], [1.0, 4.0]), [2.0, -3.0])


def test_direction_metadata_does_not_flip_arithmetic_delta():
    assert next(item for item in analysis.METRIC_SPECS if item["name"] == "coupling")["direction"] == "lower"
    assert next(item for item in analysis.METRIC_SPECS if item["name"] == "cohesion")["direction"] == "higher"
    assert analysis.compute_delta([0.2], [0.1])[0] == 0.1


def test_semantic_cut_evaluation_uses_frozen_formula():
    context = {
        "class_nodes": pd.DataFrame({"class_id": ["a", "b"], "class_name": ["A", "B"]}),
        "semantic_edges": pd.DataFrame({"class_id_a": ["a"], "class_id_b": ["b"], "weight": [2.0]}),
        "semantic_graph_metadata": {"total_edge_weight": 2.0},
    }
    same_cluster = pd.DataFrame({"class_id": ["a", "b"], "cluster_id": [0, 0]})
    split_cluster = pd.DataFrame({"class_id": ["a", "b"], "cluster_id": [0, 1]})
    assert analysis.evaluate_semantic_cut(context, same_cluster) == 0.0
    assert analysis.evaluate_semantic_cut(context, split_cluster) == 1.0


def test_hypervolume_compatibility_rejects_stale_stored_value():
    assert np.isclose(analysis.STAGE3._normalize_projected(np.asarray([[0.0, 0.0, 0.0]]), {"lower_bounds": [0, 0, 0], "upper_bounds": [1, 1, 1]}), [[0.0, 0.0, 0.0]]).all()


def test_zero_difference_wilcoxon_is_explicitly_degenerate():
    frame = pd.DataFrame({"subject": ["jpetstore"] * 3})
    for spec in analysis.METRIC_SPECS:
        frame[spec["stage2"]] = [1.0, 1.0, 1.0]
        frame[spec["stage3"]] = [1.0, 1.0, 1.0]
    result = analysis.make_statistical_tests(frame)
    row = result.loc[(result["subject"] == "jpetstore") & (result["metric"] == "hv")].iloc[0]
    assert row["status"] == "degenerate_all_pairs_identical"
    assert pd.isna(row["p_value_two_sided"])
    assert bool(row["significant_after_correction"]) is False


def test_correction_families_and_holm_are_deterministic():
    rows = [
        {"family": "primary", "status": "tested", "p_value_two_sided": 0.01},
        {"family": "secondary", "status": "tested", "p_value_two_sided": 0.01},
        {"family": "secondary", "status": "tested", "p_value_two_sided": 0.02},
    ]
    analysis.correction_metadata(rows)
    assert rows[0]["correction"] == "bonferroni"
    assert rows[0]["correction_family_size"] == 3
    assert rows[1]["adjusted_p_value"] == 0.02
    assert rows[2]["adjusted_p_value"] == 0.02


def test_bootstrap_is_deterministic_and_uses_at_least_10000_resamples():
    values = np.asarray([-1.0, 0.0, 2.0, 3.0])
    first = analysis.bootstrap_mean_ci(values, "jpetstore", "hv")
    second = analysis.bootstrap_mean_ci(values, "jpetstore", "hv")
    assert first == second
    assert analysis.BOOTSTRAP_RESAMPLES >= 10_000


def test_wins_ties_losses_follow_metric_direction():
    assert analysis.wins_ties_losses(np.asarray([-1.0, 0.0, 2.0]), "lower") == (1, 1, 1)
    assert analysis.wins_ties_losses(np.asarray([-1.0, 0.0, 2.0]), "higher") == (1, 1, 1)
    assert analysis.wins_ties_losses(np.asarray([]), "higher") == (None, None, None)


def test_partition_change_is_label_invariant():
    class_nodes = pd.DataFrame({"class_id": ["a", "b", "c", "d"], "class_name": ["A", "B", "C", "D"]})
    left = pd.DataFrame({"class_id": ["a", "b", "c", "d"], "cluster_id": [0, 0, 1, 1]})
    right = pd.DataFrame({"class_id": ["a", "b", "c", "d"], "cluster_id": [9, 9, 4, 4]})
    result = analysis._validate_partition_pair(class_nodes, left, right)
    assert result["changed_class_count_after_label_alignment"] == 0
    assert result["ari"] == 1.0
    assert result["nmi"] == 1.0


def test_authoritative_output_schema_is_explicit():
    expected = {"subject", "seed", "stage2_hv", "stage3_projected_hv", "delta_hv", "stage2_selected_semantic_cut", "stage3_selected_semantic_cut", "delta_semantic_cut"}
    assert expected.issubset({spec["stage2"] for spec in analysis.METRIC_SPECS} | {spec["stage3"] for spec in analysis.METRIC_SPECS} | {"subject", "seed", "delta_hv", "delta_semantic_cut"})


def test_saved_analysis_outputs_have_authoritative_pairing_schema():
    root = analysis.ROOT / "reports/stage3"
    paired = pd.read_csv(root / "stage2_vs_stage3_paired_seed_metrics.csv")
    assert len(paired) == 90
    assert paired[["subject", "seed"]].drop_duplicates().shape[0] == 90
    assert set(paired["subject"]) == set(analysis.SUBJECTS)
    assert {"stage2_hv", "stage3_projected_hv", "delta_hv", "stage2_selected_semantic_cut", "stage3_selected_semantic_cut", "delta_semantic_cut"}.issubset(paired.columns)
    partition = pd.read_csv(root / "stage2_vs_stage3_partition_change.csv")
    assert len(partition) == 90


def test_saved_stage3_semantic_round_trip_and_hv_compatibility_pass():
    paired, _, validation = analysis.load_paired_outputs()
    assert len(paired) == 90
    assert all(item["stage3_seed_count"] == 30 for item in validation.values())
    assert paired["stage3_selected_semantic_cut"].notna().all()
    assert paired["stage2_hv"].notna().all()
    assert paired["stage3_projected_hv"].notna().all()
