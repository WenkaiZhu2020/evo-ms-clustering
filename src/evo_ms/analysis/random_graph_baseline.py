#!/usr/bin/env python3
"""Preregistered uniform simple undirected G(n,m) random baseline."""

from __future__ import annotations

from itertools import combinations
from typing import Iterable, Mapping

import numpy as np


SUBJECT_SEED_BASES = {"jpetstore": 42000, "daytrader": 52000, "xerces": 62000}
REPETITIONS = 1000


def candidate_pairs(class_ids: Iterable[str]) -> list[tuple[str, str]]:
    ordered = sorted(str(class_id) for class_id in class_ids)
    if len(set(ordered)) != len(ordered):
        raise ValueError("random baseline class_ids must be unique")
    return list(combinations(ordered, 2))


def repetition_seed(subject: str, repetition: int) -> int:
    if subject not in SUBJECT_SEED_BASES:
        raise ValueError(f"unknown random-baseline subject: {subject}")
    if not 0 <= repetition < REPETITIONS:
        raise ValueError("repetition must be in 0..999")
    return SUBJECT_SEED_BASES[subject] + repetition


def sample_edges(class_ids: Iterable[str], edge_count: int, subject: str, repetition: int) -> list[tuple[str, str]]:
    pairs = candidate_pairs(class_ids)
    if not 0 <= edge_count <= len(pairs):
        raise ValueError(f"edge_count {edge_count} is outside candidate-pair universe")
    seed = repetition_seed(subject, repetition)
    selected_indices = np.random.default_rng(seed).choice(len(pairs), size=edge_count, replace=False)
    return sorted((pairs[int(index)] for index in selected_indices))


def mapped_ratio(edges: Iterable[tuple[str, str]], labels: Mapping[str, str]) -> tuple[float | None, int, int]:
    eligible = 0
    numerator = 0
    for left, right in edges:
        if left not in labels or right not in labels:
            continue
        eligible += 1
        numerator += int(labels[left] == labels[right])
    return (None if eligible == 0 else float(numerator / eligible), numerator, eligible)


def structural_overlap(edges: Iterable[tuple[str, str]], raw_edges: set[tuple[str, str]]) -> float:
    values = list(edges)
    if not values:
        raise ValueError("structural overlap requires at least one random edge")
    return float(sum(edge in raw_edges for edge in values) / len(values))


def baseline_rows(
    class_ids: Iterable[str],
    edge_count: int,
    subject: str,
    raw_edges: set[tuple[str, str]],
    reference_labels: Mapping[str, str] | None,
    leiden_labels: Mapping[str, str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for repetition in range(REPETITIONS):
        edges = sample_edges(class_ids, edge_count, subject, repetition)
        reference_value, _, _ = mapped_ratio(edges, reference_labels or {})
        leiden_value, _, _ = mapped_ratio(edges, leiden_labels)
        rows.append(
            {
                "subject": subject,
                "repetition": repetition,
                "random_seed": repetition_seed(subject, repetition),
                "edge_count": edge_count,
                "structural_overlap": structural_overlap(edges, raw_edges),
                "same_reference_service_ratio": reference_value,
                "same_leiden_cluster_ratio": leiden_value,
            }
        )
    return rows


def quantile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("cannot calculate a quantile of an empty list")
    return float(np.quantile(np.asarray(values, dtype=float), q, method="higher"))

