#!/usr/bin/env python3
"""Build the additive DayTrader G_raw versus G_ssa local comparison."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.visualization.config import load_visualization_config
from evo_ms.visualization.figures.stage1_daytrader_ssa_only_edges import (
    build_figure,
    prepare_figure_data,
    summary,
)
from evo_ms.visualization.provenance import sha256_file


def main() -> int:
    config = load_visualization_config()
    outputs = build_figure(config)
    with tempfile.TemporaryDirectory(prefix="daytrader-ssa-summary-") as temporary:
        data = prepare_figure_data(config, Path(temporary))
    print(json.dumps(summary(data), indent=2, sort_keys=True))
    for name, path in sorted(outputs.items()):
        print(f"{name}\t{path.relative_to(ROOT)}\t{path.stat().st_size}\t{sha256_file(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

