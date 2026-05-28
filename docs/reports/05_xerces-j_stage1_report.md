# Xerces-J Stage 1 Analysis

## Extraction Recap

- Subject: `xerces-j`
- Source path: `data/raw_projects/xerces-j`
- Normalized extraction path: `data/extracted/xerces-j/`
- Included application packages: `org.apache.xerces`, `org.apache.xml`
- Excluded packages/classes: tests, samples, tools, `org.apache.html`, and `org.w3c.dom` API surface
- Extracted class count: 814
- SSA flow evidence rows: 7668

## Graph Scale

Xerces-J is substantially larger than the earlier smoke/calibration subjects. The current run contains 814 classes, 3780 G_raw edges, and 4148 G_ssa edges. That makes it useful as a larger technical remodularization benchmark for checking whether the Stage 1 pipeline remains stable beyond small application examples.

## G_raw vs G_ssa

| metric                         | value    |
| ------------------------------ | -------- |
| class_count                    | 814      |
| raw_edge_count                 | 3780     |
| g_ssa_edge_count               | 4148     |
| new_ssa_edge_count             | 368      |
| new_ssa_edge_ratio             | 0.088717 |
| ssa_weight_share               | 0.398138 |
| raw_cluster_count              | 31       |
| ssa_cluster_count              | 30       |
| ari_raw_vs_ssa                 | 0.533355 |
| nmi_raw_vs_ssa                 | 0.754347 |
| raw_weighted_modularity        | 0.661519 |
| ssa_weighted_modularity        | 0.644268 |
| raw_internal_edge_weight_ratio | 0.791201 |
| ssa_internal_edge_weight_ratio | 0.785251 |

The SSA layer adds unique class-pair edges and changes the partition more visibly than in DayTrader. The cluster count decreases by one at the default setting, but ARI/NMI show that this is not just a label change.

## Leiden Comparison

| metric                       | raw        | ssa        | delta     |
| ---------------------------- | ---------- | ---------- | --------- |
| cluster_count                | 31.000000  | 30.000000  | -1.000000 |
| modularity                   | 0.661519   | 0.644268   | -0.017251 |
| average_cluster_size         | 26.258065  | 27.133333  | 0.875269  |
| max_cluster_size             | 118.000000 | 153.000000 | 35.000000 |
| min_cluster_size             | 1.000000   | 1.000000   | 0.000000  |
| max_cluster_ratio            | 0.144963   | 0.187961   | 0.042998  |
| singleton_ratio              | 0.013514   | 0.013514   | 0.000000  |
| internal_external_edge_ratio | 3.789285   | 3.656593   | -0.132693 |
| internal_edge_weight_ratio   | 0.791201   | 0.785251   | -0.005950 |

## Resolution Sweep

This sweep uses the same resolution grid currently used by the DayTrader calibration runner.

