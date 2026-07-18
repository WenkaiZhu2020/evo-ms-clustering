from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
EXPERIMENT_ROOT = ROOT / "experiments/05_stage3_declaration_method_body"
SCRIPT_ROOT = ROOT / "scripts/05_stage3_declaration_method_body"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_src_has_no_experiment_or_script_imports():
    for path in SRC_ROOT.rglob("*.py"):
        names = _imports(path)
        assert not any(name == "experiments" or name.startswith("experiments.") for name in names), path
        assert not any(name == "scripts" or name.startswith("scripts.") for name in names), path
        text = path.read_text(encoding="utf-8")
        assert "spec_from_file_location" not in text, path


def test_stage3_experiment_has_no_script_imports():
    for path in EXPERIMENT_ROOT.glob("*.py"):
        assert not any(
            name == "scripts" or name.startswith("scripts.")
            for name in _imports(path)
        ), path


def test_stage3_script_directory_contains_only_shell_launchers():
    paths = sorted(path.name for path in SCRIPT_ROOT.iterdir())
    assert paths == ["analyze.sh", "prepare_semantic.sh", "run_robustness.sh", "run_stage3.sh"]
    assert all(path.suffix == ".sh" for path in SCRIPT_ROOT.iterdir())


def test_final_experiment_directory_is_exactly_five_files():
    paths = sorted(path.name for path in EXPERIMENT_ROOT.iterdir() if path.is_file())
    assert paths == ["README.md", "analyze.py", "prepare_semantic.py", "run.py", "run_robustness.py"]


def test_config_has_no_private_stage2_implementation_references():
    config = (ROOT / "configs/experiments/05_stage3_declaration_method_body.yml").read_text(encoding="utf-8")
    assert "experiments/02_stage2_nsga_structure_only/run.py:_" not in config
    assert "experiments/02_stage2_nsga_structure_only/run_robustness.py:" not in config


def test_active_stage3_runtime_uses_current_report_root():
    for path in EXPERIMENT_ROOT.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "reports/stage3" not in text, path
    assert (ROOT / "results/cross_subject/05_stage3_declaration_method_body").is_dir()


def test_graph_compatibility_sidecar_digests_are_self_consistent():
    import sys
    sys.path.insert(0, str(SRC_ROOT))
    from evo_ms.analysis.provenance import graph_compatibility_digest

    sidecar = json.loads(
        (ROOT / "reports/stage3/provenance/final_graph_compatibility_contract.json").read_text(
            encoding="utf-8"
        )
    )
    for subject, record in sidecar["subjects"].items():
        assert graph_compatibility_digest(record["compatibility_contract"]) == record["compatibility_contract_sha256"], subject
