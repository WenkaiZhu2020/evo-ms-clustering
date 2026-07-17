# Stage 3 Day 4 Semantic Graph Report

## 1. Purpose and frozen method

The formal embeddings were frozen before Day 4. Each subject graph was built directly from saved `embeddings.npy` and `class_ids.csv` files. Each class selected its three highest true-cosine neighbours, exact ties used ascending lexicographic `class_id`, and OR symmetrisation produced one undirected weighted graph. `nearest_neighbors.csv`, structural graphs, Leiden partitions, reference labels, package diagnostics, and other diagnostic files were not graph inputs.

Duplicate representations receive no special treatment. Identical-text neighbours remain ordinary top-3 candidates. No post-hoc correction was applied after observing Xerces; representation-induced equivalence is quantified below.

The random baseline was frozen before semantic graph generation: uniform simple undirected G(n,m), N=1000, exact edge-count matching, uniform sampling without replacement from all unordered `i<j` pairs, no degree matching, and no edge weights. Seeds are 42000, 52000, and 62000 with `subject_seed_base + repetition_index` for repetitions 0..999. Quantiles use `numpy.quantile(method="higher")`; pass comparisons use strict `observed > p95`.

## 2. Provenance

| subject | source embedding hash | directed-selection hash | semantic-graph hash | nodes | k | tie-break | symmetrisation | graph construction commit |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| jpetstore | `0ae28938fef7b0c0295a5b1d33527708af7493b4f43d524436ffbf258db8802a` | `1caaa5d29c5a5c78312ca7e22be045646ac5332c9bb1ed9c686aa2360287fffa` | `8a51077ba7f852eae7a7fe9d8f5393bed9aef9eb8e5ca269fc01e6b96f2cb275` | 24 | 3 | `cosine_descending_then_class_id_lexicographic_ascending` | `OR` | `e87675550fc0adeb01faa173ce8dae4c4fd1e63d` |
| daytrader | `c7d2cbeec9d4c6ff5f9054b7d66563e98cffc6774771d5727030248299b7756e` | `4615d87137381b4b329864bee2ada3f9dab2fd94b75f6f8550c3fc97b23d93ed` | `699f3d1f4df32c44f9c30954e1a1cc144127d4ce7a9d8d99608478d562fa6590` | 53 | 3 | `cosine_descending_then_class_id_lexicographic_ascending` | `OR` | `e87675550fc0adeb01faa173ce8dae4c4fd1e63d` |
| xerces | `9504e21bb305a60cdfce58421b64240d1af893fd549b40b9441a00bf0fee8cb1` | `72dfa2ced5aa42a02ab16a8c424155e9c7713c967b6229480eaec546a6317d9f` | `ab6fc959bfe41ce46fbcfcbbec083a89b7db9d7d302b96877183ff3c8c2a3be9` | 814 | 3 | `cosine_descending_then_class_id_lexicographic_ascending` | `OR` | `e87675550fc0adeb01faa173ce8dae4c4fd1e63d` |

The formal graph source is `embeddings.npy + class_ids.csv`; the canonical weight format is `.17g`, with numerical zero written as `0`.

## 3. Graph summary

| subject | nodes | directed selections | edges | total weight | node coverage | isolated ratio | degree min/mean/median/max | components | largest component ratio | weight min/mean/median/max | mutual-selection ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| jpetstore | 24 | 72 | 48 | 32.617182 | 1.000000 | 0.000000 | 3/4.000000/4.000000/7 | 2 | 0.791667 | 0.515467/0.679525/0.686358/0.837673 | 0.500000 |
| daytrader | 53 | 159 | 111 | 63.847366 | 1.000000 | 0.000000 | 3/4.188679/4.000000/8 | 1 | 1.000000 | 0.242871/0.575201/0.579468/0.885107 | 0.432432 |
| xerces | 814 | 2442 | 1673 | 1225.551554 | 1.000000 | 0.000000 | 3/4.110565/4.000000/15 | 14 | 0.905405 | 0.274145/0.732547/0.733676/1.000000 | 0.459653 |

