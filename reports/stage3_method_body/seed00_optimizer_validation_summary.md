# Stage 3B seed-0 optimizer validation

## Scope

This is a controlled seed-0 validation of the isolated declaration-plus-method-body semantic graph. No formal seeds, NSGA-II runs beyond seed 0, embedding generation, graph generation, Hypervolume comparison across seeds, or decomposition-quality analysis was performed.

**SINGLE-SEED DIAGNOSTIC — NOT EFFECTIVENESS EVIDENCE**

## Frozen optimizer boundary

Structural objectives, initialization, operators, repair, population size, generations, semantic objective formula, four-dimensional Pareto front, projected three-dimensional Hypervolume, and representative selector were reused from the frozen Stage 3A/Stage 2 implementation. Only the validated Stage 3B semantic graph was substituted.

## Subject results

| Subject | Front | Projected | Structural | Semantic | Front | HV | Selector | Reproducibility |
|---|---:|---:|---|---|---|---|---|---|
| jpetstore | 100 | 61 | True | True | True | True | True | True |
| daytrader | 100 | 64 | True | True | True | True | True | True |
| xerces | 100 | 90 | True | True | True | True | True | True |

## Acceptance interpretation

- All subject-level validation gates: **True**.
- Formal seed range 0–29: **not run**.
- Stage 2 and Stage 3A results were read only for diagnostic comparison; they were not modified.
- A PASS here permits the next controlled formal-seed task only; it is not evidence of decomposition-quality improvement.
