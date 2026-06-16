from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


RUNNER_PATH = Path(__file__).resolve().parents[1] / "experiments" / "00_pre_experiment" / "run_daytrader_calibration.py"
SPEC = spec_from_file_location("daytrader_calibration_runner", RUNNER_PATH)
daytrader_calibration_runner = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(daytrader_calibration_runner)


def test_select_baseline_profiles_uses_deterministic_profile_rules() -> None:
    summary = pd.DataFrame(
        [
            _row(0.0, 0.75, mojofm=60.0, f1=0.20, max_ratio=0.35, modularity=0.28),
            _row(0.0, 1.0, mojofm=65.0, f1=0.24, max_ratio=0.26, modularity=0.34),
            _row(0.0, 1.25, mojofm=65.0, f1=0.22, max_ratio=0.22, modularity=0.31),
            _row(1.0, 1.25, mojofm=63.0, f1=0.23, max_ratio=0.26, modularity=0.333),
            _row(2.0, 1.25, mojofm=64.0, f1=0.22, max_ratio=0.29, modularity=0.34),
            _row(0.25, 1.0, mojofm=64.0, f1=0.22, max_ratio=0.31, modularity=0.329),
            _row(3.0, 0.5, mojofm=70.0, f1=0.25, max_ratio=0.7),
        ]
    )

    profiles = daytrader_calibration_runner.select_baseline_profiles(
        summary,
        {
            "type_dependency": 1.0,
            "method_call": 2.0,
            "return_value_flow": 3.0,
            "argument_passing_flow": 3.0,
        },
    )

    assert profiles["selection_source"] == "constrained_minimum_effective_ssa_calibration"
    assert profiles["selection_rule_version"] == 2
    assert profiles["reference_metric_role"] == "domain_informed_proxy_reference_sanity_check"
    assert profiles["profiles"]["raw_reference_leiden"] == {
        "graph_type": "raw",
        "ssa_lambda": 0.0,
        "resolution": 1.0,
        "seed": 42,
        "role": "internal_primary_raw_structural_reference",
    }
    assert profiles["profiles"]["ssa_selected_leiden"] == {
        "graph_type": "ssa",
        "ssa_lambda": 0.25,
        "resolution": 1.0,
        "seed": 42,
        "role": "minimum_effective_nonzero_ssa_comparison",
    }


def _row(
    ssa_lambda: float,
    resolution: float,
    mojofm: float,
    f1: float,
    max_ratio: float,
    modularity: float = 0.3,
) -> dict:
    return {
        "subject": "daytrader",
        "ssa_lambda": ssa_lambda,
        "resolution": resolution,
        "raw_edge_count": 10,
        "g_ssa_edge_count": 12 if ssa_lambda > 0 else 10,
        "new_ssa_edge_count": 2 if ssa_lambda > 0 else 0,
        "ssa_weight_share": 0.2 if ssa_lambda > 0 else 0.0,
        "cluster_count": 10,
        "max_cluster_ratio": max_ratio,
        "singleton_ratio": 0.1,
        "weighted_modularity": modularity,
        "internal_edge_weight_ratio": 0.5,
        "mojofm_vs_reference": mojofm,
        "pairwise_f1": f1,
        "reference_coverage_ratio": 1.0,
        "ari_vs_reference": 0.1,
        "nmi_vs_reference": 0.2,
        "pairwise_precision": 0.3,
        "pairwise_recall": 0.4,
    }
