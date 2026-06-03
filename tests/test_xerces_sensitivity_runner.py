from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


RUNNER_PATH = Path(__file__).resolve().parents[1] / "experiments" / "00_pre_experiment" / "run_xerces_j_sensitivity.py"
SPEC = spec_from_file_location("xerces_sensitivity_runner", RUNNER_PATH)
xerces_sensitivity_runner = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(xerces_sensitivity_runner)


def test_xerces_sensitivity_writes_only_sensitivity_outputs(tmp_path: Path) -> None:
    require_leiden()
    write_fixture_repo(tmp_path)
    report = tmp_path / "docs" / "reports" / "05_xerces-j_stage1_report.md"
    report.parent.mkdir(parents=True)
    report.write_text("do not overwrite", encoding="utf-8")

    output_dir = xerces_sensitivity_runner.run_xerces_j_sensitivity(root=tmp_path)

    assert output_dir == tmp_path / "results" / "xerces-j" / "00_pre_experiment" / "sensitivity"
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "cluster_size_summary.csv",
        "resolution_sweep.csv",
        "ssa_lambda_sweep.csv",
    ]
    assert not (tmp_path / "results" / "xerces-j" / "stage1").exists()
    assert not (tmp_path / "results" / "xerces-j" / "00_pre_experiment" / "comparison").exists()
    assert not (tmp_path / "results" / "xerces-j" / "00_pre_experiment" / "clustering").exists()
    assert report.read_text(encoding="utf-8") == "do not overwrite"


def require_leiden() -> None:
    pytest.importorskip("igraph")
    pytest.importorskip("leidenalg")


def write_fixture_repo(root: Path) -> None:
    (root / "configs" / "experiments").mkdir(parents=True)
    (root / "configs" / "subjects").mkdir(parents=True)
    (root / "configs" / "experiments" / "00_pre_experiment.yml").write_text(
        "experiment_name: 00_pre_experiment\n"
        "subjects:\n"
        "  - xerces-j\n"
        "ssa_graph:\n"
        "  ssa_lambda: 1.0\n"
        "expected_extracted_evidence_weights:\n"
        "  type_dependency: 1.0\n"
        "  method_call: 2.0\n"
        "  return_value_flow: 3.0\n"
        "  argument_passing_flow: 3.0\n"
        "leiden:\n"
        "  resolution: 1.0\n"
        "  seed: 42\n"
        "output_root: results\n",
        encoding="utf-8",
    )
    (root / "configs" / "subjects" / "xerces-j.yml").write_text(
        "subject: xerces-j\n"
        "extracted_output_path: data/extracted/xerces-j\n"
        "result_output_path: results/xerces-j\n",
        encoding="utf-8",
    )
    extracted = root / "data" / "extracted" / "xerces-j"
    extracted.mkdir(parents=True)
    (extracted / "class_nodes.csv").write_text(
        "class_id,class_name,package,class_file_path\n"
        "A,pkg.A,pkg,A.class\n"
        "B,pkg.B,pkg,B.class\n"
        "C,pkg.C,pkg,C.class\n"
        "D,pkg.D,pkg,D.class\n",
        encoding="utf-8",
    )
    (extracted / "structural_dependencies.csv").write_text(
        "source,target,dependency_type,weight,evidence_kind,evidence_location\n"
        "A,B,type,1,field_type_reference,A.field\n"
        "B,C,call,2,method_call,B.call\n"
        "C,D,type,1,field_type_reference,C.field\n",
        encoding="utf-8",
    )
    (extracted / "ssa_flow_edges.csv").write_text(
        "source,target,flow_type,weight,evidence_method,evidence_statement\n"
        "A,C,return_value_flow,3,A.method,A statement\n"
        "B,D,argument_passing_flow,3,B.method,B statement\n",
        encoding="utf-8",
    )
