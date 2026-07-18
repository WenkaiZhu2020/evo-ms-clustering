#!/usr/bin/env python3
"""Canonical final Stage 3 preference-analysis entry point.

The implementation is intentionally delegated to the final-only analysis
module.  Stage 3A is historical provenance, not a runtime comparison stage.
"""

from __future__ import annotations

from scripts.preference_analysis.final_preference import main


if __name__ == "__main__":
    raise SystemExit(main())
