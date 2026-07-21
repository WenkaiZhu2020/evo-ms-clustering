# Stage 2: Raw-Only Structure NSGA-II

Stage 2 uses **NSGA-II via pymoo** for multi-objective structural clustering on
`G_raw`. The goal is to produce a Pareto front and one selected solution that
can be compared with the frozen Stage 1 `raw_reference_leiden` baseline.

- **Input graph**: `G_raw`, rebuilt from type-reference and method-call evidence
  in `data/extracted/<subject>/`, using `raw_weight`.
- **Three optimization objectives**:
  1. minimize inter-cluster coupling, `W_external / W_total`;
  2. maximize density-based intra-cluster cohesion, averaged across clusters;
  3. minimize cluster-size imbalance, `std(sizes) / mean(sizes)`.
- **Encoding**: an integer label vector over classes with variable `k`, aligned
  with the Stage 1 `cluster_by_class` mapping and partition DataFrame schema.
- **Hard constraints or repair logic**: `max_cluster_ratio <= 0.40`,
  `singleton_ratio <= 0.15`, and a minimum cluster count.
- **Baseline**: frozen Stage 1 `raw_reference_leiden`, compared with
  `partition_similarity` for ARI/NMI and changed-partition ratio.
- **Post-hoc metrics only**: modularity, Hypervolume, MoJoFM, and Pairwise F1
  are never optimization objectives. MoJoFM and Pairwise F1 are DayTrader-only.
- **Multi-seed protocol**: NSGA-II is stochastic, so Stage 2 reports Pareto
  fronts across fixed seeds.

Design documents live in `../../docs/stage2/`:

- `workflow.md`
- `objectives_and_metrics.md`
- `experiment_design.md`
- `encoding_and_operators.md`

Output is written under:

```text
results/<subject>/03_stage2_nsga/raw/
```

Run example:

```bash
python experiments/02_stage2_nsga_structure_only/run.py --subject jpetstore
```
