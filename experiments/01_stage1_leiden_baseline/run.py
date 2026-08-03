"""Generate frozen formal Stage 1 Leiden baseline profiles."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
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
from evo_ms.extraction.evidence_weight_validation import expected_extracted_evidence_weights
from evo_ms.extraction.evidence_weight_validation import validate_extracted_evidence_weights
from evo_ms.graph.raw_graph_builder import build_raw_edges
from evo_ms.graph.ssa_graph_builder import build_ssa_edges
from evo_ms.repository_layout import STAGE1_SUBJECTS_RELATIVE, canonical_subject
from evo_ms.utils.config_loader import load_yaml
from evo_ms.utils.logging import get_logger


def run_stage1_leiden(
    root: Path = ROOT,
    subject: str | None = None,
    config_path: Path | None = None,
) -> list[Path]:
    """Run configured formal profiles for one subject or all Stage 1 subjects."""
    config = load_yaml(config_path or root / "configs" / "experiments" / "01_stage1_leiden.yml")
    subjects = [subject] if subject else list(config.get("subjects", []))
    if not subjects:
        raise ValueError("Stage 1 Leiden config has no subjects")

    profiles = _profiles(config)
    expected_weights = expected_extracted_evidence_weights(config)
    output_root = root / STAGE1_SUBJECTS_RELATIVE

    output_dirs = []
    for subject_name in subjects:
        output_dirs.append(
            run_subject(
                root=root,
                subject=subject_name,
                output_root=output_root,
                profiles=profiles,
                expected_weights=expected_weights,
            )
        )
    return output_dirs


def run_subject(
    root: Path,
    subject: str,
    output_root: Path,
    profiles: list[dict[str, object]],
    expected_weights: Mapping[str, object],
) -> Path:
    """Rebuild fixed graphs from extracted CSVs and write formal baseline outputs."""
    logger = get_logger(__name__)
    subject_config = _load_subject_config(root, subject)
    extracted_dir = root / subject_config.get("extracted_output_path", f"data/extracted/{subject}")
    logger.info("Loading extracted CSVs for %s", subject)
    extracted = load_extracted_subject(extracted_dir)
    validate_extracted_evidence_weights(
        extracted["structural_dependencies"],
        extracted["ssa_flow_edges"],
        expected_weights,
        subject=subject,
    )
    git_state = _git_state(root)

    class_nodes = extracted["class_nodes"]
    raw_edges = build_raw_edges(class_nodes, extracted["structural_dependencies"])
    output_dir = output_root / canonical_subject(subject) / "leiden_baseline"
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_profiles = []
    for profile in profiles:
        profile_name = str(profile["profile_name"])
        graph_type = _graph_type(profile)
        ssa_lambda = _ssa_lambda(profile)
        resolution = _resolution(profile)
        seed = _seed(profile)

        if graph_type == "raw":
            stage1_edges = raw_edges.copy()
        else:
            stage1_edges = build_ssa_edges(
                class_nodes,
                raw_edges,
                extracted["ssa_flow_edges"],
                ssa_lambda=ssa_lambda,
            )

        profile_dir = output_dir / profile_name
        graph_dir = profile_dir / "graph"
        clustering_dir = profile_dir / "clustering"
        metrics_dir = profile_dir / "metrics"
        summaries_dir = profile_dir / "summaries"
        for directory in [graph_dir, clustering_dir, metrics_dir, summaries_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Running Stage 1 profile %s for %s on G_%s",
            profile_name,
            subject,
            graph_type,
        )
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

        edge_table_path = graph_dir / "stage1_edges.csv"
        stage1_edges.to_csv(edge_table_path, index=False)
        clusters.to_csv(clustering_dir / "stage1_clusters.csv", index=False)
        metrics.to_csv(metrics_dir / "stage1_metrics.csv", index=False)
        cluster_summary.to_csv(summaries_dir / "stage1_cluster_summary.csv", index=False)
        _write_baseline_metadata(
            root=root,
            output_dir=profile_dir,
            subject=subject,
            profile=profile,
            graph_type=graph_type,
            ssa_lambda=ssa_lambda,
            resolution=resolution,
            seed=seed,
            expected_weights=expected_weights,
            extracted_dir=extracted_dir,
            edge_table_path=edge_table_path,
            git_state=git_state,
        )
        generated_profiles.append(
            {
                "profile_name": profile_name,
                "graph_type": graph_type,
                "profile_directory": profile_name,
            }
        )

    _write_baseline_index(root, output_dir, subject, generated_profiles, git_state)
    logger.info("Wrote Stage 1 Leiden outputs to %s", output_dir)
    return output_dir


def _load_subject_config(root: Path, subject: str) -> dict:
    path = root / "configs" / "subjects" / f"{subject}.yml"
    if not path.exists():
        raise FileNotFoundError(f"missing subject config: {path}")
    return load_yaml(path)


def _profiles(config: dict) -> list[dict[str, object]]:
    raw_profiles = config.get("profiles")
    if not isinstance(raw_profiles, Mapping) or not raw_profiles:
        raise ValueError("Stage 1 Leiden config must define profiles")
    profiles = []
    for profile_name, values in raw_profiles.items():
        if not isinstance(values, Mapping):
            raise ValueError(f"Stage 1 profile {profile_name} must be a mapping")
        profile = dict(values)
        profile["profile_name"] = str(profile_name)
        _graph_type(profile)
        _ssa_lambda(profile)
        _resolution(profile)
        _seed(profile)
        profiles.append(profile)
    return profiles


def _graph_type(profile: Mapping[str, object]) -> str:
    value = profile.get("graph_type", "ssa")
    normalized = str(value).strip().lower()
    if normalized in {"g_ssa", "ssa"}:
        return "ssa"
    if normalized in {"g_raw", "raw"}:
        return "raw"
    raise ValueError(f"unsupported Stage 1 graph_type: {value}")


def _ssa_lambda(profile: Mapping[str, object]) -> float:
    value = profile.get("ssa_lambda", 1.0)
    return 1.0 if value is None else float(value)


def _resolution(profile: Mapping[str, object]) -> float:
    value = profile.get("resolution", 1.0)
    return 1.0 if value is None else float(value)


def _seed(profile: Mapping[str, object]) -> int:
    value = profile.get("seed", 42)
    return 42 if value is None else int(value)


def _write_baseline_metadata(
    root: Path,
    output_dir: Path,
    subject: str,
    profile: Mapping[str, object],
    graph_type: str,
    ssa_lambda: float,
    resolution: float,
    seed: int,
    expected_weights: Mapping[str, object],
    extracted_dir: Path,
    edge_table_path: Path,
    git_state: Mapping[str, object],
) -> None:
    metadata = {
        "subject": subject,
        "profile_name": str(profile["profile_name"]),
        "role": "frozen_leiden_baseline_for_later_comparison",
        "selection_role": str(profile.get("selection_role", "")),
        "selection_source": str(profile.get("selection_source", "")),
        "graph_type": graph_type,
        "base_evidence_weights": {
            key: float(value)
            for key, value in expected_weights.items()
        },
        "ssa_lambda": float(ssa_lambda),
        "resolution": float(resolution),
        "seed": int(seed),
        "source_extracted_data": _relative_dir(root, extracted_dir),
        "edge_table": "graph/stage1_edges.csv",
        "edge_table_sha256": _sha256(edge_table_path),
        "extracted_input_sha256": _extracted_input_sha256(extracted_dir),
        "generated_at_utc": _utc_now(),
        "git_head": git_state["git_head"],
        "git_dirty": git_state["git_dirty"],
    }
    with (output_dir / "baseline_metadata.yml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(metadata, handle, sort_keys=False)


def _write_baseline_index(
    root: Path,
    output_dir: Path,
    subject: str,
    generated_profiles: list[dict[str, object]],
    git_state: Mapping[str, object],
) -> None:
    metadata = {
        "subject": subject,
        "generated_profiles": generated_profiles,
        "comparison_purpose": (
            "raw_reference_leiden is the structural reference; "
            "ssa_selected_leiden is retained for controlled SSA comparison."
        ),
        "generated_at_utc": _utc_now(),
        "git_head": git_state["git_head"],
        "git_dirty": git_state["git_dirty"],
    }
    with (output_dir / "baseline_index.yml").open("w", encoding="utf-8") as handle:
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


def _extracted_input_sha256(extracted_dir: Path) -> dict[str, str]:
    return {
        name: _sha256(extracted_dir / name)
        for name in ["class_nodes.csv", "structural_dependencies.csv", "ssa_flow_edges.csv"]
    }


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_head(root: Path) -> str | None:
    result = _git_command(root, ["git", "rev-parse", "HEAD"])
    return result or None


def _git_state(root: Path) -> dict[str, object]:
    return {
        "git_head": _git_head(root),
        "git_dirty": _git_dirty(root),
    }


def _git_dirty(root: Path) -> bool | None:
    result = _git_command(
        root,
        ["git", "status", "--porcelain", "--untracked-files=all", "--", ".", ":(exclude)results"],
    )
    if result is None:
        return None
    return bool(result.strip())


def _git_command(root: Path, command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frozen Stage 1 Leiden baseline profiles.")
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
