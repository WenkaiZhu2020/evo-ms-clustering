from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.clustering.leiden_baseline import run_leiden_baseline
from evo_ms.evaluation.partition_metrics import calculate_partition_metrics
from evo_ms.evaluation.partition_metrics import calculate_ssa_impact_tables
from evo_ms.evaluation.partition_metrics import calculate_stage1_smoke_metrics
from evo_ms.extraction.dependency_extractor import load_extracted_subject
from evo_ms.extraction.evidence_weight_validation import expected_extracted_evidence_weights
from evo_ms.extraction.evidence_weight_validation import validate_extracted_evidence_weights
from evo_ms.graph.raw_graph_builder import build_raw_edges, build_raw_graph
from evo_ms.graph.ssa_graph_builder import build_g_ssa_graph, build_ssa_edges
from evo_ms.utils.config_loader import load_yaml
from evo_ms.utils.logging import get_logger


def run_pre_experiment(
    root: Path = ROOT,
    subject: str | None = None,
    config_path: Path | None = None,
    resolution: float | None = None,
    ssa_lambda: float | None = None,
) -> list[Path]:
    config = load_yaml(config_path or root / "configs" / "experiments" / "00_pre_experiment.yml")
    subjects = [subject] if subject else list(config.get("subjects", []))
    if not subjects:
        raise ValueError("pre-experiment config has no subjects")

    resolution = _leiden_resolution(config) if resolution is None else float(resolution)
    ssa_lambda = _ssa_lambda(config) if ssa_lambda is None else float(ssa_lambda)
    expected_weights = expected_extracted_evidence_weights(config)
    seed = int(config.get("leiden", {}).get("seed", 42))
    output_root = root / config.get("output_root", config.get("output_directory", "results"))

    output_dirs = []
    for subject_name in subjects:
        output_dirs.append(
            run_subject(
                root=root,
                subject=subject_name,
                output_root=output_root,
                resolution=resolution,
                ssa_lambda=ssa_lambda,
                expected_weights=expected_weights,
                seed=seed,
            )
        )
    return output_dirs


def run_subject(
    root: Path,
    subject: str,
    output_root: Path,
    resolution: float,
    ssa_lambda: float,
    expected_weights: dict[str, float],
    seed: int,
) -> Path:
    logger = get_logger(__name__)
    subject_config = _load_subject_config(root, subject)
    extracted_dir = root / subject_config.get("extracted_output_path", f"data/extracted/{subject}")
    _require_extracted_inputs(extracted_dir)

    logger.info("Loading extracted CSVs for %s", subject)
    extracted = load_extracted_subject(extracted_dir)
    class_nodes = extracted["class_nodes"]
    structural_dependencies = extracted["structural_dependencies"]
    ssa_flow_edges = extracted["ssa_flow_edges"]
    validate_extracted_evidence_weights(
        structural_dependencies,
        ssa_flow_edges,
        expected_weights,
        subject=subject,
    )

    logger.info("Building G_raw and G_ssa edges for %s", subject)
    raw_edges = build_raw_edges(class_nodes, structural_dependencies)
    ssa_edges = build_ssa_edges(class_nodes, raw_edges, ssa_flow_edges, ssa_lambda=ssa_lambda)

    logger.info("Running Leiden on G_raw for %s", subject)
    raw_clusters = run_leiden_baseline(
        class_nodes,
        raw_edges,
        graph_type="raw",
        resolution=resolution,
        seed=seed,
    )

    logger.info("Running Leiden on G_ssa for %s", subject)
    ssa_clusters = run_leiden_baseline(
        class_nodes,
        ssa_edges,
        graph_type="ssa",
        resolution=resolution,
        seed=seed,
    )

    raw_metrics = _graph_metrics(subject, "raw", build_raw_graph(class_nodes, structural_dependencies))
    ssa_metrics = _graph_metrics(
        subject,
        "ssa",
        build_g_ssa_graph(class_nodes, raw_edges, ssa_flow_edges, ssa_lambda=ssa_lambda),
    )
    raw_partition_metrics = calculate_partition_metrics(
        class_nodes,
        raw_edges,
        raw_clusters,
        subject=subject,
        algorithm="leiden",
        graph_type="raw",
    )
    ssa_partition_metrics = calculate_partition_metrics(
        class_nodes,
        ssa_edges,
        ssa_clusters,
        subject=subject,
        algorithm="leiden",
        graph_type="ssa",
    )

    output_dir = output_root / subject / "00_pre_experiment"
    graph_dir = output_dir / "graph"
    clustering_dir = output_dir / "clustering"
    comparison_dir = output_dir / "comparison"
    for directory in [graph_dir, clustering_dir, comparison_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    raw_edges.to_csv(graph_dir / "raw_edges.csv", index=False)
    ssa_edges.to_csv(graph_dir / "ssa_edges.csv", index=False)
    raw_metrics.to_csv(graph_dir / "raw_graph_metrics.csv", index=False)
    ssa_metrics.to_csv(graph_dir / "ssa_graph_metrics.csv", index=False)
    raw_clusters.to_csv(clustering_dir / "leiden_raw_clusters.csv", index=False)
    ssa_clusters.to_csv(clustering_dir / "leiden_ssa_clusters.csv", index=False)
    raw_partition_metrics.to_csv(clustering_dir / "leiden_raw_partition_metrics.csv", index=False)
    ssa_partition_metrics.to_csv(clustering_dir / "leiden_ssa_partition_metrics.csv", index=False)
    _summary(raw_metrics, ssa_metrics, raw_partition_metrics, ssa_partition_metrics).to_csv(
        comparison_dir / "pre_experiment_summary.csv",
        index=False,
    )
    calculate_stage1_smoke_metrics(
        class_nodes,
        raw_edges,
        ssa_edges,
        raw_clusters,
        ssa_clusters,
        subject=subject,
        algorithm="leiden",
        ssa_flow_edges=ssa_flow_edges,
    ).to_csv(comparison_dir / "metrics_summary.csv", index=False)
    impact_tables = calculate_ssa_impact_tables(
        raw_edges,
        ssa_edges,
        raw_clusters,
        ssa_clusters,
        ssa_flow_edges=ssa_flow_edges,
    )
    impact_tables["top_new_ssa_edges"].to_csv(
        comparison_dir / "top_new_ssa_edges.csv",
        index=False,
    )
    impact_tables["top_weight_increased_edges"].to_csv(
        comparison_dir / "top_weight_increased_edges.csv",
        index=False,
    )
    impact_tables["top_moved_classes"].to_csv(
        comparison_dir / "top_moved_classes.csv",
        index=False,
    )

    logger.info("Wrote pre-experiment outputs to %s", output_dir)
    return output_dir


def _load_subject_config(root: Path, subject: str) -> dict:
    path = root / "configs" / "subjects" / f"{subject}.yml"
    if not path.exists():
        raise FileNotFoundError(f"missing subject config: {path}")
    return load_yaml(path)


def _require_extracted_inputs(extracted_dir: Path) -> None:
    missing = [
        path
        for path in [
            extracted_dir / "class_nodes.csv",
            extracted_dir / "structural_dependencies.csv",
            extracted_dir / "ssa_flow_edges.csv",
        ]
        if not path.exists()
    ]
    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"missing extracted input CSVs: {joined}")


