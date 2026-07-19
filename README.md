# Evolutionary Software Clustering — Stage 2 final branch

This repository is the `stage2-nsga` branch. It contains:

- Stage 0 pre-experiment diagnostics and calibration;
- the Stage 1 Leiden baseline and seed-robustness outputs;
- the Stage 2 structure-only NSGA-II implementation, analyses, and frozen
  formal 30-seed results.

It does not contain an active or formal Stage 3 implementation. Stage 3 is
carried by an independent branch; its historical contents remain available
through Git history.

The formal computation snapshot is `stage2-frozen @ 2da4408`, as tagged in
Git. The reproducibility cleanup in this worktree happens after that result
freeze; it does not alter or impersonate the formal computation commit.

## Workflow

```text
Java extraction with Soot / Shimple
→ normalized CSV inputs
→ graph construction and Stage 0 diagnostics
→ fixed Stage 1 Leiden baseline
→ structure-only Stage 2 NSGA-II
→ formal 30-seed outputs and cross-subject analyses
```

The main graph inputs are `G_raw`, built from structural dependencies, and
`G_ssa`, which adds selected SSA-derived flow evidence. Stage 1 compares their
Leiden partitions. Stage 2 optimizes structural objectives on the frozen raw
graph inputs.

## Main locations

| Purpose | Location |
| --- | --- |
| Stage 1 runner | `experiments/01_stage1_leiden_baseline/` |
| Stage 2 runner | `experiments/02_stage2_nsga_structure_only/` |
| Formal Stage 2 runs | `results/<subject>/03_stage2_nsga/robustness_final_30seeds/` |
| Final statistics | `results/cross_subject/03_stage2_nsga/final_statistics/` |
| Results classification | `results/FORMAL_RESULTS_INDEX.md` |
| Reproducibility guide | `docs/reproducibility/README.md` |
| Unified verifier | `scripts/reproducibility/verify.py` |
| Machine-readable environment | `configs/reproducibility/environments.json` |

The experiment and result numbering is intentionally different. The
`experiments/` sequence numbers the main implementation stages, so Stage 2 is
`02_stage2_nsga_structure_only/`. The historical `results/` sequence also
counts Stage 1 seed robustness as step `02`, so Stage 2 results remain under
`03_stage2_nsga/`. These are historical output paths, not a conflict in stage
definitions, and they are not renamed.

## Subjects and data

The three Java subjects are JPetStore, DayTrader, and Xerces-J. Normalized
extractor inputs are under `data/extracted/<subject>/`; raw checkouts are local,
ignored inputs under `data/raw_projects/`. Subject preparation scripts are in
`scripts/extraction/` and their paths are declared by
`configs/subjects/*.yml`.

## Reproduction entry point

The single human-readable entry point is
[`docs/reproducibility/README.md`](docs/reproducibility/README.md). It covers
installation with uv, the environment contract, formal manifests, checksum
validation, and the unified verifier. The standard commands are:

```bash
uv sync --frozen
uv run --frozen python scripts/reproducibility/verify.py --stage stage2
PYTHONPATH=src uv run --frozen pytest -q
```

The verifier checks saved inputs, formal seed layout, core source fingerprints,
configuration hashes, manifest environment evidence, and all three Stage 2
subjects. It never runs NSGA-II.

## Repository structure

```text
configs/       Subject, experiment, and reproducibility configuration.
data/          Raw-project placeholders, extracted CSV inputs, and references.
docs/          Stage 1/2 technical notes, reports, and public reproducibility guide.
experiments/   Python experiment runners and analyses for Stage 0–2.
results/       Generated outputs; see FORMAL_RESULTS_INDEX.md.
scripts/       Extraction, experiment wrappers, analysis, visualization, and verification.
src/           Core Python implementation.
tests/         Python tests and repository layout checks.
tools/         Java Soot extractor.
```
