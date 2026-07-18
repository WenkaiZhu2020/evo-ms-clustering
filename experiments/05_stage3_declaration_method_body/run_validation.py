#!/usr/bin/env python3
"""Canonical validation-only entry point; never runs an optimizer."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.stage3_method_body.validate_seed00_optimizer import main


if __name__ == "__main__":
    raise SystemExit(main())
