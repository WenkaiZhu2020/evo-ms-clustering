#!/usr/bin/env python3
"""Canonical read-only final Stage 3 analysis entry point."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.stage3.final_analyze import main


if __name__ == "__main__":
    raise SystemExit(main())