def _leiden_resolution(config: dict) -> float:
    value = config.get("leiden", {}).get("resolution", 1.0)
    return 1.0 if value is None else float(value)


def _ssa_lambda(config: dict) -> float:
    value = config.get("ssa_graph", {}).get("ssa_lambda", 1.0)
    return 1.0 if value is None else float(value)


def _graph_metrics(subject: str, graph_type: str, graph) -> pd.DataFrame:
    import networkx as nx

    metric_graph = graph.to_undirected() if graph.is_directed() else graph
    node_count = graph.number_of_nodes()
    edge_count = metric_graph.number_of_edges()
    degree_sum = sum(dict(metric_graph.degree()).values())
    return pd.DataFrame(
        [
            {
                "subject": subject,
                "graph_type": graph_type,
                "node_count": node_count,
                "edge_count": edge_count,
                "density": float(nx.density(metric_graph)),
                "average_degree": 0.0 if node_count == 0 else float(degree_sum / node_count),
            }
        ]
    )


def _summary(
    raw_graph_metrics: pd.DataFrame,
    ssa_graph_metrics: pd.DataFrame,
    raw_partition_metrics: pd.DataFrame,
    ssa_partition_metrics: pd.DataFrame,
) -> pd.DataFrame:
    raw = _metric_values(raw_graph_metrics, raw_partition_metrics)
    ssa = _metric_values(ssa_graph_metrics, ssa_partition_metrics)
    rows = []
    for metric in sorted(raw.keys() | ssa.keys()):
        raw_value = raw.get(metric)
        ssa_value = ssa.get(metric)
        rows.append(
            {
                "metric": metric,
                "raw": raw_value,
                "ssa": ssa_value,
                "delta": None if raw_value is None or ssa_value is None else ssa_value - raw_value,
            }
        )
    return pd.DataFrame(rows)


def _metric_values(graph_metrics: pd.DataFrame, partition_metrics: pd.DataFrame) -> dict[str, float]:
    row = {**graph_metrics.iloc[0].to_dict(), **partition_metrics.iloc[0].to_dict()}
    ignored = {"subject", "algorithm", "graph_type"}
    return {key: value for key, value in row.items() if key not in ignored}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject")
    parser.add_argument("--resolution", type=float)
    parser.add_argument("--ssa-lambda", type=float)
    args = parser.parse_args()

    try:
        run_pre_experiment(
            subject=args.subject,
            resolution=args.resolution,
            ssa_lambda=args.ssa_lambda,
        )
    except ImportError as exc:
        print(f"ERROR: missing dependency for Leiden: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
