# Stage 1 Documentation

This folder is the entry point for the current Stage 1 structural pipeline.

Stage 1 answers one question: can the project extract Java evidence, build class-level graphs, and produce a reliable Leiden baseline before later NSGA-II and semantic experiments?

## Reading Order

1. `01_stage1_overview.md`
   - High-level purpose, subject roles, and output layout.
2. `02_soot_extraction.md`
   - Java/Soot extractor inputs, package scope, and normalized CSV outputs.
3. `03_data_schema.md`
   - Exact CSV schemas for extracted inputs and generated outputs.
4. `04_graph_construction.md`
   - How `G_raw`, `G_ssa`, `raw_weight`, and `g_ssa_weight` are built.
5. `05_metric_definitions.md`
   - What each graph, partition, comparison, and reference metric means.

Cross-case interpretation and subject reports live in `docs/reports/`.

## Current Pipeline

```text
compiled Java classes
-> Soot/Shimple extraction
-> data/extracted/<subject>/*.csv
-> G_raw and G_ssa edge construction
-> Leiden on G_raw and G_ssa for pre-experiment comparison
-> Leiden on G_ssa for Stage 1 baseline
-> sensitivity / calibration outputs where available
```

## Current Subjects

- `jpetstore`: small smoke test for checking the pipeline end to end.
- `daytrader`: calibration subject with a reference mapping and weight/resolution sweep outputs.
- `xerces-j`: larger technical remodularization benchmark for transfer and scalability checks.

## Output Map

- Extracted normalized inputs: `data/extracted/<subject>/`
- Pre-experiment graph and comparison outputs: `results/<subject>/00_pre_experiment/`
- Stage 1 Leiden baseline outputs: `results/<subject>/01_stage1_leiden_baseline/`
- Xerces-J Stage 1 analysis outputs: `results/xerces-j/stage1/`
- Human-readable reports: `docs/reports/`

## Scope Boundary

Stage 1 is a structural baseline. It does not implement NSGA-II, semantic embeddings, or Stage 2/Stage 3 optimization. Those later stages should compare against both default Leiden and tuned Leiden rather than treating the default run as the only baseline.
