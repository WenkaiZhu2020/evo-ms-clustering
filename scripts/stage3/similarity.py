"""Compatibility import for the shared final true-cosine helper."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.semantic.graph import true_cosine_similarity  # noqa: E402

__all__ = ["true_cosine_similarity"]
