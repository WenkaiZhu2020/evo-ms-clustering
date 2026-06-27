
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
* At the frozen seed, switching to G_ssa changes the partition (Section 4), but a 30-seed robustness control shows this change stays within Leiden's own seed-induced variation -- within +/-2 std of the seed-noise distance on DayTrader and Xerces-J, where 19% and 37% of pure reseeds move the raw partition by at least the mean SSA effect. SSA does not repartition classes beyond seed noise, which supports shelving SSA at class level (see Section 7 and `results/<subject>/02_stage1_seed_robustness/`).
* Additional flow evidence does not automatically improve internal structural metrics.
* Higher SSA contribution may enlarge dominant clusters, though on Xerces-J this movement is within Leiden's seed-noise variation (Section 7).
* Calibration uses internal structural metrics as primary signals and reference metrics as sanity checks.
* A minimum-effective non-zero SSA profile is retained for controlled comparison rather than as an assumed improvement.

## 7. Seed Robustness Control

Leiden is stochastic, so the formal profiles fix a single seed (42). To test whether the raw->SSA partition change is meaningful, a 30-seed control (seeds 0-29, resolution 1.0, raw lambda 0.0, ssa lambda 0.25, Leiden run to convergence) compares two distance distributions per subject, with distance = 1 - ARI:

* SSA effect: `ARI(raw_seed_i, ssa_seed_i)` over the 30 seeds;
* Seed noise: `ARI(raw_seed_i, raw_seed_j)` over all 435 seed pairs.

| Subject | SSA-effect distance (mean +/- std) | Seed-noise distance (mean +/- std) | SSA effect within seed-noise +/-2 std | Reseeds moving raw >= mean SSA effect |
| --- | --- | --- | --- | ---: |
| JPetStore | 0.123 +/- 0.000 | 0.000 +/- 0.000 | n/a -- raw seed-stable (1 partition / 30 seeds) | 0% |
| DayTrader | 0.109 +/- 0.094 | 0.066 +/- 0.144 | yes (band [-0.224, 0.354]) | 19% |
| Xerces-J | 0.283 +/- 0.064 | 0.216 +/- 0.109 | yes (band [-0.002, 0.434]) | 37% |

On the two seed-unstable subjects (DayTrader, Xerces-J) the mean SSA-effect distance is the same order as the seed-noise distance and lies inside its +/-2 std band, and a substantial fraction of pure reseeds (19% and 37%) move the raw partition by at least the mean SSA effect. On Xerces-J the raw partition is itself highly seed-unstable (28 distinct partitions across 30 seeds). JPetStore is the seed-trivial 24-class case: its raw partition is identical across all seeds, so any SSA change registers as "outside" zero noise.

Conclusion: at the frozen seed, switching to G_ssa does change the partition (Section 4), but that change does not exceed Leiden's own seed-induced variation. SSA does not repartition classes beyond seed noise, which supports shelving SSA at class level. Per-subject values, raw seed distributions, and run metadata are in `results/<subject>/02_stage1_seed_robustness/`.

### Reading the Mann-Whitney result

A Mann-Whitney U test on the two distance distributions returns p < 0.05 for every subject (DayTrader p = 2.7e-14, Xerces-J p = 0.0027). This does not contradict "SSA effect within seed noise." Mann-Whitney only asks whether one distribution tends to rank higher than the other; here it is detecting a difference in distribution *shape*, not a larger repartition. The seed-noise distances are zero-inflated -- 81% of reseed pairs are identical on DayTrader (3% on Xerces-J) -- while the SSA-effect distances are never zero (smallest 0.054 on DayTrader, 0.119 on Xerces-J). A test that compares "many exact zeros" against "never zero" separates the two easily even when their non-zero magnitudes overlap, which they do.

The p-value is also not a trustworthy strict-significance statement here: the 435 seed-noise pairs are built from only 30 raw partitions, so they share data and are not independent samples, which violates the test's assumptions. It is reported as a guideline alongside the effect-size and band-overlap view above, not as proof that SSA matters.

## 8. Limitations

The current evaluation has several limits:

* reference mapping is available only for DayTrader;
* JPetStore is mainly a pipeline-validation case;
* Xerces-J is used for scale and sensitivity rather than external accuracy;
* the selected Leiden profiles should be treated as reproducible reference points for later comparison.

## 9. Reproduction

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

python experiments/01_stage1_leiden_baseline/run_seed_robustness.py --num-seeds 30
```

Main outputs:

```text
results/<subject>/00_pre_experiment/
results/daytrader/00_pre_experiment/calibration/
results/xerces-j/00_pre_experiment/sensitivity/
results/<subject>/01_stage1_leiden_baseline/
results/<subject>/02_stage1_seed_robustness/
```

Pre-experiment diagnostic results are reported separately in the calibration and sensitivity notes. They should not be mixed with the frozen formal Stage 1 profiles reported in this cross-case summary.
