# Stage 3: Declaration + Method Body Semantic Extension

This directory owns the final Stage 3 experiment implementation. The frozen
representation is `declaration_method_body_v1` and the experiment identifier is
`stage3_declaration_method_body`.

The four Python experiment entry points have distinct responsibilities:

- `prepare_semantic.py` prepares semantic inputs and owns embedding/graph
  orchestration;
- `run.py` runs one explicit Stage 3 seed and validates its output;
- `run_robustness.py` owns formal-seed execution and validation;
- `analyze.py` reads saved Stage 2 and Stage 3 artifacts for validation and
  deterministic reporting-only regeneration/checks.

`synchronize_stage2_operating_profile.py` is an internal maintenance utility,
not a fifth experiment stage. It deterministically synchronizes the frozen
Stage 2 modularity-band operating profile into the saved Stage 3 preference
analysis. Its generated CSVs are committed and reproducible byte-for-byte.

The final reporting contract is regenerated with `analyze.py
--write-reporting` and verified with `analyze.py --check-reporting`. The loader
accepts only the frozen Stage 2 5% modularity-band profile and final Stage 3
Declaration + Method Body selected solutions; it fails on incomplete seed or
class-universe alignment.

Reusable numerical behaviour is provided by `src/evo_ms`. No file in this
directory imports a script or the Stage 2 experiment.

Accepted artifact roots are write-protected by default. Generation commands
must be given explicit output destinations and must never silently overwrite
accepted semantic inputs, embeddings, graphs, or results.