## 4. Novelty and alignment

| subject | semantic edges | G_raw overlap | structural overlap | novel edges | novel ratio | same package | cross package | same Leiden | Leiden eligible edges | same reference | reference eligible edges |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| jpetstore | 48 | 20 | 0.416667 | 28 | 0.583333 | 0.833333 | 0.166667 | 0.395833 | 48 | null | 0 |
| daytrader | 111 | 42 | 0.378378 | 69 | 0.621622 | 0.540541 | 0.459459 | 0.396396 | 111 | 0.450450 | 111 |
| xerces | 1673 | 619 | 0.369994 | 1054 | 0.630006 | 0.543933 | 0.456067 | 0.615063 | 1673 | null | 0 |

Structural and novelty ratios sum to 1 within floating-point precision. G_raw uses `evo_ms.graph.raw_graph_builder.build_raw_edges`, canonical undirected endpoints, self-loop removal, and merged duplicate structural pairs. SSA was not used.

## 5. Random baseline

| subject | N | runtime seconds | structural observed | structural p50 | structural p95 | strict > p95 | reference observed | reference p50 | reference p95 | strict > p95 | valid reference values | same-Leiden observed (diagnostic) |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: |
| jpetstore | 1000 | 0.030633 | 0.416667 | 0.187500 | 0.291667 | yes | null | null | null | no | 0 | 0.395833 |
| daytrader | 1000 | 0.070240 | 0.378378 | 0.117117 | 0.162162 | yes | 0.450450 | 0.126126 | 0.189189 | yes | 1000 | 0.396396 |
| xerces | 1000 | 12.108989 | 0.369994 | 0.011357 | 0.016139 | yes | null | null | null | no | 0 | 0.615063 |

JPetStore and Xerces have no expert reference-service mapping; their reference values and random reference distributions are null, and only structural overlap can pass. DayTrader uses its existing mapping with both endpoints required in the denominator. Same-Leiden is diagnostic only.

## 6. Representation-induced ties

| subject | duplicate groups | duplicate classes | identical-vector groups | identical-text directed selections | exact-cosine-1 selections | affected nodes | identical-text edges | edges involving duplicate-group classes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| jpetstore | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 (0.000000) |
| daytrader | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 (0.000000) |
| xerces | 11 | 55 | 11 | 165 | 90 | 55 | 99 | 106 (0.063359) |

These are representation-induced equivalence and tie statistics. No graph rule was changed because of them.

### Xerces duplicate groups

The following 11 duplicate-text/vector groups are expected under the frozen simple-name input contract; the classes were not deduplicated.

