# Test Case Selection Summary

This document records why the active Stage 1 subjects are used. Stage 1 is designed to test the extraction and graph-clustering evidence pipeline, not to prove final decomposition quality.

## Active Subjects

| subject | role | reason |
| --- | --- | --- |
| JPetStore | smoke test | Small enough to inspect manually. It checks that Soot extraction, normalized CSV loading, `G_raw` / `G_ssa` construction, Leiden, and metrics can run end to end. |
| DayTrader | calibration and reference case | Provides a reference-service mapping, so it supports reference-based metrics and resolution / SSA-weight sensitivity analysis. |
| Xerces-J | transfer and scalability case | Larger technical remodularization benchmark. It tests whether the Stage 1 pipeline remains usable beyond small business-style systems. |

## Subject Rationale

JPetStore is used first because failures are easier to diagnose on a small graph. Its role is pipeline validation, not final calibration.

DayTrader is the main calibration subject because it has a usable reference mapping. This makes it possible to compare Leiden partitions with external metrics such as MoJoFM and pairwise F1, while also checking internal structural metrics.

Xerces-J is included because it is larger and more technical. It does not provide a business microservice ground truth in this repository, but it is useful for testing graph scale, sensitivity behaviour, and transfer of the Stage 1 workflow.

## Excluded or Non-Primary Subjects

CargoTracker is inactive in the current Stage 1 subject set.

PiggyMetrics is not used as an input subject because it is already a microservice demo rather than a monolithic system for decomposition.

## Link to Later Stages

The three-subject design separates smoke testing, reference-based calibration, and larger-scale transfer validation. This supports later Stage 2 and Stage 3 work by giving a clearer Leiden baseline and a measured view of how SSA evidence changes the graph.
