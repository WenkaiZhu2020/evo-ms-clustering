# Repository Consistency Audit

This audit records the documentation consistency state after adopting numbered Markdown filenames as the canonical convention.

## Scope

- Stage 1 documentation lives under `docs/stage1/`.
- Human-readable reports live under `docs/reports/`.
- Generated experiment outputs remain under `results/`.
- Root-level `reports/` is not used.

## Canonical Documentation Layout

Stage 1 technical documentation:

- `docs/stage1/00_README.md`
- `docs/stage1/01_stage1_overview.md`
- `docs/stage1/02_soot_extraction.md`
- `docs/stage1/03_data_schema.md`
- `docs/stage1/04_graph_construction.md`
- `docs/stage1/05_metric_definitions.md`

Reports:

- `docs/reports/00_README.md`
- `docs/reports/01_test_case_selection_summary.md`
- `docs/reports/02_stage1_cross_case_summary.md`
- `docs/reports/03_ssa_weight_adjustment_log.md`
- `docs/reports/04_repo_consistency_audit.md`
- `docs/reports/05_xerces-j_stage1_report.md`

Subject-specific notes may continue after the main report sequence, for example `docs/reports/06_xerces-j_extraction_notes.md`.

## Current Consistency Findings

| area | status | note |
| --- | --- | --- |
| Stage 1 story | consistent | Documentation describes `G_raw` and `G_ssa`, with JPetStore, DayTrader, and Xerces-J as active subjects. |
| Graph naming | consistent | The canonical graph names are `G_raw` and `G_ssa`. |
| Weight naming | consistent | The canonical weight columns are `raw_weight` and `g_ssa_weight`. |
| Report location | consistent | Reports are under `docs/reports/`; root-level `reports/` is not part of the layout. |
| Numbered filenames | consistent | Canonical Markdown filenames use numeric prefixes and underscores, with no spaces. |
| Later-stage scope | consistent | Stage 1 prepares baselines and evidence design; it does not prove NSGA-II or semantic embeddings. |

## Follow-Up Checks

Before committing documentation changes, run:

```bash
git status --short
git diff --check
```
