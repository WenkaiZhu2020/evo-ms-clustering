#!/usr/bin/env python3
"""Canonical final Stage 3 preference-analysis entry point."""

from __future__ import annotations

from scripts.preference_analysis.final_preference import *  # noqa: F401,F403
from scripts.preference_analysis.final_preference import _dominates, main


if __name__ == "__main__":
    raise SystemExit(main())
