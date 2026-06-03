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
from evo_ms.evaluation.partition_metrics import calculate_stage1_smoke_metrics
from evo_ms.evaluation.reference_metrics import calculate_reference_metrics
from evo_ms.evaluation.reference_metrics import load_reference_mapping
from evo_ms.evaluation.reference_metrics import reference_mapping_diagnostics
from evo_ms.extraction.dependency_extractor import load_extracted_subject
from evo_ms.graph.raw_graph_builder import build_raw_edges
from evo_ms.graph.ssa_graph_builder import build_ssa_edges
from evo_ms.utils.config_loader import load_yaml
from evo_ms.utils.logging import get_logger


SSA_LAMBDAS = [0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0]
RESOLUTIONS = [0.5, 0.75, 1.0, 1.25, 1.5]


def run_daytrader_calibration(
    root: Path = ROOT,
    subject: str = "daytrader",
    ssa_lambdas: list[float] | None = None,
    resolutions: list[float] | None = None,
) -> Path:
    logger = get_logger(__name__)
    subject_config = _load_subject_config(root, subject)
    extracted_dir = root / subject_config.get("extracted_output_path", f"data/extracted/{subject}")
    reference_path = root / subject_config.get(
        "reference_mapping_path",
        f"data/references/{subject}_reference_services.csv",
    )
    output_dir = root / subject_config.get("result_output_path", f"results/{subject}") / "00_pre_experiment"
    calibration_dir = output_dir / "calibration"
    calibration_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading extracted CSVs for %s", subject)
    extracted = load_extracted_subject(extracted_dir)
    class_nodes = extracted["class_nodes"]
    structural_dependencies = extracted["structural_dependencies"]
    ssa_flow_edges = extracted["ssa_flow_edges"]
    raw_edges = build_raw_edges(class_nodes, structural_dependencies)
    reference_mapping = load_reference_mapping(reference_path)

    diagnostics = reference_mapping_diagnostics(class_nodes, reference_mapping)
    pd.DataFrame(
        [
            {
                "subject": subject,
                "extracted_class_count": int(len(class_nodes)),
                "reference_class_count": int(len(reference_mapping)),
                "reference_coverage_ratio": diagnostics["reference_coverage_ratio"],
                "unmapped_extracted_class_count": int(
                    len(diagnostics["unmapped_extracted_classes"]),
                ),
                "reference_class_not_found_count": int(
                    len(diagnostics["reference_classes_not_found"]),
                ),
            }
        ]
    ).to_csv(calibration_dir / "reference_mapping_validation.csv", index=False)
    diagnostics["unmapped_extracted_classes"].to_csv(
        calibration_dir / "unmapped_extracted_classes.csv",
        index=False,
    )
    diagnostics["reference_classes_not_found"].to_csv(
        calibration_dir / "reference_classes_not_found.csv",
        index=False,
    )

    rows = []
    for resolution in resolutions or RESOLUTIONS:
        logger.info("Running raw Leiden for %s at resolution=%s", subject, resolution)
        raw_clusters = run_leiden_baseline(
            class_nodes,
            raw_edges,
            graph_type="raw",
            resolution=resolution,
            seed=42,
        )
        for ssa_lambda in ssa_lambdas or SSA_LAMBDAS:
            logger.info(
                "Running sweep for %s with ssa_lambda=%s resolution=%s",
                subject,
                ssa_lambda,
                resolution,
            )
            ssa_edges = build_ssa_edges(
                class_nodes,
                raw_edges,
                ssa_flow_edges,
                ssa_lambda=ssa_lambda,
            )
            clusters = run_leiden_baseline(
                class_nodes,
                ssa_edges,
                graph_type="ssa",
                resolution=resolution,
                seed=42,
            )
            smoke = calculate_stage1_smoke_metrics(
                class_nodes,
                raw_edges,
                ssa_edges,
                raw_clusters,
                clusters,
                subject=subject,
                algorithm="leiden",
                ssa_flow_edges=ssa_flow_edges,
            ).iloc[0]
            partition = calculate_partition_metrics(
                class_nodes,
                ssa_edges,
                clusters,
                subject=subject,
                algorithm="leiden",
                graph_type="ssa",
            ).iloc[0]
            reference = calculate_reference_metrics(class_nodes, clusters, reference_mapping)
            rows.append(
                {
                    "subject": subject,
                    "ssa_lambda": ssa_lambda,
                    "resolution": resolution,
                    "raw_edge_count": smoke["raw_edge_count"],
                    "g_ssa_edge_count": smoke["g_ssa_edge_count"],
                    "new_ssa_edge_count": smoke["new_ssa_edge_count"],
                    "ssa_weight_share": smoke["ssa_weight_share"],
                    "cluster_count": partition["cluster_count"],
                    "max_cluster_ratio": partition["max_cluster_ratio"],
                    "singleton_ratio": partition["singleton_ratio"],
                    "weighted_modularity": partition["modularity"],
                    "internal_edge_weight_ratio": partition["internal_edge_weight_ratio"],
                    "mojofm_vs_reference": reference["mojofm_vs_reference"],
                    "pairwise_f1": reference["pairwise_f1"],
                    "reference_coverage_ratio": reference["reference_coverage_ratio"],
                    "ari_vs_reference": reference["ari_vs_reference"],
                    "nmi_vs_reference": reference["nmi_vs_reference"],
                    "pairwise_precision": reference["pairwise_precision"],
                    "pairwise_recall": reference["pairwise_recall"],
                }
            )

    summary = pd.DataFrame(rows)
    summary.to_csv(calibration_dir / "weight_sweep_summary.csv", index=False)
    _rank_settings(summary).to_csv(calibration_dir / "top_weight_settings.csv", index=False)
    _top_ssa_degree_classes(class_nodes, build_ssa_edges(class_nodes, raw_edges, ssa_flow_edges)).to_csv(
        calibration_dir / "top_ssa_degree_classes.csv",
        index=False,
    )
    logger.info("Wrote calibration outputs to %s", calibration_dir)
    return calibration_dir


