# Stage 1 Cross-Case Summary

## 1. Purpose of Stage 1

Stage 1 evaluates the current evidence pipeline before moving to NSGA-II and semantic embeddings. It checks whether Soot extraction, normalized CSV loading, graph construction, SSA-informed evidence, and Leiden clustering work across systems with different sizes and styles.

The main comparison is between `G_raw`, which uses structural evidence with `raw_weight`, and `G_ssa`, which adds SSA flow evidence with `g_ssa_weight`. Stage 1 does not claim that a decomposition is correct in a business sense. It builds a measured baseline and shows where SSA changes the graph and the Leiden partition.

## 2. Technical Implementation Summary

The implementation uses a Soot-based extractor for Java bytecode. The extractor writes normalized CSV files, mainly `class_nodes.csv`, `structural_dependencies.csv`, and `ssa_flow_edges.csv`. The Python pipeline loads these files and constructs `G_raw` and `G_ssa`.

`G_raw` is built from type and call dependency evidence. `G_ssa` keeps the raw graph and adds return-value and argument-passing flow evidence from SSA. Leiden is then run on both graphs. The pipeline produces graph metrics, partition metrics, raw-vs-SSA comparison metrics, and SSA impact tables. DayTrader adds reference-based calibration outputs. Xerces-J adds Stage 1 resolution and SSA lambda sensitivity outputs.

## 3. Experimental Workflow

The Stage 1 design uses three subjects. JPetStore is the small pipeline smoke test. It checks that extraction, CSV loading, graph construction, Leiden clustering, and comparison metrics run end to end.

DayTrader is the main calibration case. It has a reference mapping in the repository, so it supports reference-based metrics in addition to internal graph metrics. This makes it useful for choosing candidate settings under controlled sensitivity analysis.

Xerces-J is the larger transfer and scalability benchmark. It is not a business microservice ground-truth case. It is used as a larger technical remodularization benchmark to test whether the Stage 1 pipeline remains useful beyond small business examples.

## 4. Metric Design

Stage 1 uses several metric groups because no single value is enough to judge the result.

Scale and feasibility metrics include `class_count`, `raw_edge_count`, `g_ssa_edge_count`, and `ssa_flow_evidence_count`. They answer whether the pipeline works across small, medium, and large systems.

SSA graph impact metrics include `new_ssa_edge_count`, `new_ssa_edge_ratio`, and `ssa_weight_share` when available. They answer whether SSA adds meaningful evidence to the graph instead of only repeating raw structure.

Partition-change metrics include ARI raw-vs-SSA, NMI raw-vs-SSA, and `changed_partition_ratio` when available. They answer whether SSA changes the actual clustering result, not only the edge list.

Internal structural quality metrics include weighted modularity, internal edge weight ratio, and cross-cluster edge or weight ratios when available. They answer whether clusters are structurally compact and separated.

Granularity and balance metrics include `cluster_count`, `max_cluster_ratio`, `singleton_ratio`, and cluster size summaries when available. They detect over-fragmentation, oversized clusters, and hub aggregation risk.

Reference-based metrics are available for DayTrader. These include MoJoFM, pairwise F1, and reference coverage. DayTrader is used as the calibration case because it has a reference mapping with coverage 1.0. (source: `results/daytrader/00_pre_experiment/calibration/reference_mapping_validation.csv`)

Sensitivity metrics include the resolution sweep and the lambda / SSA-weight sweep. These test whether the conclusions are stable under parameter changes.

| metric | meaning | why it matters in Stage 1 | later-stage implication |
| --- | --- | --- | --- |
| `class_count` | number of extracted classes | checks scale and extraction feasibility | selects small, medium, and large validation cases |
| `new_ssa_edge_ratio` | share of `G_ssa` edges not in `G_raw` | checks whether SSA adds graph evidence | high values need SSA control |
| `ssa_weight_share` | share of `g_ssa_weight` from SSA flow | checks strength of SSA contribution | can become an objective or penalty term |
| ARI raw-vs-SSA | similarity between raw and SSA partitions | checks whether SSA changes boundaries | large change means SSA should be controlled |
| NMI raw-vs-SSA | information overlap between partitions | complements ARI for boundary change | helps compare partition stability |
| weighted modularity | graph-community structure quality | checks Leiden baseline strength | NSGA-II should not only optimize this |
| internal edge weight ratio | share of edge weight inside clusters | checks compactness and separation | supports coupling and cohesion objectives |
| `max_cluster_ratio` | share of classes in largest cluster | detects over-aggregation | motivates size-balance objective |
| `singleton_ratio` | share of singleton clusters | detects over-fragmentation | motivates granularity constraints |
| MoJoFM / pairwise F1 | agreement with reference mapping | supports DayTrader calibration | validates settings beyond internal metrics |

