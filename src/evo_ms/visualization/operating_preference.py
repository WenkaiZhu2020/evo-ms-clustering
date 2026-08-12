"""Authoritative BALANCE-profile access for selector-dependent figures."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

import pandas as pd
from sklearn.metrics import adjusted_rand_score


AUTHORITATIVE_RELATIVE_PATH = Path(
    "results/stage3/cross_subject/operating_preference_analysis/"
    "04_selected_profiles_per_seed.csv"
)
SUBJECT_DIRECTORIES = {
    "jpetstore": "jpetstore",
    "daytrader": "daytrader",
    "xerces": "xerces-j",
}


@dataclass(frozen=True)
class BalanceSelection:
    subject: str
    stage: str
    seed: int
    solution_id: str
    weighted_modularity: float
    partition_source: str
    partition: pd.DataFrame
    representative_rule: str
    mean_ari_to_other_balance_partitions: float | None
    authoritative_source: str
    authoritative_source_commit: str


def _source_commit(root: Path) -> str:
    value = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "log",
            "-1",
            "--format=%H",
            "--",
            AUTHORITATIVE_RELATIVE_PATH.as_posix(),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(value) != 40:
        raise ValueError("authoritative operating-preference source is not committed")
    return value


def authoritative_source_commit(root: Path) -> str:
    """Return the commit that introduced the authoritative selector bundle."""

    return _source_commit(root)


def _balance_rows(root: Path, subject: str, stage: str) -> pd.DataFrame:
    if subject not in SUBJECT_DIRECTORIES or stage not in {"stage2", "stage3"}:
        raise ValueError(f"unsupported BALANCE selection: {subject}/{stage}")
    source = root / AUTHORITATIVE_RELATIVE_PATH
    rows = pd.read_csv(source)
    rows = rows.loc[
        (rows["subject"] == subject)
        & (rows["stage"] == stage)
        & (rows["profile"] == "BALANCE")
        & (rows["profile_id"] == "P1")
    ].sort_values("seed")
    if len(rows) != 30 or rows["seed"].astype(int).tolist() != list(range(30)):
        raise ValueError(f"{subject}/{stage} must have BALANCE seeds 0-29")
    if not rows["feasible"].astype(bool).all():
        raise ValueError(f"{subject}/{stage} contains an infeasible BALANCE selection")
    return rows


def _partition_path(root: Path, subject: str, stage: str, seed: int) -> Path:
    directory = SUBJECT_DIRECTORIES[subject]
    if stage == "stage2":
        return root / (
            f"results/stage2/subjects/{directory}/nsga/robustness_final_30seeds/"
            f"seed_{seed:02d}/pareto_labels.csv.xz"
        )
    run_kind = "validation" if seed == 0 else "formal"
    return root / (
        f"results/stage3/subjects/{directory}/declaration_method_body/{run_kind}/"
        f"seed_{seed:02d}/partition_labels.csv"
    )


def _load_partition(
    root: Path, subject: str, stage: str, seed: int, solution_id: str
) -> tuple[pd.DataFrame, str]:
    path = _partition_path(root, subject, stage, seed)
    labels = pd.read_csv(path)
    selected = labels.loc[
        labels["solution_id"].astype(str) == solution_id,
        ["class_id", "class_name", "cluster_id"],
    ].copy()
    if selected.empty or selected["class_id"].astype(str).duplicated().any():
        raise ValueError(f"missing or invalid labels for {subject}/{stage}/{solution_id}")
    return selected, path.relative_to(root).as_posix()


def fixed_balance_selection(
    root: Path, subject: str, stage: str, seed: int
) -> BalanceSelection:
    """Load an existing approved representative seed through the BALANCE bundle."""

    rows = _balance_rows(root, subject, stage)
    row = rows.loc[rows["seed"].astype(int) == seed]
    if len(row) != 1:
        raise ValueError(f"missing BALANCE seed {seed} for {subject}/{stage}")
    record = row.iloc[0]
    solution_id = str(record["selected_solution_id"])
    partition, partition_source = _load_partition(
        root, subject, stage, seed, solution_id
    )
    return BalanceSelection(
        subject,
        stage,
        seed,
        solution_id,
        float(record["weighted_modularity"]),
        partition_source,
        partition,
        "existing approved Stage 2 representative seed; solution resolved from authoritative BALANCE/P1",
        None,
        AUTHORITATIVE_RELATIVE_PATH.as_posix(),
        _source_commit(root),
    )


def balance_partition_medoid(root: Path, subject: str, stage: str) -> BalanceSelection:
    """Select the most representative BALANCE partition across seeds 0-29.

    The medoid maximises mean ARI to the other 29 BALANCE partitions. Exact ties
    are broken by ascending seed and then solution ID.
    """

    rows = _balance_rows(root, subject, stage)
    candidates: list[tuple[pd.Series, pd.DataFrame, str]] = []
    for _, row in rows.iterrows():
        seed = int(row["seed"])
        solution_id = str(row["selected_solution_id"])
        partition, source = _load_partition(root, subject, stage, seed, solution_id)
        candidates.append((row, partition.sort_values("class_id"), source))
    expected_classes = candidates[0][1]["class_id"].astype(str).tolist()
    if any(
        partition["class_id"].astype(str).tolist() != expected_classes
        for _row, partition, _source in candidates
    ):
        raise ValueError(f"{subject}/{stage} BALANCE partitions have different class universes")
    scores: list[tuple[float, int, str, pd.Series, pd.DataFrame, str]] = []
    for index, (row, partition, source) in enumerate(candidates):
        labels = partition["cluster_id"].to_numpy()
        similarities = [
            adjusted_rand_score(labels, other[1]["cluster_id"].to_numpy())
            for other_index, other in enumerate(candidates)
            if other_index != index
        ]
        scores.append(
            (
                float(sum(similarities) / len(similarities)),
                int(row["seed"]),
                str(row["selected_solution_id"]),
                row,
                partition,
                source,
            )
        )
    mean_ari, seed, solution_id, row, partition, source = sorted(
        scores, key=lambda value: (-value[0], value[1], value[2])
    )[0]
    return BalanceSelection(
        subject,
        stage,
        seed,
        solution_id,
        float(row["weighted_modularity"]),
        source,
        partition,
        "maximum mean ARI to the other 29 BALANCE/P1 partitions; ties by seed then solution_id",
        mean_ari,
        AUTHORITATIVE_RELATIVE_PATH.as_posix(),
        _source_commit(root),
    )


def representative_provenance(*selections: BalanceSelection) -> list[dict[str, object]]:
    return [
        {
            "subject": selection.subject,
            "stage": selection.stage,
            "profile": "BALANCE",
            "profile_id": "P1",
            "seed": selection.seed,
            "solution_id": selection.solution_id,
            "partition_source": selection.partition_source,
            "authoritative_source": selection.authoritative_source,
            "authoritative_source_commit": selection.authoritative_source_commit,
            "representative_rule": selection.representative_rule,
            "mean_ari_to_other_balance_partitions": selection.mean_ari_to_other_balance_partitions,
        }
        for selection in selections
    ]
