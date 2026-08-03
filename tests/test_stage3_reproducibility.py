from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_provenance_points_to_final_representation_and_existing_hashes() -> None:
    provenance_root = ROOT / "results/stage3/provenance"
    manifest = json.loads((provenance_root / "final_stage3_provenance.json").read_text(encoding="utf-8"))
    embedding_manifest = json.loads((provenance_root / "embedding_generation_manifest.json").read_text(encoding="utf-8"))
    graph_manifest = json.loads((provenance_root / "semantic_graph_generation_manifest.json").read_text(encoding="utf-8"))
    assert manifest["representation_id"] == "declaration_method_body_v1"
    for subject, values in manifest["subjects"].items():
        embedding_values = embedding_manifest["subjects"][subject]
        graph_values = graph_manifest["subjects"][subject]
        assert embedding_values["representation_id"] == manifest["representation_id"]
        assert graph_values["representation_id"] == manifest["representation_id"]
        assert values["embedding_aggregate_sha256"] == embedding_values["aggregate_embedding_sha256"]
        assert values["graph_sha256"] == graph_values["graph_hash"]
