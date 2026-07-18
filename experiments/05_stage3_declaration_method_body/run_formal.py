#!/usr/bin/env python3
"""Canonical formal-run wrapper. Use only after an explicitly approved run."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.stage3.final_formal_stage3 import main


if __name__ == "__main__":
    raise SystemExit(main())