1. `org.apache.xerces.dom.ObjectFactory; org.apache.xerces.impl.dv.ObjectFactory; org.apache.xerces.parsers.ObjectFactory; org.apache.xerces.xinclude.ObjectFactory; org.apache.xml.serialize.ObjectFactory` — size 5; final intra-group edges 9; directed intra-group selections 15; top-k slots 15.
2. `org.apache.xerces.dom.ObjectFactory$ConfigurationError; org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError; org.apache.xerces.parsers.ObjectFactory$ConfigurationError; org.apache.xerces.xinclude.ObjectFactory$ConfigurationError; org.apache.xml.serialize.ObjectFactory$ConfigurationError` — size 5; final intra-group edges 9; directed intra-group selections 15; top-k slots 15.
3. `org.apache.xerces.dom.SecuritySupport; org.apache.xerces.impl.dv.SecuritySupport; org.apache.xerces.parsers.SecuritySupport; org.apache.xerces.xinclude.SecuritySupport; org.apache.xml.serialize.SecuritySupport` — size 5; final intra-group edges 9; directed intra-group selections 15; top-k slots 15.
4. `org.apache.xerces.dom.SecuritySupport$1; org.apache.xerces.impl.dv.SecuritySupport$1; org.apache.xerces.parsers.SecuritySupport$1; org.apache.xerces.xinclude.SecuritySupport$1; org.apache.xml.serialize.SecuritySupport$1` — size 5; final intra-group edges 9; directed intra-group selections 15; top-k slots 15.
5. `org.apache.xerces.dom.SecuritySupport$2; org.apache.xerces.impl.dv.SecuritySupport$2; org.apache.xerces.parsers.SecuritySupport$2; org.apache.xerces.xinclude.SecuritySupport$2; org.apache.xml.serialize.SecuritySupport$2` — size 5; final intra-group edges 9; directed intra-group selections 15; top-k slots 15.
6. `org.apache.xerces.dom.SecuritySupport$3; org.apache.xerces.impl.dv.SecuritySupport$3; org.apache.xerces.parsers.SecuritySupport$3; org.apache.xerces.xinclude.SecuritySupport$3; org.apache.xml.serialize.SecuritySupport$3` — size 5; final intra-group edges 9; directed intra-group selections 15; top-k slots 15.
7. `org.apache.xerces.dom.SecuritySupport$4; org.apache.xerces.impl.dv.SecuritySupport$4; org.apache.xerces.parsers.SecuritySupport$4; org.apache.xerces.xinclude.SecuritySupport$4; org.apache.xml.serialize.SecuritySupport$4` — size 5; final intra-group edges 9; directed intra-group selections 15; top-k slots 15.
8. `org.apache.xerces.dom.SecuritySupport$5; org.apache.xerces.impl.dv.SecuritySupport$5; org.apache.xerces.parsers.SecuritySupport$5; org.apache.xerces.xinclude.SecuritySupport$5; org.apache.xml.serialize.SecuritySupport$5` — size 5; final intra-group edges 9; directed intra-group selections 15; top-k slots 15.
9. `org.apache.xerces.dom.SecuritySupport$6; org.apache.xerces.impl.dv.SecuritySupport$6; org.apache.xerces.parsers.SecuritySupport$6; org.apache.xerces.xinclude.SecuritySupport$6; org.apache.xml.serialize.SecuritySupport$6` — size 5; final intra-group edges 9; directed intra-group selections 15; top-k slots 15.
10. `org.apache.xerces.dom.SecuritySupport$7; org.apache.xerces.impl.dv.SecuritySupport$7; org.apache.xerces.parsers.SecuritySupport$7; org.apache.xerces.xinclude.SecuritySupport$7; org.apache.xml.serialize.SecuritySupport$7` — size 5; final intra-group edges 9; directed intra-group selections 15; top-k slots 15.
11. `org.apache.xerces.dom.SecuritySupport$8; org.apache.xerces.impl.dv.SecuritySupport$8; org.apache.xerces.parsers.SecuritySupport$8; org.apache.xerces.xinclude.SecuritySupport$8; org.apache.xml.serialize.SecuritySupport$8` — size 5; final intra-group edges 9; directed intra-group selections 15; top-k slots 15.

## 7. Top-10 highest-weight edges for manual review

### jpetstore

