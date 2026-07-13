# Experiment Design

## Research Question

Stage 2 asks whether structure-only NSGA-II on `G_raw` can produce a useful
alternative to the frozen Stage 1 raw Leiden baseline. The comparison target is
only:

```text
raw_reference_leiden
graph = G_raw
resolution = 1.0
seed = 42
```

The claim does not require NSGA-II to outperform Leiden in modularity. The
expected value is a Pareto front that exposes trade-offs between coupling,
cohesion, and cluster-size balance, plus a selected solution that can be compared
directly with the raw Leiden partition.

## Subjects

| Subject | Role | Frozen scale |
| --- | --- | --- |
| JPetStore | Pipeline validation on a small system. | 24 classes |
| DayTrader | Main case with a DDD proxy reference for post-hoc checks. | 53 classes |
| Xerces-J | Larger-scale feasibility and performance stress case. | 814 classes |

Class counts come from `data/extracted/<subject>/`, aligned with frozen Stage 1.

## Multi-Seed Protocol

NSGA-II is stochastic, so single-seed results are insufficient. Stage 2:

- uses the experiment YAML for standard defaults, while the formal robustness
  runner defines the 30-seed evaluation set as seeds `0..29`; the saved formal
  manifests confirm this set for all three subjects;
- retains each seed's Pareto front and Hypervolume;
- reports mean and standard deviation for Hypervolume across seeds;
- preserves seed, metadata, input hashes, and git head for reproducibility.

## Initial Algorithm Configuration

- Engine: pymoo `NSGA2`; do not hand-write the NSGA-II core.
- Population and generations: config defaults, currently population `100` and
  generations `100`.
- Initialization: Leiden -> NSGA-II hybrid warm start, followed by random fill
  for diversity. The seed set contains the frozen raw Leiden partition,
  graph-local perturbations of it, and strongest-edge raw-graph groupings.
- Objective evaluation: O(E) edge-weight processing; no `_weighted_modularity`
  inside the optimization loop.
- Constraints or repair: `max_cluster_ratio <= 0.40` and minimum cluster
  count. `singleton_ratio` is diagnostic-only.
- Leiden resolution is not carried into Stage 2. Resolution is a Leiden-only
  parameter; NSGA-II controls granularity through the balance objective,
  admissibility constraints, and genetic operators.

## Selected-Solution Reporting

The runner keeps the full Pareto front, then selects one final solution for the
Stage 1 comparison. The default rule is:

```text
highest weighted modularity among feasible Pareto solutions
```

The selected solution is not the only Stage 2 output. The Pareto front remains
the primary multi-objective artifact.

Because Stage 2 uses heuristic seeding, each solution records:

- whether it exactly matches an injected seed;
- the injected seed name and category when applicable;
- otherwise that it is a newly evolved non-seed solution.

Reports should distinguish injected-seed solutions from newly evolved solutions.
Preserving an injected Leiden seed establishes a competitive anchor, but the
stronger Pareto-front claim depends on non-seed trade-off solutions.

## Out of Scope

The final Stage 2 experiment has no graph arm beyond `G_raw`. Semantic
embeddings, LLM evidence, method-level refinement, and later-stage experiments
are outside this design.
