# Stage 3 report layout contract

The final Stage 3 experiment uses three ownership layers:

* `results/cross_subject/05_stage3_declaration_method_body/` stores generated
  machine-readable tables, analysis data, hashes, manifests, inventories, and
  validation evidence;
* `docs/reports/05_stage3_declaration_method_body/` stores human-readable
  findings, explanations, reproducibility guidance, and thesis figures;
* `reports/stage3/` is a legacy mixed root and is retired only after the
  migration manifest, byte-level checks, and all active path references pass.

Subject-specific formal results remain under
`results/<subject>/05_stage3_declaration_method_body/`. Scientific inputs and
intermediate artifacts remain under `data/`.

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
results/cross_subject/05_stage3_declaration_method_body/
  formal_statistics/
  stage2_vs_stage3/
  preference_response/
  quality/
  provenance/
  validation/
  figures/
```

## Current human-readable root

```text
docs/reports/05_stage3_declaration_method_body/
  README.md
  main_findings.md
  formal_results.md
  stage2_vs_stage3.md
  preference_response.md
  input_and_graph_quality.md
  reproducibility.md
  figures/
```

