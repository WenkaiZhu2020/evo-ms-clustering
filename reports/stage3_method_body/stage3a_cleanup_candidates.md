# Stage 3A cleanup recommendation

No Stage 3A file is deleted in this audit, and no Git history is rewritten.
Removing a file from the Stage 3B working tree is separate from removing a
Stage 3A commit from Git history; the latter is out of scope and must not be
done.

| Category | Examples | Recommendation |
| --- | --- | --- |
| Safe to remove later from a temporary Stage 3B workspace | Interrupted or invalid files under an explicitly marked `stage3b_incomplete/` directory | Remove only after recording the PID, command, stop time, and invalid status. None currently exists. |
| Retain for comparison | `results/*/04_stage3_semantic/`, Stage 3A paired reports, and frozen input/embedding/graph hashes | Keep until Stage 3B validation and comparison are complete. |
| Retain because shared code depends on them | `src/evo_ms/`, common tests, and the frozen Stage 3A implementation used as a reference | Keep; route future Stage 3B calls through explicit adapters. |
| Retain until Stage 3B validation completes | Stage 3A configuration, method contract, and provenance manifests | Keep read-only for declaration-preservation regression checks. |
| Never remove from this branch | `stage3-declaration-final` tag, closure report, and frozen Stage 3A provenance | These are the audit trail for the confirmatory experiment. |

The current audit found no partial Stage 3B scientific outputs, no Stage 3B
lock, and no active Stage 3B computation.