| rank | class_id_a | class_name_a | class_id_b | class_name_b | weight | selected_by | G_raw | same package | same Leiden | same reference | duplicate text | plausible | questionable | unclear | reviewer note |
| ---: | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `org.mybatis.jpetstore.domain.Category` | `Category` | `org.mybatis.jpetstore.domain.Product` | `Product` | 0.83767322003103628 | both | false | true | true | null | false |  |  |  |  |
| 2 | `org.mybatis.jpetstore.mapper.CategoryMapper` | `CategoryMapper` | `org.mybatis.jpetstore.mapper.ProductMapper` | `ProductMapper` | 0.82084958065968483 | both | false | true | true | null | false |  |  |  |  |
| 3 | `org.mybatis.jpetstore.web.actions.CartActionBean` | `CartActionBean` | `org.mybatis.jpetstore.web.actions.CatalogActionBean` | `CatalogActionBean` | 0.81618301364302681 | both | false | true | false | null | false |  |  |  |  |
| 4 | `org.mybatis.jpetstore.domain.Cart` | `Cart` | `org.mybatis.jpetstore.domain.CartItem` | `CartItem` | 0.81196855193719097 | both | true | true | true | null | false |  |  |  |  |
| 5 | `org.mybatis.jpetstore.web.actions.CartActionBean` | `CartActionBean` | `org.mybatis.jpetstore.web.actions.OrderActionBean` | `OrderActionBean` | 0.77684882940959299 | both | true | true | false | null | false |  |  |  |  |
| 6 | `org.mybatis.jpetstore.mapper.AccountMapper` | `AccountMapper` | `org.mybatis.jpetstore.mapper.OrderMapper` | `OrderMapper` | 0.77582806454861453 | both | false | true | false | null | false |  |  |  |  |
| 7 | `org.mybatis.jpetstore.domain.CartItem` | `CartItem` | `org.mybatis.jpetstore.domain.LineItem` | `LineItem` | 0.77549063676445351 | both | true | true | false | null | false |  |  |  |  |
| 8 | `org.mybatis.jpetstore.mapper.OrderMapper` | `OrderMapper` | `org.mybatis.jpetstore.service.OrderService` | `OrderService` | 0.75916172732423637 | both | true | false | true | null | false |  |  |  |  |
| 9 | `org.mybatis.jpetstore.web.actions.AccountActionBean` | `AccountActionBean` | `org.mybatis.jpetstore.web.actions.OrderActionBean` | `OrderActionBean` | 0.75606106250451166 | both | true | true | true | null | false |  |  |  |  |
| 10 | `org.mybatis.jpetstore.mapper.LineItemMapper` | `LineItemMapper` | `org.mybatis.jpetstore.mapper.OrderMapper` | `OrderMapper` | 0.75601713603617771 | both | false | true | true | null | false |  |  |  |  |

### daytrader

| rank | class_id_a | class_name_a | class_id_b | class_name_b | weight | selected_by | G_raw | same package | same Leiden | same reference | duplicate text | plausible | questionable | unclear | reviewer note |
| ---: | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `com.ibm.websphere.samples.daytrader.TradeAction` | `TradeAction` | `com.ibm.websphere.samples.daytrader.TradeServices` | `TradeServices` | 0.88510737884310564 | both | true | true | false | true | false |  |  |  |  |
| 2 | `com.ibm.websphere.samples.daytrader.entities.AccountDataBean` | `AccountDataBean` | `com.ibm.websphere.samples.daytrader.entities.AccountProfileDataBean` | `AccountProfileDataBean` | 0.8735390664435394 | both | true | true | true | true | false |  |  |  |  |
| 3 | `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBLocal` | `TradeSLSBLocal` | `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBRemote` | `TradeSLSBRemote` | 0.85053413029234015 | both | false | true | false | true | false |  |  |  |  |
| 4 | `com.ibm.websphere.samples.daytrader.ejb3.DTBroker3MDB` | `DTBroker3MDB` | `com.ibm.websphere.samples.daytrader.ejb3.DTStreamer3MDB` | `DTStreamer3MDB` | 0.83183289783766978 | both | false | true | true | false | false |  |  |  |  |
| 5 | `com.ibm.websphere.samples.daytrader.util.KeyBlock` | `KeyBlock` | `com.ibm.websphere.samples.daytrader.util.KeyBlock$KeyBlockIterator` | `KeyBlock$KeyBlockIterator` | 0.81327601661828264 | both | true | true | true | true | false |  |  |  |  |
| 6 | `com.ibm.websphere.samples.daytrader.TradeAction` | `TradeAction` | `com.ibm.websphere.samples.daytrader.direct.TradeDirect` | `TradeDirect` | 0.80676137116021041 | both | true | false | true | false | false |  |  |  |  |
| 7 | `com.ibm.websphere.samples.daytrader.TradeServices` | `TradeServices` | `com.ibm.websphere.samples.daytrader.direct.TradeDirect` | `TradeDirect` | 0.80395515982694621 | both | true | false | false | false | false |  |  |  |  |
| 8 | `com.ibm.websphere.samples.daytrader.web.websocket.JsonDecoder` | `JsonDecoder` | `com.ibm.websphere.samples.daytrader.web.websocket.JsonEncoder` | `JsonEncoder` | 0.78278246146333363 | both | false | true | true | true | false |  |  |  |  |
| 9 | `com.ibm.websphere.samples.daytrader.entities.AccountDataBean` | `AccountDataBean` | `com.ibm.websphere.samples.daytrader.entities.OrderDataBean` | `OrderDataBean` | 0.77922262289217936 | both | true | true | true | false | false |  |  |  |  |
| 10 | `com.ibm.websphere.samples.daytrader.web.websocket.ActionDecoder` | `ActionDecoder` | `com.ibm.websphere.samples.daytrader.web.websocket.JsonDecoder` | `JsonDecoder` | 0.77577578285854487 | both | false | true | false | true | false |  |  |  |  |

