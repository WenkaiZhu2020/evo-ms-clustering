
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
| DayTrader | constrained calibration case | compare raw and SSA settings and select formal Leiden profiles with reference-based sanity checks |
| Xerces-J | larger-scale sensitivity case | inspect scale behaviour and SSA sensitivity under the same workflow |

## 3. Formal Stage 1 Results

Formal Stage 1 uses the frozen profiles:

```text
raw: lambda=0.0, resolution=1.0
SSA: lambda=0.25, resolution=1.0
```

| Subject | Raw Clusters | SSA Clusters | Raw Modularity | SSA Modularity |
| --- | ---: | ---: | ---: | ---: |
| JPetStore | 4 | 4 | 0.442070 | 0.413664 |
| DayTrader | 11 | 11 | 0.324597 | 0.325156 |
| Xerces-J | 31 | 29 | 0.661519 | 0.652311 |

Diagnostic and pre-experiment settings may use different lambda values and should not be mixed with the formal Stage 1 outputs.

## 4. Formal Raw-vs-SSA Comparison

| Subject | Cluster count delta | ARI raw-vs-SSA | NMI raw-vs-SSA | Changed partition ratio |
| --- | ---: | ---: | ---: | ---: |
| JPetStore | 0 | 0.876593 | 0.912301 | 0.541667 |
| DayTrader | 0 | 0.945670 | 0.969307 | 0.377358 |
| Xerces-J | -2 | 0.701535 | 0.862387 | 0.831695 |

## 5. DayTrader Calibration

DayTrader is used for constrained internal-primary calibration with reference-based sanity checks. All 53 retained classes are mapped to a domain-informed proxy reference, giving 53 / 53 coverage (100%). These metrics are calibration evidence, not an independent validation result.

The calibration sweep varies:

```text
ssa_lambda
Leiden resolution
```

The selected formal profiles are:

| Profile                | Graph Type | Lambda | Resolution | Seed | Role                                                 |
| ---------------------- | ---------- | -----: | ---------: | ---: | ---------------------------------------------------- |
| `raw_reference_leiden` | raw        |    0.0 |        1.0 |   42 | internal-primary raw structural reference |
| `ssa_selected_leiden`  | ssa        |   0.25 |        1.0 |   42 | minimum-effective non-zero SSA comparison profile |

The selected SSA profile is the minimum non-zero SSA setting within the near-best internal structural-quality band. Reference metrics are retained as sanity checks; this does not mean that SSA automatically improves clustering quality.

The selected profile record is stored at:

```text
results/daytrader/00_pre_experiment/calibration/selected_baseline_profiles.yml
```

## 6. Main Findings

* SSA adds new class-level relations in all three subjects.
* SSA changes clustering behaviour, but the amount of change differs by subject.
* Additional flow evidence does not automatically improve internal structural metrics.
* Higher SSA contribution may enlarge dominant clusters.
* Calibration uses internal structural metrics as primary signals and reference metrics as sanity checks.
* A minimum-effective non-zero SSA profile is retained for controlled comparison rather than as an assumed improvement.

## 7. Limitations

The current evaluation has several limits:

* reference mapping is available only for DayTrader;
* JPetStore is mainly a pipeline-validation case;
* Xerces-J is used for scale and sensitivity rather than external accuracy;
* the selected Leiden profiles should be treated as reproducible reference points for later comparison.

## 8. Reproduction

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
```

Pre-experiment diagnostic results are reported separately in the calibration and sensitivity notes. They should not be mixed with the frozen formal Stage 1 profiles reported in this cross-case summary.