## 5. Cross-Subject Result Summary

| subject | role | class_count | raw_edge_count | g_ssa_edge_count | new_ssa_edge_count | new_ssa_edge_ratio | ssa_flow_evidence_count | raw_cluster_count | ssa_cluster_count | ARI raw-vs-SSA | NMI raw-vs-SSA | raw_weighted_modularity | ssa_weighted_modularity | raw_internal_edge_weight_ratio | ssa_internal_edge_weight_ratio | raw_max_cluster_ratio | ssa_max_cluster_ratio | raw_singleton_ratio | ssa_singleton_ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| jpetstore | smoke test / small business case | 24 | 53 | 60 | 7 | 0.116667 | 56 | 4 | 4 | 0.519342 | 0.680797 | 0.442070 | 0.387485 | 0.748148 | 0.663176 | 0.291667 | 0.333333 | 0.000000 | 0.000000 |
| daytrader | calibration / reference-based case | 121 | 267 | 275 | 8 | 0.029091 | 285 | 28 | 28 | 0.789757 | 0.913621 | 0.357424 | 0.348186 | 0.599927 | 0.566815 | 0.264463 | 0.297521 | 0.123967 | 0.123967 |
| xerces-j | larger transfer / scalability case | 814 | 3780 | 4148 | 368 | 0.088717 | 7668 | 31 | 30 | 0.533355 | 0.754347 | 0.661519 | 0.644268 | 0.791201 | 0.785251 | 0.144963 | 0.187961 | 0.013514 | 0.013514 |

Sources: `results/jpetstore/00_pre_experiment/comparison/metrics_summary.csv`; `results/daytrader/00_pre_experiment/comparison/metrics_summary.csv`; `results/xerces-j/stage1/graph_summary.csv`.

## 6. Result Comparison and Analysis

`G_ssa` changes the graph in all cases. JPetStore adds 7 SSA-added class-pair edges over 60 `G_ssa` edges. DayTrader adds 8 over 275. Xerces-J adds 368 over 4148. This suggests that SSA is not only a minor implementation detail, especially for Xerces-J. (source: `results/jpetstore/00_pre_experiment/comparison/metrics_summary.csv`; `results/daytrader/00_pre_experiment/comparison/metrics_summary.csv`; `results/xerces-j/stage1/graph_summary.csv`)

The partition change is subject-dependent. DayTrader is the most stable under the default setting, with ARI 0.789757 and NMI 0.913621. JPetStore has ARI 0.519342 and NMI 0.680797. Xerces-J has ARI 0.533355 and NMI 0.754347. This suggests that SSA changes boundaries more strongly in JPetStore and Xerces-J than in DayTrader under the current weighting setting. (source: `results/jpetstore/00_pre_experiment/comparison/metrics_summary.csv`; `results/daytrader/00_pre_experiment/comparison/metrics_summary.csv`; `results/xerces-j/stage1/graph_summary.csv`)

Under internal structural metrics, `G_raw` is stronger than `G_ssa` in all three default comparisons. Raw modularity is 0.442070 versus 0.387485 for JPetStore, 0.357424 versus 0.348186 for DayTrader, and 0.661519 versus 0.644268 for Xerces-J. Raw internal edge weight ratio is also higher in all three cases. This does not mean SSA is worse in general. It means that, in this stage, SSA changes boundaries while sometimes lowering internal structural compactness. (source: `results/jpetstore/00_pre_experiment/comparison/metrics_summary.csv`; `results/daytrader/00_pre_experiment/comparison/metrics_summary.csv`; `results/xerces-j/stage1/graph_summary.csv`)