| subject  | graph_type | resolution | cluster_count | weighted_modularity | internal_edge_weight_ratio | ari_vs_default_partition | nmi_vs_default_partition | cluster_size_distribution                                                                                                                                                           |
| -------- | ---------- | ---------- | ------------- | ------------------- | -------------------------- | ------------------------ | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| xerces-j | G_raw      | 0.500000   | 27            | 0.618650            | 0.906283                   | 0.493034                 | 0.807733                 | {"1": 11, "100": 1, "11": 3, "16": 1, "173": 1, "2": 1, "23": 1, "298": 1, "35": 1, "37": 1, "4": 1, "5": 1, "6": 1, "62": 1, "9": 1}                                               |
| xerces-j | G_raw      | 0.750000   | 28            | 0.653313            | 0.819871                   | 0.612411                 | 0.825150                 | {"1": 11, "101": 1, "11": 3, "133": 1, "145": 1, "15": 1, "16": 1, "167": 1, "2": 1, "23": 1, "34": 1, "4": 1, "5": 1, "54": 1, "62": 1, "9": 1}                                    |
| xerces-j | G_raw      | 1.000000   | 31            | 0.661519            | 0.791201                   | 1.000000                 | 1.000000                 | {"1": 11, "100": 1, "11": 4, "112": 1, "118": 1, "16": 1, "2": 1, "23": 1, "34": 1, "4": 1, "46": 2, "5": 1, "55": 1, "56": 1, "62": 1, "71": 1, "9": 1}                            |
| xerces-j | G_raw      | 1.250000   | 33            | 0.661672            | 0.778835                   | 0.777664                 | 0.879554                 | {"1": 11, "100": 1, "11": 3, "119": 1, "14": 1, "16": 1, "2": 1, "23": 1, "25": 2, "32": 1, "35": 1, "36": 1, "4": 1, "45": 1, "46": 1, "5": 1, "70": 1, "78": 1, "86": 1, "9": 1}  |
| xerces-j | G_raw      | 1.500000   | 33            | 0.658408            | 0.764055                   | 0.670320                 | 0.843866                 | {"1": 11, "11": 3, "115": 1, "15": 1, "16": 1, "2": 1, "23": 1, "24": 1, "30": 1, "33": 1, "34": 1, "35": 1, "4": 1, "43": 1, "46": 1, "5": 1, "73": 1, "84": 2, "9": 1, "95": 1}   |
| xerces-j | G_ssa      | 0.500000   | 27            | 0.597984            | 0.916284                   | 0.495243                 | 0.795274                 | {"1": 11, "10": 2, "104": 1, "11": 2, "15": 1, "17": 1, "2": 1, "208": 1, "23": 1, "306": 1, "33": 1, "35": 1, "4": 1, "5": 1, "9": 1}                                              |
| xerces-j | G_ssa      | 0.750000   | 27            | 0.621497            | 0.873639                   | 0.513113                 | 0.782011                 | {"1": 11, "10": 1, "108": 1, "11": 2, "146": 1, "17": 1, "2": 1, "23": 1, "236": 1, "33": 1, "35": 1, "4": 1, "5": 1, "64": 1, "89": 1, "9": 1}                                     |
| xerces-j | G_ssa      | 1.000000   | 30            | 0.644268            | 0.785251                   | 1.000000                 | 1.000000                 | {"1": 11, "104": 1, "11": 3, "112": 1, "15": 1, "153": 1, "17": 1, "2": 1, "23": 1, "31": 1, "32": 1, "35": 1, "4": 1, "44": 1, "5": 1, "88": 1, "9": 1, "96": 1}                   |
| xerces-j | G_ssa      | 1.250000   | 32            | 0.639359            | 0.749200                   | 0.755980                 | 0.880338                 | {"1": 11, "105": 1, "11": 3, "111": 1, "122": 1, "15": 1, "17": 1, "2": 1, "22": 1, "23": 1, "26": 1, "32": 1, "35": 1, "4": 1, "43": 1, "49": 1, "5": 1, "64": 1, "86": 1, "9": 1} |
| xerces-j | G_ssa      | 1.500000   | 34            | 0.633797            | 0.739213                   | 0.731345                 | 0.885712                 | {"1": 11, "104": 1, "11": 3, "15": 1, "17": 1, "18": 1, "2": 1, "23": 2, "31": 1, "32": 1, "35": 1, "4": 1, "5": 1, "59": 1, "6": 1, "66": 2, "71": 1, "87": 1, "9": 1, "97": 1}    |

## SSA Weight / Lambda Sweep

`changed_partition_ratio` is the fraction of classes whose same-cluster membership set changes relative to the G_raw Leiden partition; it avoids treating cluster label renumbering as movement.

