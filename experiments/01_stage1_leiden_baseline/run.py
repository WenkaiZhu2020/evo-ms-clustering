from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.clustering.cluster_summary import summarize_clusters
from evo_ms.clustering.leiden_baseline import run_leiden_baseline
from evo_ms.evaluation.partition_metrics import calculate_partition_metrics
from evo_ms.extraction.dependency_extractor import load_extracted_subject
from evo_ms.graph.raw_graph_builder import build_raw_edges
from evo_ms.graph.ssa_graph_builder import build_ssa_edges
from evo_ms.utils.config_loader import load_yaml
from evo_ms.utils.logging import get_logger


def run_stage1_leiden(
    root: Path = ROOT,
    subject: str | None = None,
    config_path: Path | None = None,
) -> list[Path]:
    config = load_yaml(config_path or root / "configs" / "experiments" / "01_stage1_leiden.yml")
    subjects = [subject] if subject else list(config.get("subjects", []))
    if not subjects:
        raise ValueError("Stage 1 Leiden config has no subjects")

    graph_type = _graph_type(config)
    ssa_lambda = _ssa_lambda(config)
    resolution = _resolution(config)
    seed = int(config.get("seed", 42))
    output_root = root / config.get("output_root", config.get("output_directory", "results"))

    output_dirs = []
    for subject_name in subjects:
        output_dirs.append(
            run_subject(
                root=root,
                subject=subject_name,
                output_root=output_root,
                graph_type=graph_type,
                ssa_lambda=ssa_lambda,
                resolution=resolution,
                seed=seed,
            )
        )
    return output_dirs


def run_subject(
    root: Path,
    subject: str,
    output_root: Path,
    graph_type: str,
    ssa_lambda: float,
    resolution: float,
    seed: int,
) -> Path:
    logger = get_logger(__name__)
    if graph_type != "ssa":
        raise ValueError("Stage 1 Leiden baseline currently supports graph_type: ssa")

    subject_config = _load_subject_config(root, subject)
    extracted_dir = root / subject_config.get("extracted_output_path", f"data/extracted/{subject}")
    logger.info("Loading extracted CSVs for %s", subject)
    extracted = load_extracted_subject(extracted_dir)
    class_nodes = extracted["class_nodes"]
    raw_edges = build_raw_edges(class_nodes, extracted["structural_dependencies"])
    stage1_edges = build_ssa_edges(
        class_nodes,
        raw_edges,
        extracted["ssa_flow_edges"],
        ssa_lambda=ssa_lambda,
    )

    logger.info("Running fixed Stage 1 Leiden baseline on G_ssa for %s", subject)
    clusters = run_leiden_baseline(
        class_nodes,
        stage1_edges,
        graph_type=graph_type,
        resolution=resolution,
        seed=seed,
    )
    metrics = calculate_partition_metrics(
        class_nodes,
        stage1_edges,
        clusters,
        subject=subject,
        algorithm="leiden",
        graph_type=graph_type,
    )
    cluster_summary = summarize_clusters(clusters)

    output_dir = output_root / subject / "01_stage1_leiden_baseline"
    graph_dir = output_dir / "graph"
    clustering_dir = output_dir / "clustering"
    metrics_dir = output_dir / "metrics"
    summaries_dir = output_dir / "summaries"
    for directory in [graph_dir, clustering_dir, metrics_dir, summaries_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    edge_table_path = graph_dir / "stage1_edges.csv"
    stage1_edges.to_csv(edge_table_path, index=False)
    clusters.to_csv(clustering_dir / "stage1_clusters.csv", index=False)
    metrics.to_csv(metrics_dir / "stage1_metrics.csv", index=False)
    cluster_summary.to_csv(summaries_dir / "stage1_cluster_summary.csv", index=False)
    _write_baseline_metadata(
        root=root,
        output_dir=output_dir,
        subject=subject,
        graph_type=graph_type,
        ssa_lambda=ssa_lambda,
        resolution=resolution,
        seed=seed,
        extracted_dir=extracted_dir,
        edge_table_path=edge_table_path,
    )

    logger.info("Wrote Stage 1 Leiden outputs to %s", output_dir)
    return output_dir


def _load_subject_config(root: Path, subject: str) -> dict:
    path = root / "configs" / "subjects" / f"{subject}.yml"
    if not path.exists():
        raise FileNotFoundError(f"missing subject config: {path}")
    return load_yaml(path)


def _graph_type(config: dict) -> str:
    value = config.get("graph_type", config.get("input_graph_type", "ssa"))
    normalized = str(value).strip().lower()
    if normalized in {"g_ssa", "ssa"}:
        return "ssa"
    if normalized in {"g_raw", "raw"}:
        return "raw"
    raise ValueError(f"unsupported Stage 1 graph_type: {value}")


def _ssa_lambda(config: dict) -> float:
    value = config.get("ssa_lambda", 1.0)
    return 1.0 if value is None else float(value)


def _resolution(config: dict) -> float:
    value = config.get("resolution", 1.0)
    return 1.0 if value is None else float(value)


def _write_baseline_metadata(
    root: Path,
    output_dir: Path,
    subject: str,
    graph_type: str,
    ssa_lambda: float,
    resolution: float,
    seed: int,
    extracted_dir: Path,
    edge_table_path: Path,
) -> None:
    metadata = {
        "subject": subject,
        "role": "frozen_leiden_baseline_for_later_comparison",
        "baseline_name": "default_ssa_informed_leiden",
        "graph_type": graph_type,
        "ssa_lambda": float(ssa_lambda),
        "resolution": float(resolution),
        "seed": int(seed),
        "source_extracted_data": _relative_dir(root, extracted_dir),
        "edge_table": "graph/stage1_edges.csv",
        "edge_table_sha256": _sha256(edge_table_path),
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    git_head = _git_head(root)
    if git_head:
        metadata["git_head"] = git_head
    with (output_dir / "baseline_metadata.yml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(metadata, handle, sort_keys=False)


def _relative_dir(root: Path, path: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        relative = path
    text = relative.as_posix()
    return text if text.endswith("/") else f"{text}/"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the fixed default SSA-informed Leiden baseline.")
    parser.add_argument("--subject")
    args = parser.parse_args()

    try:
        run_stage1_leiden(subject=args.subject)
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
