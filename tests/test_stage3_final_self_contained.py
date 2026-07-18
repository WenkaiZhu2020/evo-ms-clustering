from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiments/05_stage3_declaration_method_body.yml"
FINAL_RUNTIME_FILES = (
    ROOT / "experiments/05_stage3_declaration_method_body/run.py",
    ROOT / "scripts/stage3_method_body/run_formal_stage3b.py",
    ROOT / "scripts/stage3_method_body/analyze_formal_stage3b.py",
    ROOT / "scripts/preference_analysis/analyze_preference_response.py",
    ROOT / "scripts/preference_analysis/final_preference.py",
)


def test_final_config_is_self_contained():
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["experiment_name"] == "stage3_declaration_method_body"
    assert config["representation_id"] == "declaration_method_body_v1"
    assert "base_experiment_config" not in config
    assert config["input"]["semantic_text_root"] == "data/semantic_text/declaration_method_body"
    assert config["input"]["stage3a_input_required"] is False
    assert all("05_stage3_declaration_method_body" in value for value in config["outputs"]["result_roots"].values())


def test_final_runtime_has_no_stage3a_artifact_reads():
    forbidden = ("experiments/04_stage3_semantic", "data/semantic_inputs", "/04_stage3_semantic/")
    for path in FINAL_RUNTIME_FILES:
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), path


def test_final_representation_artifacts_exist_and_are_scoped():
    for subject in ("jpetstore", "daytrader", "xerces"):
        text = ROOT / "data/semantic_text/declaration_method_body" / subject / "class_semantic_inputs.csv"
        embedding = ROOT / "data/embeddings/declaration_method_body" / subject / "embeddings.npy"
        graph = ROOT / "data/semantic_graphs/declaration_method_body" / subject / "semantic_edges.csv"
        assert text.is_file()
        assert embedding.is_file()
        assert graph.is_file()