def _load_subject_config(root: Path, subject: str) -> dict:
    path = root / "configs" / "subjects" / f"{subject}.yml"
    if not path.exists():
        raise FileNotFoundError(f"missing subject config: {path}")
    return load_yaml(path)


def _rank_settings(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return summary
    ranked = summary.copy()
    reference_cluster_target = max(1, int(round(ranked["cluster_count"].median())))
    ranked["rejected_extreme_cluster_count"] = ranked["cluster_count"].gt(
        max(reference_cluster_target * 3, reference_cluster_target + 10),
    )
    ranked["rejected_high_max_cluster_ratio"] = ranked["max_cluster_ratio"].gt(0.6)
    ranked["rejected_high_singleton_ratio"] = ranked["singleton_ratio"].gt(0.25)
    ranked["rejected_low_reference_coverage"] = ranked["reference_coverage_ratio"].lt(0.8)
    ranked["is_candidate"] = ~ranked.loc[
        :,
        [
            "rejected_extreme_cluster_count",
            "rejected_high_max_cluster_ratio",
            "rejected_high_singleton_ratio",
            "rejected_low_reference_coverage",
        ],
    ].any(axis=1)
    ranked["ranking_score"] = ranked["mojofm_vs_reference"] + 100.0 * ranked["pairwise_f1"]
    return (
        ranked.sort_values(
            ["is_candidate", "ranking_score", "mojofm_vs_reference", "pairwise_f1"],
            ascending=[False, False, False, False],
        )
        .head(10)
        .reset_index(drop=True)
    )


def _top_ssa_degree_classes(class_nodes: pd.DataFrame, ssa_edges: pd.DataFrame) -> pd.DataFrame:
    weights: dict[str, float] = {str(row["class_id"]): 0.0 for row in class_nodes.to_dict("records")}
    edge_counts: dict[str, int] = {class_id: 0 for class_id in weights}
    for row in ssa_edges.to_dict("records"):
        if float(row.get("ssa_flow_weight", 0.0)) <= 0:
            continue
        for node in [str(row["source"]), str(row["target"])]:
            weights[node] = weights.get(node, 0.0) + float(row["ssa_flow_weight"])
            edge_counts[node] = edge_counts.get(node, 0) + 1
    names = dict(zip(class_nodes["class_id"].astype(str), class_nodes["class_name"], strict=True))
    rows = [
        {
            "class_id": class_id,
            "class_name": names.get(class_id, class_id),
            "ssa_flow_degree": edge_counts.get(class_id, 0),
            "ssa_flow_incident_weight": weight,
        }
        for class_id, weight in weights.items()
        if weight > 0
    ]
    return (
        pd.DataFrame(rows)
        .sort_values(["ssa_flow_incident_weight", "ssa_flow_degree", "class_name"], ascending=[False, False, True])
        .head(20)
        .reset_index(drop=True)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DayTrader reference-based calibration.")
    parser.add_argument("--subject", default="daytrader")
    args = parser.parse_args()

    try:
        run_daytrader_calibration(subject=args.subject)
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
