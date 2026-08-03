from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


RUNNER_PATH = Path(__file__).resolve().parents[1] / "experiments" / "00_pre_experiment" / "run.py"
SPEC = spec_from_file_location("pre_experiment_runner", RUNNER_PATH)
pre_experiment_runner = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(pre_experiment_runner)


def test_run_pre_experiment_writes_expected_outputs_to_temp_results(tmp_path: Path) -> None:
    require_leiden()
    write_fixture_repo(tmp_path)

    output_dirs = pre_experiment_runner.run_pre_experiment(root=tmp_path, subject="jpetstore")

    output_dir = output_dirs[0]
    assert output_dir == tmp_path / "results" / "pre_experiment" / "subjects" / "jpetstore"
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "clustering",
        "comparison",
        "graph",
    ]
    assert sorted(path.name for path in (output_dir / "graph").iterdir()) == [
        "raw_edges.csv",
        "raw_graph_metrics.csv",
        "ssa_edges.csv",
        "ssa_graph_metrics.csv",
    ]
    assert sorted(path.name for path in (output_dir / "clustering").iterdir()) == [
        "leiden_raw_clusters.csv",
        "leiden_raw_partition_metrics.csv",
        "leiden_ssa_clusters.csv",
        "leiden_ssa_partition_metrics.csv",
    ]
    assert sorted(path.name for path in (output_dir / "comparison").iterdir()) == [
        "metrics_summary.csv",
        "pre_experiment_summary.csv",
        "top_moved_classes.csv",
        "top_new_ssa_edges.csv",
        "top_weight_increased_edges.csv",
    ]

    raw_edges = pd.read_csv(output_dir / "graph" / "raw_edges.csv")
    ssa_edges = pd.read_csv(output_dir / "graph" / "ssa_edges.csv")
    raw_clusters = pd.read_csv(output_dir / "clustering" / "leiden_raw_clusters.csv")
    summary = pd.read_csv(output_dir / "comparison" / "pre_experiment_summary.csv")
    metrics_summary = pd.read_csv(output_dir / "comparison" / "metrics_summary.csv")
    new_edges = pd.read_csv(output_dir / "comparison" / "top_new_ssa_edges.csv")
    increased_edges = pd.read_csv(output_dir / "comparison" / "top_weight_increased_edges.csv")
    moved_classes = pd.read_csv(output_dir / "comparison" / "top_moved_classes.csv")
    summary_values = summary.set_index("metric")

    assert list(raw_edges.columns) == ["source", "target", "type_weight", "call_weight", "raw_weight"]
    assert "g_ssa_weight" in ssa_edges.columns
    assert set(raw_clusters["class_id"]) == {"A", "B", "C"}
    assert {"edge_count", "cluster_count", "modularity"}.issubset(set(summary["metric"]))
    assert metrics_summary.loc[0, "raw_edge_count"] == len(raw_edges)
    assert metrics_summary.loc[0, "g_ssa_edge_count"] == len(ssa_edges)
    assert summary_values.loc["edge_count", "raw"] == metrics_summary.loc[0, "raw_edge_count"]
    assert summary_values.loc["edge_count", "ssa"] == metrics_summary.loc[0, "g_ssa_edge_count"]
    assert summary_values.loc["density", "raw"] == pytest.approx(2.0 / 3.0)
    assert summary_values.loc["density", "ssa"] == pytest.approx(1.0)
    assert {"ari_raw_vs_ssa", "nmi_raw_vs_ssa", "ssa_weighted_modularity"}.issubset(
        metrics_summary.columns,
    )
    assert list(new_edges.columns) == [
        "source",
        "target",
        "raw_weight",
        "ssa_flow_weight",
        "g_ssa_weight",
        "flow_type_summary",
    ]
    assert "weight_increase" in increased_edges.columns
    assert {
        "lost_same_cluster_neighbors",
        "gained_same_cluster_neighbors",
        "membership_jaccard",
    }.issubset(moved_classes.columns)


def test_run_pre_experiment_uses_config_subjects(tmp_path: Path) -> None:
    require_leiden()
    write_fixture_repo(tmp_path)

    output_dirs = pre_experiment_runner.run_pre_experiment(root=tmp_path)

    assert output_dirs == [tmp_path / "results" / "pre_experiment" / "subjects" / "jpetstore"]


def test_run_pre_experiment_accepts_ssa_lambda_override(tmp_path: Path) -> None:
    require_leiden()
    write_fixture_repo(tmp_path)

    output_dirs = pre_experiment_runner.run_pre_experiment(
        root=tmp_path,
        subject="jpetstore",
        ssa_lambda=0.0,
    )

    ssa_edges = pd.read_csv(output_dirs[0] / "graph" / "ssa_edges.csv")
    metrics_summary = pd.read_csv(output_dirs[0] / "comparison" / "metrics_summary.csv")
    assert len(ssa_edges) == 2
    assert metrics_summary.loc[0, "g_ssa_edge_count"] == 2
    assert metrics_summary.loc[0, "new_ssa_edge_count"] == 0


def test_run_pre_experiment_reports_missing_extracted_inputs(tmp_path: Path) -> None:
    write_minimal_config(tmp_path)

    with pytest.raises(FileNotFoundError, match="missing extracted input CSVs"):
        pre_experiment_runner.run_pre_experiment(root=tmp_path, subject="jpetstore")


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
    (extracted / "structural_dependencies.csv").write_text(
        "source,target,dependency_type,weight,evidence_kind,evidence_location\n"
        "A,B,type,1,field_type_reference,A.field\n"
        "B,C,call,2,method_call,B.call\n",
        encoding="utf-8",
    )
    (extracted / "ssa_flow_edges.csv").write_text(
        "source,target,flow_type,weight,evidence_method,evidence_statement\n"
        "A,C,return_value_flow,3,A.method,A statement\n",
        encoding="utf-8",
    )


def write_minimal_config(root: Path) -> None:
    (root / "configs" / "experiments").mkdir(parents=True)
    (root / "configs" / "subjects").mkdir(parents=True)
    (root / "configs" / "experiments" / "00_pre_experiment.yml").write_text(
        "experiment_name: 00_pre_experiment\n"
        "subjects:\n"
        "  - jpetstore\n"
        "leiden:\n"
        "  resolution: 1.0\n"
        "  seed: 42\n"
        "output_root: results\n",
        encoding="utf-8",
    )
    (root / "configs" / "subjects" / "jpetstore.yml").write_text(
        "subject: jpetstore\n"
        "extracted_output_path: data/extracted/jpetstore\n",
        encoding="utf-8",
    )
