# Reproducibility entry point

The final repository exposes one supported Python environment for Stage 1,
Stage 2, and Stage 3:

```bash
uv sync --frozen
uv run --frozen pytest
```

The supported dependency contract is `pyproject.toml` plus `uv.lock`. Exact
versions and the distinction between supported reproduction and historical
generation environments are machine-readable in
`configs/reproducibility/environments.json`.

## Historical environment ownership

- Stage 1 did not preserve a complete historical lock. The unified environment
  supports its code and tests without claiming to reconstruct missing history.
- The `stage2-nsga` branch remains authoritative for the environment that
  generated Stage 2 formal artifacts. Stage 3 does not edit that branch's
  environment record.
- The final Stage 3 branch uses the unified lock as a compatible superset. The
  previous Stage 3 requirements lock is retained under
  `results/stage3/provenance/environment/` as historical evidence only.

Stage-specific scientific contracts and safe read-only validation commands are
documented in `docs/stage2/reproducibility.md` and
`docs/stage3/reproducibility.md`.
