# Stage 3 report layout contract

The final Stage 3 experiment uses three ownership layers:

* `results/stage3/` stores generated
  machine-readable tables, analysis data, hashes, manifests, inventories, and
  validation evidence;
* `docs/stage3/findings/` stores human-readable
  findings, explanations, reproducibility guidance, and thesis figures;
* `reports/stage3/` is a legacy mixed root and is retired only after the
  migration manifest, byte-level checks, and all active path references pass.

Subject-specific formal results remain under
`results/stage3/subjects/<subject>/declaration_method_body/`. Scientific inputs and
intermediate artifacts remain under `data/`.

The current configuration's `outputs.report_root` is a layout-only output
location and now points to the machine-readable result root. Frozen per-run
configuration snapshots and historical manifest config hashes retain the
original values and are not rewritten.

## Historical paths

Paths embedded in frozen configuration snapshots and historical provenance
files are evidence of the original run and are not rewritten during this
migration. Current code must use the current report locator instead. A legacy
path appearing in immutable evidence is therefore not an active output path.

## Migration invariants

The migration is content-preserving. No semantic input, embedding, graph,
optimizer result, seed result, statistical output, or external metric is
regenerated. CSV, JSON, and PDF bytes are hash-checked before and after each
move. The first migration pass does not rename files merely to shorten their
names.

## Current machine-readable roots

```text
results/stage3/
  subjects/<subject>/declaration_method_body/
  cross_subject/formal_statistics/
  cross_subject/stage2_comparison/
  cross_subject/preference_analysis/
  data_quality/
  reproducibility_checks/
  provenance/
```

## Current human-readable root

```text
docs/stage3/findings/
  README.md
  formal_results.md
  stage2_vs_stage3.md
  preference_response.md
  input_quality_summary.md
  semantic_graph_quality_summary.md
  figures/
```
