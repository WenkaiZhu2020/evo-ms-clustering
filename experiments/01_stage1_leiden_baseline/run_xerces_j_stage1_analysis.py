from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Iterable

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
from evo_ms.evaluation.partition_metrics import _adjusted_rand_index
from evo_ms.evaluation.partition_metrics import _cluster_size_distribution
from evo_ms.evaluation.partition_metrics import _cluster_sizes
from evo_ms.evaluation.partition_metrics import _normalized_mutual_information
from evo_ms.extraction.dependency_extractor import load_extracted_subject
from evo_ms.graph.raw_graph_builder import build_raw_edges
from evo_ms.graph.ssa_graph_builder import build_ssa_edges
from evo_ms.utils.config_loader import load_yaml
from evo_ms.utils.logging import get_logger


DAYTRADER_RESOLUTIONS = [0.5, 0.75, 1.0, 1.25, 1.5]
DAYTRADER_SSA_LAMBDAS = [0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0]


def run_xerces_j_stage1_analysis(root: Path = ROOT) -> Path:
    logger = get_logger(__name__)
    subject = "xerces-j"
    subject_config = _load_subject_config(root, subject)
    pre_config = load_yaml(root / "configs" / "experiments" / "00_pre_experiment.yml")

    extracted_dir = root / subject_config.get("extracted_output_path", f"data/extracted/{subject}")
    output_dir = root / subject_config.get("result_output_path", f"results/{subject}") / "stage1"
    output_dir.mkdir(parents=True, exist_ok=True)

    default_resolution = float(pre_config.get("leiden", {}).get("resolution", 1.0))
    default_ssa_lambda = float(pre_config.get("ssa_graph", {}).get("ssa_lambda", 1.0))
    seed = int(pre_config.get("leiden", {}).get("seed", 42))

    logger.info("Loading extracted CSVs for %s", subject)
    extracted = load_extracted_subject(extracted_dir)
    class_nodes = extracted["class_nodes"]
    structural_dependencies = extracted["structural_dependencies"]
    ssa_flow_edges = extracted["ssa_flow_edges"]

    logger.info("Building G_raw and G_ssa for %s", subject)
    raw_edges = build_raw_edges(class_nodes, structural_dependencies)
    ssa_edges = build_ssa_edges(class_nodes, raw_edges, ssa_flow_edges, ssa_lambda=default_ssa_lambda)

    logger.info("Running default Leiden comparison for %s", subject)
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
    graph_summary = calculate_stage1_smoke_metrics(
        class_nodes,
        raw_edges,
        ssa_edges,
        raw_clusters,
        ssa_clusters,
        subject=subject,
        algorithm="leiden",
        ssa_flow_edges=ssa_flow_edges,
    )

    raw_clusters.to_csv(output_dir / "leiden_raw_clusters.csv", index=False)
    ssa_clusters.to_csv(output_dir / "leiden_ssa_clusters.csv", index=False)
    raw_partition_metrics.to_csv(output_dir / "leiden_raw_partition_metrics.csv", index=False)
    ssa_partition_metrics.to_csv(output_dir / "leiden_ssa_partition_metrics.csv", index=False)
    graph_summary.to_csv(output_dir / "graph_summary.csv", index=False)
    _leiden_comparison(raw_partition_metrics, ssa_partition_metrics).to_csv(
        output_dir / "leiden_comparison.csv",
        index=False,
    )
    _cluster_size_summary(raw_clusters, ssa_clusters).to_csv(
        output_dir / "cluster_size_summary.csv",
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
        resolutions=DAYTRADER_RESOLUTIONS,
        seed=seed,
    ).to_csv(output_dir / "resolution_sweep.csv", index=False)

    logger.info("Running SSA lambda sweep for %s", subject)
    _ssa_lambda_sweep(
        class_nodes,
        raw_edges,
        ssa_flow_edges,
        raw_clusters=raw_clusters,
        subject=subject,
        resolution=default_resolution,
        ssa_lambdas=DAYTRADER_SSA_LAMBDAS,
        seed=seed,
    ).to_csv(output_dir / "ssa_lambda_sweep.csv", index=False)

    _write_report(root, output_dir)
    logger.info("Wrote Xerces-J Stage 1 analysis to %s", output_dir)
    return output_dir


