from importlib.util import module_from_spec, spec_from_file_location
import hashlib
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


RUNNER_PATH = Path(__file__).resolve().parents[1] / "experiments" / "01_stage1_leiden_baseline" / "run.py"
SPEC = spec_from_file_location("stage1_runner", RUNNER_PATH)
stage1_runner = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(stage1_runner)


def test_run_stage1_leiden_writes_two_profile_outputs_to_temp_results(tmp_path: Path) -> None:
    require_leiden()
    write_fixture_repo(tmp_path)
    assert not (tmp_path / "results" / "jpetstore" / "00_pre_experiment").exists()

    output_dirs = stage1_runner.run_stage1_leiden(root=tmp_path, subject="jpetstore")

    output_dir = output_dirs[0]
    assert output_dir == tmp_path / "results" / "jpetstore" / "01_stage1_leiden_baseline"
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "baseline_index.yml",
        "raw_reference_leiden",
        "ssa_selected_leiden",
    ]

    index = yaml.safe_load((output_dir / "baseline_index.yml").read_text(encoding="utf-8"))
    assert index["subject"] == "jpetstore"
    assert [row["profile_name"] for row in index["generated_profiles"]] == [
        "raw_reference_leiden",
        "ssa_selected_leiden",
    ]

    raw_dir = output_dir / "raw_reference_leiden"
    ssa_dir = output_dir / "ssa_selected_leiden"
    _assert_profile_layout(raw_dir)
    _assert_profile_layout(ssa_dir)

    raw_edges = pd.read_csv(raw_dir / "graph" / "stage1_edges.csv")
    ssa_edges = pd.read_csv(ssa_dir / "graph" / "stage1_edges.csv")
    assert list(raw_edges.columns) == ["source", "target", "type_weight", "call_weight", "raw_weight"]
    assert "g_ssa_weight" in ssa_edges.columns
    assert len(raw_edges) == 1
    assert len(ssa_edges) == 2
    assert raw_edges["source"].ne(raw_edges["target"]).all()
    assert ssa_edges["source"].ne(ssa_edges["target"]).all()
    assert len(_undirected_pairs(raw_edges)) == len(raw_edges)
    assert len(_undirected_pairs(ssa_edges)) == len(ssa_edges)

    raw_clusters = pd.read_csv(raw_dir / "clustering" / "stage1_clusters.csv")
    ssa_clusters = pd.read_csv(ssa_dir / "clustering" / "stage1_clusters.csv")
    assert list(raw_clusters.columns) == ["class_id", "class_name", "cluster_id"]
    assert list(ssa_clusters.columns) == ["class_id", "class_name", "cluster_id"]

    raw_metadata = yaml.safe_load((raw_dir / "baseline_metadata.yml").read_text(encoding="utf-8"))
    ssa_metadata = yaml.safe_load((ssa_dir / "baseline_metadata.yml").read_text(encoding="utf-8"))
    assert raw_metadata["profile_name"] == "raw_reference_leiden"
    assert raw_metadata["graph_type"] == "raw"
    assert raw_metadata["ssa_lambda"] == 0.0
    assert raw_metadata["resolution"] == 1.0
    assert raw_metadata["selection_role"] == "strongest_admissible_raw_structural_reference"
    assert ssa_metadata["profile_name"] == "ssa_selected_leiden"
    assert ssa_metadata["graph_type"] == "ssa"
    assert ssa_metadata["ssa_lambda"] == 2.0
    assert ssa_metadata["resolution"] == 1.25
    assert ssa_metadata["selection_role"] == "strongest_admissible_nonzero_ssa_comparison"
    for metadata, profile_dir in [(raw_metadata, raw_dir), (ssa_metadata, ssa_dir)]:
        assert metadata["role"] == "frozen_leiden_baseline_for_later_comparison"
        assert metadata["selection_source"] == "daytrader_reference_calibration"
        assert metadata["source_extracted_data"] == "data/extracted/jpetstore/"
        assert metadata["edge_table"] == "graph/stage1_edges.csv"
        assert metadata["edge_table_sha256"] == _sha256(profile_dir / "graph" / "stage1_edges.csv")
        assert metadata["extracted_input_sha256"] == {
            "class_nodes.csv": _sha256(tmp_path / "data" / "extracted" / "jpetstore" / "class_nodes.csv"),
            "structural_dependencies.csv": _sha256(
                tmp_path / "data" / "extracted" / "jpetstore" / "structural_dependencies.csv",
            ),
            "ssa_flow_edges.csv": _sha256(tmp_path / "data" / "extracted" / "jpetstore" / "ssa_flow_edges.csv"),
        }
        assert metadata["base_evidence_weights"] == {
            "type_dependency": 1.0,
            "method_call": 2.0,
            "return_value_flow": 3.0,
            "argument_passing_flow": 3.0,
        }
        assert "generated_at_utc" in metadata
        assert "git_head" in metadata
        assert "git_dirty" in metadata

    assert not (tmp_path / "results" / "jpetstore" / "00_pre_experiment").exists()


