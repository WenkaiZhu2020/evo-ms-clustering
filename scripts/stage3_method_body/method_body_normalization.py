"""Compatibility import for the reusable final Stage 3 normalizer."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.semantic.method_body import *  # noqa: F401,F403,E402