The larger subject behaves differently from the smaller subjects. Xerces-J has 814 classes and 4148 `G_ssa` edges, while JPetStore has 24 classes and 60 `G_ssa` edges. Xerces-J still produces non-empty Leiden partitions and sensitivity tables, which indicates that the pipeline scales beyond small business systems for Stage 1 graph construction and Leiden analysis. (source: `results/xerces-j/stage1/graph_summary.csv`; `results/jpetstore/00_pre_experiment/comparison/metrics_summary.csv`)

## 7. Sensitivity Findings

The purpose of these sweeps is not to overfit the final setting on each subject, but to understand parameter behaviour and define safer fixed settings for later stages.

DayTrader is the main calibration subject because it has reference coverage 1.0. Its weight sweep has 35 rows. The top ranked row is raw-only: lambda 0.0, resolution 1.0, cluster_count 28, MoJoFM 65.740741, and pairwise F1 0.240366. The first non-raw candidate is lambda 2.0 at resolution 1.25, with cluster_count 31, MoJoFM 63.888889, and pairwise F1 0.223185. This supports using DayTrader for calibration, but it does not show that SSA is automatically better than raw structure. (source: `results/daytrader/00_pre_experiment/calibration/reference_mapping_validation.csv`; `results/daytrader/00_pre_experiment/calibration/weight_sweep_summary.csv`; `results/daytrader/00_pre_experiment/calibration/top_weight_settings.csv`)

### Why resolution sweep was used

Leiden resolution controls clustering granularity. A single default value may hide whether a result is stable or only a parameter accident. The sweep checks how cluster_count, modularity, internal edge weight ratio, max cluster ratio, and singleton ratio change when granularity changes. It also creates a fairer baseline for Stage 2, because NSGA-II should be compared not only with default Leiden but also with a tuned Leiden baseline.

In DayTrader's raw-only sweep rows, resolution 0.50 gives cluster_count 25, max_cluster_ratio 0.611570, weighted_modularity 0.136885, and internal_edge_weight_ratio 0.968579. At resolution 1.00, cluster_count is 28, max_cluster_ratio is 0.264463, weighted_modularity is 0.357424, and internal_edge_weight_ratio is 0.599927. At resolution 1.50, cluster_count is 33, max_cluster_ratio is 0.223140, weighted_modularity is 0.351148, and internal_edge_weight_ratio is 0.535623. This shows why a tuned Leiden baseline is more fair than a default-only baseline. (source: `results/daytrader/00_pre_experiment/calibration/weight_sweep_summary.csv`)

In Xerces-J, `G_raw` changes from 27 clusters at resolution 0.50 to 33 clusters at resolution 1.50. Its weighted modularity is 0.618650 at 0.50, 0.661519 at 1.00, and 0.658408 at 1.50. `G_ssa` changes from 27 clusters at 0.50 to 34 clusters at 1.50. Its weighted modularity is 0.597984 at 0.50, 0.644268 at 1.00, and 0.633797 at 1.50. (source: `results/xerces-j/stage1/resolution_sweep.csv`)

The Xerces-J resolution sweep records cluster_count, weighted_modularity, internal_edge_weight_ratio, ARI against default partition, NMI against default partition, and cluster size distribution. It does not record max_cluster_ratio or singleton_ratio in that sweep file, so those sweep-specific values are not computed. Default max/singleton ratios are available in `results/xerces-j/stage1/graph_summary.csv`.

JPetStore has no resolution sweep file in the inspected results. It was used only for smoke testing in this report. (source: inspected `results/jpetstore/`)

### Why lambda / SSA-weight sweep was used

Lambda controls how strongly SSA flow evidence contributes to `G_ssa`. Lambda 0.0 is the raw-structure baseline. Low lambda tests SSA as a weak behavioural signal. Higher lambda tests whether SSA begins to dominate graph boundaries. The purpose is not simply to find the highest modularity. It is to detect the useful range of SSA influence.

