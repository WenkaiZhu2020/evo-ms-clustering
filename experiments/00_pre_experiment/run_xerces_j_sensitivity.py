"""Run Xerces-J scale and sensitivity diagnostics for Stage 1."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.clustering.cluster_summary import summarize_clusters
from evo_ms.clustering.leiden_baseline import run_leiden_baseline
from evo_ms.evaluation.partition_metrics import calculate_partition_metrics
from evo_ms.evaluation.partition_metrics import calculate_ssa_impact_tables
from evo_ms.evaluation.partition_metrics import calculate_stage1_smoke_metrics
from evo_ms.evaluation.partition_metrics import cluster_size_distribution
from evo_ms.evaluation.partition_metrics import partition_similarity
from evo_ms.extraction.dependency_extractor import load_extracted_subject
from evo_ms.extraction.evidence_weight_validation import expected_extracted_evidence_weights
from evo_ms.extraction.evidence_weight_validation import validate_extracted_evidence_weights
from evo_ms.graph.raw_graph_builder import build_raw_edges
from evo_ms.graph.ssa_graph_builder import build_ssa_edges
from evo_ms.repository_layout import pre_experiment_subject_root
from evo_ms.utils.config_loader import load_yaml
from evo_ms.utils.logging import get_logger


SENSITIVITY_RESOLUTIONS = [0.5, 0.75, 1.0, 1.25, 1.5]
SSA_LAMBDAS = [0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0]


def run_xerces_j_sensitivity(root: Path = ROOT) -> Path:
    """Generate Xerces-J resolution, lambda, and cluster-size sensitivity CSVs."""
    logger = get_logger(__name__)
    subject = "xerces-j"
    subject_config = _load_subject_config(root, subject)
    pre_config = load_yaml(root / "configs" / "experiments" / "00_pre_experiment.yml")
    expected_weights = expected_extracted_evidence_weights(pre_config)

    extracted_dir = root / subject_config.get("extracted_output_path", f"data/extracted/{subject}")
    output_dir = pre_experiment_subject_root(subject, root)
    sensitivity_dir = output_dir / "sensitivity"
    sensitivity_dir.mkdir(parents=True, exist_ok=True)

    default_resolution = float(pre_config.get("leiden", {}).get("resolution", 1.0))
    default_ssa_lambda = float(pre_config.get("ssa_graph", {}).get("ssa_lambda", 1.0))
    seed = int(pre_config.get("leiden", {}).get("seed", 42))

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

    logger.info("Building G_raw and G_ssa for %s", subject)
    raw_edges = build_raw_edges(class_nodes, structural_dependencies)
    ssa_edges = build_ssa_edges(class_nodes, raw_edges, ssa_flow_edges, ssa_lambda=default_ssa_lambda)

    logger.info("Running default in-memory partitions for %s sensitivity analysis", subject)
    raw_clusters = run_leiden_baseline(
        class_nodes,
        raw_edges,
        graph_type="raw",
        resolution=default_resolution,
        seed=seed,
    )
    ssa_clusters = run_leiden_baseline(
        class_nodes,
        ssa_edges,
        graph_type="ssa",
        resolution=default_resolution,
        seed=seed,
    )

    _cluster_size_summary(raw_clusters, ssa_clusters).to_csv(
        sensitivity_dir / "cluster_size_summary.csv",
        index=False,
    )

    logger.info("Running resolution sweep for %s", subject)
    _resolution_sweep(
        class_nodes,
        raw_edges,
        ssa_edges,
        default_raw_clusters=raw_clusters,
        default_ssa_clusters=ssa_clusters,
        subject=subject,
        resolutions=SENSITIVITY_RESOLUTIONS,
        seed=seed,
    ).to_csv(sensitivity_dir / "resolution_sweep.csv", index=False)

    logger.info("Running SSA lambda sweep for %s", subject)
    _ssa_lambda_sweep(
        class_nodes,
        raw_edges,
        ssa_flow_edges,
        raw_clusters=raw_clusters,
        subject=subject,
        resolution=default_resolution,
        ssa_lambdas=SSA_LAMBDAS,
        seed=seed,
    ).to_csv(sensitivity_dir / "ssa_lambda_sweep.csv", index=False)

    logger.info("Wrote Xerces-J sensitivity outputs to %s", sensitivity_dir)
    return sensitivity_dir


def _load_subject_config(root: Path, subject: str) -> dict:
    path = root / "configs" / "subjects" / f"{subject}.yml"
    if not path.exists():
        raise FileNotFoundError(f"missing subject config: {path}")
    return load_yaml(path)


def _cluster_size_summary(raw_clusters: pd.DataFrame, ssa_clusters: pd.DataFrame) -> pd.DataFrame:
    raw = summarize_clusters(raw_clusters).assign(graph_type="G_raw")
    ssa = summarize_clusters(ssa_clusters).assign(graph_type="G_ssa")
    return pd.concat([raw, ssa], ignore_index=True).loc[
        :,
        ["graph_type", "cluster_id", "cluster_size", "class_names"],
    ]


def _resolution_sweep(
    class_nodes: pd.DataFrame,
    raw_edges: pd.DataFrame,
    ssa_edges: pd.DataFrame,
    default_raw_clusters: pd.DataFrame,
    default_ssa_clusters: pd.DataFrame,
    subject: str,
    resolutions: Iterable[float],
    seed: int,
) -> pd.DataFrame:
    """Measure how raw and SSA partitions change across Leiden resolutions."""
    rows = []
    defaults = {
        "raw": default_raw_clusters,
        "ssa": default_ssa_clusters,
    }
    for graph_type, edges in [("raw", raw_edges), ("ssa", ssa_edges)]:
        for resolution in resolutions:
            clusters = run_leiden_baseline(
                class_nodes,
                edges,
                graph_type=graph_type,
                resolution=float(resolution),
                seed=seed,
            )
            partition = calculate_partition_metrics(
                class_nodes,
                edges,
                clusters,
                subject=subject,
                algorithm="leiden",
                graph_type=graph_type,
            ).iloc[0]
            ari, nmi = partition_similarity(class_nodes, defaults[graph_type], clusters)
            rows.append(
                {
                    "subject": subject,
                    "graph_type": "G_raw" if graph_type == "raw" else "G_ssa",
                    "resolution": float(resolution),
                    "cluster_count": partition["cluster_count"],
                    "weighted_modularity": partition["modularity"],
                    "internal_edge_weight_ratio": partition["internal_edge_weight_ratio"],
                    "ari_vs_default_partition": ari,
                    "nmi_vs_default_partition": nmi,
                    "cluster_size_distribution": cluster_size_distribution(clusters),
                }
            )
    return pd.DataFrame(rows)


def _ssa_lambda_sweep(
    class_nodes: pd.DataFrame,
    raw_edges: pd.DataFrame,
    ssa_flow_edges: pd.DataFrame,
    raw_clusters: pd.DataFrame,
    subject: str,
    resolution: float,
    ssa_lambdas: Iterable[float],
    seed: int,
) -> pd.DataFrame:
    """Measure how the Xerces-J SSA partition changes as lambda increases."""
    rows = []
    for ssa_lambda in ssa_lambdas:
        ssa_edges = build_ssa_edges(
            class_nodes,
            raw_edges,
            ssa_flow_edges,
            ssa_lambda=float(ssa_lambda),
        )
        ssa_clusters = run_leiden_baseline(
            class_nodes,
            ssa_edges,
            graph_type="ssa",
            resolution=resolution,
            seed=seed,
        )
        smoke = calculate_stage1_smoke_metrics(
            class_nodes,
            raw_edges,
            ssa_edges,
            raw_clusters,
            ssa_clusters,
            subject=subject,
            algorithm="leiden",
            ssa_flow_edges=ssa_flow_edges,
        ).iloc[0]
        partition = calculate_partition_metrics(
            class_nodes,
            ssa_edges,
            ssa_clusters,
            subject=subject,
            algorithm="leiden",
            graph_type="ssa",
        ).iloc[0]
        moved = calculate_ssa_impact_tables(
            raw_edges,
            ssa_edges,
            raw_clusters,
            ssa_clusters,
            ssa_flow_edges=ssa_flow_edges,
            top_n=len(class_nodes),
        )["top_moved_classes"]
        rows.append(
            {
                "subject": subject,
                "ssa_lambda": float(ssa_lambda),
                "resolution": float(resolution),
                "raw_edge_count": smoke["raw_edge_count"],
                "g_ssa_edge_count": smoke["g_ssa_edge_count"],
                "new_ssa_edge_count": smoke["new_ssa_edge_count"],
                "ssa_weight_share": smoke["ssa_weight_share"],
                "cluster_count": partition["cluster_count"],
                "max_cluster_ratio": partition["max_cluster_ratio"],
                "singleton_ratio": partition["singleton_ratio"],
                "weighted_modularity": partition["modularity"],
                "internal_edge_weight_ratio": partition["internal_edge_weight_ratio"],
                "changed_partition_count": int(len(moved)),
                "changed_partition_ratio": 0.0 if len(class_nodes) == 0 else float(len(moved) / len(class_nodes)),
                "ari_raw_vs_ssa": smoke["ari_raw_vs_ssa"],
                "nmi_raw_vs_ssa": smoke["nmi_raw_vs_ssa"],
                "cluster_size_distribution": smoke["ssa_cluster_size_distribution"],
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Xerces-J scale and sensitivity analysis.")
    parser.parse_args()

    try:
        run_xerces_j_sensitivity()
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