def test_run_stage1_leiden_uses_config_subjects(tmp_path: Path) -> None:
    require_leiden()
    write_fixture_repo(tmp_path)

    output_dirs = stage1_runner.run_stage1_leiden(root=tmp_path)

    assert output_dirs == [tmp_path / "results" / "jpetstore" / "01_stage1_leiden_baseline"]


def test_run_stage1_leiden_uses_profile_config_values(tmp_path: Path) -> None:
    require_leiden()
    write_fixture_repo(tmp_path)
    config_path = tmp_path / "configs" / "experiments" / "01_stage1_leiden.yml"
    config_path.write_text(
        "experiment_name: 01_stage1_leiden_baseline\n"
        "subjects:\n"
        "  - jpetstore\n"
        "expected_extracted_evidence_weights:\n"
        "  type_dependency: 1.0\n"
        "  method_call: 2.0\n"
        "  return_value_flow: 3.0\n"
        "  argument_passing_flow: 3.0\n"
        "profiles:\n"
        "  custom_ssa:\n"
        "    graph_type: ssa\n"
        "    ssa_lambda: 0.5\n"
        "    resolution: 1.25\n"
        "    seed: 7\n"
        "    selection_source: fixture\n"
        "    selection_role: fixture_role\n"
        "output_root: results\n",
        encoding="utf-8",
    )

    output_dirs = stage1_runner.run_stage1_leiden(root=tmp_path, subject="jpetstore")
    metadata = yaml.safe_load(
        (output_dirs[0] / "custom_ssa" / "baseline_metadata.yml").read_text(encoding="utf-8"),
    )

    assert metadata["ssa_lambda"] == 0.5
    assert metadata["resolution"] == 1.25
    assert metadata["seed"] == 7
    assert metadata["selection_source"] == "fixture"
    assert metadata["selection_role"] == "fixture_role"