DayTrader shows why reference-based calibration matters. The raw-only top row has lambda 0.0, resolution 1.0, `ssa_weight_share` 0.000000, max_cluster_ratio 0.264463, singleton_ratio 0.123967, weighted_modularity 0.357424, internal_edge_weight_ratio 0.599927, MoJoFM 65.740741, and pairwise F1 0.240366. The first non-raw candidate has lambda 2.0, resolution 1.25, `ssa_weight_share` 0.384529, max_cluster_ratio 0.289256, singleton_ratio 0.123967, weighted_modularity 0.346829, internal_edge_weight_ratio 0.505959, MoJoFM 63.888889, and pairwise F1 0.223185. (source: `results/daytrader/00_pre_experiment/calibration/weight_sweep_summary.csv`; `results/daytrader/00_pre_experiment/calibration/top_weight_settings.csv`)

Xerces-J shows stronger partition movement under lambda. At lambda 0.0, changed_partition_ratio is 0.000000 and ARI raw-vs-SSA is 1.000000. At lambda 0.25, `ssa_weight_share` is 0.141909, changed_partition_ratio is 0.831695, and ARI is 0.701535. At lambda 1.0, `ssa_weight_share` is 0.398138, changed_partition_ratio is 0.893120, and ARI is 0.533355. At lambda 2.0, `ssa_weight_share` is 0.569526 and ARI is 0.478488. This suggests that SSA can reveal behaviour-related relations, but it may also strengthen technical hubs, merge unrelated classes, or reduce internal structural metrics if it is too strong. (source: `results/xerces-j/stage1/ssa_lambda_sweep.csv`)

Later stages should therefore treat SSA as a controlled evidence channel or objective, not as a fixed addition that is always better.

| subject | sweep | notable row | key result |
| --- | --- | --- | --- |
| daytrader | reference-based weight/resolution sweep | lambda 0.0, resolution 1.0 | MoJoFM 65.740741, pairwise F1 0.240366, cluster_count 28 |
| daytrader | reference-based weight/resolution sweep | lambda 2.0, resolution 1.25 | MoJoFM 63.888889, pairwise F1 0.223185, cluster_count 31 |
| xerces-j | resolution sweep on `G_raw` | resolution 1.25 | cluster_count 33, weighted_modularity 0.661672, internal_edge_weight_ratio 0.778835 |
| xerces-j | resolution sweep on `G_ssa` | resolution 1.0 | cluster_count 30, weighted_modularity 0.644268, internal_edge_weight_ratio 0.785251 |
| xerces-j | SSA lambda sweep | lambda 0.25, resolution 1.0 | `ssa_weight_share` 0.141909, changed_partition_ratio 0.831695, ARI 0.701535 |
| xerces-j | SSA lambda sweep | lambda 1.0, resolution 1.0 | `ssa_weight_share` 0.398138, changed_partition_ratio 0.893120, ARI 0.533355 |

Sources: `results/daytrader/00_pre_experiment/calibration/top_weight_settings.csv`; `results/daytrader/00_pre_experiment/calibration/weight_sweep_summary.csv`; `results/xerces-j/stage1/resolution_sweep.csv`; `results/xerces-j/stage1/ssa_lambda_sweep.csv`.

## 8. Key Findings

1. The extraction and graph construction pipeline is feasible across all three subjects. The extracted class counts are 24 for JPetStore, 121 for DayTrader, and 814 for Xerces-J. (source: `data/extracted/jpetstore/class_nodes.csv`; `data/extracted/daytrader/class_nodes.csv`; `data/extracted/xerces-j/class_nodes.csv`)

2. `G_ssa` introduces non-trivial additional evidence. The new SSA-added edge counts are 7 for JPetStore, 8 for DayTrader, and 368 for Xerces-J. (source: `results/jpetstore/00_pre_experiment/comparison/metrics_summary.csv`; `results/daytrader/00_pre_experiment/comparison/metrics_summary.csv`; `results/xerces-j/stage1/graph_summary.csv`)

3. SSA has a two-sided effect. It may add behaviour-related links, but it can also reduce internal structural metrics. Under the current default setting, `G_raw` has higher weighted modularity than `G_ssa` in all three subjects. (source: `results/jpetstore/00_pre_experiment/comparison/metrics_summary.csv`; `results/daytrader/00_pre_experiment/comparison/metrics_summary.csv`; `results/xerces-j/stage1/graph_summary.csv`)