| subject  | ssa_lambda | resolution | raw_edge_count | g_ssa_edge_count | new_ssa_edge_count | ssa_weight_share | cluster_count | max_cluster_ratio | singleton_ratio | weighted_modularity | internal_edge_weight_ratio | changed_partition_count | changed_partition_ratio | ari_raw_vs_ssa | nmi_raw_vs_ssa | cluster_size_distribution                                                                                                                                         |
| -------- | ---------- | ---------- | -------------- | ---------------- | ------------------ | ---------------- | ------------- | ----------------- | --------------- | ------------------- | -------------------------- | ----------------------- | ----------------------- | -------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| xerces-j | 0.000000   | 1.000000   | 3780           | 3780             | 0                  | 0.000000         | 31            | 0.144963          | 0.013514        | 0.661519            | 0.791201                   | 0                       | 0.000000                | 1.000000       | 1.000000       | {"1": 11, "100": 1, "11": 4, "112": 1, "118": 1, "16": 1, "2": 1, "23": 1, "34": 1, "4": 1, "46": 2, "5": 1, "55": 1, "56": 1, "62": 1, "71": 1, "9": 1}          |
| xerces-j | 0.250000   | 1.000000   | 3780           | 4148             | 368                | 0.141909         | 29            | 0.192875          | 0.013514        | 0.652311            | 0.792226                   | 677                     | 0.831695                | 0.701535       | 0.862387       | {"1": 11, "101": 1, "11": 3, "118": 1, "157": 1, "16": 1, "2": 1, "23": 1, "34": 1, "35": 1, "4": 1, "5": 1, "54": 1, "55": 1, "63": 1, "9": 1, "94": 1}          |
| xerces-j | 0.500000   | 1.000000   | 3780           | 4148             | 368                | 0.248547         | 29            | 0.195332          | 0.013514        | 0.647901            | 0.794963                   | 727                     | 0.893120                | 0.677905       | 0.841655       | {"1": 11, "104": 1, "106": 1, "11": 3, "117": 1, "159": 1, "17": 1, "2": 1, "23": 1, "26": 1, "35": 1, "4": 1, "44": 1, "5": 1, "54": 1, "65": 1, "9": 1}         |
| xerces-j | 1.000000   | 1.000000   | 3780           | 4148             | 368                | 0.398138         | 30            | 0.187961          | 0.013514        | 0.644268            | 0.785251                   | 727                     | 0.893120                | 0.533355       | 0.754347       | {"1": 11, "104": 1, "11": 3, "112": 1, "15": 1, "153": 1, "17": 1, "2": 1, "23": 1, "31": 1, "32": 1, "35": 1, "4": 1, "44": 1, "5": 1, "88": 1, "9": 1, "96": 1} |
| xerces-j | 2.000000   | 1.000000   | 3780           | 4148             | 368                | 0.569526         | 29            | 0.178133          | 0.013514        | 0.645935            | 0.795984                   | 727                     | 0.893120                | 0.478488       | 0.713425       | {"1": 11, "11": 3, "114": 1, "125": 1, "145": 1, "15": 1, "17": 1, "2": 1, "23": 1, "33": 1, "35": 1, "4": 1, "5": 1, "58": 1, "88": 1, "9": 1, "97": 1}          |
| xerces-j | 3.000000   | 1.000000   | 3780           | 4148             | 368                | 0.664939         | 30            | 0.120393          | 0.013514        | 0.647479            | 0.779876                   | 738                     | 0.906634                | 0.436266       | 0.679209       | {"1": 11, "11": 2, "15": 1, "17": 1, "2": 1, "23": 1, "33": 1, "35": 1, "4": 1, "5": 1, "6": 1, "64": 1, "89": 1, "9": 1, "92": 1, "96": 2, "97": 1, "98": 1}     |
| xerces-j | 4.000000   | 1.000000   | 3780           | 4148             | 368                | 0.725730         | 31            | 0.181818          | 0.013514        | 0.653576            | 0.798408                   | 727                     | 0.893120                | 0.451063       | 0.701357       | {"1": 11, "101": 1, "11": 3, "112": 1, "120": 1, "148": 1, "15": 3, "2": 1, "22": 1, "23": 1, "35": 1, "4": 1, "5": 1, "6": 1, "60": 1, "78": 1, "9": 1}          |

## Interpretation

At the default setting, G_ssa has 368 new class-pair edges and an SSA weight share of 0.398138. The raw-vs-SSA ARI is 0.533355 and NMI is 0.754347, so SSA materially changes the partition. The internal edge weight ratio remains close between G_raw and G_ssa, which suggests that SSA changes the boundary structure without completely collapsing the graph into one broad cluster.

## Comparison With DayTrader Style Findings

DayTrader's Stage 1 calibration style combines a raw-vs-SSA comparison with a lambda/resolution sweep. In the current DayTrader output, the default run has 121 classes, 267 G_raw edges, 275 G_ssa edges, 8 new SSA edges, SSA weight share 0.238029, ARI 0.789757, and NMI 0.913621.

Xerces-J is larger and more sensitive: 814 classes, 3780 G_raw edges, 4148 G_ssa edges, 368 new SSA edges, SSA weight share 0.398138, ARI 0.533355, and NMI 0.754347.

The DayTrader sweep is reference-guided; its top row currently reports lambda 0.0 at resolution 1.0 with MoJoFM 65.740741 and pairwise F1 0.240366. The first non-raw candidate in that ranked table reports lambda 2.0 at resolution 1.25 with MoJoFM 63.888889 and pairwise F1 0.223185. Xerces-J has no equivalent business reference mapping here, so this report does not rank lambda settings as final.

## Implication For Later NSGA-II Experiment

Xerces-J is useful later as a technical remodularization benchmark because it is large enough to stress graph construction, Leiden stability, and objective trade-offs. It should not be used as business microservice ground truth: no reference service mapping was computed here, and no NSGA-II, semantics, or embedding objective was implemented in this Stage 1 run.

## Limitations

- Xerces-J is a parser/XML infrastructure codebase, not a business microservice decomposition case.
- Reference-based metrics are not computed because no validated Xerces-J service mapping exists in this repository.
- The extraction used staged Java 8-compatible bytecode for `org.apache.xerces` and `org.apache.xml` under Java 17.
- `org.w3c.dom` is treated as external API/JDK/library surface for this run.

## Reproduction Commands

```bash
bash scripts/run_stage1_xerces_j.sh
PYTHONPATH=src .venv/bin/python -m pytest
```

Generated outputs are under `results/xerces-j/stage1/`.