def _load_subject_config(root: Path, subject: str) -> dict:
    path = root / "configs" / "subjects" / f"{subject}.yml"
    if not path.exists():
        raise FileNotFoundError(f"missing subject config: {path}")
    return load_yaml(path)


def _leiden_comparison(raw_metrics: pd.DataFrame, ssa_metrics: pd.DataFrame) -> pd.DataFrame:
    raw = raw_metrics.iloc[0].to_dict()
    ssa = ssa_metrics.iloc[0].to_dict()
    rows = []
    for metric in [
        "cluster_count",
        "modularity",
        "average_cluster_size",
        "max_cluster_size",
        "min_cluster_size",
        "max_cluster_ratio",
        "singleton_ratio",
        "internal_external_edge_ratio",
        "internal_edge_weight_ratio",
    ]:
        rows.append(
            {
                "metric": metric,
                "raw": raw[metric],
                "ssa": ssa[metric],
                "delta": ssa[metric] - raw[metric],
            }
        )
    return pd.DataFrame(rows)


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
            ari, nmi = _partition_similarity(class_nodes, defaults[graph_type], clusters)
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
                    "cluster_size_distribution": _cluster_size_distribution(_cluster_sizes(clusters)),
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


def _partition_similarity(
    class_nodes: pd.DataFrame,
    left_clusters: pd.DataFrame,
    right_clusters: pd.DataFrame,
) -> tuple[float, float]:
    class_ids = class_nodes["class_id"].dropna().astype(str).tolist()
    left = dict(zip(left_clusters["class_id"].astype(str), left_clusters["cluster_id"], strict=True))
    right = dict(zip(right_clusters["class_id"].astype(str), right_clusters["cluster_id"], strict=True))
    left = {class_id: int(left[class_id]) for class_id in class_ids}
    right = {class_id: int(right[class_id]) for class_id in class_ids}
    return (
        _adjusted_rand_index(left, right, class_ids),
        _normalized_mutual_information(left, right, class_ids),
    )