4. Leiden is a strong Stage 1 baseline. It gives non-empty partitions across the three subjects and supports comparison, sweep, and reporting outputs. (source: `results/jpetstore/00_pre_experiment/clustering/leiden_raw_clusters.csv`; `results/daytrader/00_pre_experiment/clustering/leiden_raw_clusters.csv`; `results/xerces-j/stage1/leiden_raw_clusters.csv`)

5. Larger systems show stronger scale effects. Xerces-J has 814 classes, 4148 `G_ssa` edges, and default raw-vs-SSA ARI 0.533355. This suggests that SSA boundary effects need more control on larger technical systems. (source: `results/xerces-j/stage1/graph_summary.csv`)

6. Later stages should treat SSA as a controlled objective or evidence channel, not as automatically better than raw structural evidence. (source: `results/daytrader/00_pre_experiment/calibration/top_weight_settings.csv`; `results/xerces-j/stage1/ssa_lambda_sweep.csv`)

## 9. Implications for Stage 2 and Stage 3

Stage 2 should compare NSGA-II against both default Leiden and tuned Leiden. The first direct comparison can use structure-only NSGA-II, because that keeps the comparison against Leiden clean. The resolution sweep shows that Leiden results change with granularity, so a default-only comparison would be weak. Stage 2 should not only compare modularity, because Leiden is already strong on graph modularity.

Stage 2 should use multi-objective evaluation: structural quality, coupling, cluster-size balance, oversized-cluster reduction, and possibly SSA consistency. SSA may be kept as a controlled input at first, or later moved from fixed graph-weight addition into a separate objective or penalty term. This would let the search use SSA without assuming that more SSA weight is always better.

Stage 3 should then add semantic embeddings as another independent evidence channel, separate from structure and SSA. It should use ablation: structure-only, structure+SSA, and structure+SSA+semantic. This is safer than uncontrolled parameter search because each evidence channel can be measured.

DayTrader should remain the calibration case because it has reference coverage 1.0. Xerces-J should be used for transfer and scalability validation because it is a larger technical remodularization benchmark. Future runs should use fixed configurations and multi-seed robustness checks. (source for DayTrader coverage: `results/daytrader/00_pre_experiment/calibration/reference_mapping_validation.csv`)

## 10. Limitations

Stage 1 mainly uses internal structural metrics. These metrics can show compactness and partition change, but they cannot prove that a decomposition is correct.

Xerces-J is a technical remodularization benchmark. It is not a business microservice ground-truth case. Lack of external ground truth limits claims about correctness for JPetStore and Xerces-J.

Stage 1 does not prove that NSGA-II or semantic embeddings are better. It only prepares the evidence base, baseline partitions, and sensitivity observations needed for later stages.

## 11. Reproducibility Notes

The following scripts appear responsible for reproducing the current Stage 1 runs. Extraction commands are listed for completeness, but this report did not rerun Soot extraction.

| subject | extraction script | pre-experiment script | Stage 1 / sweep script |
| --- | --- | --- | --- |
| jpetstore | `bash scripts/extract_soot_jpetstore.sh` | `bash scripts/run_pre_jpetstore.sh` | `bash scripts/run_stage1_jpetstore.sh` |
| daytrader | `bash scripts/extract_soot_daytrader.sh` | `bash scripts/run_pre_daytrader.sh` | `bash scripts/run_stage1_daytrader.sh`; `bash scripts/run_daytrader_weight_sweep.sh` |
| xerces-j | `bash scripts/extract_soot_xerces_j.sh` | `bash scripts/run_pre_xerces_j.sh` | `bash scripts/run_stage1_xerces_j.sh` |

Sources: `scripts/extract_soot_jpetstore.sh`; `scripts/run_pre_jpetstore.sh`; `scripts/run_stage1_jpetstore.sh`; `scripts/extract_soot_daytrader.sh`; `scripts/run_pre_daytrader.sh`; `scripts/run_stage1_daytrader.sh`; `scripts/run_daytrader_weight_sweep.sh`; `scripts/extract_soot_xerces_j.sh`; `scripts/run_pre_xerces_j.sh`; `scripts/run_stage1_xerces_j.sh`.
