# Reproducibility guide

This is the single public human-readable entry point for reproducing and
verifying the saved work in the `stage2-nsga` branch. Verification reads saved
artifacts and never runs a new NSGA-II experiment.

## 1. Repository scope

The branch contains Stage 0 pre-experiment work, Stage 1 Leiden baseline and
seed-robustness outputs, and Stage 2 structure-only NSGA-II code, analyses, and
formal 30-seed results. Stage 3 is not present in this branch; its historical
content is preserved by Git history and its formal work belongs to an
independent Stage 3 branch.

## 2. Supported environment

The machine-readable contract is
`configs/reproducibility/environments.json`. It is the only environment and
stage-status index. The supported Python target is 3.13.7 and the supported
dependency manager is uv. The exact Python package set is locked in `uv.lock`.

The formal Stage 2 manifests directly record Python 3.13.7, NumPy 2.4.4, and
pymoo 0.6.2. The other locked package versions are supported reproduction
targets, not claims that the historical formal run recorded a complete freeze.

## 3. Installation with uv

From the repository root:

```bash
uv sync --frozen
```

This is the only supported Python installation entry. Do not install from an
independent requirements file.

## 4. Unified verification commands

Full Stage 2 verification, including the supported local environment:

```bash
uv run --frozen python scripts/reproducibility/verify.py --stage stage2
```

Environment only:

```bash
uv run --frozen python scripts/reproducibility/verify.py \
  --stage stage2 \
  --environment-only
```

Skip local environment checks and verify files, hashes, seeds, and manifests:

```bash
uv run --frozen python scripts/reproducibility/verify.py \
  --stage stage2 \
  --skip-environment
```

The repository-level status entry point is:

```bash
uv run --frozen python scripts/reproducibility/verify.py --stage all
```

It runs Stage 2 verification, reports Stage 1 as `not implemented / not
formally frozen`, and reports Stage 3 as `not present in this branch`. Because
Stage 1 has no formal verifier, `--stage all` returns nonzero even when Stage 2
passes; this prevents an incomplete stage from being presented as verified.

## 5. Stage 1 status

Stage 1 saved outputs and seed-robustness results are present, but a formal
Stage 1 environment record and repository-level verifier were not recorded.
The unified CLI reports this explicitly rather than claiming a pass.

## 6. Stage 2 formal provenance

The verifier retains the formal checks for all three subjects:

- formal seeds exactly `0..29`;
- per-seed Pareto, selected-solution, partition, metadata, and metric files;
- extracted `class_nodes.csv` and `structural_dependencies.csv` hashes;
- extraction and optimization source fingerprints; the formal runner
  fingerprint remains historical because its retired selected-summary writers
  were removed after the formal run;
- algorithm and bounds configuration hashes;
- consistent manifest identity across subjects;
- formal manifest Python, NumPy, and pymoo evidence.

The formal computation snapshot is tagged `stage2-frozen @ 2da4408`. The
cleanup that introduces uv and the unified verifier is later work and must not
be confused with the formal computation commit.

## 7. Stage 3 status in this branch

Stage 3 is not present in `stage2-nsga`: there are no active Stage 3 runners,
scripts, formal results, or manifests here. Git history retains the historical
content, while formal Stage 3 work is handled by an independent branch.

## 8. Formal result locations

Use only these paths for formal Stage 2 thesis numbers:

```text
results/jpetstore/03_stage2_nsga/robustness_final_30seeds/
results/daytrader/03_stage2_nsga/robustness_final_30seeds/
results/xerces-j/03_stage2_nsga/robustness_final_30seeds/
results/cross_subject/03_stage2_nsga/final_statistics/
```

The result-numbering difference is historical: `experiments/02_...` is the
Stage 2 implementation sequence, while `results/03_...` follows the result
sequence that counts Stage 1 seed robustness as step 02. Frozen result paths
are therefore left unchanged.

## 9. Manifests and verification

Formal manifests are the three `robustness_manifest.json` files inside the
formal 30-seed directories. The active read-only verifier is:

```bash
python scripts/reproducibility/verify.py --stage stage2 --skip-environment
```

The former saved-output checksum snapshot was removed because it listed the
retired `selected_solution.csv` and `selected_partition.csv` files. The
current canonical profile and downstream provenance are recorded in
`results/cross_subject/03_stage2_nsga/modularity_band/`, and the cleanup
inventory is recorded in
`results/cross_subject/03_stage2_nsga/final_statistics/historical_selector_cleanup_inventory.csv`.

## 10. External Java/build toolchain

`configs/reproducibility/environments.json` distinguishes current cleanup-host
observations from formal evidence. Java, Javac, Maven, and Ant versions were
not recorded in the formal Stage 2 manifests; they are therefore `unknown` as
formal evidence. The current cleanup host exposes Java/Javac 25.0.1 and Maven
3.9.11, while Ant is not installed. The Soot dependency declaration is 4.5.0,
but the formal runtime use of that version was not recorded. No Java extractor
or formal experiment is rerun by these checks.

## 11. Historical NumPy discrepancy

An older Git snapshot recorded NumPy 2.3.5. The formal Stage 2 manifests record
NumPy 2.4.4. The older snapshot is not an installation or verification source;
its contents remain traceable through Git history. The supported post-freeze
reproduction environment uses NumPy 2.4.4 in both `pyproject.toml` and
`uv.lock`.

## 12. Known limitations and evidence gaps

- The formal manifests do not contain a complete dependency freeze, wheel
  hashes, or the versions of every Python package used by the project.
- The formal computation was recorded with a dirty worktree; the manifests
  retain its working-tree diff hash.
- Raw Java checkout revisions and formal Java/build-tool versions were not
  recorded, so exact source-to-CSV re-extraction is not claimed.
- Stage 1 has saved outputs but no formal environment record.
- Stage 3 is intentionally absent from this branch.

## 13. Freeze tag versus cleanup commit

`stage2-frozen` identifies the formal computation snapshot at `2da4408`. The
uv lock, environment contract, unified CLI, documentation, and layout checks
are reproducibility-cleanup changes made after that freeze. They preserve the
formal outputs and provenance; they are not evidence that the formal runs were
executed from the cleaned worktree.
