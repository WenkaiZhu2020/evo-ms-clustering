"""Stage 2 structure-only NSGA-II optimization scaffold.

Module layout:
- `encoding.py`: integer label-vector encoding, conversion, and relabeling.
- `objectives.py`: three structural objectives plus anti-degeneration constraints.
- `problem.py`: lazy-import pymoo Problem wrapper.
"""

from evo_ms.optimization.objectives import STRUCTURAL_OBJECTIVES, ObjectiveSpec

__all__ = ["STRUCTURAL_OBJECTIVES", "ObjectiveSpec"]