### xerces

| rank | class_id_a | class_name_a | class_id_b | class_name_b | weight | selected_by | G_raw | same package | same Leiden | same reference | duplicate text | plausible | questionable | unclear | reviewer note |
| ---: | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `org.apache.xerces.dom.SecuritySupport` | `SecuritySupport` | `org.apache.xerces.impl.dv.SecuritySupport` | `SecuritySupport` | 1 | both | false | false | false | null | true |  |  |  |  |
| 2 | `org.apache.xerces.dom.SecuritySupport` | `SecuritySupport` | `org.apache.xerces.parsers.SecuritySupport` | `SecuritySupport` | 1 | both | false | false | false | null | true |  |  |  |  |
| 3 | `org.apache.xerces.dom.SecuritySupport` | `SecuritySupport` | `org.apache.xerces.xinclude.SecuritySupport` | `SecuritySupport` | 1 | both | false | false | false | null | true |  |  |  |  |
| 4 | `org.apache.xerces.dom.SecuritySupport` | `SecuritySupport` | `org.apache.xml.serialize.SecuritySupport` | `SecuritySupport` | 1 | b | false | false | false | null | true |  |  |  |  |
| 5 | `org.apache.xerces.dom.SecuritySupport$1` | `SecuritySupport$1` | `org.apache.xerces.impl.dv.SecuritySupport$1` | `SecuritySupport$1` | 1 | both | false | false | false | null | true |  |  |  |  |
| 6 | `org.apache.xerces.dom.SecuritySupport$1` | `SecuritySupport$1` | `org.apache.xerces.parsers.SecuritySupport$1` | `SecuritySupport$1` | 1 | both | false | false | false | null | true |  |  |  |  |
| 7 | `org.apache.xerces.dom.SecuritySupport$1` | `SecuritySupport$1` | `org.apache.xerces.xinclude.SecuritySupport$1` | `SecuritySupport$1` | 1 | both | false | false | false | null | true |  |  |  |  |
| 8 | `org.apache.xerces.dom.SecuritySupport$1` | `SecuritySupport$1` | `org.apache.xml.serialize.SecuritySupport$1` | `SecuritySupport$1` | 1 | b | false | false | false | null | true |  |  |  |  |
| 9 | `org.apache.xerces.dom.SecuritySupport$3` | `SecuritySupport$3` | `org.apache.xerces.impl.dv.SecuritySupport$3` | `SecuritySupport$3` | 1 | both | false | false | false | null | true |  |  |  |  |
| 10 | `org.apache.xerces.dom.SecuritySupport$3` | `SecuritySupport$3` | `org.apache.xerces.parsers.SecuritySupport$3` | `SecuritySupport$3` | 1 | both | false | false | false | null | true |  |  |  |  |

## 8. Go/no-go result

### jpetstore technical criteria