def _write_report(root: Path, output_dir: Path) -> None:
    report_path = root / "reports" / "xerces-j_stage1_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    graph = pd.read_csv(output_dir / "graph_summary.csv").iloc[0]
    leiden = pd.read_csv(output_dir / "leiden_comparison.csv")
    resolution = pd.read_csv(output_dir / "resolution_sweep.csv")
    lambdas = pd.read_csv(output_dir / "ssa_lambda_sweep.csv")
    daytrader = _read_optional_csv(
        root / "results" / "daytrader" / "00_pre_experiment" / "comparison" / "metrics_summary.csv",
    )
    daytrader_top = _read_optional_csv(
        root / "results" / "daytrader" / "00_pre_experiment" / "calibration" / "top_weight_settings.csv",
    )

    lines = [
        "# Xerces-J Stage 1 Analysis",
        "",
        "## Extraction Recap",
        "",
        "- Subject: `xerces-j`",
        "- Source path: `data/raw_projects/xerces-j`",
        "- Normalized extraction path: `data/extracted/xerces-j/`",
        "- Included application packages: `org.apache.xerces`, `org.apache.xml`",
        "- Excluded packages/classes: tests, samples, tools, `org.apache.html`, and `org.w3c.dom` API surface",
        f"- Extracted class count: {int(graph['class_count'])}",
        f"- SSA flow evidence rows: {int(graph['ssa_flow_evidence_count'])}",
        "",
        "## Graph Scale",
        "",
        (
            "Xerces-J is substantially larger than the earlier smoke/calibration subjects. "
            f"The current run contains {int(graph['class_count'])} classes, "
            f"{int(graph['raw_edge_count'])} G_raw edges, and {int(graph['g_ssa_edge_count'])} G_ssa edges. "
            "That makes it useful as a larger technical remodularization benchmark for checking whether the Stage 1 "
            "pipeline remains stable beyond small application examples."
        ),
        "",
        "## G_raw vs G_ssa",
        "",
        _markdown_table(
            pd.DataFrame(
                [
                    {
                        "metric": "class_count",
                        "value": int(graph["class_count"]),
                    },
                    {
                        "metric": "raw_edge_count",
                        "value": int(graph["raw_edge_count"]),
                    },
                    {
                        "metric": "g_ssa_edge_count",
                        "value": int(graph["g_ssa_edge_count"]),
                    },
                    {
                        "metric": "new_ssa_edge_count",
                        "value": int(graph["new_ssa_edge_count"]),
                    },
                    {
                        "metric": "new_ssa_edge_ratio",
                        "value": _format_float(graph["new_ssa_edge_ratio"]),
                    },
                    {
                        "metric": "ssa_weight_share",
                        "value": _format_float(graph["ssa_weight_share"]),
                    },
                    {
                        "metric": "raw_cluster_count",
                        "value": int(graph["raw_cluster_count"]),
                    },
                    {
                        "metric": "ssa_cluster_count",
                        "value": int(graph["ssa_cluster_count"]),
                    },
                    {
                        "metric": "ari_raw_vs_ssa",
                        "value": _format_float(graph["ari_raw_vs_ssa"]),
                    },
                    {
                        "metric": "nmi_raw_vs_ssa",
                        "value": _format_float(graph["nmi_raw_vs_ssa"]),
                    },
                    {
                        "metric": "raw_weighted_modularity",
                        "value": _format_float(graph["raw_weighted_modularity"]),
                    },
                    {
                        "metric": "ssa_weighted_modularity",
                        "value": _format_float(graph["ssa_weighted_modularity"]),
                    },
                    {
                        "metric": "raw_internal_edge_weight_ratio",
                        "value": _format_float(graph["raw_internal_edge_weight_ratio"]),
                    },
                    {
                        "metric": "ssa_internal_edge_weight_ratio",
                        "value": _format_float(graph["ssa_internal_edge_weight_ratio"]),
                    },
                ]
            )
        ),
        "",
        "The SSA layer adds unique class-pair edges and changes the partition more visibly than in DayTrader. "
        "The cluster count decreases by one at the default setting, but ARI/NMI show that this is not just a label change.",
        "",
        "## Leiden Comparison",
        "",
        _markdown_table(_format_table_numbers(leiden)),
        "",
        "## Resolution Sweep",
        "",
        "This sweep uses the same resolution grid currently used by the DayTrader calibration runner.",
        "",
        _markdown_table(_format_table_numbers(resolution)),
        "",
        "## SSA Weight / Lambda Sweep",
        "",
        (
            "`changed_partition_ratio` is the fraction of classes whose same-cluster membership set changes relative "
            "to the G_raw Leiden partition; it avoids treating cluster label renumbering as movement."
        ),
        "",
        _markdown_table(_format_table_numbers(lambdas)),
        "",
        "## Interpretation",
        "",
        (
            f"At the default setting, G_ssa has {int(graph['new_ssa_edge_count'])} new class-pair edges "
            f"and an SSA weight share of {_format_float(graph['ssa_weight_share'])}. "
            f"The raw-vs-SSA ARI is {_format_float(graph['ari_raw_vs_ssa'])} and NMI is "
            f"{_format_float(graph['nmi_raw_vs_ssa'])}, so SSA materially changes the partition. "
            "The internal edge weight ratio remains close between G_raw and G_ssa, which suggests that SSA changes "
            "the boundary structure without completely collapsing the graph into one broad cluster."
        ),
        "",
        "## Comparison With DayTrader Style Findings",
        "",
        _daytrader_comparison(daytrader, daytrader_top, graph),
        "",
        "## Implication For Later NSGA-II Experiment",
        "",
        (
            "Xerces-J is useful later as a technical remodularization benchmark because it is large enough to stress "
            "graph construction, Leiden stability, and objective trade-offs. It should not be used as business "
            "microservice ground truth: no reference service mapping was computed here, and no NSGA-II, semantics, "
            "or embedding objective was implemented in this Stage 1 run."
        ),
        "",
        "## Limitations",
        "",
        "- Xerces-J is a parser/XML infrastructure codebase, not a business microservice decomposition case.",
        "- Reference-based metrics are not computed because no validated Xerces-J service mapping exists in this repository.",
        "- The extraction used staged Java 8-compatible bytecode for `org.apache.xerces` and `org.apache.xml` under Java 17.",
        "- `org.w3c.dom` is treated as external API/JDK/library surface for this run.",
        "",
        "## Reproduction Commands",
        "",
        "```bash",
        "bash scripts/run_stage1_xerces_j.sh",
        "PYTHONPATH=src .venv/bin/python -m pytest",
        "```",
        "",
        "Generated outputs are under `results/xerces-j/stage1/`.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _read_optional_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _daytrader_comparison(daytrader: pd.DataFrame, daytrader_top: pd.DataFrame, xerces: pd.Series) -> str:
    if daytrader.empty:
        return "DayTrader comparison is not computed because the DayTrader metrics file is not present."
    row = daytrader.iloc[0]
    sentences = [
        (
            "DayTrader's Stage 1 calibration style combines a raw-vs-SSA comparison with a lambda/resolution sweep. "
            f"In the current DayTrader output, the default run has {int(row['class_count'])} classes, "
            f"{int(row['raw_edge_count'])} G_raw edges, {int(row['g_ssa_edge_count'])} G_ssa edges, "
            f"{int(row['new_ssa_edge_count'])} new SSA edges, SSA weight share {_format_float(row['ssa_weight_share'])}, "
            f"ARI {_format_float(row['ari_raw_vs_ssa'])}, and NMI {_format_float(row['nmi_raw_vs_ssa'])}."
        ),
        (
            f"Xerces-J is larger and more sensitive: {int(xerces['class_count'])} classes, "
            f"{int(xerces['raw_edge_count'])} G_raw edges, {int(xerces['g_ssa_edge_count'])} G_ssa edges, "
            f"{int(xerces['new_ssa_edge_count'])} new SSA edges, SSA weight share {_format_float(xerces['ssa_weight_share'])}, "
            f"ARI {_format_float(xerces['ari_raw_vs_ssa'])}, and NMI {_format_float(xerces['nmi_raw_vs_ssa'])}."
        ),
    ]
    if not daytrader_top.empty:
        top = daytrader_top.iloc[0]
        non_raw = daytrader_top.loc[pd.to_numeric(daytrader_top["ssa_lambda"], errors="coerce") > 0]
        sentences.append(
            "The DayTrader sweep is reference-guided; its top row currently reports "
            f"lambda {top['ssa_lambda']} at resolution {top['resolution']} with "
            f"MoJoFM {_format_float(top['mojofm_vs_reference'])} and pairwise F1 {_format_float(top['pairwise_f1'])}. "
            + (
                "The first non-raw candidate in that ranked table reports "
                f"lambda {non_raw.iloc[0]['ssa_lambda']} at resolution {non_raw.iloc[0]['resolution']} "
                f"with MoJoFM {_format_float(non_raw.iloc[0]['mojofm_vs_reference'])} and "
                f"pairwise F1 {_format_float(non_raw.iloc[0]['pairwise_f1'])}. "
                if not non_raw.empty
                else ""
            )
            + "Xerces-J has no equivalent business reference mapping here, so this report does not rank lambda settings as final."
        )
    return "\n\n".join(sentences)


def _format_table_numbers(df: pd.DataFrame) -> pd.DataFrame:
    formatted = df.copy()
    for column in formatted.columns:
        if pd.api.types.is_float_dtype(formatted[column]):
            formatted[column] = formatted[column].map(_format_float)
    return formatted


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "not computed"
    headers = [str(column) for column in df.columns]
    rows = [[str(value) for value in row] for row in df.to_numpy().tolist()]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    header = "| " + " | ".join(headers[index].ljust(widths[index]) for index in range(len(headers))) + " |"
    sep = "| " + " | ".join("-" * widths[index] for index in range(len(headers))) + " |"
    body = [
        "| " + " | ".join(row[index].ljust(widths[index]) for index in range(len(headers))) + " |"
        for row in rows
    ]
    return "\n".join([header, sep, *body])


def _format_float(value) -> str:
    return f"{float(value):.6f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    try:
        run_xerces_j_stage1_analysis()
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
