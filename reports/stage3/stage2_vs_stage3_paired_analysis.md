# Paired Stage 2 versus Stage 3 analysis

## Executive conclusion

Direct answer: no, on the preregistered primary metric. Stage 3 did not outperform Stage 2 on the primary projected 3D Hypervolume comparison; the corrected result favored Stage 2. The comparison uses the same 30 seed IDs (0–29) for JPetStore, DayTrader, and Xerces, and compares Stage 2 three-objective Hypervolume with Stage 3 projected three-dimensional Hypervolume. The arithmetic delta is always Stage 3 minus Stage 2. Semantic-cut values for the saved Stage 2 representatives were evaluated on the frozen Stage 3 semantic graph; they were not used for reselection. This is a paired result comparison and does not by itself establish an improvement in decomposition quality.

## Scope and frozen-data policy

No optimizer, embedding, graph construction, representative reselection, configuration, seed, objective, or statistical setting was rerun or changed. All 90 pairs passed exact seed and class-scope validation. Hypervolume was independently recomputed from each saved Pareto/projected front and checked against the stored value.

## Primary projected-Hypervolume comparison

| subject | n | Stage 2 median | Stage 3 median | median delta | mean delta | wins/ties/losses | Wilcoxon p | Holm/Bonferroni adjusted p | corrected significant |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| jpetstore | 30 | 0.404319 | 0.378562 | -0.026426 | -0.023669 | 2/0/28 | 0.000000 | 0.000000 | yes |
| daytrader | 30 | 0.187982 | 0.182184 | -0.002263 | -0.001652 | 13/0/17 | 0.745655 | 1.000000 | no |
| xerces | 30 | 0.133234 | 0.133868 | -0.000376 | 0.001196 | 14/0/16 | 0.745655 | 1.000000 | no |

Primary correction: two-sided paired Wilcoxon tests across the three subjects, Bonferroni family size 3, alpha = 0.05/3. Bootstrap intervals are deterministic 95% intervals for the mean arithmetic delta, based on 10,000 resamples per subject/metric.

## Key paired values

| subject | Stage 2 HV mean | Stage 3 projected HV mean | mean delta | HV wins/ties/losses | HV rank-biserial | HV bootstrap mean CI | MoJoFM delta | Pairwise F1 delta | semantic-cut delta | partition ARI | mean Stage 3 coupling–semantic rho |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| jpetstore | 0.401254 | 0.377585 | -0.023669 | 2/0/28 | -0.961290 | [-0.028991, -0.018014] | N/A | N/A | 0.000122 | 0.993294 | -0.037595 |
| daytrader | 0.184832 | 0.183180 | -0.001652 | 13/0/17 | -0.070968 | [-0.008365, 0.004856] | 1.666667 | 0.013838 | -0.039918 | 0.538795 | 0.747947 |
| xerces | 0.134422 | 0.135618 | 0.001196 | 14/0/16 | 0.070968 | [-0.002817, 0.005360] | N/A | N/A | -0.002274 | 0.991516 | 0.923489 |

External-quality metrics below are evaluation-only calculations on the saved representatives. Subjects without a complete frozen reference remain N/A; no values were invented or used for reselection.

## External-reference evaluation

| subject | reference status | reference path | MoJoFM mean delta | Pairwise F1 mean delta | reference ARI mean delta | reference NMI mean delta |
|---|---|---|---:|---:|---:|---:|
| jpetstore | unavailable | N/A | N/A | N/A | N/A | N/A |
| daytrader | available | data/references/daytrader_reference_services.csv | 1.666667 | 0.013838 | 0.015670 | 0.026123 |
| xerces | unavailable | N/A | N/A | N/A | N/A | N/A |


## Semantic-cut evaluation

The Stage 2 selected partition was evaluated with the exact frozen Stage 3 graph and formula. Lower semantic cut is better; these values are secondary and were not used to select either solution.

| subject | Stage 2 median | Stage 3 median | median delta | wins/ties/losses | corrected p |
|---|---:|---:|---:|---:|---:|
| jpetstore | 0.598786 | 0.598786 | 0.000000 | 0/28/2 | 1.000000 |
| daytrader | 0.616084 | 0.572338 | -0.043740 | 19/1/10 | 0.219562 |
| xerces | 0.383980 | 0.382498 | -0.001365 | 21/8/1 | 0.019060 |

## Partition change

ARI and NMI are label-invariant. The changed-class ratio uses deterministic maximum-overlap Hungarian label alignment and is descriptive only.

| subject | mean changed-class ratio | mean ARI | mean NMI | mean cluster-count delta |
|---|---:|---:|---:|---:|
| jpetstore | 0.002778 | 0.993294 | 0.994581 | 0.000000 |
| daytrader | 0.283648 | 0.538795 | 0.691566 | 0.700000 |
| xerces | 0.005242 | 0.991516 | 0.991809 | 0.133333 |

## Secondary paired metrics

See `stage2_vs_stage3_paired_descriptive_summary.csv` and `stage2_vs_stage3_paired_statistical_tests.csv` for all structural metrics, directions, paired sample sizes, bootstrap intervals, wins/ties/losses, proportions improved, and corrected values. Secondary inferential tests use Holm correction over all eligible non-degenerate secondary tests. Cluster count and size summaries are descriptive only.

Reference-dependent metrics are available only for DayTrader because it has the complete frozen proxy reference. JPetStore and Xerces remain unavailable with explicit reasons in the manifest and external-evaluation CSV; no values were imputed.

## Statistical-analysis contract

The repository contains a Stage 3 internal Wilcoxon/Bonferroni configuration in `configs/experiments/04_stage3_semantic.yml` and a Stage 2 selected-versus-Leiden protocol in `docs/stage2/reproducibility.md`; neither is a complete frozen Stage 2-versus-Stage 3 paired contract. This report therefore labels the transparent two-sided Wilcoxon, rank-biserial, deterministic bootstrap, primary Bonferroni, and secondary Holm procedure as a post-hoc analysis protocol established after formal execution.

## Provenance and validation

Analysis source commit at start: `5ae6d197e4e5bc13d92d726f3f19de3a5fabda94`. Subject pair validation: all passed. No embeddings, semantic graphs, or optimizer runs were generated by this analysis. Frozen source validation details are recorded in `stage2_vs_stage3_analysis_manifest.json`.

## Outputs

- `stage2_vs_stage3_paired_seed_metrics.csv` — authoritative one-row-per-subject/seed dataset.
- `stage2_vs_stage3_partition_change.csv` — paired partition-change diagnostics.
- `stage2_vs_stage3_paired_descriptive_summary.csv` — paired descriptive metrics.
- `stage2_vs_stage3_paired_statistical_tests.csv` — two-sided paired tests and corrections.
- `stage2_vs_stage3_external_metric_evaluation.csv` — evaluation-only external metrics for saved partitions.
