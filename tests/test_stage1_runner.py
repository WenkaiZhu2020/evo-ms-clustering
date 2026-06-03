from importlib.util import module_from_spec, spec_from_file_location
import hashlib
from pathlib import Path
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


def test_run_stage1_leiden_writes_outputs_to_temp_results(tmp_path: Path) -> None:
    require_leiden()
    write_fixture_repo(tmp_path)
    assert not (tmp_path / "results" / "jpetstore" / "00_pre_experiment").exists()

    output_dirs = stage1_runner.run_stage1_leiden(root=tmp_path, subject="jpetstore")

    output_dir = output_dirs[0]
    assert output_dir == tmp_path / "results" / "jpetstore" / "01_stage1_leiden_baseline"
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "baseline_metadata.yml",
        "clustering",
        "graph",
        "metrics",
        "summaries",
    ]
    assert sorted(path.name for path in (output_dir / "graph").iterdir()) == ["stage1_edges.csv"]
    assert sorted(path.name for path in (output_dir / "clustering").iterdir()) == ["stage1_clusters.csv"]
    assert sorted(path.name for path in (output_dir / "metrics").iterdir()) == ["stage1_metrics.csv"]
    assert sorted(path.name for path in (output_dir / "summaries").iterdir()) == ["stage1_cluster_summary.csv"]

    edges = pd.read_csv(output_dir / "graph" / "stage1_edges.csv")
    clusters = pd.read_csv(output_dir / "clustering" / "stage1_clusters.csv")
    metrics = pd.read_csv(output_dir / "metrics" / "stage1_metrics.csv")
    summary = pd.read_csv(output_dir / "summaries" / "stage1_cluster_summary.csv")
    metadata = yaml.safe_load((output_dir / "baseline_metadata.yml").read_text(encoding="utf-8"))

    assert list(edges.columns) == [
        "source",
        "target",
        "type_weight",
        "call_weight",
        "return_flow_weight",
        "argument_flow_weight",
        "ssa_flow_weight",
        "g_ssa_weight",
    ]
    assert len(edges) == 2
    assert edges["source"].ne(edges["target"]).all()
    assert len(_undirected_pairs(edges)) == len(edges)
    assert list(clusters.columns) == ["class_id", "class_name", "cluster_id"]
    assert set(clusters["class_id"]) == {"A", "B", "C", "D"}
    assert metrics.loc[0, "graph_type"] == "ssa"
    assert "g_ssa_weight" not in metrics.columns
    assert list(summary.columns) == ["cluster_id", "cluster_size", "class_names"]
    assert metadata["subject"] == "jpetstore"
    assert metadata["role"] == "frozen_leiden_baseline_for_later_comparison"
    assert metadata["baseline_name"] == "default_ssa_informed_leiden"
    assert metadata["graph_type"] == "ssa"
    assert metadata["ssa_lambda"] == 1.0
    assert metadata["resolution"] == 1.0
    assert metadata["seed"] == 42
    assert metadata["source_extracted_data"] == "data/extracted/jpetstore/"
    assert metadata["edge_table"] == "graph/stage1_edges.csv"
    assert metadata["edge_table_sha256"] == _sha256(output_dir / "graph" / "stage1_edges.csv")
    assert "generated_at_utc" in metadata
    assert not (tmp_path / "results" / "jpetstore" / "00_pre_experiment").exists()


def test_run_stage1_leiden_uses_config_subjects(tmp_path: Path) -> None:
    require_leiden()
    write_fixture_repo(tmp_path)

    output_dirs = stage1_runner.run_stage1_leiden(root=tmp_path)

    assert output_dirs == [tmp_path / "results" / "jpetstore" / "01_stage1_leiden_baseline"]


def test_run_stage1_leiden_uses_fixed_config_values(tmp_path: Path) -> None:
    require_leiden()
    write_fixture_repo(tmp_path)
    config_path = tmp_path / "configs" / "experiments" / "01_stage1_leiden.yml"
    config_path.write_text(
        "experiment_name: 01_stage1_leiden_baseline\n"
        "subjects:\n"
        "  - jpetstore\n"
        "graph_type: ssa\n"
        "ssa_lambda: 0.5\n"
        "resolution: 1.25\n"
        "seed: 7\n"
        "output_root: results\n",
        encoding="utf-8",
    )

    output_dirs = stage1_runner.run_stage1_leiden(root=tmp_path, subject="jpetstore")
    metadata = yaml.safe_load((output_dirs[0] / "baseline_metadata.yml").read_text(encoding="utf-8"))

    assert metadata["ssa_lambda"] == 0.5
    assert metadata["resolution"] == 1.25
    assert metadata["seed"] == 7


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
        "C,C,call,4,method_call,C.self\n",
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
        "graph_type: ssa\n"
        "ssa_lambda: 1.0\n"
        "resolution: 1.0\n"
        "seed: 42\n"
        "output_root: results\n",
        encoding="utf-8",
    )
    (root / "configs" / "subjects" / "jpetstore.yml").write_text(
        "subject: jpetstore\n"
        "extracted_output_path: data/extracted/jpetstore\n",
        encoding="utf-8",
    )


def _undirected_pairs(edges: pd.DataFrame) -> set[tuple[str, str]]:
    return {
        tuple(sorted((str(row["source"]), str(row["target"]))))
        for row in edges.to_dict("records")
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
