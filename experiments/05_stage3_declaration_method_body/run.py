#!/usr/bin/env python3
"""Canonical final Stage 3 experiment entry point."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.optimization import stage3_runtime as _runtime  # noqa: E402
from evo_ms.optimization.stage3_runtime import *  # noqa: F401,F403,E402

# Explicitly re-export private helpers used by the frozen adapter. Star
# imports intentionally omit underscore-prefixed names.
_nondominated_indices = _runtime._nondominated_indices
_front_arrays = _runtime._front_arrays
_solution_rows = _runtime._solution_rows
_project_front = _runtime._project_front
_normalize_projected = _runtime._normalize_projected
_independent_projected_hv = _runtime._independent_projected_hv
_redundancy = _runtime._redundancy


if __name__ == "__main__":
    from evo_ms.optimization.stage3_runtime import main

    raise SystemExit(main())
