#!/usr/bin/env python3
"""Render the human-readable Stage 3 Day 4 report from frozen artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from build_semantic_graphs import ROOT, SUBJECTS, subject_graph_dir


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def fmt(value, digits: int = 6):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def graph_data(subject: str):
    graph = subject_graph_dir(subject)
    diagnostics = ROOT / "results" / subject / "04_stage3_semantic" / "diagnostics"
    return (
        load_json(graph / "graph_metadata.json"),
        load_json(diagnostics / "graph_structure.json"),
        load_json(diagnostics / "novelty_alignment.json"),
        load_json(diagnostics / "random_baseline_summary.json"),
        load_json(diagnostics / "representation_ties.json"),
        rows(diagnostics / "top_weight_edges.csv"),
    )


def render(go_no_go: dict) -> str:
    data = {subject: graph_data(subject) for subject in SUBJECTS}
    lines = [
        "# Stage 3 Day 4 Semantic Graph Report",
        "",
        "## 1. Purpose and frozen method",
        "",
        "The formal embeddings were frozen before Day 4. Each subject graph was built directly from saved `embeddings.npy` and `class_ids.csv` files. Each class selected its three highest true-cosine neighbours, exact ties used ascending lexicographic `class_id`, and OR symmetrisation produced one undirected weighted graph. `nearest_neighbors.csv`, structural graphs, Leiden partitions, reference labels, package diagnostics, and other diagnostic files were not graph inputs.",
        "",
        "Duplicate representations receive no special treatment. Identical-text neighbours remain ordinary top-3 candidates. No post-hoc correction was applied after observing Xerces; representation-induced equivalence is quantified below.",
        "",
        "The random baseline was frozen before semantic graph generation: uniform simple undirected G(n,m), N=1000, exact edge-count matching, uniform sampling without replacement from all unordered `i<j` pairs, no degree matching, and no edge weights. Seeds are 42000, 52000, and 62000 with `subject_seed_base + repetition_index` for repetitions 0..999. Quantiles use `numpy.quantile(method=\"higher\")`; pass comparisons use strict `observed > p95`.",
        "",
        "## 2. Provenance",
        "",
        "| subject | source embedding hash | directed-selection hash | semantic-graph hash | nodes | k | tie-break | symmetrisation | graph construction commit |",
        "| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for subject, (metadata, *_rest) in data.items():
        lines.append(
            f"| {subject} | `{metadata['source_aggregate_embedding_sha256']}` | `{metadata['directed_selection_sha256']}` | `{metadata['semantic_graph_sha256']}` | {metadata['node_count']} | {metadata['k']} | `{metadata['tie_break']}` | `{metadata['symmetrisation']}` | `{metadata['construction_git_commit']}` |"
        )
    lines += [
        "",
        "The formal graph source is `embeddings.npy + class_ids.csv`; the canonical weight format is `.17g`, with numerical zero written as `0`.",
        "",
        "## 3. Graph summary",
        "",
        "| subject | nodes | directed selections | edges | total weight | node coverage | isolated ratio | degree min/mean/median/max | components | largest component ratio | weight min/mean/median/max | mutual-selection ratio |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |",
    ]
    for subject, (_metadata, structure, *_rest) in data.items():
        lines.append(
            f"| {subject} | {structure['node_count']} | {structure['directed_selection_count']} | {structure['edge_count']} | {fmt(structure['total_edge_weight'])} | {fmt(structure['node_coverage'])} | {fmt(structure['isolated_node_ratio'])} | {fmt(structure['degree_min'])}/{fmt(structure['degree_mean'])}/{fmt(structure['degree_median'])}/{fmt(structure['degree_max'])} | {structure['connected_component_count']} | {fmt(structure['largest_connected_component_ratio'])} | {fmt(structure['edge_weight_min'])}/{fmt(structure['edge_weight_mean'])}/{fmt(structure['edge_weight_median'])}/{fmt(structure['edge_weight_max'])} | {fmt(structure['mutual_selection_edge_ratio'])} |"
        )
    lines += ["", "## 4. Novelty and alignment", "", "| subject | semantic edges | G_raw overlap | structural overlap | novel edges | novel ratio | same package | cross package | same Leiden | Leiden eligible edges | same reference | reference eligible edges |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for subject, (_metadata, _structure, novelty, *_rest) in data.items():
        leiden = novelty["fixed_leiden"]
        reference = novelty["reference_service"]
        lines.append(
            f"| {subject} | {novelty['semantic_edge_count']} | {novelty['overlap_edge_count']} | {fmt(novelty['structural_overlap'])} | {novelty['novel_edge_count']} | {fmt(novelty['novel_edge_ratio'])} | {fmt(novelty['same_package_ratio'])} | {fmt(novelty['cross_package_ratio'])} | {fmt(leiden['ratio'])} | {leiden['eligible_edge_count']} | {fmt(reference['ratio'])} | {reference['eligible_edge_count']} |"
        )
    lines += ["", "Structural and novelty ratios sum to 1 within floating-point precision. G_raw uses `evo_ms.graph.raw_graph_builder.build_raw_edges`, canonical undirected endpoints, self-loop removal, and merged duplicate structural pairs. SSA was not used.", "", "## 5. Random baseline", "", "| subject | N | runtime seconds | structural observed | structural p50 | structural p95 | strict > p95 | reference observed | reference p50 | reference p95 | strict > p95 | valid reference values | same-Leiden observed (diagnostic) |", "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: |"]
    for subject, (_metadata, _structure, _novelty, summary, *_rest) in data.items():
        structural = summary["metrics"]["structural_overlap"]
        reference = summary["metrics"]["same_reference_service_ratio"]
        leiden = summary["metrics"]["same_leiden_cluster_ratio"]
        lines.append(
            f"| {subject} | {summary['repetitions']} | {fmt(summary['runtime_seconds'])} | {fmt(structural['observed'])} | {fmt(structural['random_p50'])} | {fmt(structural['random_p95'])} | {fmt(structural['observed_strictly_greater_than_p95'])} | {fmt(reference['observed'])} | {fmt(reference['random_p50'])} | {fmt(reference['random_p95'])} | {fmt(reference['observed_strictly_greater_than_p95'])} | {reference['valid_random_value_count']} | {fmt(leiden['observed'])} |"
        )
    lines += ["", "JPetStore and Xerces have no expert reference-service mapping; their reference values and random reference distributions are null, and only structural overlap can pass. DayTrader uses its existing mapping with both endpoints required in the denominator. Same-Leiden is diagnostic only.", "", "## 6. Representation-induced ties", "", "| subject | duplicate groups | duplicate classes | identical-vector groups | identical-text directed selections | exact-cosine-1 selections | affected nodes | identical-text edges | edges involving duplicate-group classes |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for subject, (_metadata, _structure, _novelty, _summary, ties, *_rest) in data.items():
        lines.append(
            f"| {subject} | {ties['duplicate_text_group_count']} | {ties['duplicate_text_class_count']} | {ties['identical_embedding_group_count']} | {ties['directed_identical_text_selection_count']} | {ties['directed_exact_cosine_one_selection_count']} | {ties['nodes_with_identical_text_top3_neighbour_count']} | {ties['identical_text_undirected_edge_count']} | {ties['edges_involving_duplicate_text_group_class_count']} ({fmt(ties['edges_involving_duplicate_text_group_class_ratio'])}) |"
        )
    lines += ["", "These are representation-induced equivalence and tie statistics. No graph rule was changed because of them.", ""]
    xerces_groups = data["xerces"][4]["duplicate_text_groups"]
    lines += ["### Xerces duplicate groups", "", "The following 11 duplicate-text/vector groups are expected under the frozen simple-name input contract; the classes were not deduplicated.", ""]
    for index, group in enumerate(xerces_groups, start=1):
        lines.append(f"{index}. `{'; '.join(group['members'])}` — size {group['group_size']}; final intra-group edges {group['actual_final_intra_group_semantic_edges']}; directed intra-group selections {group['directed_intra_group_selections']}; top-k slots {group['top_k_slots_occupied_by_intra_group_selections']}.")
    lines += ["", "## 7. Top-10 highest-weight edges for manual review", ""]
    for subject, (_metadata, _structure, _novelty, _summary, _ties, top_edges) in data.items():
        lines += [f"### {subject}", "", "| rank | class_id_a | class_name_a | class_id_b | class_name_b | weight | selected_by | G_raw | same package | same Leiden | same reference | duplicate text | plausible | questionable | unclear | reviewer note |", "| ---: | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for row in top_edges:
            lines.append(f"| {row['rank']} | `{row['class_id_a']}` | `{row['class_name_a']}` | `{row['class_id_b']}` | `{row['class_name_b']}` | {row['weight']} | {row['selected_by']} | {row['overlaps_G_raw']} | {row['same_package']} | {row['same_Leiden_cluster']} | {row['same_reference_service'] or 'null'} | {row['duplicate_text_pair']} |  |  |  |  |")
        lines.append("")
    lines += ["## 8. Go/no-go result", ""]
    for subject, result in go_no_go["subjects"].items():
        lines += [f"### {subject} technical criteria", "", "| criterion | observed | operator | expected | pass | evidence |", "| --- | --- | --- | --- | --- | --- |"]
        for name, item in result["technical_criteria"].items():
            lines.append(f"| {name} | `{item['observed']}` | `{item['operator']}` | `{item['expected']}` | {fmt(item['pass'])} | `{item['evidence_source']}` |")
        lines += [f"", f"Technical pass: **{result['technical_pass']}**.", "", f"Novelty: observed `{result['novelty']['observed']}` >= `{result['novelty']['threshold']}` -> **{result['novelty']['pass']}**.", "", f"Random baseline: structural observed `{result['random_baseline']['structural_overlap_observed']}` vs p95 `{result['random_baseline']['structural_overlap_p95']}`, strict pass **{result['random_baseline']['structural_overlap_strict_gt_p95']}**; same-reference observed `{result['random_baseline']['same_reference_observed']}` vs p95 `{result['random_baseline']['same_reference_p95']}`, strict pass **{result['random_baseline']['same_reference_strict_gt_p95']}**; subject pass **{result['random_baseline']['pass']}**.", ""]
    lines += ["### Cross-subject evidence", "", f"- All-subject novelty pass: **{go_no_go['cross_subject_evidence']['all_subjects_novelty_pass']}**.", f"- Random-baseline subject pass count: **{go_no_go['cross_subject_evidence']['random_baseline_subject_pass_count']}** / required **{go_no_go['cross_subject_evidence']['required_random_baseline_subject_pass_count']}**.", f"- Overall technical pass: **{go_no_go['overall_technical_pass']}**.", f"- Overall evidence pass: **{go_no_go['overall_evidence_pass']}**.", f"- Final status: **{go_no_go['overall_status']}**.", "", "## 9. Interpretation boundary", "", "GO means that the frozen semantic signal is technically valid and provides the preregistered evidence required to justify later Stage 3 integration. It does not prove improved decomposition quality. NO_GO_EVIDENCE would not justify changing the model or k. Graph overlap alone does not support a causal claim. No optimisation result, semantic objective run, or Stage 3 NSGA-II result was generated in Day 4.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "reports/stage3/go_no_go_status.json")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/stage3/day4_semantic_graph_report.md")
    args = parser.parse_args()
    args.output.write_text(render(load_json(args.input)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
