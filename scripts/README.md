# Scripts

Scripts are user-facing entry points around the Python experiment code.

## Responsibilities

- `extraction/`: prepare Java subjects and invoke the Soot/Shimple extractor.
- `00_pre_experiment/`: Stage 0 diagnostic and calibration wrappers.
- `01_stage1_leiden_baseline/`: Stage 1 formal baseline wrappers.
- `02_stage2_nsga_structure_only/`: Stage 2 run, smoke, test, and seed-verification wrappers.
- `reproducibility/`: repository-level verification. The only public verification CLI is `verify.py`.
- `visualization/`: optional visualization helpers when present.
- `analysis/`: optional post-hoc analysis helpers when present.

The Python implementations remain under `experiments/` and `src/`; shell files
in this directory should remain thin, explicit launchers. Stage 3 launchers
are intentionally absent from the `stage2-nsga` branch.

## Recommended verification entry point

```bash
uv run --frozen python scripts/reproducibility/verify.py --stage stage2
```

The Stage 2 shell wrappers call the same CLI in `--environment-only` mode
before any run command.
