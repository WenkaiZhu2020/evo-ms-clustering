# Stage 2 initialization diagnostics

This directory archives diagnostic experiments that compare the Stage 1
Leiden-seeded Stage 2 initializer with independent random NSGA-II
initialization. These experiments are evidence for the Stage 1-to-Stage 2
knowledge-transfer claim; they are not part of the frozen formal Stage 2
pipeline.

The branch is intentionally based on Stage 2 diagnostic commit `ecfaa3c` so
that the archived outputs remain tied to the code state that generated them.
Do not merge this branch into the later formal Stage 2 branch without first
porting and rerunning the diagnostics.

## Included experiments

- `stage2_initialisation_ablation/run.py`: paired DayTrader comparison with
  all factors fixed except the initial population source.
- `xerces_random_repair_control/run.py`: Xerces-J independent uniform random
  initialization, with and without the standard Stage 2 repair policy.
- `xerces_random_budget_chase/run.py`: Xerces-J random-initialization budget
  chase at 100, 200, 300, and 500 generations against a fresh 100-generation
  Stage 1 Leiden-seeded baseline.

The primary fair baseline is `random_with_repair`: it does not read Stage 1
labels, but retains the same feasibility repair used by Stage 2. The
`random_without_repair` arm is an additional constraint-handling control.

## Archived evidence

Only aggregate trajectories, per-seed summaries, manifests, and tables needed
to audit the reported comparisons are committed. Per-run logs, Python caches,
duplicate intermediate fronts, the separate constraint ablation, and the
separate hill-climbing diagnostic are deliberately excluded.

For Xerces-J at 100 generations and 10 paired seeds, the mean hypervolume is
`0.130173995` for Leiden-seeded initialization and `0.018483150` for
independent random initialization with repair. The seeded initializer wins on
all 10 seeds. At 500 generations, random initialization reaches a mean
hypervolume of only `0.022602142`.
