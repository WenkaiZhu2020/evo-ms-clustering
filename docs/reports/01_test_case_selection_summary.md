
# Test Case Selection Summary

Stage 1 uses three subject systems with different roles.

The aim is not to claim final decomposition quality from one benchmark. Instead, the subject set is used to check the pipeline, calibrate the graph settings, and inspect behaviour at a larger scale.

## Active Subjects

| Subject | Role | Reason |
| --- | --- | --- |
| JPetStore | pipeline-validation case | Small enough for manual inspection. It checks whether extraction, normalized CSV loading, graph construction, Leiden, and metrics run correctly from end to end. |
| DayTrader | constrained calibration case | Provides a usable domain-informed proxy reference. It supports reference-based sanity checks and the selection of reproducible Leiden profiles. |
| Xerces-J | larger-scale sensitivity case | Contains a larger technical codebase. It is used to inspect whether the same workflow remains usable beyond small business-style systems. |

## JPetStore

JPetStore is used first because the graph is small and easy to inspect.

Its main role is to verify:

```text
compiled classes
-> Soot / Shimple extraction
-> normalized CSV files
-> G_raw and G_ssa
-> Leiden clustering
-> Stage 1 metrics
```

JPetStore is not used as the main calibration subject.

## DayTrader

DayTrader is the main calibration subject because a reference-service mapping is available.

This allows the pipeline to report external metrics such as:

* MoJoFM;
* pairwise precision;
* pairwise recall;
* pairwise F1;
* ARI;
* NMI.

DayTrader is also used to compare lambda and resolution settings before the formal Leiden profiles are frozen. Calibration is internal-primary; reference metrics are used as sanity checks.

## Xerces-J

Xerces-J is included as the larger-scale subject.

It is a technical remodularization case rather than a business microservice reference-decomposition case. Its purpose is to inspect:

* graph scale;
* cluster-size behaviour;
* sensitivity to SSA contribution;
* transfer of the Stage 1 workflow.

## Inactive or Excluded Subjects

CargoTracker is inactive in the current Stage 1 subject set.

PiggyMetrics is not used as an input subject because it is already a microservice demo rather than a monolithic system for decomposition.

## Link to Later Stages

The three subjects provide separate evidence for:

```text
pipeline validation
constrained internal-primary calibration with reference-based sanity checks
larger-scale sensitivity
```

The frozen Leiden profiles can then be used as reference points for Stage 2 NSGA-II evaluation.
