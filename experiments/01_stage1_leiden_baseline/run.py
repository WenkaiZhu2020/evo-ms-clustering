from __future__ import annotations

import argparse
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
from evo_ms.extraction.dependency_extractor import load_class_nodes_csv
from evo_ms.utils.config_loader import load_yaml
from evo_ms.utils.logging import get_logger


def run_stage1_leiden(
    root: Path = ROOT,
    subject: str | None = None,
    config_path: Path | None = None,
    resolution: float | None = None,
) -> list[Path]:
    config = load_yaml(config_path or root / "configs" / "experiments" / "01_stage1_leiden.yml")
    subjects = [subject] if subject else list(config.get("subjects", []))
    if not subjects:
        raise ValueError("Stage 1 Leiden config has no subjects")

    resolution = _resolution(config) if resolution is None else float(resolution)
    seed = int(config.get("seed", 42))
    output_root = root / config.get("output_root", config.get("output_directory", "results"))

    output_dirs = []
    for subject_name in subjects:
        output_dirs.append(
            run_subject(
                root=root,
                subject=subject_name,
                output_root=output_root,
                resolution=resolution,
                seed=seed,
            )
        )
    return output_dirs


def run_subject(
    root: Path,
    subject: str,
    output_root: Path,
    resolution: float,
    seed: int,
) -> Path:
    logger = get_logger(__name__)
    subject_config = _load_subject_config(root, subject)
    extracted_dir = root / subject_config.get("extracted_output_path", f"data/extracted/{subject}")
    class_nodes_path = extracted_dir / "class_nodes.csv"
    if not class_nodes_path.exists():
        raise FileNotFoundError(f"missing class_nodes.csv: {class_nodes_path}")

    ssa_edges_path = output_root / subject / "00_pre_experiment" / "graph" / "ssa_edges.csv"
    if not ssa_edges_path.exists():
        raise FileNotFoundError(f"missing ssa_edges.csv: {ssa_edges_path}. Run the Pre-experiment first.")

    logger.info("Loading G_ssa inputs for %s", subject)
    class_nodes = load_class_nodes_csv(class_nodes_path)
    ssa_edges = pd.read_csv(ssa_edges_path)

    logger.info("Running Leiden on G_ssa for %s", subject)
    clusters = run_leiden_baseline(
        class_nodes,
        ssa_edges,
        graph_type="ssa",
        resolution=resolution,
        seed=seed,
    )
    metrics = calculate_partition_metrics(
        class_nodes,
        ssa_edges,
        clusters,
        subject=subject,
        algorithm="leiden",
        graph_type="ssa",
    )
    cluster_summary = summarize_clusters(clusters)

    output_dir = output_root / subject / "01_stage1_leiden_baseline"
    clustering_dir = output_dir / "clustering"
    metrics_dir = output_dir / "metrics"
    summaries_dir = output_dir / "summaries"
    for directory in [clustering_dir, metrics_dir, summaries_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    clusters.to_csv(clustering_dir / "stage1_clusters.csv", index=False)
    metrics.to_csv(metrics_dir / "stage1_metrics.csv", index=False)
    cluster_summary.to_csv(summaries_dir / "stage1_cluster_summary.csv", index=False)

    logger.info("Wrote Stage 1 Leiden outputs to %s", output_dir)
    return output_dir


def _load_subject_config(root: Path, subject: str) -> dict:
    path = root / "configs" / "subjects" / f"{subject}.yml"
    if not path.exists():
        raise FileNotFoundError(f"missing subject config: {path}")
    return load_yaml(path)


def _resolution(config: dict) -> float:
    value = config.get("resolution", 1.0)
    return 1.0 if value is None else float(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject")
    parser.add_argument("--resolution", type=float)
    args = parser.parse_args()

    try:
        run_stage1_leiden(subject=args.subject, resolution=args.resolution)
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
