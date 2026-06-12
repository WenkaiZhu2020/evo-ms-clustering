
# Stage 1 Cross-Case Summary

## 1. Scope

Stage 1 evaluates class-level graph construction and Leiden baselines.

The Pre-experiment layer is used for diagnostics, calibration, and sensitivity analysis. The formal Stage 1 layer freezes reproducible Leiden profiles for later comparison with NSGA-II.

Two graph settings are used:

| Graph | Evidence |
| --- | --- |
| `G_raw` | type dependencies and method calls |
| `G_ssa` | `G_raw` plus scoped return-value and argument-passing SSA flow evidence |

Stage 1 does not claim that the generated clusters are final microservice boundaries. It provides measured evidence and reproducible baselines for later stages.

## 2. Subject Roles

| Subject | Role | Main Purpose |
| --- | --- | --- |
| JPetStore | pipeline-validation case | verify the complete extraction, graph-construction, Leiden, and metrics pipeline |
| DayTrader | reference-based calibration case | compare raw and SSA settings and select formal Leiden profiles |
| Xerces-J | larger-scale sensitivity case | inspect scale behaviour and SSA sensitivity under the same workflow |

## 3. Default Diagnostic Results

| Subject | Classes | Raw Edges | SSA Edges | New SSA Edges | Raw Clusters | SSA Clusters | Raw Modularity | SSA Modularity | Raw Max-Cluster Ratio | SSA Max-Cluster Ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| JPetStore | 24 | 53 | 60 | 7 | 4 | 4 | 0.442070 | 0.387485 | 0.291667 | 0.333333 |
| DayTrader | 121 | 267 | 275 | 8 | 28 | 28 | 0.357424 | 0.348186 | 0.264463 | 0.297521 |
| Xerces-J | 814 | 3780 | 4148 | 368 | 31 | 30 | 0.661519 | 0.644268 | 0.144963 | 0.187961 |

Source:

```text
results/<subject>/00_pre_experiment/comparison/metrics_summary.csv
````

The default runs show that SSA adds new class-pair evidence in all three subjects.

The number of new edges is limited in JPetStore and DayTrader, but more visible in Xerces-J. The SSA setting also changes cluster boundaries and increases the largest-cluster ratio in the three subjects.

Raw structural modularity remains higher in the current default comparison. This is an internal graph result. It should not be interpreted as final decomposition correctness.

## 4. DayTrader Calibration

DayTrader is used for calibration because it provides a reference mapping.

The calibration sweep varies:

```text
ssa_lambda
Leiden resolution
```

The selected formal profiles are:

| Profile                | Graph Type | Lambda | Resolution | Seed | Role                                                 |
| ---------------------- | ---------- | -----: | ---------: | ---: | ---------------------------------------------------- |
| `raw_reference_leiden` | raw        |    0.0 |       1.25 |   42 | strongest admissible raw structural reference        |
| `ssa_selected_leiden`  | ssa        |   0.25 |        1.5 |   42 | strongest admissible non-zero SSA comparison profile |

The raw profile produced the stronger reference-based result.

The non-zero SSA profile is still retained because the dissertation needs to inspect the effect of behavioural enrichment under a controlled setting. This does not mean that SSA automatically improves clustering quality.

The selected profile record is stored at:

```text
results/daytrader/00_pre_experiment/calibration/selected_baseline_profiles.yml
```

## 5. Main Findings

* SSA adds new class-level relations in all three subjects.
* SSA changes clustering behaviour, but the amount of change differs by subject.
* Additional flow evidence does not automatically improve internal structural metrics.
* Higher SSA contribution may enlarge dominant clusters.
* Raw structural Leiden remains the stronger reference in the current DayTrader calibration.
* A non-zero SSA profile is retained for controlled comparison rather than as an assumed improvement.

## 6. Limitations

The current evaluation has several limits:

* reference mapping is available only for DayTrader;
* JPetStore is mainly a pipeline-validation case;
* Xerces-J is used for scale and sensitivity rather than external accuracy;
* the selected Leiden profiles should be treated as reproducible reference points for later comparison.

## 7. Reproduction

Run:

```bash
bash scripts/run_pre_jpetstore.sh
bash scripts/run_pre_daytrader.sh
bash scripts/run_pre_xerces_j.sh

bash scripts/run_daytrader_calibration.sh
bash scripts/run_xerces_j_sensitivity.sh

bash scripts/run_stage1_jpetstore.sh
bash scripts/run_stage1_daytrader.sh
bash scripts/run_stage1_xerces_j.sh
```

Main outputs:

```text
results/<subject>/00_pre_experiment/
results/daytrader/00_pre_experiment/calibration/
results/xerces-j/00_pre_experiment/sensitivity/
results/<subject>/01_stage1_leiden_baseline/