| criterion | observed | operator | expected | pass | evidence |
| --- | --- | --- | --- | --- | --- |
| embedding_coverage | `1.0` | `==` | `1.0` | yes | `results/jpetstore/04_stage3_semantic/embeddings/class_ids.csv` |
| embedding_nan_count | `0` | `==` | `0` | yes | `results/jpetstore/04_stage3_semantic/embeddings/embedding_metadata.json` |
| embedding_inf_count | `0` | `==` | `0` | yes | `results/jpetstore/04_stage3_semantic/embeddings/embedding_metadata.json` |
| embedding_all_zero_vector_count | `0` | `==` | `0` | yes | `results/jpetstore/04_stage3_semantic/embeddings/embedding_metadata.json` |
| semantic_graph_total_weight | `32.61718195030124` | `>` | `0.0` | yes | `results/jpetstore/04_stage3_semantic/graph/graph_metadata.json` |
| node_coverage | `1.0` | `>=` | `0.95` | yes | `results/jpetstore/04_stage3_semantic/diagnostics/graph_structure.json` |
| isolated_node_ratio | `0.0` | `<=` | `0.05` | yes | `results/jpetstore/04_stage3_semantic/diagnostics/graph_structure.json` |
| class_scope_exact_match | `True` | `==` | `True` | yes | `results/jpetstore/04_stage3_semantic/embeddings/class_ids.csv` |
| graph_source_embedding_hash_match | `0ae28938fef7b0c0295a5b1d33527708af7493b4f43d524436ffbf258db8802a` | `==` | `0ae28938fef7b0c0295a5b1d33527708af7493b4f43d524436ffbf258db8802a` | yes | `results/jpetstore/04_stage3_semantic/graph/graph_metadata.json` |
| graph_construction_provenance_test | `True` | `==` | `True` | yes | `tests/test_stage3_semantic_graph.py` |
| graph_construction_excludes_diagnostic_and_structural_data | `embeddings.npy + class_ids.csv only` | `==` | `formal source contract` | yes | `results/jpetstore/04_stage3_semantic/graph/graph_metadata.json` |
| no_self_loop_or_duplicate_semantic_edge | `{'self_loops': 0, 'duplicate_edges': 0}` | `==` | `{'self_loops': 0, 'duplicate_edges': 0}` | yes | `results/jpetstore/04_stage3_semantic/graph/semantic_edges.csv` |

Technical pass: **True**.

Novelty: observed `0.5833333333333334` >= `0.2` -> **True**.

Random baseline: structural observed `0.4166666666666667` vs p95 `0.2916666666666667`, strict pass **True**; same-reference observed `None` vs p95 `None`, strict pass **False**; subject pass **True**.

### daytrader technical criteria

| criterion | observed | operator | expected | pass | evidence |
| --- | --- | --- | --- | --- | --- |
| embedding_coverage | `1.0` | `==` | `1.0` | yes | `results/daytrader/04_stage3_semantic/embeddings/class_ids.csv` |
| embedding_nan_count | `0` | `==` | `0` | yes | `results/daytrader/04_stage3_semantic/embeddings/embedding_metadata.json` |
| embedding_inf_count | `0` | `==` | `0` | yes | `results/daytrader/04_stage3_semantic/embeddings/embedding_metadata.json` |
| embedding_all_zero_vector_count | `0` | `==` | `0` | yes | `results/daytrader/04_stage3_semantic/embeddings/embedding_metadata.json` |
| semantic_graph_total_weight | `63.84736648489945` | `>` | `0.0` | yes | `results/daytrader/04_stage3_semantic/graph/graph_metadata.json` |
| node_coverage | `1.0` | `>=` | `0.95` | yes | `results/daytrader/04_stage3_semantic/diagnostics/graph_structure.json` |
| isolated_node_ratio | `0.0` | `<=` | `0.05` | yes | `results/daytrader/04_stage3_semantic/diagnostics/graph_structure.json` |
| class_scope_exact_match | `True` | `==` | `True` | yes | `results/daytrader/04_stage3_semantic/embeddings/class_ids.csv` |
| graph_source_embedding_hash_match | `c7d2cbeec9d4c6ff5f9054b7d66563e98cffc6774771d5727030248299b7756e` | `==` | `c7d2cbeec9d4c6ff5f9054b7d66563e98cffc6774771d5727030248299b7756e` | yes | `results/daytrader/04_stage3_semantic/graph/graph_metadata.json` |
| graph_construction_provenance_test | `True` | `==` | `True` | yes | `tests/test_stage3_semantic_graph.py` |
| graph_construction_excludes_diagnostic_and_structural_data | `embeddings.npy + class_ids.csv only` | `==` | `formal source contract` | yes | `results/daytrader/04_stage3_semantic/graph/graph_metadata.json` |
| no_self_loop_or_duplicate_semantic_edge | `{'self_loops': 0, 'duplicate_edges': 0}` | `==` | `{'self_loops': 0, 'duplicate_edges': 0}` | yes | `results/daytrader/04_stage3_semantic/graph/semantic_edges.csv` |

