from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


RUNNER_PATH = Path(__file__).resolve().parents[1] / "experiments" / "01_stage1_leiden_baseline" / "run.py"
SPEC = spec_from_file_location("stage1_runner", RUNNER_PATH)
stage1_runner = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(stage1_runner)


def test_run_stage1_leiden_writes_outputs_to_temp_results(tmp_path: Path) -> None:
    require_leiden()
    write_fixture_repo(tmp_path)

    output_dirs = stage1_runner.run_stage1_leiden(root=tmp_path, subject="jpetstore")

    output_dir = output_dirs[0]
    assert output_dir == tmp_path / "results" / "jpetstore" / "01_stage1_leiden_baseline"
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "clustering",
        "metrics",
        "summaries",
    ]
    assert sorted(path.name for path in (output_dir / "clustering").iterdir()) == ["stage1_clusters.csv"]
    assert sorted(path.name for path in (output_dir / "metrics").iterdir()) == ["stage1_metrics.csv"]
    assert sorted(path.name for path in (output_dir / "summaries").iterdir()) == ["stage1_cluster_summary.csv"]

    clusters = pd.read_csv(output_dir / "clustering" / "stage1_clusters.csv")
    metrics = pd.read_csv(output_dir / "metrics" / "stage1_metrics.csv")
    summary = pd.read_csv(output_dir / "summaries" / "stage1_cluster_summary.csv")

    assert list(clusters.columns) == ["class_id", "class_name", "cluster_id"]
    assert set(clusters["class_id"]) == {"A", "B", "C"}
    assert metrics.loc[0, "graph_type"] == "ssa"
    assert "g_ssa_weight" not in metrics.columns
    assert list(summary.columns) == ["cluster_id", "cluster_size", "class_names"]


def test_run_stage1_leiden_uses_config_subjects(tmp_path: Path) -> None:
    require_leiden()
    write_fixture_repo(tmp_path)

    output_dirs = stage1_runner.run_stage1_leiden(root=tmp_path)

    assert output_dirs == [tmp_path / "results" / "jpetstore" / "01_stage1_leiden_baseline"]


def test_run_stage1_leiden_reports_missing_pre_experiment_output(tmp_path: Path) -> None:
    write_minimal_config(tmp_path)
    extracted = tmp_path / "data" / "extracted" / "jpetstore"
    extracted.mkdir(parents=True)
    (extracted / "class_nodes.csv").write_text(
        "class_id,class_name,package,class_file_path\n"
        "A,pkg.A,pkg,A.class\n",
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="Run the Pre-experiment first"):
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
        "C,pkg.C,pkg,C.class\n",
        encoding="utf-8",
    )
    pre_output = root / "results" / "jpetstore" / "00_pre_experiment"
    graph_dir = pre_output / "graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "ssa_edges.csv").write_text(
        "source,target,type_weight,call_weight,return_flow_weight,argument_flow_weight,ssa_flow_weight,g_ssa_weight\n"
        "A,B,1,2,3,0,3,6\n"
        "B,C,0,0,0,3,3,3\n",
        encoding="utf-8",
    )


def write_minimal_config(root: Path) -> None:
    (root / "configs" / "experiments").mkdir(parents=True)
    (root / "configs" / "subjects").mkdir(parents=True)
    (root / "configs" / "experiments" / "01_stage1_leiden.yml").write_text(
        "experiment_name: 01_stage1_leiden_baseline\n"
        "subjects:\n"
        "  - jpetstore\n"
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
