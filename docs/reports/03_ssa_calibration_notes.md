
# SSA Calibration Notes

## 1. Purpose

`ssa_lambda` controls the overall contribution of SSA-derived flow evidence in `G_ssa`.

It is separate from the embedded base weights of individual evidence rows.

DayTrader is used for calibration because a reference-service mapping is available. This allows different lambda and resolution settings to be compared with external metrics.

## 2. Frozen Base Evidence Weights

| Evidence Channel | Embedded Row Weight |
| --- | ---: |
| Type dependency | 1.0 |
| Method call | 2.0 |
| `return_value_flow` | 3.0 |
| `argument_passing_flow` | 3.0 |

These values are stored in:

```text
data/extracted/<subject>/structural_dependencies.csv
data/extracted/<subject>/ssa_flow_edges.csv
````

The config block:

```text
expected_extracted_evidence_weights
```

is used only for validation.

Changing the YAML values does not reweight an existing extracted dataset. Reweighting requires a new extraction or an explicit change in the graph-construction logic.

## 3. Graph Formula

For each class pair:

```text
raw_ssa_flow_sum
=
return_flow_weight
+
argument_flow_weight
```

```text
ssa_flow_weight
=
ssa_lambda * raw_ssa_flow_sum
```

```text
g_ssa_weight
=
raw_weight
+
ssa_flow_weight
```

When:

```text
ssa_lambda = 0
```

the SSA contribution is removed. The resulting graph is equivalent to the raw structural setting.

## 4. Sweep Dimensions

| Item                | Value                                                                 |
| ------------------- | --------------------------------------------------------------------- |
| Lambda grid         | `0.0`, `0.25`, `0.5`, `1.0`, `2.0`, `3.0`, `4.0`                      |
| Resolution grid     | `0.5`, `0.75`, `1.0`, `1.25`, `1.5`                                   |
| Seed                | `42`                                                                  |
| Calibration subject | DayTrader                                                             |
| External metrics    | MoJoFM, pairwise F1, ARI, NMI, pairwise precision, pairwise recall    |
| Additional checks   | cluster count, max-cluster ratio, singleton ratio, reference coverage |

Calibration outputs are stored under:

```text
results/daytrader/00_pre_experiment/calibration/
```

The main files are:

```text
weight_sweep_summary.csv
top_weight_settings.csv
selected_baseline_profiles.yml
```

## 5. Frozen Leiden Profiles

| Profile                | Graph Type | Lambda | Resolution | Seed | Role                                                 |
| ---------------------- | ---------- | -----: | ---------: | ---: | ---------------------------------------------------- |
| `raw_reference_leiden` | raw        |    0.0 |       1.25 |   42 | strongest admissible raw structural reference        |
| `ssa_selected_leiden`  | ssa        |   0.25 |        1.5 |   42 | strongest admissible non-zero SSA comparison profile |

The raw profile produced the stronger reference-based result in the current DayTrader calibration.

The selected SSA profile is still retained because the dissertation needs a reproducible non-zero SSA setting. Its purpose is to evaluate the effect of behavioural enrichment under controlled conditions.

## 6. Interpretation

Two forms of comparison are used.

### Matched-setting comparison

A fixed resolution is used while lambda changes.

This shows how SSA strength affects the graph and partition without changing clustering granularity.

### Calibrated-profile comparison

The frozen raw and SSA profiles use their selected settings.

This provides reproducible Leiden reference points for later NSGA-II evaluation.

The selected SSA profile should not be described as an improvement over raw. It is retained as a controlled SSA-informed comparison.
