# SSA Calibration Notes

## 1. Purpose

`ssa_lambda` controls the overall contribution of SSA-derived flow evidence after extraction. The embedded row weights are fixed in the normalized CSV rows; lambda scales their aggregate contribution during graph construction.

DayTrader is used for constrained internal-primary calibration with reference-based sanity checks. Its service mapping is a domain-informed proxy reference, not an independent validation oracle.

## 2. Evidence Weights and Formula

| Evidence Channel | Embedded Row Weight |
| --- | ---: |
| Type dependency | 1.0 |
| Method call | 2.0 |
| Return-value flow | 3.0 |
| Argument-passing flow | 3.0 |

```text
raw_ssa_flow_sum = return_flow_weight + argument_flow_weight
ssa_flow_weight = ssa_lambda * raw_ssa_flow_sum
g_ssa_weight = raw_weight + ssa_flow_weight
```

`expected_extracted_evidence_weights` is a validation check only. Changing YAML does not reweight an existing extracted dataset.

## 3. Sweep Space

| Item | Values |
| --- | --- |
| Lambda sweep | 0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0 |
| Calibration lambda regime | 0.0 for raw; 0.0 < lambda <= 1.0 for SSA |
| Stress-testing regime | lambda > 1.0 |
| Resolution grid | 0.5, 0.75, 1.0, 1.25, 1.5 |
| Seed | 42 |

Values above 1.0 are retained in the sweep output for sensitivity and stress testing, but they are not eligible for selecting the formal SSA calibration profile.

## 4. Selection Rule

Candidates must pass these filters:

* non-extreme cluster count;
* `max_cluster_ratio <= 0.4`;
* `singleton_ratio <= 0.15`;
* `reference_coverage_ratio >= 0.8`;
* for SSA candidates, `ssa_lambda <= 1.0`.

Raw candidates use `ssa_lambda = 0.0` and are ranked by weighted modularity, internal edge weight ratio, balance metrics, resolution proximity to 1.0, then reference metrics.

SSA candidates use `0.0 < ssa_lambda <= 1.0`. The rule first keeps candidates within 0.005 weighted-modularity points of the best admissible SSA candidate, then chooses the lowest non-zero lambda in that near-best band. Internal edge weight ratio, balance metrics, resolution proximity, and reference metrics break ties.

MoJoFM and pairwise F1 remain in the output as reference-based sanity checks. They are not primary ranking signals.

## 5. Selected Profiles

| Profile | Graph Type | Lambda | Resolution | Seed | Role |
| --- | --- | ---: | ---: | ---: | --- |
| `raw_reference_leiden` | raw | 0.0 | 1.0 | 42 | internal-primary raw structural reference |
| `ssa_selected_leiden` | ssa | 0.25 | 1.0 | 42 | minimum-effective non-zero SSA comparison profile |

All 53 retained DayTrader classes are mapped to reference services, so reference coverage is 53 / 53 = 100%.

The selected profiles are representative controlled-comparison settings. They are not universal optima. The formal Leiden profiles use a fixed seed of 42 for reproducibility; Stage 1 does not claim multi-seed stability.