Technical pass: **True**.

Novelty: observed `0.6216216216216216` >= `0.2` -> **True**.

Random baseline: structural observed `0.3783783783783784` vs p95 `0.16216216216216217`, strict pass **True**; same-reference observed `0.45045045045045046` vs p95 `0.1891891891891892`, strict pass **True**; subject pass **True**.

### xerces technical criteria

| criterion | observed | operator | expected | pass | evidence |
| --- | --- | --- | --- | --- | --- |
| embedding_coverage | `1.0` | `==` | `1.0` | yes | `results/xerces/04_stage3_semantic/embeddings/class_ids.csv` |
| embedding_nan_count | `0` | `==` | `0` | yes | `results/xerces/04_stage3_semantic/embeddings/embedding_metadata.json` |
| embedding_inf_count | `0` | `==` | `0` | yes | `results/xerces/04_stage3_semantic/embeddings/embedding_metadata.json` |
| embedding_all_zero_vector_count | `0` | `==` | `0` | yes | `results/xerces/04_stage3_semantic/embeddings/embedding_metadata.json` |
| semantic_graph_total_weight | `1225.551553681053` | `>` | `0.0` | yes | `results/xerces/04_stage3_semantic/graph/graph_metadata.json` |
| node_coverage | `1.0` | `>=` | `0.95` | yes | `results/xerces/04_stage3_semantic/diagnostics/graph_structure.json` |
| isolated_node_ratio | `0.0` | `<=` | `0.05` | yes | `results/xerces/04_stage3_semantic/diagnostics/graph_structure.json` |
| class_scope_exact_match | `True` | `==` | `True` | yes | `results/xerces/04_stage3_semantic/embeddings/class_ids.csv` |
| graph_source_embedding_hash_match | `9504e21bb305a60cdfce58421b64240d1af893fd549b40b9441a00bf0fee8cb1` | `==` | `9504e21bb305a60cdfce58421b64240d1af893fd549b40b9441a00bf0fee8cb1` | yes | `results/xerces/04_stage3_semantic/graph/graph_metadata.json` |
| graph_construction_provenance_test | `True` | `==` | `True` | yes | `tests/test_stage3_semantic_graph.py` |
| graph_construction_excludes_diagnostic_and_structural_data | `embeddings.npy + class_ids.csv only` | `==` | `formal source contract` | yes | `results/xerces/04_stage3_semantic/graph/graph_metadata.json` |
| no_self_loop_or_duplicate_semantic_edge | `{'self_loops': 0, 'duplicate_edges': 0}` | `==` | `{'self_loops': 0, 'duplicate_edges': 0}` | yes | `results/xerces/04_stage3_semantic/graph/semantic_edges.csv` |

Technical pass: **True**.

Novelty: observed `0.630005977286312` >= `0.2` -> **True**.

Random baseline: structural observed `0.369994022713688` vs p95 `0.016138673042438732`, strict pass **True**; same-reference observed `None` vs p95 `None`, strict pass **False**; subject pass **True**.

### Cross-subject evidence

- All-subject novelty pass: **True**.
- Random-baseline subject pass count: **3** / required **2**.
- Overall technical pass: **True**.
- Overall evidence pass: **True**.
- Final status: **GO**.

## 9. Interpretation boundary

GO means that the frozen semantic signal is technically valid and provides the preregistered evidence required to justify later Stage 3 integration. It does not prove improved decomposition quality. NO_GO_EVIDENCE would not justify changing the model or k. Graph overlap alone does not support a causal claim. No optimisation result, semantic objective run, or Stage 3 NSGA-II result was generated in Day 4.
