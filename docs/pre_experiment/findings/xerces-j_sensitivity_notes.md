
# Xerces-J Sensitivity Notes

## 1. Role

Xerces-J is the larger-scale Stage 1 subject.

It is used to check whether the same class-level extraction, graph-construction, and Leiden workflow remains usable on a larger Java system.

Xerces-J is a technical remodularization case. It is not treated as a business microservice reference-decomposition subject.

## 2. Default Diagnostic Result

These values come from the default pre-experiment diagnostic setting, not from the frozen formal Stage 1 SSA profile.

| Metric | Raw Setting | SSA Setting |
| --- | ---: | ---: |
| Class count | 814 | 814 |
| Edge count | 3780 | 4148 |
| Cluster count | 31 | 30 |
| Weighted modularity | 0.661519 | 0.644268 |
| Max-cluster ratio | 0.144963 | 0.187961 |

Source:

```text
results/pre_experiment/subjects/xerces-j/comparison/metrics_summary.csv
```

Under the default diagnostic setting, SSA adds:

```text
368
```

new class-pair edges.

The SSA partition also has a larger dominant cluster and slightly lower weighted modularity than the raw partition.

## 3. Formal Stage 1 Result

Formal Stage 1 uses the frozen baseline profiles. These outputs are the comparison targets for later stages, while sensitivity results are used for robustness and stress interpretation.

| Metric | Raw Profile | SSA Profile |
| --- | ---: | ---: |
| Cluster count | 31 | 29 |
| Weighted modularity | 0.661519 | 0.652311 |
| Max-cluster ratio | 0.144963 | 0.192875 |

## 4. Sensitivity Outputs

The Xerces-J sensitivity runner writes:

```text
results/pre_experiment/subjects/xerces-j/sensitivity/
  cluster_size_summary.csv
  resolution_sweep.csv
  ssa_lambda_sweep.csv
```

The generic Pre-experiment runner remains responsible for the default raw-vs-SSA comparison.

## 5. Main Observation

Xerces-J shows visible sensitivity to the SSA contribution at a fixed seed.

This must be read against a seed-noise baseline. On Xerces-J the raw Leiden partition is itself highly seed-unstable (28 distinct partitions across 30 seeds), and 37% of pure reseeds move the raw partition by at least the mean SSA effect. The lambda-sweep and SSA-driven movement described below are therefore real at a fixed seed, but lie within the same order as Leiden's own seed-induced variation on this subject. See section 7 "Seed Robustness Control" in `02_stage1_cross_case_summary.md`.

As lambda increases, SSA-derived evidence can connect more classes across existing structural regions. This may enlarge dominant clusters or shift cluster boundaries more strongly at a fixed seed (read against the seed-noise baseline above).

The result supports a cautious interpretation:

* SSA provides additional behavioural evidence;
* the additional evidence changes the partition at a fixed seed, but within Leiden's seed-noise band on this subject (section 7);
* a stronger SSA contribution may increase aggregation risk;
* the effect should be controlled rather than assumed to be beneficial.

## 6. Limitation

This is a case-specific result.

Xerces-J alone cannot support a general claim that larger systems always show stronger SSA sensitivity.

Its role is to provide larger-scale evidence for the current pipeline and to identify risks that should be considered in later stages.

## 7. Reproduction

Run:

```bash
bash scripts/00_pre_experiment/run_pre_xerces_j.sh
bash scripts/00_pre_experiment/run_xerces_j_sensitivity.sh
bash scripts/01_stage1_leiden_baseline/run_stage1_xerces_j.sh
```

The formal Stage 1 profiles are stored under:

```text
results/stage1/subjects/xerces-j/leiden_baseline/
```
