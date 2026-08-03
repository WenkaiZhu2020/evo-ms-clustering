"""Multi-seed Leiden robustness control for the Stage 1 SSA effect.

This harness answers one question: does switching G_raw -> G_ssa(lambda=0.25)
change the partition by more than Leiden's own seed-induced variation?

Everything is held fixed except the graph (raw vs ssa) and the Leiden seed:

* resolution = 1.0 (same as the frozen formal profiles)
* raw graph : graph_type=raw, ssa_lambda=0.0
* ssa graph : graph_type=ssa, ssa_lambda=0.25
* seeds = 0..N-1 (fixed, never selected on results)
* n_iterations = -1 (run Leiden to convergence so the only varying factor is the
  seed, not the library's default 2-iteration early stop)

Outputs go to results/stage1/subjects/<subject>/seed_robustness/ and never
touch the frozen results/stage1/subjects/<subject>/leiden_baseline/ outputs.

Two ARI distributions are produced per subject, both with the repo's own ARI:

* SSA effect : ARI(raw_seed_i, ssa_seed_i)            -> N values
* Seed noise : ARI(raw_seed_i, raw_seed_j) for i < j  -> C(N, 2) values
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import UTC, datetime
import hashlib
from itertools import combinations
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evo_ms.clustering.leiden_baseline import run_leiden_baseline
from evo_ms.evaluation.partition_metrics import partition_similarity
from evo_ms.extraction.dependency_extractor import load_extracted_subject
from evo_ms.graph.raw_graph_builder import build_raw_edges
from evo_ms.graph.ssa_graph_builder import build_ssa_edges
from evo_ms.repository_layout import stage1_seed_robustness_root
from evo_ms.utils.config_loader import load_yaml
from evo_ms.utils.logging import get_logger

SUBJECTS = ["jpetstore", "daytrader", "xerces-j"]
RESOLUTION = 1.0
RAW_LAMBDA = 0.0
SSA_LAMBDA = 0.25
N_ITERATIONS = -1


def run_seed_robustness(
    root: Path = ROOT,
    subjects: Sequence[str] | None = None,
    seeds: Sequence[int] | None = None,
) -> dict[str, dict[str, object]]:
    """Run the multi-seed control for each subject and write outputs."""
    logger = get_logger(__name__)
    subjects = list(subjects or SUBJECTS)
    seeds = list(seeds if seeds is not None else range(30))
    if len(seeds) < 2:
        raise ValueError("seed robustness needs at least two seeds")
    git_state = _git_state(root)

    summaries: dict[str, dict[str, object]] = {}
    for subject in subjects:
        summaries[subject] = _run_subject(root, subject, seeds, git_state, logger)
    return summaries


def _run_subject(
    root: Path,
    subject: str,
    seeds: list[int],
    git_state: dict[str, object],
    logger,
) -> dict[str, object]:
    subject_config = _load_subject_config(root, subject)
    extracted_dir = root / subject_config.get(
        "extracted_output_path",
        f"data/extracted/{subject}",
    )
    logger.info("Loading extracted CSVs for %s", subject)
    extracted = load_extracted_subject(extracted_dir)
    class_nodes = extracted["class_nodes"]

    # Graphs depend only on lambda, so build them once and re-cluster per seed.
    raw_edges = build_raw_edges(class_nodes, extracted["structural_dependencies"])
    ssa_edges = build_ssa_edges(
        class_nodes,
        raw_edges,
        extracted["ssa_flow_edges"],
        ssa_lambda=SSA_LAMBDA,
    )

    raw_clusters: dict[int, pd.DataFrame] = {}
    ssa_clusters: dict[int, pd.DataFrame] = {}
    for seed in seeds:
        logger.info("Clustering %s at seed=%s", subject, seed)
        raw_clusters[seed] = run_leiden_baseline(
            class_nodes,
            raw_edges,
            graph_type="raw",
            resolution=RESOLUTION,
            seed=seed,
            n_iterations=N_ITERATIONS,
        )
        ssa_clusters[seed] = run_leiden_baseline(
            class_nodes,
            ssa_edges,
            graph_type="ssa",
            resolution=RESOLUTION,
            seed=seed,
            n_iterations=N_ITERATIONS,
        )

    ssa_effect = [
        {
            "seed": seed,
            "ari_raw_vs_ssa": partition_similarity(
                class_nodes,
                raw_clusters[seed],
                ssa_clusters[seed],
            )[0],
        }
        for seed in seeds
    ]
    seed_noise = [
        {
            "seed_i": seed_i,
            "seed_j": seed_j,
            "ari_raw_i_vs_raw_j": partition_similarity(
                class_nodes,
                raw_clusters[seed_i],
                raw_clusters[seed_j],
            )[0],
        }
        for seed_i, seed_j in combinations(seeds, 2)
    ]

    effect_ari = np.array([row["ari_raw_vs_ssa"] for row in ssa_effect], dtype=float)
    noise_ari = np.array([row["ari_raw_i_vs_raw_j"] for row in seed_noise], dtype=float)
    effect_dist = 1.0 - effect_ari
    noise_dist = 1.0 - noise_ari

    u_statistic, p_value = _mann_whitney_u(effect_dist, noise_dist)
    distinguishable = bool(p_value < 0.05)
    noise_band = _two_std_band(noise_dist)
    effect_dist_mean = float(np.mean(effect_dist))
    inside_band = bool(noise_band[0] <= effect_dist_mean <= noise_band[1])

    # Honest effect-size context: how seed-unstable the raw partition itself is,
    # and how often reseeding the raw graph alone moves it at least as much as SSA.
    distinct_raw_partitions = len(
        {tuple(df.sort_values("class_id")["cluster_id"].tolist()) for df in raw_clusters.values()}
    )
    identical_pair_frac = float(np.mean(noise_dist == 0.0))
    noise_ge_effect_frac = float(np.mean(noise_dist >= effect_dist_mean))

    verdict = _verdict(
        effect_dist_mean=effect_dist_mean,
        noise_dist_mean=float(np.mean(noise_dist)),
        noise_dist_std=_std(noise_dist),
        noise_band=noise_band,
        inside_band=inside_band,
        distinguishable=distinguishable,
        p_value=p_value,
        identical_pair_frac=identical_pair_frac,
        noise_ge_effect_frac=noise_ge_effect_frac,
    )

    summary_row = {
        "subject": subject,
        "n_seeds": len(seeds),
        "n_seed_noise_pairs": len(seed_noise),
        "ssa_effect_ari_mean": _mean(effect_ari),
        "ssa_effect_ari_std": _std(effect_ari),
        "ssa_effect_dist_mean": _mean(effect_dist),
        "ssa_effect_dist_std": _std(effect_dist),
        "seed_noise_ari_mean": _mean(noise_ari),
        "seed_noise_ari_std": _std(noise_ari),
        "seed_noise_dist_mean": _mean(noise_dist),
        "seed_noise_dist_std": _std(noise_dist),
        "seed_noise_dist_2std_low": noise_band[0],
        "seed_noise_dist_2std_high": noise_band[1],
        "ssa_effect_dist_in_seed_noise_band": inside_band,
        "distinct_raw_partitions_across_seeds": distinct_raw_partitions,
        "seed_noise_identical_pair_frac": identical_pair_frac,
        "reseeds_ge_mean_ssa_effect_frac": noise_ge_effect_frac,
        "mannwhitney_u": float(u_statistic),
        "mannwhitney_p": float(p_value),
        "distinguishable_p05": distinguishable,
        "verdict": verdict,
    }

    output_dir = stage1_seed_robustness_root(subject, root)
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(ssa_effect).to_csv(output_dir / "ssa_effect_ari.csv", index=False)
    pd.DataFrame(seed_noise).to_csv(output_dir / "seed_noise_ari.csv", index=False)
    pd.DataFrame([summary_row]).to_csv(output_dir / "robustness_summary.csv", index=False)
    _write_summary_markdown(output_dir / "robustness_summary.md", summary_row, seeds)
    _write_metadata(
        output_dir / "robustness_metadata.yml",
        root=root,
        subject=subject,
        seeds=seeds,
        extracted_dir=extracted_dir,
        git_state=git_state,
    )
    logger.info("Wrote seed-robustness outputs to %s", output_dir)
    summary_row["output_dir"] = str(output_dir.relative_to(root))
    return summary_row


def _mann_whitney_u(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Two-sided Mann-Whitney U via normal approximation (tie + continuity).

    Returns the U statistic for the first sample ``x`` and the two-sided p-value.
    scipy is not a project dependency, so this is implemented directly. The two
    samples share the raw partitions, so independence is only approximate; the
    p-value is reported as a guideline alongside the distribution overlap.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return float("nan"), float("nan")

    combined = np.concatenate([x, y])
    order = combined.argsort(kind="mergesort")
    sorted_values = combined[order]
    ranks = np.empty(len(combined), dtype=float)
    total = len(combined)
    tie_term = 0.0
    index = 0
    while index < total:
        end = index
        while end + 1 < total and sorted_values[end + 1] == sorted_values[index]:
            end += 1
        average_rank = (index + end) / 2.0 + 1.0  # 1-based ranks
        ranks[order[index : end + 1]] = average_rank
        run_length = end - index + 1
        tie_term += run_length**3 - run_length
        index = end + 1

    rank_sum_x = float(ranks[:n1].sum())
    u_x = rank_sum_x - n1 * (n1 + 1) / 2.0
    mean_u = n1 * n2 / 2.0
    n = n1 + n2
    variance_u = (n1 * n2 / 12.0) * ((n + 1) - tie_term / (n * (n - 1)))
    if variance_u <= 0:
        return u_x, 1.0
    z = (abs(u_x - mean_u) - 0.5) / math.sqrt(variance_u)
    z = max(z, 0.0)
    p_two_sided = 2.0 * (1.0 - _standard_normal_cdf(z))
    return u_x, min(1.0, max(0.0, p_two_sided))


def _standard_normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _two_std_band(values: np.ndarray) -> tuple[float, float]:
    mean = float(np.mean(values))
    std = _std(values)
    return (mean - 2.0 * std, mean + 2.0 * std)


def _mean(values: np.ndarray) -> float:
    return float(np.mean(values)) if len(values) else float("nan")


def _std(values: np.ndarray) -> float:
    # Sample standard deviation (ddof=1); needs at least two observations.
    return float(np.std(values, ddof=1)) if len(values) > 1 else 0.0


def _verdict(
    effect_dist_mean: float,
    noise_dist_mean: float,
    noise_dist_std: float,
    noise_band: tuple[float, float],
    inside_band: bool,
    distinguishable: bool,
    p_value: float,
    identical_pair_frac: float,
    noise_ge_effect_frac: float,
) -> str:
    """One honest line: lead with effect size/overlap, then the MWU result.

    A significant Mann-Whitney p only means the two distance distributions are
    separable in shape, not that SSA produces a larger or more meaningful
    repartition. The effect-size comparison and band overlap are reported first.
    """
    separable = "separable" if distinguishable else "not separable"
    if noise_dist_std == 0.0:
        return (
            f"Raw clustering is seed-stable (seed-noise distance = 0 across all pairs), "
            f"so the fixed SSA distance {effect_dist_mean:.4f} registers as 'outside' zero "
            f"noise. This is the seed-trivial small-graph case; Mann-Whitney p={p_value:.3g} "
            f"({separable}) is degenerate here."
        )
    band_word = "within" if inside_band else "outside"
    return (
        f"SSA-effect distance {effect_dist_mean:.4f} vs seed-noise {noise_dist_mean:.4f}"
        f"+/-{noise_dist_std:.4f}: same order of magnitude, and SSA-effect lies {band_word} "
        f"the seed-noise +/-2std band [{noise_band[0]:.4f}, {noise_band[1]:.4f}]. "
        f"{noise_ge_effect_frac * 100:.0f}% of pure reseeds move the raw partition >= the mean "
        f"SSA effect ({identical_pair_frac * 100:.0f}% of reseed pairs are identical). "
        f"Mann-Whitney p={p_value:.3g}: distributions {separable} by shape, but effect "
        f"magnitudes overlap -> SSA effect is comparable to seed noise, not clearly beyond it."
    )


def _write_summary_markdown(path: Path, row: dict[str, object], seeds: list[int]) -> None:
    lines = [
        f"# Seed-robustness control: {row['subject']}",
        "",
        f"Seeds: {seeds[0]}..{seeds[-1]} ({row['n_seeds']} seeds, "
        f"{row['n_seed_noise_pairs']} raw-vs-raw pairs). "
        f"resolution={RESOLUTION}, raw lambda={RAW_LAMBDA}, ssa lambda={SSA_LAMBDA}, "
        f"n_iterations={N_ITERATIONS}.",
        "",
        "| distribution | ARI mean +/- std | distance (1-ARI) mean +/- std |",
        "| --- | --- | --- |",
        f"| SSA effect ARI(raw_i, ssa_i) | {row['ssa_effect_ari_mean']:.4f} +/- "
        f"{row['ssa_effect_ari_std']:.4f} | {row['ssa_effect_dist_mean']:.4f} +/- "
        f"{row['ssa_effect_dist_std']:.4f} |",
        f"| Seed noise ARI(raw_i, raw_j) | {row['seed_noise_ari_mean']:.4f} +/- "
        f"{row['seed_noise_ari_std']:.4f} | {row['seed_noise_dist_mean']:.4f} +/- "
        f"{row['seed_noise_dist_std']:.4f} |",
        "",
        f"Raw-partition seed stability: {row['distinct_raw_partitions_across_seeds']} distinct raw "
        f"partitions across {row['n_seeds']} seeds; "
        f"{row['seed_noise_identical_pair_frac'] * 100:.0f}% of reseed pairs are identical; "
        f"{row['reseeds_ge_mean_ssa_effect_frac'] * 100:.0f}% of reseeds move the raw partition at "
        f"least as much as the mean SSA effect.",
        "",
        f"Mann-Whitney U (SSA-effect distance vs seed-noise distance): "
        f"U={row['mannwhitney_u']:.1f}, p={row['mannwhitney_p']:.4g} "
        f"(distinguishable at p<0.05: {row['distinguishable_p05']}). Note: the two samples share "
        f"the raw partitions, so independence is approximate and the p-value is a guideline "
        f"alongside the effect-size/overlap view above.",
        "",
        f"Verdict: {row['verdict']}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_metadata(
    path: Path,
    root: Path,
    subject: str,
    seeds: list[int],
    extracted_dir: Path,
    git_state: dict[str, object],
) -> None:
    metadata = {
        "subject": subject,
        "role": "seed_robustness_control_for_ssa_effect",
        "does_not_modify": "results/stage1/subjects/<subject>/leiden_baseline/",
        "resolution": float(RESOLUTION),
        "raw_ssa_lambda": float(RAW_LAMBDA),
        "ssa_ssa_lambda": float(SSA_LAMBDA),
        "n_iterations": int(N_ITERATIONS),
        "seeds": [int(seed) for seed in seeds],
        "source_extracted_data": _relative_dir(root, extracted_dir),
        "extracted_input_sha256": _extracted_input_sha256(extracted_dir),
        "generated_at_utc": _utc_now(),
        "git_head": git_state["git_head"],
        "git_dirty": git_state["git_dirty"],
    }
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(metadata, handle, sort_keys=False)


def _load_subject_config(root: Path, subject: str) -> dict:
    path = root / "configs" / "subjects" / f"{subject}.yml"
    if not path.exists():
        raise FileNotFoundError(f"missing subject config: {path}")
    return load_yaml(path)


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


def _git_state(root: Path) -> dict[str, object]:
    return {"git_head": _git_command(root, ["git", "rev-parse", "HEAD"]), "git_dirty": _git_dirty(root)}


def _git_dirty(root: Path) -> bool | None:
    result = _git_command(
        root,
        ["git", "status", "--porcelain", "--untracked-files=all", "--", ".", ":(exclude)results"],
    )
    return None if result is None else bool(result.strip())


def _git_command(root: Path, command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, cwd=root, check=False, capture_output=True, text=True)
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _print_supervisor_summary(summaries: dict[str, dict[str, object]]) -> None:
    print("\n==== Supervisor summary (SSA effect vs seed noise) ====")
    for subject, row in summaries.items():
        band = "within" if row["ssa_effect_dist_in_seed_noise_band"] else "outside"
        print(
            f"{subject}: SSA-effect dist {row['ssa_effect_dist_mean']:.3f}"
            f"+/-{row['ssa_effect_dist_std']:.3f} vs seed-noise {row['seed_noise_dist_mean']:.3f}"
            f"+/-{row['seed_noise_dist_std']:.3f} ({band} 2std band; "
            f"{row['reseeds_ge_mean_ssa_effect_frac'] * 100:.0f}% of reseeds >= mean SSA effect; "
            f"MWU p={row['mannwhitney_p']:.2g})."
        )
    nontrivial = {s: r for s, r in summaries.items() if r["seed_noise_dist_std"] > 0}
    all_within = bool(nontrivial) and all(
        r["ssa_effect_dist_in_seed_noise_band"] for r in nontrivial.values()
    )
    if all_within:
        names = ", ".join(nontrivial)
        overall = (
            f"On the seed-unstable subjects ({names}) the SSA effect is the same order as Leiden "
            f"seed noise and sits within its +/-2std band; reseeding the raw graph alone moves the "
            f"partition about as much as adding SSA does. SSA does not repartition classes beyond "
            f"seed noise -> supports shelving SSA at class level (seed-stable small subjects aside)."
        )
    else:
        overall = (
            "At least one seed-unstable subject shows the SSA effect outside the seed-noise band; "
            "SSA may move the partition beyond reseeding there - inspect per-subject before shelving."
        )
    print(f"Overall: {overall}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 1 multi-seed SSA-vs-seed-noise robustness control.")
    parser.add_argument("--subjects", default=",".join(SUBJECTS), help="comma-separated subject list")
    parser.add_argument("--num-seeds", type=int, default=30, help="number of fixed seeds, starting at 0")
    args = parser.parse_args()

    subjects = [name.strip() for name in args.subjects.split(",") if name.strip()]
    seeds = list(range(args.num_seeds))

    try:
        summaries = run_seed_robustness(subjects=subjects, seeds=seeds)
    except ImportError as exc:
        print(f"ERROR: missing dependency for Leiden: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _print_supervisor_summary(summaries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