def test_run_stage1_leiden_validates_embedded_evidence_weights(tmp_path: Path) -> None:
    write_fixture_repo(tmp_path)
    path = tmp_path / "data" / "extracted" / "jpetstore" / "ssa_flow_edges.csv"
    path.write_text(
        "source,target,flow_type,weight,evidence_method,evidence_statement\n"
        "A,B,argument_passing_flow,1,A.method,A statement\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="argument_passing_flow expected 3.0"):
        stage1_runner.run_stage1_leiden(root=tmp_path, subject="jpetstore")


def test_run_stage1_leiden_reports_missing_extracted_input(tmp_path: Path) -> None:
    write_minimal_config(tmp_path)
    extracted = tmp_path / "data" / "extracted" / "jpetstore"
    extracted.mkdir(parents=True)
    (extracted / "class_nodes.csv").write_text(
        "class_id,class_name,package,class_file_path\n"
        "A,pkg.A,pkg,A.class\n",
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="structural_dependencies.csv"):
        stage1_runner.run_stage1_leiden(root=tmp_path, subject="jpetstore")


def test_git_dirty_ignores_generated_results(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    (tmp_path / "results" / "jpetstore").mkdir(parents=True)
    (tmp_path / "results" / "jpetstore" / "generated.csv").write_text("x\n", encoding="utf-8")

    assert stage1_runner._git_dirty(tmp_path) is False

    (tmp_path / "README.md").write_text("dirty\n", encoding="utf-8")
    assert stage1_runner._git_dirty(tmp_path) is True


def require_leiden() -> None:
    pytest.importorskip("igraph")
    pytest.importorskip("leidenalg")


def write_fixture_repo(root: Path) -> None:
    write_minimal_config(root)
    extracted = root / "data" / "extracted" / "jpetstore"
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
        "B,A,type,1,field_type_reference,B.field\n"
        "A,B,call,2,method_call,A.call\n"
        "C,C,call,2,method_call,C.self\n",
        encoding="utf-8",
    )
    (extracted / "ssa_flow_edges.csv").write_text(
        "source,target,flow_type,weight,evidence_method,evidence_statement\n"
        "A,B,argument_passing_flow,3,A.method,A statement\n"
        "C,D,return_value_flow,3,C.method,C statement\n"
        "D,C,return_value_flow,3,D.method,D statement\n"
        "B,B,argument_passing_flow,3,B.method,B self\n",
        encoding="utf-8",
    )


def write_minimal_config(root: Path) -> None:
    (root / "configs" / "experiments").mkdir(parents=True)
    (root / "configs" / "subjects").mkdir(parents=True)
    (root / "configs" / "experiments" / "01_stage1_leiden.yml").write_text(
        "experiment_name: 01_stage1_leiden_baseline\n"
        "subjects:\n"
        "  - jpetstore\n"
        "expected_extracted_evidence_weights:\n"
        "  type_dependency: 1.0\n"
        "  method_call: 2.0\n"
        "  return_value_flow: 3.0\n"
        "  argument_passing_flow: 3.0\n"
        "profiles:\n"
        "  raw_reference_leiden:\n"
        "    graph_type: raw\n"
        "    ssa_lambda: 0.0\n"
        "    resolution: 1.0\n"
        "    seed: 42\n"
        "    selection_source: daytrader_reference_calibration\n"
        "    selection_role: strongest_admissible_raw_structural_reference\n"
        "  ssa_selected_leiden:\n"
        "    graph_type: ssa\n"
        "    ssa_lambda: 2.0\n"
        "    resolution: 1.25\n"
        "    seed: 42\n"
        "    selection_source: daytrader_reference_calibration\n"
        "    selection_role: strongest_admissible_nonzero_ssa_comparison\n"
        "output_root: results\n",
        encoding="utf-8",
    )
    (root / "configs" / "subjects" / "jpetstore.yml").write_text(
        "subject: jpetstore\n"
        "extracted_output_path: data/extracted/jpetstore\n",
        encoding="utf-8",
    )


def _assert_profile_layout(profile_dir: Path) -> None:
    assert sorted(path.name for path in profile_dir.iterdir()) == [
        "baseline_metadata.yml",
        "clustering",
        "graph",
        "metrics",
        "summaries",
    ]
    assert sorted(path.name for path in (profile_dir / "graph").iterdir()) == ["stage1_edges.csv"]
    assert sorted(path.name for path in (profile_dir / "clustering").iterdir()) == ["stage1_clusters.csv"]
    assert sorted(path.name for path in (profile_dir / "metrics").iterdir()) == ["stage1_metrics.csv"]
    assert sorted(path.name for path in (profile_dir / "summaries").iterdir()) == ["stage1_cluster_summary.csv"]


def _undirected_pairs(edges: pd.DataFrame) -> set[tuple[str, str]]:
    return {
        tuple(sorted((str(row["source"]), str(row["target"]))))
        for row in edges.to_dict("records")
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
