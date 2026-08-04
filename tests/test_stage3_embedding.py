from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evo_ms.semantic.embeddings import load_saved_embeddings


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"jpetstore": 24, "daytrader": 53, "xerces": 814}


def test_final_embedding_artifacts_have_frozen_scope_and_dimension() -> None:
    for subject, count in EXPECTED.items():
        directory = ROOT / "data/embeddings/declaration_method_body" / subject
        vectors = load_saved_embeddings(directory / "embeddings.npy", rows=count, dimension=3584)
        metadata = json.loads((directory / "embedding_metadata.json").read_text(encoding="utf-8"))
        assert vectors.shape == (count, 3584)
        assert np.isfinite(vectors).all()
        assert metadata["representation_id"] == "declaration_method_body_v1"
        assert metadata["model_revision"] == "9a0457648f060c4279d4a3982d2d27a4df6fac59"
        assert metadata["output_dimension"] == 3584
