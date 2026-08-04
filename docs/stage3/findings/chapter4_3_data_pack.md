# Chapter 4.3 data pack — final Stage 3 Declaration + Method Body

**Scope.** Branch `stage3-Declaration+Method-Body`, audited HEAD `c0cedb74b5b2fa61867888e24c8c68b3fc013405`; final experiment `stage3_declaration_method_body`, representation `declaration_method_body_v1`. This is a descriptive, data-first report. It reads accepted Stage 2 and Stage 3 seeds 0–29, performs only deterministic calculations on frozen files, and does not regenerate semantic text, embeddings, graphs, optimizer runs, or accepted scientific artifacts.

**Notation.** Unless a table says otherwise, Δ = Stage 3 − Stage 2; std is sample standard deviation; IQR = Q3 − Q1. `Direct read` means the value is serialized in the cited artifact. `Recomputed` means the formula and frozen inputs are stated at table level and apply to every value in that table. Displayed recomputed floats use 17 significant digits.

## 1. Artifact and completeness audit

> **Value provenance.** `results/stage2/subjects/<subject>/nsga/robustness_final_30seeds/ and results/stage3/subjects/<subject>/declaration_method_body/; validation/formal_runs/validation_per_seed.csv` — **direct filesystem/read plus validation recomputation**. A valid front requires the saved validation flag, a non-empty feasible front, finite objectives, coupling/fsem in [0,1], and nonnegative cohesion/imbalance.

| Subject | Expected | Stage 2 found | Stage 3 found | Paired | Missing/extra | Valid fronts | Fallbacks | Infeasible runs | Out-of-range rows | Four-way class universe |
|---|---|---|---|---|---|---|---|---|---|---|
| JPetStore | 0–29 | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29] | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29] | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29] | S2 missing=[], extra=[]; S3 missing=[], extra=[] | S2 30/30; S3 30/30 | S2=0; S3=0 | S2=0; S3=0 | S2=0; S3=0 | True (24 IDs) |
| DayTrader | 0–29 | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29] | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29] | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29] | S2 missing=[], extra=[]; S3 missing=[], extra=[] | S2 30/30; S3 30/30 | S2=0; S3=0 | S2=0; S3=0 | S2=0; S3=0 | True (53 IDs) |
| Xerces-J | 0–29 | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29] | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29] | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29] | S2 missing=[], extra=[]; S3 missing=[], extra=[] | S2 30/30; S3 30/30 | S2=0; S3=0 | S2=0; S3=0 | S2=0; S3=0 | True (814 IDs) |

The Stage 3 structural input is the same `data/extracted/<subject>/class_nodes.csv` used by Stage 2. Four-way equality was recomputed between that structural set, final semantic-text IDs, semantic-graph `class_mapping.csv`, and actual graph endpoints. All sets are exactly equal for all subjects.

## 2. Experimental setup

> **Value provenance.** `configs/experiments/05_stage3_declaration_method_body.yml` — **direct read**. Executable selector/repair details are cross-checked against `src/evo_ms/optimization/selection.py`, `problem.py`, and `stage3_problem.py`.

| Item | Frozen value |
|---|---|
| Experiment / representation | `stage3_declaration_method_body` / `declaration_method_body_v1` |
| Display name | Final Stage 3 Declaration + Method Body Semantic Extension |
| Subjects / classes | JPetStore 24; DayTrader 53; Xerces-J 814 |
| Semantic input count | 24; 53; 814; one row per structural class |
| Embedding | `nomic-ai/nomic-embed-code`, revision `9a0457648f060c4279d4a3982d2d27a4df6fac59`, 3584 dimensions, packaged last-token pooling and packaged L2 normalization; no query prompt |
| Tokenizer | same model/revision; maximum 32768; `truncation=false`; body evidence independently capped at 256 tokens |
| Similarity / graph | true cosine on saved float32 vectors; top-3 non-self candidates; cosine descending then class-ID lexicographic tie-break; OR symmetrisation; no threshold; one undirected reciprocal edge; self-loops and duplicate final edges forbidden |
| NSGA-II | pymoo NSGA2; population 100; 100 generations; 10,000 evaluations per run; seeds 0–29 |
| Initialization | unchanged structure-aware Stage 2 initialization: frozen raw Leiden, perturbations, raw-graph groupings, then random fill |
| Objectives | minimize coupling; maximize cohesion (implemented as negative cohesion); minimize imbalance; minimize `f_semantic` |
| Constraints | minimum 2 clusters; maximum cluster ratio 0.40 |
| Repair | canonical relabel; split oversized clusters at `floor(0.40 × class_count)`; enforce at least two clusters; apply after initialization, crossover and mutation; duplicate individuals eliminated |
| Operating selector | project 4D front to structural 3D, apply exact 3D nondominance, deduplicate exact 3D objective tuples, then choose minimum imbalance within 5% relative band of the maximum weighted modularity; tie-break by higher modularity, lower coupling, solution ID, canonical labels |


**Stage 2 identity versus Stage 3 addition.** The class universe, raw graph `G_raw`, three structural objective implementations, constraints, repair, initialization, NSGA-II population/generation budget, projected-HV bounds/reference point, and operating selector are inherited unchanged. The single scientific addition is the separate semantic graph `G_sem` and its fourth minimization objective `f_semantic = 1 - W_sem,intra / W_sem,total`; `G_raw` and `G_sem` are never fused.


**Selector answer.** The final operating selector does **not** directly read `f_semantic`: the saved metadata sets `semantic_objective_used_for_selection=false`, and the executable selector accepts only projected structural rows plus post-hoc modularity. Semantic evidence can affect which solutions survive the 4D search, but not the representative-selection score.

### Declaration/body coverage and empty-body categories
> **Value provenance.** `data/semantic_text/declaration_method_body/<subject>/class_semantic_inputs.csv` — **direct read/count**. Empty categories are grouped by the saved `kind` field.

| Subject | Declarations | Exact declarations | Non-empty bodies | Empty bodies | Empty categories | Empty reason evidence |
|---|---|---|---|---|---|---|
| JPetStore | 24 | 24 | 17 | 7 | interface=7 | all empty rows have 0 extracted concrete and 0 normalized methods |
| DayTrader | 53 | 53 | 49 | 4 | interface=4 | all empty rows have 0 extracted concrete and 0 normalized methods |
| Xerces-J | 814 | 814 | 694 | 120 | class=4, interface=116 | all empty rows have 0 extracted concrete and 0 normalized methods |

## 3. Semantic input and embedding validation

> **Value provenance.** `data/semantic_text/declaration_method_body/<subject>/class_semantic_inputs.csv; data/embeddings/declaration_method_body/<subject>/embedding_metadata.json; results/stage3/data_quality/{input,embedding}/` — **direct read plus descriptive recomputation**. Token min/mean/median/population-std/max are recomputed from `total_token_count`; duplicate-member counts group exact saved semantic text.

| Subject | Classes | Declaration exact | Non-empty body | Empty body | Total tokens min/mean/median/std/max | Body-budget affected classes | Embeddings | Dim | NaN/Inf | Dropped/duplicates | Frozen hashes / status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| JPetStore | 24 | 24 | 17 | 7 | 27/110.29166666666667/73/97.735817030173507/466 | 0 | 24 | 3584 | 0/0 | dropped=0; duplicate members=0; groups=0 | input `2d9007f75a14f4a4ed6152563241b898837b6c12b66a98a2464b4cc3f969a921`; embedding `e7615e77d4f3258df46e499fd94c2dbb59bee03c0d2f6c3bb822c3aff4577139`; reproducibility passed |
| DayTrader | 53 | 53 | 49 | 4 | 29/174.67924528301887/114/178.42072110656071/975 | 1 | 53 | 3584 | 0/0 | dropped=0; duplicate members=0; groups=0 | input `da53d434b820e3c25bc69df63ced807cd0113d412fa36acc9694d1a97631d655`; embedding `db7ef8d78036796c5c5c79cc95f54eb1b9b9974de5e6f035d1929391b415f66c`; reproducibility passed |
| Xerces-J | 814 | 814 | 694 | 120 | 15/136.25184275184276/75/187.08756891506772/1833 | 7 | 814 | 3584 | 0/0 | dropped=0; duplicate members=55; groups=11 | input `65488944220cc3a503994d6f2289e0f7bdc06c619351a2e8243bca243538c8a3`; embedding `36bdeca0e1ef32f36631c30ebbf86a1875621490e92f9b4a7fd0860755676236`; reproducibility passed |

**Classes affected by the independent 256-token method-body evidence budget (exact removed-token counts).** These are not embedding-model tokenizer truncations.

- **JPetStore**: none.
- **DayTrader**: `com.ibm.websphere.samples.daytrader.direct.TradeDirect` (31 removed).
- **Xerces-J**: `org.apache.xerces.dom.CoreDocumentImpl` (1 removed); `org.apache.xerces.impl.dv.xs.XSSimpleTypeDecl` (342 removed); `org.apache.xerces.impl.xpath.regex.Token` (44 removed); `org.apache.xerces.impl.xs.XMLSchemaValidator` (125 removed); `org.apache.xerces.impl.xs.traversers.XSDHandler` (134 removed); `org.apache.xerces.util.EncodingMap` (34 removed); `org.apache.xerces.xinclude.XIncludeHandler` (73 removed).

<!-- BEGIN GENERATED: input_controls -->
No semantic input reached the embedding model's 32,768-token context limit, and tokenizer truncation was disabled. A separate 256-token method-body evidence budget affected no JPetStore classes, one DayTrader class, and seven Xerces-J classes.

| subject | class_count | embedding_model_max_tokens | model_tokenizer_truncation_count | embedding_context_limit_exceeded_count | method_body_budget_tokens | body_budget_capped_classes | body_tokens_removed_by_budget | affected_class_ids |
|---|---|---|---|---|---|---|---|---|
| jpetstore | 24 | 32768 | 0 | 0 | 256 | 0 | 0 |  |
| daytrader | 53 | 32768 | 0 | 0 | 256 | 1 | 31 | com.ibm.websphere.samples.daytrader.direct.TradeDirect |
| xerces | 814 | 32768 | 0 | 0 | 256 | 7 | 753 | org.apache.xerces.dom.CoreDocumentImpl;org.apache.xerces.impl.dv.xs.XSSimpleTypeDecl;org.apache.xerces.impl.xpath.regex.Token;org.apache.xerces.impl.xs.XMLSchemaValidator;org.apache.xerces.impl.xs.traversers.XSDHandler;org.apache.xerces.util.EncodingMap;org.apache.xerces.xinclude.XIncludeHandler |
<!-- END GENERATED: input_controls -->

## 4. Semantic graph validity

> **Value provenance.** `data/semantic_graphs/declaration_method_body/<subject>/semantic_edges.csv; results/stage3/data_quality/semantic_graph/semantic_graph_quality_per_subject.csv` — **direct read plus sum**. Total weight is recomputed as `Σ edge.weight`; the remaining graph statistics and reproducibility status are read directly.

| Subject | Nodes | Edges | Total weight | Weight mean/median/min/max | Isolated | Degree min/mean/median/max | Determinism |
|---|---|---|---|---|---|---|---|
| JPetStore | 24 | 47 | 30.426882932868651 | 0.64738048793337555/0.64060347762808123/0.50474016832623458/0.82744405789383135 | 0 | 3/3.9166666666666665/4/7 | hash `2dcf34b9e931cfdb0eec205f7da5bd0f24f6956be98d838369e12573026a9214`; byte-identical replay passed |
| DayTrader | 53 | 112 | 66.895144934783588 | 0.59727807977485337/0.61256713386086992/0.3203311854752639/0.86411717927773823 | 0 | 3/4.2264150943396226/4/8 | hash `c7761509fe91acb398ee5bc3a0c71e3a368a34aae316b04c5907d34bced1714d`; byte-identical replay passed |
| Xerces-J | 814 | 1681 | 1216.3228214638384 | 0.7235709824294102/0.71547949571209202/0.43257303728805391/1 | 0 | 3/4.1302211302211305/4/14 | hash `7d5d45f6e7cc46cdb57c57688bc89b5e90e0ecea7390833a7acb2e8887d935a5`; byte-identical replay passed |

## 5. Semantic–structural overlap

> **Value provenance.** `data/extracted/<subject>/structural_dependencies.csv; data/semantic_graphs/declaration_method_body/<subject>/semantic_edges.csv; configs/experiments/05_stage3_declaration_method_body.yml:random_graph_baseline` — **recomputed**. Raw edges are rebuilt with the frozen `build_raw_edges`; overlap is `|E_raw ∩ E_sem|/|E_sem|`. Each random graph uniformly samples `|E_sem|` unordered distinct pairs without replacement from lexicographically sorted nodes using `numpy.random.default_rng(subject_base + repetition)`, repetitions 0–999. Random std is population std. No canonical empirical-p formula/value is stored.

| Subject | Raw edges | Semantic edges | Overlap | Semantic-only | Structural overlap | Novel proportion | Sum check | Random n | Random mean | Random std | Random min–max | Observed−random | Empirical p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| JPetStore | 53 | 47 | 25 | 22 | 0.53191489361702127 | 0.46808510638297873 | 1 | 1000 | 0.19323404255319149 | 0.051624913886767952 | 0.042553191489361701–0.40425531914893614 | 0.33868085106382978 | not stored; 0/1000 random overlaps ≥ observed |
| DayTrader | 161 | 112 | 49 | 63 | 0.4375 | 0.5625 | 1 | 1000 | 0.11719642857142856 | 0.028152798053928958 | 0.035714285714285712–0.20535714285714285 | 0.32030357142857147 | not stored; 0/1000 random overlaps ≥ observed |
| Xerces-J | 3780 | 1681 | 587 | 1094 | 0.3491969066032124 | 0.65080309339678766 | 1 | 1000 | 0.011392028554431884 | 0.0025456239436723433 | 0.003569303985722784–0.020226055919095775 | 0.33780487804878051 | not stored; 0/1000 random overlaps ≥ observed |

All three sum checks equal 1 within floating-point precision; observed overlap is above every one of the 1,000 deterministic random draws.

## 6. Objective redundancy

> **Value provenance.** `results/stage3/subjects/<subject>/declaration_method_body/{validation,formal}/seed_*/objective_redundancy.json and pareto_front_4d.csv; posthoc_metrics.csv` — **direct read for coupling; recomputed for three supporting diagnostics**. Spearman is evaluated on every saved final 4D-front row. IQR is Q3−Q1; std is sample std. Only `f_semantic` versus coupling is the frozen official redundancy diagnostic.

**Per-seed values.**

| Subject | Seed | ρ(fsem,coupling) | ρ(fsem,modularity) | ρ(fsem,cohesion) | ρ(fsem,imbalance) |
|---|---|---|---|---|---|
| JPetStore | 0 | 0.60962612213714407 | -0.34408640864086404 | 0.35203120312031205 | -0.039404644080578449 |
| JPetStore | 1 | -0.068515429201750355 | 0.23459627479967038 | -0.058614564835482295 | -0.2264829792772747 |
| JPetStore | 2 | 0.23267300101857954 | 0.45665303526468731 | 0.48156760146511818 | 0.021412213586381439 |
| JPetStore | 3 | 0.36563563603018034 | -0.075950050706742156 | 0.1870938319495547 | -0.1128089772495298 |
| JPetStore | 4 | 0.57138313634358762 | -0.11494183900993529 | 0.46078746111056806 | -0.043887376339197051 |
| JPetStore | 5 | 0.41382538633253979 | 0.0020822269628232868 | 0.59341668244242218 | 0.13624085625951646 |
| JPetStore | 6 | 0.13092491222793065 | 0.33011701170117008 | 0.39113111311131105 | -0.26605072845097927 |
| JPetStore | 7 | 0.15082382465859476 | 0.42908619588010671 | 0.36992010177214729 | 0.021559001142350643 |
| JPetStore | 8 | 0.16563200449381699 | 0.21816981698169816 | 0.47601560156015593 | -0.038262521882976713 |
| JPetStore | 9 | 0.21194380372126945 | 0.30219712630536943 | 0.43901721877550964 | 0.0097413820742520852 |
| JPetStore | 10 | 0.70044166617362191 | -0.52879687968796873 | 0.4561176117611761 | 0.05930942212601556 |
| JPetStore | 11 | -0.03075501312818317 | 0.45414941494149408 | 0.21592559255925592 | -0.29265455736294971 |
| JPetStore | 12 | 0.39673595195618544 | -0.11562625638525834 | 0.34211529056821161 | 0.061064938506495893 |
| JPetStore | 13 | 0.32586302694636576 | 0.11133513351335132 | 0.32009096937128578 | -0.1862137898368626 |
| JPetStore | 14 | 0.43781130433254112 | 0.016747775264479525 | 0.5743028761152067 | -0.12033244358776574 |
| JPetStore | 15 | 0.65632558079227932 | -0.42985427499225876 | 0.46694409524391151 | -0.0087334675565462015 |
| JPetStore | 16 | -0.029456333680817882 | 0.59356582292924143 | 0.47614394647754366 | 0.10004709146655633 |
| JPetStore | 17 | 0.61327636465977176 | -0.37099532550450343 | 0.42529980588191985 | -0.080482267363695209 |
| JPetStore | 18 | 0.53898134515187446 | -0.053969558864805964 | 0.39539991239071343 | -0.10647283034618397 |
| JPetStore | 19 | 0.62855111170779887 | -0.33964302110305722 | 0.47229348000845084 | -0.13714002554325988 |
| JPetStore | 20 | 0.26469988224916552 | -0.065682765325124084 | 0.11068140018471713 | -0.13640649345412992 |
| JPetStore | 21 | 0.35366870977624121 | 0.10349834983498349 | 0.45040039124232489 | 0.043595739682965033 |
| JPetStore | 22 | 0.078815265750754579 | 0.3861949366702393 | 0.30987377624300505 | -0.2854587273730736 |
| JPetStore | 23 | 0.45763373031935933 | -0.23263126312631263 | 0.46191419141914186 | -0.013538666721903899 |
| JPetStore | 24 | 0.35634232782647529 | -0.013159473862020134 | 0.22462315780984937 | -0.11026300725597737 |
| JPetStore | 25 | 0.48508907048130467 | 0.019585958595859584 | 0.4612661266126612 | -0.055819680671889131 |
| JPetStore | 26 | 0.5580902723570319 | -0.31529552955295531 | 0.31061506150615065 | -0.052178560608821797 |
| JPetStore | 27 | 0.0095926499468434925 | 0.3476969420825502 | 0.24108900198558272 | -0.031014860643338478 |
| JPetStore | 28 | 0.52517441996230685 | -0.13418022310606473 | 0.29891058125470205 | -0.28789984528414297 |
| JPetStore | 29 | 0.33421648882569294 | 0.17665766576657663 | 0.21527752775277526 | -0.043855572917506656 |
| DayTrader | 0 | 0.79549948252999481 | -0.16677517784406851 | 0.59153492810025643 | -0.63379918272477831 |
| DayTrader | 1 | 0.78087814374747933 | -0.25754575457545753 | 0.54395439543954394 | -0.67419350972163616 |
| DayTrader | 2 | 0.87266121005288599 | -0.47754261952626648 | 0.5870662290308456 | -0.75715134387220728 |
| DayTrader | 3 | 0.4597996357745528 | -0.48378928167256641 | 0.018127921560011698 | -0.44578396413352539 |
| DayTrader | 4 | 0.63689279624696105 | -0.11287830373561519 | 0.36819792438786902 | -0.14429865507653689 |
| DayTrader | 5 | 0.64698434425744622 | -0.10545454545454544 | 0.27677167716771678 | -0.61369705189854884 |
| DayTrader | 6 | 0.59579086691433836 | -0.1546634343341789 | 0.34176357997559786 | -0.67908274015300041 |
| DayTrader | 7 | 0.70386894500787023 | 0.048286973558493838 | 0.35634670371208599 | -0.75626389518460746 |
| DayTrader | 8 | 0.75545087693584556 | -0.19649564956495646 | 0.54303030303030297 | -0.86541173365934698 |
| DayTrader | 9 | 0.8529295281685727 | -0.38636663666366633 | 0.44832883288328823 | -0.74321855151415062 |
| DayTrader | 10 | 0.81810871953899855 | -0.15488795345990342 | 0.57160516051605159 | -0.68341449220733175 |
| DayTrader | 11 | 0.78247798505632027 | -0.36536453645364536 | 0.38064206420642061 | -0.73254184709100389 |
| DayTrader | 12 | 0.75029403294519659 | -0.36097918085725278 | 0.3042913420095964 | -0.59092041032738518 |
| DayTrader | 13 | 0.64817265084519582 | -0.16471696584822368 | 0.35432343234323427 | -0.56062742651730313 |
| DayTrader | 14 | 0.87714824061873975 | -0.24468720278298781 | 0.54973462266860884 | -0.64256782304939009 |
| DayTrader | 15 | 0.79908068893958029 | -0.39182718271827177 | 0.37282928292829282 | -0.7072688486945985 |
| DayTrader | 16 | 0.78191522879160924 | -0.44648064806480642 | 0.25276927692769274 | -0.8392129565885057 |
| DayTrader | 17 | 0.76217079011747291 | -0.40026402640264019 | 0.44975697569756967 | -0.64166794183164999 |
| DayTrader | 18 | 0.7460073148275328 | -0.48044404440444038 | 0.35378337833783374 | -0.812201656774303 |
| DayTrader | 19 | 0.84815899382257665 | -0.22711739309251067 | 0.33603461156650366 | -0.82677755981159273 |
| DayTrader | 20 | 0.76046889113993665 | -0.011005100510051003 | 0.47519951995199522 | -0.7000813118348308 |
| DayTrader | 21 | 0.77508783405039539 | -0.17256525652565255 | 0.57736573657365731 | -0.63445486577695542 |
| DayTrader | 22 | 0.78989972938553454 | -0.16830483048304828 | 0.54835883588358836 | -0.61380090432343293 |
| DayTrader | 23 | 0.81073637029720069 | -0.43923924164386607 | 0.23698769876987696 | -0.77155441414994297 |
| DayTrader | 24 | 0.81976548834253915 | -0.027512998917005774 | 0.50160517015706652 | -0.8328552741139631 |
| DayTrader | 25 | 0.76830296482817551 | -0.44955295529552947 | 0.32273724193737202 | -0.84738836536614781 |
| DayTrader | 26 | 0.85708713642096224 | -0.35114311431143108 | 0.67571557155715567 | -0.73364216797564141 |
| DayTrader | 27 | 0.80436732853725523 | -0.04244237156446215 | 0.57449917341744738 | -0.83041297134299008 |
| DayTrader | 28 | 0.82696606298666631 | -0.12823320802100327 | 0.50546206259472193 | -0.54461936351307394 |
| DayTrader | 29 | 0.7450292082138722 | -0.23768376837683766 | 0.46694269426942686 | -0.72373888756805949 |
| Xerces-J | 0 | 0.90940839730648548 | -0.65403332754449361 | -0.11769647582855657 | -0.67423146854780358 |
| Xerces-J | 1 | 0.91040723439264593 | -0.8013129391859789 | -0.075277979467178666 | -0.58437794407259158 |
| Xerces-J | 2 | 0.93157754195626574 | -0.68752081464700276 | -0.022916360385222809 | -0.60651247078722059 |
| Xerces-J | 3 | 0.93885070162649265 | -0.7306450645064505 | -0.23121512151215118 | -0.65321332133213328 |
| Xerces-J | 4 | 0.91685568556855679 | -0.67509150915091487 | -0.12607260726072606 | -0.6447044704470446 |
| Xerces-J | 5 | 0.91127512751275119 | -0.68139213921392128 | -0.029846984698469844 | -0.64634863486348626 |
| Xerces-J | 6 | 0.93388779377372433 | -0.7411183351918601 | 0.032289325800702783 | -0.50947047546126523 |
| Xerces-J | 7 | 0.88342564313407557 | -0.51373537353735366 | -0.31930393039303928 | -0.75715198665803318 |
| Xerces-J | 8 | 0.88844550989151716 | -0.78215421542154218 | -0.20291629162916291 | -0.78955895589558944 |
| Xerces-J | 9 | 0.94883257625308282 | -0.68196424232002795 | 0.27320213982163111 | -0.57920965859744222 |
| Xerces-J | 10 | 0.91270000810494223 | -0.61312931293129302 | -0.076231623162316228 | -0.69149714971497134 |
| Xerces-J | 11 | 0.94779477947794755 | -0.75789978997899776 | 0.043204320432043204 | -0.54852685268526846 |
| Xerces-J | 12 | 0.94387038703870374 | -0.74795079507950779 | -0.055253525352535249 | -0.50342634263426334 |
| Xerces-J | 13 | 0.92700504355391933 | -0.71298743770929274 | 0.19106567976587574 | -0.55625129388577355 |
| Xerces-J | 14 | 0.93374137413741365 | -0.72865286528652851 | 0.081308130813081317 | -0.56376837683768377 |
| Xerces-J | 15 | 0.92461078257946239 | -0.69790997847028147 | -0.29764355022168165 | -0.8456936435414395 |
| Xerces-J | 16 | 0.90810681068106791 | -0.71545154515451537 | -0.04298829882988299 | -0.47349534953495342 |
| Xerces-J | 17 | 0.95597333319052735 | -0.79961596159615955 | -0.055997599759975994 | -0.63665166516651661 |
| Xerces-J | 18 | 0.92889288928892877 | -0.7737293729372936 | -0.095781578157815767 | -0.40339633963396337 |
| Xerces-J | 19 | 0.94026966858486982 | -0.74387861950115641 | -0.045400676269860114 | -0.78888325497881306 |
| Xerces-J | 20 | 0.94483048304830475 | -0.77146114611461136 | 0.13262526252625262 | -0.66268226822682252 |
| Xerces-J | 21 | 0.93343194378604122 | -0.66939294747660261 | 0.053435503857137766 | -0.5765693866494197 |
| Xerces-J | 22 | 0.92236423642364218 | -0.7188358835883587 | -0.23762376237623761 | -0.71619561956195621 |
| Xerces-J | 23 | 0.93925237851348509 | -0.77177780846159039 | -0.18208330083316615 | -0.65216112909142376 |
| Xerces-J | 24 | 0.95337219734061662 | -0.80355476614452914 | 0.25355611628111807 | -0.65764973792596604 |
| Xerces-J | 25 | 0.92471647164716453 | -0.69482148214821471 | -0.43257125712571259 | -0.89390939093909372 |
| Xerces-J | 26 | 0.91997227698233142 | -0.75478774314094033 | 0.25409017128878625 | -0.53317291681283119 |
| Xerces-J | 27 | 0.88637263726372628 | -0.69117311731173103 | -0.22245424542454242 | -0.68254425442544253 |
| Xerces-J | 28 | 0.94378320967484375 | -0.74030225113519854 | 0.23827854269096951 | -0.50786230982019709 |
| Xerces-J | 29 | 0.95427542754275407 | -0.8356435643564355 | 0.17887788778877886 | -0.46594659465946586 |

**Subject summaries.**

| Subject | Pair | Mean | Median | Std | IQR | Min–max | Undefined | Status |
|---|---|---|---|---|---|---|---|---|
| JPetStore | coupling | 0.34816834067228342 | 0.36098898192832785 | 0.22359080325198541 | 0.35831965955380241 | -0.068515429201750355–0.70044166617362191 | 0 | official |
| JPetStore | modularity | 0.034917360587547672 | 0.0094150011136514052 | 0.29882951950933556 | 0.41483864485480781 | -0.52879687968796873–0.59356582292924143 | 0 | supporting diagnostic |
| JPetStore | cohesion | 0.36405503489534008 | 0.39326551275101224 | 0.14128130959391305 | 0.16010079521574389 | -0.058614564835482295–0.59341668244242218 | 0 | supporting diagnostic |
| JPetStore | imbalance | -0.074079712632134989 | -0.048032968474009424 | 0.1158763800428734 | 0.13751065065409138 | -0.29265455736294971–0.13624085625951646 | 0 | supporting diagnostic |
| DayTrader | coupling | 0.76240004964472363 | 0.78139668626954428 | 0.089954211627505679 | 0.069186637871600398 | 0.4597996357745528–0.87714824061873975 | 0 | official |
| DayTrader | modularity | -0.25192254698487987 | -0.23240058073467418 | 0.15675976571276182 | 0.23574248208901041 | -0.48378928167256641–0.048286973558493838 | 0 | supporting diagnostic |
| DayTrader | cohesion | 0.42952554492005429 | 0.44904290429042892 | 0.14081462239939874 | 0.20248919620642042 | 0.018127921560011698–0.67571557155715567 | 0 | supporting diagnostic |
| DayTrader | imbalance | -0.68608833722654816 | -0.7036750802647147 | 0.14416683312409698 | 0.13399054309268643 | -0.86541173365934698–-0.14429865507653689 | 0 | supporting diagnostic |
| Xerces-J | coupling | 0.92727675167587642 | 0.93023521562259726 | 0.019747803518085701 | 0.029165896931504398 | 0.88342564313407557–0.95597333319052735 | 0 | official |
| Xerces-J | modularity | -0.72306414497475957 | -0.72964896489648945 | 0.064074154320456753 | 0.079636916767523158 | -0.8356435643564355–-0.51373537353735366 | 0 | supporting diagnostic |
| Xerces-J | cohesion | -0.03791140292072856 | -0.050327100811197678 | 0.18466529837495332 | 0.24242060151415157 | -0.43257125712571259–0.27320213982163111 | 0 | supporting diagnostic |
| Xerces-J | imbalance | -0.6268354421129626 | -0.6406780678067806 | 0.11509965997813143 | 0.13000809497063803 | -0.89390939093909372–-0.40339633963396337 | 0 | supporting diagnostic |

## 7. Formal front health

> **Value provenance.** `results/stage3/subjects/<subject>/declaration_method_body/{validation,formal}/seed_*/pareto_front_4d.csv and projected_front_3d.csv` — **direct sizes plus exact recomputation**. 3D dominated removals are counted by minimization nondominance on coupling/negative-cohesion/imbalance; duplicate removals use exact projected triples. The saved projected-row count is asserted equal to the recomputed count.

**Per-seed front health.**

| Subject | Seed | 4D front | Projected final | Removed by 3D ND | Removed as projected duplicates |
|---|---|---|---|---|---|
| JPetStore | 0 | 100 | 61 | 39 | 0 |
| JPetStore | 1 | 100 | 51 | 49 | 0 |
| JPetStore | 2 | 100 | 41 | 59 | 0 |
| JPetStore | 3 | 100 | 69 | 31 | 0 |
| JPetStore | 4 | 100 | 51 | 49 | 0 |
| JPetStore | 5 | 100 | 45 | 55 | 0 |
| JPetStore | 6 | 100 | 43 | 57 | 0 |
| JPetStore | 7 | 100 | 49 | 51 | 0 |
| JPetStore | 8 | 100 | 51 | 49 | 0 |
| JPetStore | 9 | 100 | 52 | 48 | 0 |
| JPetStore | 10 | 100 | 60 | 40 | 0 |
| JPetStore | 11 | 100 | 45 | 55 | 0 |
| JPetStore | 12 | 100 | 50 | 50 | 0 |
| JPetStore | 13 | 100 | 52 | 48 | 0 |
| JPetStore | 14 | 100 | 52 | 48 | 0 |
| JPetStore | 15 | 100 | 59 | 41 | 0 |
| JPetStore | 16 | 99 | 45 | 54 | 0 |
| JPetStore | 17 | 100 | 48 | 52 | 0 |
| JPetStore | 18 | 100 | 47 | 53 | 0 |
| JPetStore | 19 | 100 | 62 | 38 | 0 |
| JPetStore | 20 | 100 | 61 | 39 | 0 |
| JPetStore | 21 | 100 | 42 | 58 | 0 |
| JPetStore | 22 | 100 | 44 | 56 | 0 |
| JPetStore | 23 | 100 | 58 | 42 | 0 |
| JPetStore | 24 | 100 | 55 | 45 | 0 |
| JPetStore | 25 | 100 | 53 | 47 | 0 |
| JPetStore | 26 | 100 | 65 | 35 | 0 |
| JPetStore | 27 | 100 | 46 | 54 | 0 |
| JPetStore | 28 | 100 | 48 | 52 | 0 |
| JPetStore | 29 | 100 | 55 | 45 | 0 |
| DayTrader | 0 | 100 | 64 | 36 | 0 |
| DayTrader | 1 | 100 | 77 | 23 | 0 |
| DayTrader | 2 | 100 | 76 | 24 | 0 |
| DayTrader | 3 | 100 | 74 | 26 | 0 |
| DayTrader | 4 | 100 | 74 | 26 | 0 |
| DayTrader | 5 | 100 | 67 | 33 | 0 |
| DayTrader | 6 | 99 | 61 | 38 | 0 |
| DayTrader | 7 | 100 | 76 | 24 | 0 |
| DayTrader | 8 | 100 | 68 | 32 | 0 |
| DayTrader | 9 | 100 | 66 | 34 | 0 |
| DayTrader | 10 | 100 | 67 | 33 | 0 |
| DayTrader | 11 | 100 | 67 | 33 | 0 |
| DayTrader | 12 | 100 | 76 | 24 | 0 |
| DayTrader | 13 | 100 | 68 | 32 | 0 |
| DayTrader | 14 | 100 | 77 | 23 | 0 |
| DayTrader | 15 | 100 | 67 | 33 | 0 |
| DayTrader | 16 | 100 | 65 | 35 | 0 |
| DayTrader | 17 | 100 | 74 | 26 | 0 |
| DayTrader | 18 | 100 | 62 | 38 | 0 |
| DayTrader | 19 | 100 | 67 | 33 | 0 |
| DayTrader | 20 | 100 | 59 | 41 | 0 |
| DayTrader | 21 | 100 | 70 | 30 | 0 |
| DayTrader | 22 | 100 | 71 | 29 | 0 |
| DayTrader | 23 | 100 | 64 | 36 | 0 |
| DayTrader | 24 | 100 | 73 | 27 | 0 |
| DayTrader | 25 | 100 | 66 | 34 | 0 |
| DayTrader | 26 | 100 | 72 | 28 | 0 |
| DayTrader | 27 | 100 | 49 | 51 | 0 |
| DayTrader | 28 | 100 | 70 | 30 | 0 |
| DayTrader | 29 | 100 | 76 | 24 | 0 |
| Xerces-J | 0 | 100 | 90 | 10 | 0 |
| Xerces-J | 1 | 100 | 83 | 17 | 0 |
| Xerces-J | 2 | 100 | 86 | 14 | 0 |
| Xerces-J | 3 | 100 | 79 | 21 | 0 |
| Xerces-J | 4 | 100 | 86 | 14 | 0 |
| Xerces-J | 5 | 100 | 78 | 22 | 0 |
| Xerces-J | 6 | 100 | 72 | 28 | 0 |
| Xerces-J | 7 | 100 | 84 | 16 | 0 |
| Xerces-J | 8 | 100 | 80 | 20 | 0 |
| Xerces-J | 9 | 100 | 84 | 16 | 0 |
| Xerces-J | 10 | 100 | 91 | 9 | 0 |
| Xerces-J | 11 | 100 | 83 | 17 | 0 |
| Xerces-J | 12 | 100 | 88 | 12 | 0 |
| Xerces-J | 13 | 100 | 85 | 15 | 0 |
| Xerces-J | 14 | 100 | 86 | 14 | 0 |
| Xerces-J | 15 | 100 | 85 | 15 | 0 |
| Xerces-J | 16 | 100 | 86 | 14 | 0 |
| Xerces-J | 17 | 100 | 88 | 12 | 0 |
| Xerces-J | 18 | 100 | 82 | 18 | 0 |
| Xerces-J | 19 | 100 | 86 | 14 | 0 |
| Xerces-J | 20 | 100 | 86 | 14 | 0 |
| Xerces-J | 21 | 100 | 82 | 18 | 0 |
| Xerces-J | 22 | 100 | 83 | 17 | 0 |
| Xerces-J | 23 | 100 | 87 | 13 | 0 |
| Xerces-J | 24 | 100 | 79 | 21 | 0 |
| Xerces-J | 25 | 100 | 83 | 17 | 0 |
| Xerces-J | 26 | 100 | 86 | 14 | 0 |
| Xerces-J | 27 | 100 | 81 | 19 | 0 |
| Xerces-J | 28 | 100 | 85 | 15 | 0 |
| Xerces-J | 29 | 100 | 87 | 13 | 0 |

**Subject summaries (mean/median/sample-std/range).**

| Subject | 4D front | Projected front | Total ND removals | Total duplicate removals | At population limit | 4D HV |
|---|---|---|---|---|---|---|
| JPetStore | 99.966666666666669/100/0.18257418583505536/99–100 | 52/51/7.2158828647118005/41–69 | 1439 | 0 | 29/30 | unavailable: no frozen 4D normalization/reference point or stored 4D-HV values |
| DayTrader | 99.966666666666669/100/0.18257418583505536/99–100 | 68.766666666666666/68/6.2900212890014897/49–77 | 936 | 0 | 29/30 | unavailable: no frozen 4D normalization/reference point or stored 4D-HV values |
| Xerces-J | 100/100/0/100–100 | 84.033333333333331/85/3.8639209434810216/72–91 | 479 | 0 | 30/30 | unavailable: no frozen 4D normalization/reference point or stored 4D-HV values |

The configuration labels 4D HV as Stage-3-internal only, but the accepted artifacts do not store a 4D reference point, normalization bounds, or per-seed 4D HV. It is therefore reported missing rather than inferred. No Stage 3 4D quantity is compared with Stage 2 3D HV.

## 8. Stage 2 versus Stage 3 projected Hypervolume

> **Value provenance.** `results/stage3/cross_subject/stage2_comparison/paired_per_seed.csv; formal_statistics/formal_statistical_tests.csv; configs/experiments/stage2_robustness_bounds.yml` — **direct read plus relative-difference/descriptive recomputation**. Relative difference is `(Stage3_projected−Stage2)/Stage2`. The saved Stage 3 HV contract removes fsem, re-filters exact 3D nondominance, deduplicates exact triples, and uses the same subject-specific Stage 2 bounds and reference `[1.1,1.1,1.1]`. IQR is Q3−Q1; std is sample std.

**Per-seed paired HV.**

| Subject | Seed | Stage 2 3D HV | Stage 3 projected 3D HV | Absolute difference | Relative difference |
|---|---|---|---|---|---|
| JPetStore | 0 | 0.40787796639549112 | 0.40539329983443922 | -0.0024846665610519002 | -0.0060916910589935772 |
| JPetStore | 1 | 0.40485147405653832 | 0.38876923891856641 | -0.016082235137971902 | -0.039723790497366442 |
| JPetStore | 2 | 0.4104289000041989 | 0.38978727721011502 | -0.020641622794083901 | -0.050292810262319992 |
| JPetStore | 3 | 0.39642942616537352 | 0.40625147748052182 | 0.0098220513151481004 | 0.024776292239847383 |
| JPetStore | 4 | 0.40378611234558692 | 0.38972579981931021 | -0.014060312526276901 | -0.034821188981960231 |
| JPetStore | 5 | 0.39038945670391312 | 0.38222996476479421 | -0.0081594919391189003 | -0.020900902416807317 |
| JPetStore | 6 | 0.39815529664132221 | 0.38562011166260762 | -0.012535184978714401 | -0.031483155151912731 |
| JPetStore | 7 | 0.38274836879224972 | 0.36657534544482312 | -0.016173023347426301 | -0.042254976548848674 |
| JPetStore | 8 | 0.40916193649272842 | 0.3877423964241527 | -0.021419540068575701 | -0.052349786620379778 |
| JPetStore | 9 | 0.40770511044770091 | 0.39168011027951632 | -0.016025000168184401 | -0.039305369880175252 |
| JPetStore | 10 | 0.40112088499475301 | 0.40785762896096062 | 0.0067367439662075002 | 0.016794797324740957 |
| JPetStore | 11 | 0.39385797532413402 | 0.37692806594347072 | -0.016929909380663102 | -0.042984807827568965 |
| JPetStore | 12 | 0.40772255652538952 | 0.37313501313165898 | -0.034587543393730102 | -0.084831076525384061 |
| JPetStore | 13 | 0.38453024765020011 | 0.40475397009308722 | 0.020223722442887102 | 0.052593320204251531 |
| JPetStore | 14 | 0.39471113218938492 | 0.37726231367162683 | -0.0174488185177579 | -0.044206552830098639 |
| JPetStore | 15 | 0.39221776838997791 | 0.39005407790762431 | -0.0021636904823534001 | -0.0055165539573471421 |
| JPetStore | 16 | 0.3994348942068604 | 0.37929323636438372 | -0.020141657842476401 | -0.050425383797454773 |
| JPetStore | 17 | 0.40530352034533962 | 0.3870211213066968 | -0.018282399038642799 | -0.045107920659226607 |
| JPetStore | 18 | 0.40111430011279903 | 0.39124314247112302 | -0.0098711576416757006 | -0.024609338632155722 |
| JPetStore | 19 | 0.40787000683489832 | 0.3901845295436665 | -0.017685477291231901 | -0.043360573209274306 |
| JPetStore | 20 | 0.40611712122297933 | 0.39503104273214812 | -0.011086078490831 | -0.027297737306535216 |
| JPetStore | 21 | 0.40912685773288782 | 0.37021192527113711 | -0.038914932461750602 | -0.095117032104398355 |
| JPetStore | 22 | 0.38354141839049383 | 0.37637220010906641 | -0.0071692182814274003 | -0.01869216188309613 |
| JPetStore | 23 | 0.40731159757656632 | 0.38784903659326803 | -0.019462560983298401 | -0.047782977698393986 |
| JPetStore | 24 | 0.40375029375707921 | 0.39068832414476662 | -0.013061969612312201 | -0.03235160398464372 |
| JPetStore | 25 | 0.39318706620902433 | 0.3942142695236282 | 0.0010272033146037 | 0.002612505351480198 |
| JPetStore | 26 | 0.40913023204855992 | 0.39338069133487352 | -0.015749540713685901 | -0.038495177036482288 |
| JPetStore | 27 | 0.40642060589073842 | 0.37962107349570262 | -0.026799532395036001 | -0.065940387880432785 |
| JPetStore | 28 | 0.40969366199730273 | 0.37448252130624871 | -0.035211140691054001 | -0.085945046158136168 |
| JPetStore | 29 | 0.40992401036420972 | 0.39404277760251433 | -0.015881232761695101 | -0.038741894497922244 |
| DayTrader | 0 | 0.1736456084309618 | 0.20617415501213041 | 0.032528546581168501 | 0.18732720553714052 |
| DayTrader | 1 | 0.19223290711101021 | 0.1500941166426786 | -0.042138790468331203 | -0.21920695629909709 |
| DayTrader | 2 | 0.1826760227031991 | 0.1689117639932704 | -0.013764258709928701 | -0.075347922000097572 |
| DayTrader | 3 | 0.15509115619875261 | 0.22391007235345781 | 0.068818916154704701 | 0.4437320466327061 |
| DayTrader | 4 | 0.1953586636451953 | 0.24492190270348471 | 0.0495632390582895 | 0.25370381908582623 |
| DayTrader | 5 | 0.19056332639215481 | 0.18737266262143151 | -0.0031906637707233001 | -0.016743325335103174 |
| DayTrader | 6 | 0.20982175696033081 | 0.184457992839652 | -0.0253637641206787 | -0.12088243129845738 |
| DayTrader | 7 | 0.19022619662112211 | 0.15842834709545511 | -0.031797849525666902 | -0.16715809962283748 |
| DayTrader | 8 | 0.1371183452268139 | 0.13828999457173341 | 0.0011716493449194 | 0.0085448037093900607 |
| DayTrader | 9 | 0.177501493969656 | 0.19956088755442231 | 0.022059393584766201 | 0.12427722770906575 |
| DayTrader | 10 | 0.1867410737095177 | 0.18053186709280861 | -0.0062092066167089002 | -0.03325035298001839 |
| DayTrader | 11 | 0.20393360224335461 | 0.20059539672649671 | -0.0033382055168577002 | -0.016369080328774901 |
| DayTrader | 12 | 0.18231829251163101 | 0.1904557513289479 | 0.0081374588173169001 | 0.044633254870998562 |
| DayTrader | 13 | 0.19584894950109111 | 0.21195197190032641 | 0.016103022399235101 | 0.082221642956249771 |
| DayTrader | 14 | 0.1678277869443002 | 0.18555143757204121 | 0.017723650627740901 | 0.10560617493945296 |
| DayTrader | 15 | 0.2046457362452293 | 0.19323189657653431 | -0.011413839668695001 | -0.055773650006651805 |
| DayTrader | 16 | 0.21511356610811971 | 0.21736129371335031 | 0.0022477276052306002 | 0.010449027673600311 |
| DayTrader | 17 | 0.2136885880409492 | 0.19186461566851601 | -0.021823972372433002 | -0.10212979819142733 |
| DayTrader | 18 | 0.2105584739498762 | 0.1899775169247076 | -0.0205809570251686 | -0.097744615256225367 |
| DayTrader | 19 | 0.17132990543169971 | 0.1600232822463202 | -0.0113066231853793 | -0.065993284458368343 |
| DayTrader | 20 | 0.18922231189202771 | 0.1817451437536324 | -0.0074771681383951002 | -0.039515256227615772 |
| DayTrader | 21 | 0.16807504709681181 | 0.187537343338914 | 0.019462296242101999 | 0.11579527466020485 |
| DayTrader | 22 | 0.18942751063024801 | 0.2176470062748454 | 0.028219495644597001 | 0.14897253070954555 |
| DayTrader | 23 | 0.16600325028172561 | 0.168715733567702 | 0.0027124832859765002 | 0.016339940822682791 |
| DayTrader | 24 | 0.17669227378125271 | 0.2134953988049956 | 0.036803125023742701 | 0.20828938490715007 |
| DayTrader | 25 | 0.19749996128277481 | 0.22098704280933421 | 0.023487081526559001 | 0.11892195509310134 |
| DayTrader | 26 | 0.1781931928294016 | 0.19614340396539051 | 0.017950211135988801 | 0.10073455024274727 |
| DayTrader | 27 | 0.17416353563707221 | 0.1709561225617949 | -0.0032074130752771002 | -0.018416099923241218 |
| DayTrader | 28 | 0.18932030870649061 | 0.20097450376837411 | 0.011654195061883201 | 0.061558081864061288 |
| DayTrader | 29 | 0.1601261641598532 | 0.15266590736225771 | -0.0074602567975952001 | -0.04658986766302569 |
| Xerces-J | 0 | 0.1309247538177381 | 0.13548027988038641 | 0.0045555260626481001 | 0.03479499429871076 |
| Xerces-J | 1 | 0.12909889936078031 | 0.1243685597017765 | -0.0047303396590036 | -0.036641208270756696 |
| Xerces-J | 2 | 0.1411527738240233 | 0.1514422118833508 | 0.0102894380593274 | 0.072895755291039865 |
| Xerces-J | 3 | 0.1249790398633267 | 0.1398327997201417 | 0.014853759856815 | 0.11885000775376915 |
| Xerces-J | 4 | 0.1388876636709945 | 0.1341514195113673 | -0.0047362441596271003 | -0.034101258775917652 |
| Xerces-J | 5 | 0.13366918848832271 | 0.13738027381943871 | 0.0037110853311159001 | 0.027763206862291962 |
| Xerces-J | 6 | 0.1234554666995543 | 0.12629100151738201 | 0.0028355348178276001 | 0.022968078236084672 |
| Xerces-J | 7 | 0.1532506593007282 | 0.2277787198274514 | 0.074528060526723103 | 0.48631477911279081 |
| Xerces-J | 8 | 0.1493299836131344 | 0.14402940123942801 | -0.0053005823737063001 | -0.035495767463810141 |
| Xerces-J | 9 | 0.13069933902078981 | 0.1254347882226256 | -0.0052645507981639002 | -0.040279857860082958 |
| Xerces-J | 10 | 0.14250147396256241 | 0.14073404256967201 | -0.0017674313928903 | -0.012402899027940829 |
| Xerces-J | 11 | 0.12884043299249551 | 0.12829620840265371 | -0.00054422458984150002 | -0.0042240201868422424 |
| Xerces-J | 12 | 0.14129626029385481 | 0.1250876833771867 | -0.016208576916668001 | -0.11471341763015536 |
| Xerces-J | 13 | 0.1382217554666994 | 0.13820418827356781 | -1.7567193131645675e-05 | -0.00012709427016228627 |
| Xerces-J | 14 | 0.1249951012945113 | 0.12827730636067131 | 0.0032822050661598001 | 0.02625866959719109 |
| Xerces-J | 15 | 0.13672034819460921 | 0.14866383927137841 | 0.0119434910767691 | 0.087357084987588748 |
| Xerces-J | 16 | 0.1239646261870352 | 0.13196245561857781 | 0.0079978294315424005 | 0.064517029394140626 |
| Xerces-J | 17 | 0.12965031262985111 | 0.12822577686164521 | -0.0014245357682058 | -0.010987522816646897 |
| Xerces-J | 18 | 0.13273078827404761 | 0.13080719437895941 | -0.0019235938950878 | -0.01449244685503245 |
| Xerces-J | 19 | 0.134986835737814 | 0.14173818775476821 | 0.0067513520169540002 | 0.050014892045231789 |
| Xerces-J | 20 | 0.13525012561038791 | 0.12275716389604251 | -0.0124929617143453 | -0.092369316907945823 |
| Xerces-J | 21 | 0.1327997096490168 | 0.13981654948518021 | 0.0070168398361634002 | 0.052837764892021084 |
| Xerces-J | 22 | 0.1262164725878927 | 0.13098169961611991 | 0.0047652270282270001 | 0.037754398697118344 |
| Xerces-J | 23 | 0.13110970971128311 | 0.12977440839700871 | -0.0013353013142744 | -0.010184610409212745 |
| Xerces-J | 24 | 0.12579573581395101 | 0.12502956790555381 | -0.00076616790839690002 | -0.006090571380975485 |
| Xerces-J | 25 | 0.13807242658593441 | 0.1486607382627782 | 0.0105883116768437 | 0.076686648729634446 |
| Xerces-J | 26 | 0.13231548869125681 | 0.12633587329927351 | -0.0059796153919831002 | -0.045192104500600495 |
| Xerces-J | 27 | 0.14750888287368161 | 0.13789276820331381 | -0.0096161146703679003 | -0.065190071831826582 |
| Xerces-J | 28 | 0.13663954480451571 | 0.13018828807058841 | -0.0064512567339272001 | -0.047213687246666629 |
| Xerces-J | 29 | 0.13759559216429401 | 0.12689945076717221 | -0.0106961413971218 | -0.077736075908232782 |

**Subject summaries. Values are mean/median/sample-std/IQR; inferential results are in the generated six-row formal table below.**

| Subject | Stage 2 | Stage 3 projected |
|---|---|---|
| JPetStore | 0.40125400666028949/0.40431879320106262/0.0084110715637503095/0.012692438574139098 | 0.38758006611154999/0.38924751936893831/0.010576762586862198/0.013580350423820775 |
| DayTrader | 0.18483216694142079/0.1879816928007727/0.018250435439330161/0.021951287804627739 | 0.18981781771150022/0.19021663412682777/0.024457768754331422/0.031524183506642989 |
| Xerces-J | 0.13442197970616959/0.13323444906866977/0.0075522709004011918/0.008947670568460131 | 0.13688409486984865/0.13147207761734886/0.018914252982772783/0.012597704870610849 |

<!-- BEGIN GENERATED: formal_statistics -->
**Formal confirmatory family: exactly three subjects × two primary metrics (six rows).** Differences are Stage 3 − Stage 2; Wilcoxon is paired, two-sided, with SciPy `zero_method="wilcox"`; Holm is applied across these six rows only (family-wise alpha 0.05).

| subject | metric | n_pairs | paired_median_difference | better_count | tie_count | worse_count | raw_p_value | holm_adjusted_p_value | rank_biserial | corrected_significant |
|---|---|---|---|---|---|---|---|---|---|---|
| jpetstore | projected_hypervolume | 30 | -0.015953116464939993 | 4 | 0 | 26 | 9.220093488693237e-06 | 4.6100467443466187e-05 | -0.8451612903225807 | True |
| jpetstore | selected_f_semantic | 30 | 0.004660012634131405 | 13 | 0 | 17 | 0.136610162687313 | 0.546440650749252 | -0.30752688172043013 | False |
| daytrader | projected_hypervolume | 30 | 0.0017096884750750496 | 16 | 0 | 14 | 0.40449450351297855 | 0.8089890070259571 | 0.17849462365591398 | False |
| daytrader | selected_f_semantic | 30 | -0.02144213222782898 | 16 | 0 | 14 | 0.23665234446525574 | 0.7099570333957672 | -0.25161290322580643 | False |
| xerces | projected_hypervolume | 30 | -0.0006551962491194996 | 13 | 0 | 17 | 0.8393927440047264 | 0.8393927440047264 | 0.04516129032258064 | False |
| xerces | selected_f_semantic | 30 | -0.029560631084392053 | 30 | 0 | 0 | 1.862645149230957e-09 | 1.1175870895385742e-08 | -1.0 | True |
<!-- END GENERATED: formal_statistics -->

## 9. Selected Stage 2 versus Stage 3 profiles

> **Value provenance.** `results/stage2/cross_subject/operating_profile/canonical_operating_solution_per_seed.csv; Stage 3 selected_solution.json/posthoc_metrics.csv; frozen raw and semantic graphs` — **direct read plus frozen-graph recomputation**. Stage 2 is the active canonical 5% modularity-band solution. Stage 3 is the formal projected-front selector output. Stage 2 fsem is `1−W_sem,intra/W_sem,total`; its internal ratio is `W_raw,intra/W_raw,total`. Each per-seed vector is `modularity/coupling/cohesion/imbalance/fsem/clusters/max-ratio/singleton-ratio/internal-edge-ratio`.

**Per-seed selected profiles.**

| Subject | Seed | Stage 2 active profile | Stage 3 formal profile |
|---|---|---|---|
| JPetStore | 0 | 0.43411979881115709/0.27407407407407408/4.8999999999999995/0/0.55731731063187895/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 1 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 2 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 3 | 0.43411979881115709/0.27407407407407408/4.8999999999999995/0/0.55731731063187895/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 4 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 5 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 6 | 0.42449931412894398/0.2839506172839506/4.8333333333333339/0/0.55084266188650755/4/0.25/0/0.71604938271604934 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 7 | 0.43411979881115709/0.27407407407407408/4.8999999999999995/0/0.55731731063187895/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 8 | 0.43411979881115709/0.27407407407407408/4.8999999999999995/0/0.55731731063187895/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 9 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 10 | 0.4366925773510138/0.25185185185185183/4.9083333333333332/0.11785113019775791/0.48699955575999887/4/0.29166666666666669/0/0.74814814814814812 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 11 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 12 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.43705532693187032/0.25185185185185183/4.9690476190476192/0.1666666666666666/0.46566906033572092/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 13 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 14 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.439893308946807/0.25185185185185183/5.420238095238096/0.2041241452319312/0.53359056396179605/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 15 | 0.43411979881115709/0.27407407407407408/4.8999999999999995/0/0.55731731063187895/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 16 | 0.43411979881115709/0.27407407407407408/4.8999999999999995/0/0.55731731063187895/4/0.25/0/0.72592592592592597 | 0.43768632830361243/0.27654320987654302/5.7172619047619042/0.23570226039551581/0.53271422465418405/4/0.33333333333333331/0/0.72345679012345665 |
| JPetStore | 17 | 0.4366925773510138/0.25185185185185183/4.9083333333333332/0.11785113019775791/0.48699955575999887/4/0.29166666666666669/0/0.74814814814814812 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 18 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 19 | 0.43411979881115709/0.27407407407407408/4.8999999999999995/0/0.55731731063187895/4/0.25/0/0.72592592592592597 | 0.43991159884164022/0.25432098765432082/6.6589285714285706/0.3118047822311617/0.51211372451079595/4/0.33333333333333331/0/0.74567901234567902 |
| JPetStore | 20 | 0.4366925773510138/0.25185185185185183/4.9083333333333332/0.11785113019775791/0.48699955575999887/4/0.29166666666666669/0/0.74814814814814812 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 21 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 22 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 23 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 24 | 0.43652796829751589/0.27407407407407408/5.2190476190476192/0.11785113019775791/0.5328605686809067/4/0.29166666666666669/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 25 | 0.43411979881115709/0.27407407407407408/4.8999999999999995/0/0.55731731063187895/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 26 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 27 | 0.43411979881115709/0.27407407407407408/4.8999999999999995/0/0.55731731063187895/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 28 | 0.42773662551440361/0.27407407407407408/4.9000000000000004/0/0.50760005590338708/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| JPetStore | 29 | 0.43411979881115709/0.27407407407407408/4.8999999999999995/0/0.55731731063187895/4/0.25/0/0.72592592592592597 | 0.44206980643194632/0.25185185185185183/5.477380952380952/0.2041241452319312/0.51226006853751815/4/0.29166666666666652/0/0.74814814814814812 |
| DayTrader | 0 | 0.2660538093503631/0.53459409594095941/14.832683982683983/0.65929830979834525/0.62899560929106757/10/0.22641509433962259/0/0.46540590405904059 | 0.25978825690009633/0.4640221402214022/5.2646103896103904/0.47094279148485602/0.73455240274065903/8/0.22641509433962251/0.018867924528301602/0.53597785977859747 |
| DayTrader | 1 | 0.1698876479078443/0.62177121771217714/16.69781946448613/0.489839810782912/0.81472336863136663/9/0.20754716981132071/0.018867924528301799/0.37822878228782286 | 0.31524954980868958/0.43035055350553503/7.4663299663299645/0.68602486651689965/0.59601041786308095/9/0.22641509433962251/0.018867924528301602/0.56964944649446492 |
| DayTrader | 2 | 0.3184115267697879/0.42527675276752769/7.0604118104118099/0.83126002912870534/0.57397739909295775/10/0.2452830188679245/0.056603773584905599/0.57472324723247237 | 0.25698775207309271/0.45710332103321022/7.0852628852628845/0.66226146319940515/0.58347035131700065/9/0.2452830188679245/0/0.54289667896678961 |
| DayTrader | 3 | 0.17729186949387951/0.48431734317343172/4.6917171717171708/0.046216787599682597/0.81611617334639242/5/0.20754716981132071/0/0.51568265682656822 | 0.16353784415381051/0.4501845018450184/4.7542667708108883/0.3749925832896564/0.54359574924179666/4/0.33962264150943372/0/0.54981549815498154 |
| DayTrader | 4 | 0.28865762567911663/0.42573800738007378/7.3237022237022238/0.71797349397888466/0.60020368596578599/9/0.26415094339622641/0.018867924528301799/0.57426199261992616 | 0.30470196739559641/0.44142066420664178/7.2116161616161598/0.65387635664767763/0.62294854996394566/10/0.22641509433962251/0/0.55857933579335795 |
| DayTrader | 5 | 0.17798811290695929/0.34501845018450178/5.6280864197530862/0.81416788718458177/0.66810918700495914/9/0.30188679245283018/0.037735849056603703/0.65498154981549817 | 0.31327326101904912/0.43357933579335772/4.5533648170011807/0.81022303975788235/0.58432734734644742/11/0.22641509433962251/0.075471698113207503/0.56642066420664205 |
| DayTrader | 6 | 0.3198640107365095/0.42158671586715868/7.6715963049296381/0.71797349397888477/0.58181152128561764/9/0.2452830188679245/0.018867924528301799/0.57841328413284132 | 0.31407269100366292/0.42988929889298882/6.423271173271174/0.83872116116576845/0.59149350778491272/11/0.2452830188679245/0.056603773584905502/0.57011070110701112 |
| DayTrader | 7 | 0.18738011209678529/0.60332103321033215/6.599503968253968/0.32843198463262657/0.74633925477584195/8/0.1886792452830188/0/0.39667896678966791 | 0.32176264365272772/0.40959409594095941/6.6752429388793022/0.92317960926226916/0.54686906915457834/11/0.26415094339622641/0.075471698113207503/0.59040590405904025 |
| DayTrader | 8 | 0.30536289334295558/0.44234317343173429/5.452452408702408/0.60347870157431982/0.63157312385646625/8/0.2452830188679245/0.018867924528301799/0.55765682656826565 | 0.15980663900273681/0.53182656826568264/13.224944561157796/0.69555881476100956/0.78253928018257002/8/0.320754716981132/0/0.4681734317343173 |
| DayTrader | 9 | 0.26719854202693322/0.48385608856088558/6.508658008658009/0.60671453550239718/0.70495173071528205/9/0.20754716981132071/0.018867924528301799/0.51614391143911442 | 0.32145882834520212/0.42250922509225092/7.0262626262626258/0.77358490566037696/0.55062324798047635/10/0.22641509433962251/0.037735849056603703/0.57749077490774903 |
| DayTrader | 10 | 0.28485833866641241/0.46632841328413283/8.0498051948051952/0.58490566037735847/0.69043089661912782/10/0.22641509433962259/0/0.53367158671586712 | 0.32120075553845923/0.42204797047970471/8.4207944832944825/0.64895786875169204/0.53444077439510163/8/0.2452830188679245/0.018867924528301602/0.57795202952029523 |
| DayTrader | 11 | 0.17239093285766799/0.57702952029520294/23.901388888888889/0.60406832428611767/0.7654203450148932/6/0.30188679245283018/0/0.42297047970479706 | 0.31499094511240311/0.43588560885608851/6.0699374699374697/0.64261835343118456/0.56736347025748834/9/0.22641509433962251/0.018867924528301602/0.56411439114391115 |
| DayTrader | 12 | 0.30005814616494869/0.4372693726937269/5.6718073593073592/0.51152610232928142/0.58332978004933977/8/0.22641509433962259/0/0.5627306273062731 | 0.30174849113574181/0.42158671586715862/6.9447688674961405/0.91465657687100566/0.58889642725379876/11/0.26415094339622641/0.056603773584905502/0.57841328413284132 |
| DayTrader | 13 | 0.32459676389891201/0.41789667896678961/7.9497354497354502/0.74426728012513277/0.56229782254486149/9/0.2452830188679245/0.018867924528301799/0.58210332103321039 | 0.30104969465285042/0.4460332103321033/7.5613516113516113/0.68133849378369005/0.60267144867585354/9/0.22641509433962251/0/0.55396678966789636 |
| DayTrader | 14 | 0.31639768657834161/0.42481549815498149/8.0895285270285271/0.63115957296897096/0.58557249338859418/8/0.2452830188679245/0.018867924528301799/0.57518450184501846 | 0.32459676389891201/0.41789667896678961/7.6179098679098685/0.77381496809093875/0.56093191610184345/9/0.26415094339622641/0.037735849056603703/0.58210332103321005 |
| DayTrader | 15 | 0.19694082664996401/0.39206642066420661/6.6310356310356315/0.66628088992488965/0.68753391778259543/8/0.26415094339622641/0/0.60793357933579339 | 0.32176264365272772/0.40959409594095941/6.6752429388793022/0.92317960926226916/0.54686906915457834/11/0.26415094339622641/0.075471698113207503/0.59040590405904025 |
| DayTrader | 16 | 0.28224452706934799/0.45710332103321027/5.4418185980685978/0.60347870157431982/0.68580044535045404/8/0.2452830188679245/0/0.54289667896678961 | 0.32459676389891201/0.41789667896678961/7.1948551448551452/0.80072057260086582/0.56870880469639773/10/0.2452830188679245/0.037735849056603703/0.58210332103321005 |
| DayTrader | 17 | 0.3008659800043571/0.45156826568265679/5.2777922077922081/0.7011661953230961/0.61859589080456767/10/0.22641509433962259/0.037735849056603703/0.54843173431734316 | 0.32335618472651512/0.41881918819188191/7.2696903096903105/0.86071658324204092/0.53629589846044334/10/0.26415094339622641/0.056603773584905502/0.58118081180811776 |
| DayTrader | 18 | 0.31339219152108477/0.42850553505535049/6.866421911421912/0.835531691527718/0.580613504346154/10/0.26415094339622641/0.056603773584905599/0.57149446494464939 | 0.31295210611238933/0.43496309963099622/6.5211858848222484/0.79065384300969666/0.56236981717724643/11/0.22641509433962251/0.056603773584905502/0.56503690036900345 |
| DayTrader | 19 | 0.26632475388407029/0.43588560885608851/14.142612942612944/0.5059278368978084/0.65845780757664873/8/0.2452830188679245/0/0.56411439114391149 | 0.31246978867390141/0.4321955719557195/6.7763558663558667/0.78726966207641735/0.60613760757314661/10/0.2452830188679245/0.037735849056603703/0.56780442804428044 |
| DayTrader | 20 | 0.32459676389891201/0.41789667896678961/7.9497354497354502/0.74426728012513277/0.56229782254486149/9/0.2452830188679245/0.018867924528301799/0.58210332103321039 | 0.14590549301480091/0.51983394833948315/12.972835497835495/0.85261309642981153/0.72120774195686665/11/0.30188679245283012/0.056603773584905502/0.48016605166051662 |
| DayTrader | 21 | 0.32459676389891201/0.41789667896678961/7.0977855477855485/0.85240430174162407/0.5429508424933509/10/0.26415094339622641/0.056603773584905599/0.58210332103321039 | 0.29887607484239032/0.43726937269372668/7.4318015318015309/0.74067118590152925/0.60246773793424802/10/0.2452830188679245/0.037735849056603703/0.5627306273062731 |
| DayTrader | 22 | 0.31455468930842428/0.43081180811808117/6.2674144037780399/0.84337723164630229/0.59866699554001424/11/0.22641509433962259/0.056603773584905599/0.56918819188191883 | 0.14013885295679501/0.43450184501845002/9.6175396825396824/0.81831126196986526/0.77501636233877225/10/0.28301886792452802/0.018867924528301602/0.56549815498154965 |
| DayTrader | 23 | 0.19081548028349279/0.48247232472324719/17.90077541506113/0.5597130933657104/0.75161080776576861/7/0.2452830188679245/0/0.51752767527675281 | 0.30988757131575001/0.42896678966789642/7.1834998334998348/0.86894935393731743/0.54840061217864366/10/0.26415094339622641/0.056603773584905502/0.5710332103321033 |
| DayTrader | 24 | 0.32459676389891201/0.41789667896678961/6.5407774044137685/0.8929931748074893/0.56870880469639773/11/0.2452830188679245/0.075471698113207503/0.58210332103321039 | 0.29950519379501922/0.43542435424354242/7.1869796869796865/0.81504192703604406/0.63637908018089095/11/0.26415094339622641/0.018867924528301602/0.56457564575645725 |
| DayTrader | 25 | 0.30456676107351471/0.441420664206642/7.2128020128020118/0.68602486651689976/0.6350380204864785/9/0.2452830188679245/0/0.55857933579335795 | 0.32459676389891201/0.41789667896678961/8.5934523809523817/0.64455437179391395/0.56052835612303653/8/0.2452830188679245/0.018867924528301602/0.58210332103321005 |
| DayTrader | 26 | 0.1414578326479759/0.52167896678966785/15.911111111111111/0.41035024850814228/0.78484829382340093/6/0.22641509433962259/0/0.47832103321033209 | 0.32311811096662613/0.41974169741697392/5.5936674436674441/0.73560712036294051/0.57622653800679302/9/0.26415094339622641/0.037735849056603703/0.58025830258302546 |
| DayTrader | 27 | 0.2697474630996311/0.4372693726937269/7.0289577089577078/0.80515427522082528/0.59406990716586794/10/0.26415094339622641/0.018867924528301799/0.5627306273062731 | 0.30703834540651648/0.44649446494464923/7.7857142857142847/0.72242225355006195/0.61287788121175202/9/0.2452830188679245/0.018867924528301602/0.55350553505535061 |
| DayTrader | 28 | 0.3217160501286746/0.42297047970479701/7.1042857142857141/0.74067118590152914/0.59038814703921005/10/0.22641509433962259/0.037735849056603703/0.57702952029520294 | 0.15772844017646781/0.66466789667896675/8.2111291486291496/0.3917082923023904/0.7889820692666617/8/0.20754716981132071/0/0.33533210332103303 |
| DayTrader | 29 | 0.31401045992701621/0.42850553505535049/7.3509539842873188/0.69067944217823107/0.59789287163161875/9/0.22641509433962259/0.018867924528301799/0.57149446494464939 | 0.13502494774717111/0.54658671586715835/14.198721913007628/0.54161132431725745/0.81306785165725126/7/0.28301886792452802/0/0.45341328413284132 |
| Xerces-J | 0 | 0.6445400584325518/0.22904385334291871/3.7196161217625847/1.134130883083136/0.41862844397167187/27/0.14004914004913999/0.0012285012285012001/0.77095614665708123 | 0.65975444195277955/0.2102947519769949/8.3119051885321973/1.2843238580427818/0.38743299874057813/30/0.14496314496314491/0.011056511056511001/0.78970524802300501 |
| Xerces-J | 1 | 0.63819939603522413/0.23390366642703089/1.112041898559373/1.238915318974344/0.42540891670347281/29/0.1461916461916461/0.0036855036855036002/0.76609633357296913 | 0.66151914293438985/0.2087994248741912/8.337180593738605/1.2847820672188999/0.38751061880264831/30/0.14619164619164601/0.0122850122850121/0.79120057512580855 |
| Xerces-J | 2 | 0.63020160102870937/0.2431631919482386/8.8332822269063556/1.2128885058444507/0.4277240931550701/29/0.14250614250614249/0.0049140049140049/0.75683680805176134 | 0.66051159611368215/0.2096046010064701/8.0710642040951743/1.3190385138584708/0.38445925714281493/31/0.14619164619164601/0.0135135135135135/0.79039539899352984 |
| Xerces-J | 3 | 0.63641353861039707/0.23746944644140899/8.5216390012315966/1.1985501265320009/0.44026076985286988/29/0.1388206388206388/0.0061425061425060996/0.7625305535585909 | 0.66057151256332436/0.20931703810208471/8.0681103606820024/1.3160201505210101/0.3875944403566805/31/0.14496314496314491/0.0135135135135135/0.7906829618979152 |
| Xerces-J | 4 | 0.63234478978295339/0.2437383177570093/3.8963290889673945/1.2074998506251751/0.4347542763667992/29/0.1388206388206388/0.0012285012285012001/0.75626168224299062 | 0.66151614119939917/0.20885693745506831/8.0689461274527865/1.3125671853101499/0.38726933998467672/31/0.1437346437346437/0.0135135135135135/0.79114306254493172 |
| Xerces-J | 5 | 0.63063836835445553/0.24209920920201289/8.3892595917622597/1.1971616830479741/0.4343012981789095/29/0.14004914004913999/0.0024570024570024001/0.75790079079798711 | 0.66050210798495546/0.20994967649173241/8.0711190811117248/1.3126384721797144/0.38740546571461082/31/0.14496314496314491/0.0122850122850121/0.79005032350826743 |
| Xerces-J | 6 | 0.63605517362568531/0.2395111430625449/3.8914034353627631/1.146495110342064/0.42911221495647667/27/0.14496314496314491/0.0024570024570024001/0.76048885693745505 | 0.66151914293438985/0.2087994248741912/8.3373020139290226/1.2845706063703295/0.38822607644591772/30/0.14496314496314491/0.0122850122850121/0.79120057512580855 |
| Xerces-J | 7 | 0.63418724397006132/0.2396836808051761/3.4750488911135551/1.2060128421171543/0.42319212795056527/29/0.1412776412776412/0.0049140049140049/0.7603163191948239 | 0.65864084788678912/0.2116750539180445/8.0700468475517901/1.3165533057103995/0.38424145078674071/31/0.14496314496314491/0.0135135135135135/0.78832494608195525 |
| Xerces-J | 8 | 0.63002186491057033/0.2431344356578001/8.3536041230581812/1.2040878903204473/0.44830085749075022/29/0.14496314496314491/0.0036855036855036002/0.75686556434219987 | 0.66142909874045785/0.2089144500359453/8.069567794028135/1.3150955028303588/0.38612787711636071/31/0.14496314496314491/0.0135135135135135/0.79108554996405445 |
| Xerces-J | 9 | 0.6388500663348492/0.23815959741193379/8.8488320661618953/1.1924665987157697/0.39636467710675327/28/0.1437346437346437/0.0036855036855036002/0.76184040258806618 | 0.65718917742229976/0.21199137311286831/8.0667760199562171/1.3186482913305175/0.38708202181436008/31/0.14496314496314491/0.0135135135135135/0.78800862688713125 |
| Xerces-J | 10 | 0.65065294248072036/0.22035945363048159/3.4857120149502694/1.2298739259652731/0.40204443016187619/29/0.1437346437346437/0.0073710073710073001/0.77964054636951829 | 0.66067126608821691/0.20989216391085541/8.0670792022224234/1.3136360821598527/0.38724960941420822/31/0.14496314496314491/0.0135135135135135/0.79010783608914426 |
| Xerces-J | 11 | 0.63930430202169541/0.2335298346513299/8.5309300034524007/1.2310832816176889/0.40895866371894862/29/0.14004914004913999/0.0085995085995085995/0.76647016534867007 | 0.66151914293438985/0.2087994248741912/8.0687653361834233/1.3145261655890887/0.38873194738704031/31/0.14496314496314491/0.0135135135135135/0.79120057512580855 |
| Xerces-J | 12 | 0.62961131728515973/0.24264557872034501/0.89467946900540707/1.1895571749773652/0.42056790925721621/28/0.14496314496314491/0.0012285012285012001/0.75735442127965491 | 0.66142452130132834/0.2089144500359453/8.3204850755890281/1.2790603534775595/0.38916781974038422/30/0.14496314496314491/0.0122850122850121/0.79108554996405445 |
| Xerces-J | 13 | 0.64438634189907795/0.22711718188353699/2.2771743943854217/1.1834312447601769/0.42794880692530179/28/0.14250614250614249/0.0012285012285012001/0.77288281811646298 | 0.66151914293438985/0.2087994248741912/8.6181944987648667/1.2485924679897535/0.38873194738704031/29/0.14496314496314491/0.011056511056511001/0.79120057512580855 |
| Xerces-J | 14 | 0.64119572376804923/0.2299640546369518/8.289614165721126/1.2684678233359443/0.40866074739916891/30/0.14004914004913999/0.0085995085995085995/0.7700359453630482 | 0.66120778693885296/0.20897196261682241/8.0677460510329908/1.3143837927453998/0.38600427115074032/31/0.14496314496314491/0.0135135135135135/0.79102803738317762 |
| Xerces-J | 15 | 0.63595934757746841/0.23396117900790789/8.5943412179631835/1.2501688697817359/0.40247818583387041/29/0.1461916461916461/0.0073710073710073001/0.76603882099209197 | 0.65993907015472175/0.210409777138749/8.1183925075533239/1.319995843706075/0.393203020082174/31/0.14496314496314491/0.0135135135135135/0.78959022286125091 |
| Xerces-J | 16 | 0.63400255085456736/0.237411933860532/8.8693193089230284/1.1989693670726742/0.41115176154927913/28/0.1437346437346437/0.0049140049140049/0.76258806613946806 | 0.66079980153820161/0.20925952552120761/8.0696646119455497/1.3169086225867788/0.38699130386354502/31/0.14496314496314491/0.0135135135135135/0.79074047447879225 |
| Xerces-J | 17 | 0.6489239551166387/0.22312005751258079/8.6620131916023926/1.2407509664871843/0.39506008049944163/29/0.14496314496314491/0.0085995085995085995/0.7768799424874191 | 0.66151914293438985/0.2087994248741912/8.0687653361834233/1.3145261655890887/0.38873194738704031/31/0.14496314496314491/0.0135135135135135/0.79120057512580855 |
| Xerces-J | 18 | 0.62032377722455934/0.25380301941049599/0.88897094695229495/1.2469402451630931/0.43605604691999011/30/0.14004914004913999/0.0061425061425060996/0.7461969805895039 | 0.65938533191448745/0.21084112149532711/8.3565652775121269/1.280829041536546/0.3862766047014447/30/0.14496314496314491/0.0098280098280098/0.78915887850467292 |
| Xerces-J | 19 | 0.63991516790956848/0.2321207764198418/0.98318321869938097/1.2282714772877512/0.41248324942256553/29/0.1437346437346437/0.0061425061425060996/0.76787922358015814 | 0.66139497447131834/0.20911574406901501/8.069293873736445/1.3143481971247724/0.38528412233155412/31/0.1437346437346437/0.0135135135135135/0.79088425593098455 |
| Xerces-J | 20 | 0.62934051820242942/0.24460100647016531/8.8917275754272751/1.186248826942371/0.42876358679564464/28/0.1437346437346437/0.0036855036855036002/0.75539899352983464 | 0.66151256723283625/0.2087994248741912/8.0678961439896089/1.3140277931479822/0.38583617237821671/31/0.14496314496314491/0.0135135135135135/0.79120057512580855 |
| Xerces-J | 21 | 0.63360001405773314/0.24115025161754131/8.5603955797526119/1.2240952933113811/0.4053480938519034/29/0.1412776412776412/0.0085995085995085995/0.75884974838245867 | 0.65758467295923595/0.21259525521207751/8.0440994632462655/1.3174414182205771/0.38821765888878662/31/0.14496314496314491/0.0135135135135135/0.78740474478792233 |
| Xerces-J | 22 | 0.63256901814635325/0.23873472322070449/8.2704962072405603/1.2655733217139431/0.414922531431407/30/0.14250614250614249/0.0061425061425060996/0.76126527677929545 | 0.66121903145466765/0.20911574406901501/8.0694885524223139/1.3150955028303588/0.38699671449371631/31/0.14496314496314491/0.0135135135135135/0.79088425593098455 |
| Xerces-J | 23 | 0.64774975908080923/0.2251617541337167/3.6165225708687743/1.1834669522760886/0.41251749692805195/28/0.1388206388206388/0.0061425061425060996/0.77483824586628325 | 0.66151914293438985/0.2087994248741912/8.9308619118886181/1.2198986269944039/0.3869715688121082/28/0.14619164619164601/0.0098280098280098/0.79120057512580855 |
| Xerces-J | 24 | 0.63207866240871668/0.24212796549245141/8.2792557500351975/1.2464318008547099/0.42046305938977613/30/0.1437346437346437/0.011056511056511001/0.75787203450754848 | 0.66204481412553795/0.20862688713155991/8.3377792809534679/1.2807229891335243/0.38632029909276311/30/0.14619164619164601/0.011056511056511001/0.79137311286843992 |
| Xerces-J | 25 | 0.64244014138339467/0.23174694464414089/8.5434903390104058/1.2218048453131405/0.41168713216168229/29/0.14496314496314491/0.0049140049140049/0.76825305535585908 | 0.66151914293438985/0.2087994248741912/8.0687653361834233/1.3145261655890887/0.38873194738704031/31/0.14496314496314491/0.0135135135135135/0.79120057512580855 |
| Xerces-J | 26 | 0.63410908887938722/0.2387922358015816/8.2314229347878811/1.2521579752278154/0.41169889344774901/30/0.14004914004913999/0.0061425061425060996/0.7612077641984184 | 0.66049344181892145/0.2093745506829619/8.0701596936972262/1.3184353939989015/0.38721113787416872/31/0.14496314496314491/0.0135135135135135/0.79062544931703815 |
| Xerces-J | 27 | 0.63306327572602239/0.24264557872034501/3.6845989357803335/1.1978057076849282/0.40740968489977303/28/0.14496314496314491/0.0073710073710073001/0.75735442127965491 | 0.66104479024810203/0.20940330697340021/8.067974841997799/1.3123533014676931/0.3874423958280499/31/0.1437346437346437/0.0135135135135135/0.79059669302659952 |
| Xerces-J | 28 | 0.65210526208073682/0.21932422717469441/3.4573180814214917/1.2638907569790572/0.41290614060656994/30/0.14742014742014739/0.0073710073710073001/0.78067577282530554 | 0.64960415570778585/0.2209920920201292/8.0496672935840596/1.315557907912452/0.3865762911593103/31/0.14496314496314491/0.0135135135135135/0.77900790797987063 |
| Xerces-J | 29 | 0.63270340077763965/0.24080517613227889/3.6033790581492142/1.2036879862635033/0.42671349578534912/29/0.1412776412776412/0.0012285012285012001/0.75919482386772108 | 0.66122506510738244/0.2090294751976994/8.0707713782731663/1.3165888417131688/0.3876332449014393/31/0.14496314496314491/0.0135135135135135/0.79097052480230035 |

<!-- BEGIN GENERATED: selected_fsemantic_pairs -->
**Selected `f_semantic` pairs.** Stage 2 uses only the frozen 5% modularity-band profile; both partitions are evaluated on the same final Declaration + Method Body graph.

| subject | seed | stage2_solution_id | stage3_solution_id | stage2_f_semantic | stage3_f_semantic | delta_stage3_minus_stage2 |
|---|---|---|---|---|---|---|
| daytrader | 0 | seed0_solution054 | seed0_solution041 | 0.6289956092910673 | 0.734552402740659 | 0.10555679344959168 |
| daytrader | 1 | seed1_solution064 | seed1_solution032 | 0.8147233686313666 | 0.596010417863081 | -0.21871295076828567 |
| daytrader | 2 | seed2_solution041 | seed2_solution034 | 0.5739773990929578 | 0.583470351317001 | 0.009492952224043227 |
| daytrader | 3 | seed3_solution060 | seed3_solution043 | 0.8161161733463924 | 0.5435957492417968 | -0.27252042410459565 |
| daytrader | 4 | seed4_solution042 | seed4_solution043 | 0.6002036859657859 | 0.622948549963946 | 0.022744863998160114 |
| daytrader | 5 | seed5_solution037 | seed5_solution034 | 0.6681091870049591 | 0.5843273473464473 | -0.08378183965851183 |
| daytrader | 6 | seed6_solution038 | seed6_solution030 | 0.5818115212856176 | 0.5914935077849127 | 0.009681986499295081 |
| daytrader | 7 | seed7_solution074 | seed7_solution038 | 0.746339254775842 | 0.5468690691545783 | -0.19947018562126362 |
| daytrader | 8 | seed8_solution052 | seed8_solution042 | 0.6315731238564661 | 0.78253928018257 | 0.15096615632610388 |
| daytrader | 9 | seed9_solution051 | seed9_solution034 | 0.7049517307152819 | 0.5506232479804762 | -0.1543284827348057 |
| daytrader | 10 | seed10_solution040 | seed10_solution032 | 0.6904308966191277 | 0.5344407743951016 | -0.15599012222402608 |
| daytrader | 11 | seed11_solution061 | seed11_solution030 | 0.7654203450148932 | 0.5673634702574886 | -0.19805687475740463 |
| daytrader | 12 | seed12_solution034 | seed12_solution031 | 0.5833297800493398 | 0.5888964272537991 | 0.0055666472044593185 |
| daytrader | 13 | seed13_solution033 | seed13_solution032 | 0.5622978225448614 | 0.6026714486758535 | 0.04037362613099216 |
| daytrader | 14 | seed14_solution042 | seed14_solution029 | 0.5855724933885942 | 0.5609319161018438 | -0.024640577286750398 |
| daytrader | 15 | seed15_solution030 | seed15_solution029 | 0.6875339177825954 | 0.5468690691545783 | -0.1406648486280171 |
| daytrader | 16 | seed16_solution039 | seed16_solution036 | 0.685800445350454 | 0.5687088046963976 | -0.11709164065405642 |
| daytrader | 17 | seed17_solution037 | seed17_solution027 | 0.6185958908045677 | 0.5362958984604432 | -0.08229999234412444 |
| daytrader | 18 | seed18_solution034 | seed18_solution032 | 0.580613504346154 | 0.5623698171772464 | -0.018243687168907563 |
| daytrader | 19 | seed19_solution030 | seed19_solution031 | 0.6584578075766486 | 0.6061376075731466 | -0.052320200003502015 |
| daytrader | 20 | seed20_solution038 | seed20_solution040 | 0.5622978225448614 | 0.721207741956867 | 0.1589099194120056 |
| daytrader | 21 | seed21_solution030 | seed21_solution034 | 0.5429508424933509 | 0.602467737934248 | 0.05951689544089711 |
| daytrader | 22 | seed22_solution037 | seed22_solution034 | 0.5986669955400141 | 0.7750163623387722 | 0.17634936679875812 |
| daytrader | 23 | seed23_solution055 | seed23_solution029 | 0.7516108077657686 | 0.548400612178644 | -0.2032101955871246 |
| daytrader | 24 | seed24_solution029 | seed24_solution038 | 0.5687088046963976 | 0.6363790801808911 | 0.06767027548449345 |
| daytrader | 25 | seed25_solution047 | seed25_solution026 | 0.6350380204864785 | 0.5605283561230365 | -0.07450966436344197 |
| daytrader | 26 | seed26_solution052 | seed26_solution038 | 0.7848482938234009 | 0.576226538006793 | -0.2086217558166079 |
| daytrader | 27 | seed27_solution030 | seed27_solution029 | 0.5940699071658679 | 0.612877881211752 | 0.01880797404588408 |
| daytrader | 28 | seed28_solution041 | seed28_solution068 | 0.59038814703921 | 0.7889820692666617 | 0.19859392222745165 |
| daytrader | 29 | seed29_solution040 | seed29_solution051 | 0.5978928716316187 | 0.8130678516572516 | 0.21517498002563284 |
| jpetstore | 0 | seed0_solution006 | seed0_solution000 | 0.5573173106318791 | 0.5122600685375185 | -0.04505724209436057 |
| jpetstore | 1 | seed1_solution007 | seed1_solution000 | 0.5076000559033871 | 0.5122600685375185 | 0.004660012634131405 |
| jpetstore | 2 | seed2_solution008 | seed2_solution000 | 0.5076000559033871 | 0.5122600685375185 | 0.004660012634131405 |
| jpetstore | 3 | seed3_solution007 | seed3_solution000 | 0.5573173106318791 | 0.5122600685375185 | -0.04505724209436057 |
| jpetstore | 4 | seed4_solution007 | seed4_solution000 | 0.5076000559033871 | 0.5122600685375185 | 0.004660012634131405 |
| jpetstore | 5 | seed5_solution009 | seed5_solution000 | 0.5076000559033871 | 0.5122600685375185 | 0.004660012634131405 |
| jpetstore | 6 | seed6_solution011 | seed6_solution000 | 0.5508426618865075 | 0.5122600685375185 | -0.03858259334898906 |
| jpetstore | 7 | seed7_solution007 | seed7_solution000 | 0.5573173106318791 | 0.5122600685375185 | -0.04505724209436057 |
| jpetstore | 8 | seed8_solution009 | seed8_solution001 | 0.5573173106318791 | 0.5122600685375185 | -0.04505724209436057 |
| jpetstore | 9 | seed9_solution008 | seed9_solution000 | 0.5076000559033871 | 0.5122600685375185 | 0.004660012634131405 |
| jpetstore | 10 | seed10_solution002 | seed10_solution002 | 0.486999555759999 | 0.5122600685375185 | 0.025260512777519506 |
| jpetstore | 11 | seed11_solution008 | seed11_solution000 | 0.5076000559033871 | 0.5122600685375185 | 0.004660012634131405 |
| jpetstore | 12 | seed12_solution008 | seed12_solution002 | 0.5076000559033871 | 0.465669060335721 | -0.04193099556766611 |
| jpetstore | 13 | seed13_solution009 | seed13_solution000 | 0.5076000559033871 | 0.5122600685375185 | 0.004660012634131405 |
| jpetstore | 14 | seed14_solution009 | seed14_solution003 | 0.5076000559033871 | 0.5335905639617965 | 0.02599050805840941 |
| jpetstore | 15 | seed15_solution008 | seed15_solution001 | 0.5573173106318791 | 0.5122600685375185 | -0.04505724209436057 |
| jpetstore | 16 | seed16_solution007 | seed16_solution008 | 0.5573173106318791 | 0.5327142246541845 | -0.02460308597769456 |
| jpetstore | 17 | seed17_solution002 | seed17_solution000 | 0.486999555759999 | 0.5122600685375185 | 0.025260512777519506 |
| jpetstore | 18 | seed18_solution007 | seed18_solution000 | 0.5076000559033871 | 0.5122600685375185 | 0.004660012634131405 |
| jpetstore | 19 | seed19_solution008 | seed19_solution002 | 0.5573173106318791 | 0.5121137245107963 | -0.04520358612108277 |
| jpetstore | 20 | seed20_solution002 | seed20_solution000 | 0.486999555759999 | 0.5122600685375185 | 0.025260512777519506 |
| jpetstore | 21 | seed21_solution008 | seed21_solution000 | 0.5076000559033871 | 0.5122600685375185 | 0.004660012634131405 |
| jpetstore | 22 | seed22_solution009 | seed22_solution000 | 0.5076000559033871 | 0.5122600685375185 | 0.004660012634131405 |
| jpetstore | 23 | seed23_solution008 | seed23_solution000 | 0.5076000559033871 | 0.5122600685375185 | 0.004660012634131405 |
| jpetstore | 24 | seed24_solution009 | seed24_solution000 | 0.5328605686809068 | 0.5122600685375185 | -0.020600500143388323 |
| jpetstore | 25 | seed25_solution009 | seed25_solution000 | 0.5573173106318791 | 0.5122600685375185 | -0.04505724209436057 |
| jpetstore | 26 | seed26_solution009 | seed26_solution000 | 0.5076000559033871 | 0.5122600685375185 | 0.004660012634131405 |
| jpetstore | 27 | seed27_solution007 | seed27_solution000 | 0.5573173106318791 | 0.5122600685375185 | -0.04505724209436057 |
| jpetstore | 28 | seed28_solution008 | seed28_solution000 | 0.5076000559033871 | 0.5122600685375185 | 0.004660012634131405 |
| jpetstore | 29 | seed29_solution009 | seed29_solution000 | 0.5573173106318791 | 0.5122600685375185 | -0.04505724209436057 |
| xerces | 0 | seed0_solution021 | seed0_solution018 | 0.418628443971672 | 0.38743299874057846 | -0.03119544523109352 |
| xerces | 1 | seed1_solution019 | seed1_solution017 | 0.4254089167034729 | 0.3875106188026485 | -0.03789829790082444 |
| xerces | 2 | seed2_solution022 | seed2_solution014 | 0.4277240931550701 | 0.38445925714281526 | -0.04326483601225484 |
| xerces | 3 | seed3_solution012 | seed3_solution013 | 0.44026076985287 | 0.38759444035668067 | -0.052666329496189324 |
| xerces | 4 | seed4_solution018 | seed4_solution017 | 0.4347542763667993 | 0.38726933998467694 | -0.04748493638212237 |
| xerces | 5 | seed5_solution016 | seed5_solution015 | 0.4343012981789095 | 0.3874054657146111 | -0.046895832464298404 |
| xerces | 6 | seed6_solution021 | seed6_solution017 | 0.4291122149564768 | 0.388226076445918 | -0.04088613851055878 |
| xerces | 7 | seed7_solution022 | seed7_solution013 | 0.4231921279505654 | 0.38424145078674077 | -0.03895067716382461 |
| xerces | 8 | seed8_solution016 | seed8_solution016 | 0.4483008574907502 | 0.3861278771163609 | -0.06217298037438934 |
| xerces | 9 | seed9_solution022 | seed9_solution013 | 0.39636467710675327 | 0.38708202181436047 | -0.009282655292392805 |
| xerces | 10 | seed10_solution022 | seed10_solution018 | 0.4020444301618762 | 0.3872496094142086 | -0.01479482074766758 |
| xerces | 11 | seed11_solution020 | seed11_solution013 | 0.40895866371894873 | 0.3887319473870403 | -0.020226716331908423 |
| xerces | 12 | seed12_solution022 | seed12_solution013 | 0.4205679092572163 | 0.3891678197403844 | -0.03140008951683193 |
| xerces | 13 | seed13_solution022 | seed13_solution015 | 0.4279488069253018 | 0.3887319473870403 | -0.039216859538261484 |
| xerces | 14 | seed14_solution019 | seed14_solution014 | 0.4086607473991689 | 0.38600427115074054 | -0.02265647624842837 |
| xerces | 15 | seed15_solution021 | seed15_solution015 | 0.4024781858338704 | 0.3932030200821741 | -0.00927516575169629 |
| xerces | 16 | seed16_solution022 | seed16_solution015 | 0.41115176154927924 | 0.3869913038635454 | -0.024160457685733827 |
| xerces | 17 | seed17_solution018 | seed17_solution010 | 0.39506008049944163 | 0.3887319473870403 | -0.006328133112401324 |
| xerces | 18 | seed18_solution021 | seed18_solution011 | 0.4360560469199901 | 0.38627660470144487 | -0.049779442218545245 |
| xerces | 19 | seed19_solution014 | seed19_solution012 | 0.41248324942256553 | 0.3852841223315543 | -0.027199127091011244 |
| xerces | 20 | seed20_solution022 | seed20_solution013 | 0.42876358679564475 | 0.38583617237821677 | -0.04292741441742798 |
| xerces | 21 | seed21_solution022 | seed21_solution016 | 0.4053480938519034 | 0.3882176588887869 | -0.017130434963116503 |
| xerces | 22 | seed22_solution014 | seed22_solution015 | 0.414922531431407 | 0.3869967144937164 | -0.027925816937690584 |
| xerces | 23 | seed23_solution015 | seed23_solution013 | 0.41251749692805206 | 0.38697156881210826 | -0.025545928115943806 |
| xerces | 24 | seed24_solution014 | seed24_solution012 | 0.42046305938977613 | 0.3863202990927632 | -0.03414276029701291 |
| xerces | 25 | seed25_solution022 | seed25_solution013 | 0.4116871321616823 | 0.3887319473870403 | -0.02295518477464198 |
| xerces | 26 | seed26_solution022 | seed26_solution017 | 0.411698893447749 | 0.38721113787416894 | -0.024487755573580072 |
| xerces | 27 | seed27_solution024 | seed27_solution020 | 0.40740968489977303 | 0.38744239582804996 | -0.01996728907172307 |
| xerces | 28 | seed28_solution020 | seed28_solution013 | 0.41290614060657005 | 0.38657629115931047 | -0.02632984944725958 |
| xerces | 29 | seed29_solution019 | seed29_solution010 | 0.4267134957853491 | 0.38763324490143936 | -0.03908025088390976 |
<!-- END GENERATED: selected_fsemantic_pairs -->

**Selected-profile descriptive metrics.** The confirmatory selected-`f_semantic` rows use the active Stage 2 5% profile and appear only in the formal six-row family above. The remaining structural metrics below are descriptive; they are not part of the confirmatory Holm family. Relative change is `(Stage3 median−Stage2 median)/|Stage2 median|`; it is NA when the Stage 2 median is zero.

| Subject | Metric | Stage 2 median | Stage 3 median | Paired median Δ | Relative change | B/T/W or I/T/D |
|---|---|---|---|---|---|---|
| JPetStore | weighted_modularity | 0.42773662551440361 | 0.44206980643194632 | 0.010737692424935052 | 0.033509360813573946 | 30/0/0 (better/tie/worse) |
| JPetStore | coupling | 0.27407407407407408 | 0.25185185185185183 | -0.022222222222222254 | -0.081081081081081197 | 26/3/1 (better/tie/worse) |
| JPetStore | cohesion | 4.9000000000000004 | 5.477380952380952 | 0.57738095238095166 | 0.117832847424684 | 30/0/0 (better/tie/worse) |
| JPetStore | imbalance | 0 | 0.2041241452319312 | 0.2041241452319312 | NA | 0/0/30 (better/tie/worse) |
| JPetStore | cluster_count | 4 | 4 | 0 | 0 | 0/30/0 (increase/tie/decrease) |
| JPetStore | max_cluster_ratio | 0.25 | 0.29166666666666652 | 0.041666666666666519 | 0.16666666666666607 | 0/4/26 (better/tie/worse) |
| JPetStore | singleton_ratio | 0 | 0 | 0 | NA | 0/30/0 (better/tie/worse) |
| JPetStore | internal_edge_weight_ratio | 0.72592592592592597 | 0.74814814814814812 | 0.022222222222222143 | 0.030612244897959072 | 26/3/1 (better/tie/worse) |
| DayTrader | weighted_modularity | 0.29435788592203266 | 0.31117867999482574 | 0.012121709518525092 | 0.057144023915324776 | 17/0/13 (better/tie/worse) |
| DayTrader | coupling | 0.43657749077490771 | 0.43404059040590387 | -8.3266726846886741e-17 | -0.0058108821975703297 | 15/0/15 (better/tie/worse) |
| DayTrader | cohesion | 7.1010356310356313 | 7.1909174159174158 | 0.06914428485952584 | 0.012657560045037541 | 18/0/12 (better/tie/worse) |
| DayTrader | imbalance | 0.67615287822089476 | 0.75712804578095305 | 0.078066160780511651 | 0.11975866726045974 | 13/0/17 (better/tie/worse) |
| DayTrader | cluster_count | 9 | 10 | 0.5 | 0.1111111111111111 | 15/6/9 (increase/tie/decrease) |
| DayTrader | max_cluster_ratio | 0.2452830188679245 | 0.2452830188679245 | 0.0094339622641508997 | 0 | 8/7/15 (better/tie/worse) |
| DayTrader | singleton_ratio | 0.018867924528301799 | 0.02830188679245265 | 0.018867924528301602 | 0.49999999999999745 | 9/4/17 (better/tie/worse) |
| DayTrader | internal_edge_weight_ratio | 0.56342250922509229 | 0.56595940959409585 | -1.1102230246251565e-16 | 0.0045026606631188822 | 15/0/15 (better/tie/worse) |
| Xerces-J | weighted_modularity | 0.63507329577376481 | 0.6612134091967603 | 0.024305788934827544 | 0.04116078190808941 | 29/0/1 (better/tie/worse) |
| Xerces-J | coupling | 0.23844716031631913 | 0.20911574406901501 | -0.028152408339324336 | -0.12301013024602039 | 29/0/1 (better/tie/worse) |
| Xerces-J | cohesion | 8.2509595710142207 | 8.0696162029868432 | -0.051369855086192295 | -0.021978457955901302 | 15/0/15 (better/tie/worse) |
| Xerces-J | imbalance | 1.2101941782348129 | 1.3144549791672442 | 0.091112249388071276 | 0.086152125673341046 | 0/0/30 (better/tie/worse) |
| Xerces-J | cluster_count | 29 | 31 | 2 | 0.068965517241379309 | 27/3/0 (increase/tie/decrease) |
| Xerces-J | max_cluster_ratio | 0.1431203931203931 | 0.14496314496314491 | 0.0024570024570023663 | 0.012875536480686513 | 3/7/20 (better/tie/worse) |
| Xerces-J | singleton_ratio | 0.0055282555282554994 | 0.0135135135135135 | 0.0079852579852579507 | 1.4444444444444549 | 0/1/29 (better/tie/worse) |
| Xerces-J | internal_edge_weight_ratio | 0.76155283968368082 | 0.79088425593098455 | 0.028152408339324253 | 0.038515273949325503 | 29/0/1 (better/tie/worse) |

## 10. Partition similarity and selector behaviour

> **Value provenance.** `active Stage 2 canonical labels; Stage 3 selected_solution.json, pareto_front_4d.csv and posthoc_metrics.csv; frozen raw Leiden clusters` — **recomputed**. Partitions are canonical-label normalized. ARI/NMI use scikit-learn 1.9.0. Rank is `1 + count(strictly better)`; favorable percentile is `100 × count(no better than selected)/front_size`, so higher is better. Tolerance is 1e−12.

**Subject behaviour summary.**

<!-- BEGIN GENERATED: partition_similarity -->
`non_identical_pair_proportion` is the number of matching-seed selected partition pairs that are not exactly identical after canonical label normalization, divided by the number of paired seeds. A value of 1.0 does not mean every class changed. `changed_partition_ratio` remains the separate class-level same-cluster-neighbour metric.

| subject | n_pairs | exact_identical_count | non_identical_pair_count | non_identical_pair_proportion | ari_mean | ari_median | nmi_mean | nmi_median | class_level_changed_partition_ratio_mean | definition |
|---|---|---|---|---|---|---|---|---|---|---|
| jpetstore | 30 | 0 | 30 | 1.0 | 0.730516942669876 | 0.736107120023509 | 0.7961113982359874 | 0.81282037916066 | 0.8527777777777777 | matching-seed Stage 2/Stage 3 partition pairs not exactly identical after canonical label normalization, divided by paired seeds |
| daytrader | 30 | 0 | 30 | 1.0 | 0.48336967969605316 | 0.5338838903063949 | 0.6449405796231047 | 0.6990927643631761 | 0.9 | matching-seed Stage 2/Stage 3 partition pairs not exactly identical after canonical label normalization, divided by paired seeds |
| xerces | 30 | 0 | 30 | 1.0 | 0.9558316058211893 | 0.9563786374669818 | 0.9548334816167005 | 0.9557754408883967 | 0.802948402948403 | matching-seed Stage 2/Stage 3 partition pairs not exactly identical after canonical label normalization, divided by paired seeds |
<!-- END GENERATED: partition_similarity -->

**Per-seed selector diagnostics.**

| Subject | Seed | ARI | NMI | S2=S3 | Δ clusters | S3=Leiden | S2 in S3 front | Leiden in S3 front | fsem rank; pct | modularity rank; pct | imbalance rank; pct | minimum fsem |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| JPetStore | 0 | 0.78035470668485674 | 0.83415102130756402 | False | 0 | True | False | True | 40/100; 61% | 1/100; 100% | 14/100; 87% | False |
| JPetStore | 1 | 0.6757617098681219 | 0.75223809951890475 | False | 0 | True | False | True | 60/100; 41% | 1/100; 100% | 22/100; 79% | False |
| JPetStore | 2 | 0.6757617098681219 | 0.75223809951890475 | False | 0 | True | False | True | 60/100; 41% | 1/100; 100% | 13/100; 88% | False |
| JPetStore | 3 | 0.78035470668485674 | 0.83415102130756402 | False | 0 | True | True | True | 40/100; 61% | 1/100; 100% | 16/100; 85% | False |
| JPetStore | 4 | 0.6757617098681219 | 0.75223809951890475 | False | 0 | True | False | True | 37/100; 64% | 1/100; 100% | 14/100; 87% | False |
| JPetStore | 5 | 0.6757617098681219 | 0.75223809951890475 | False | 0 | True | False | True | 47/100; 54% | 1/100; 100% | 13/100; 88% | False |
| JPetStore | 6 | 0.57116871305138694 | 0.67032517773024547 | False | 0 | True | False | True | 57/100; 44% | 1/100; 100% | 19/100; 82% | False |
| JPetStore | 7 | 0.78035470668485674 | 0.83415102130756402 | False | 0 | True | False | True | 63/100; 38% | 1/100; 100% | 26/100; 75% | False |
| JPetStore | 8 | 0.78035470668485674 | 0.83415102130756402 | False | 0 | True | False | True | 49/100; 52% | 1/100; 100% | 19/100; 82% | False |
| JPetStore | 9 | 0.6757617098681219 | 0.75223809951890475 | False | 0 | True | False | True | 61/100; 40% | 1/100; 100% | 20/100; 81% | False |
| JPetStore | 10 | 0.79199638254578342 | 0.83627251870834529 | False | 0 | True | False | True | 42/100; 59% | 1/100; 100% | 14/100; 87% | False |
| JPetStore | 11 | 0.6757617098681219 | 0.75223809951890475 | False | 0 | True | False | True | 61/100; 40% | 1/100; 100% | 26/100; 75% | False |
| JPetStore | 12 | 0.76852698993595614 | 0.83161412951689884 | False | 0 | False | False | False | 38/100; 63% | 1/100; 100% | 14/100; 87% | False |
| JPetStore | 13 | 0.6757617098681219 | 0.75223809951890475 | False | 0 | True | False | True | 50/100; 51% | 1/100; 100% | 18/100; 83% | False |
| JPetStore | 14 | 0.78035470668485674 | 0.83415102130756402 | False | 0 | False | False | False | 56/100; 45% | 1/100; 100% | 16/100; 85% | False |
| JPetStore | 15 | 0.78035470668485674 | 0.83415102130756402 | False | 0 | True | True | True | 38/100; 63% | 1/100; 100% | 13/100; 88% | False |
| JPetStore | 16 | 0.79204339963833637 | 0.8737101996493658 | False | 0 | False | False | False | 74/99; 26.262626262626263% | 1/99; 100% | 40/99; 60.606060606060609% | False |
| JPetStore | 17 | 0.79199638254578342 | 0.83627251870834529 | False | 0 | True | False | True | 39/100; 62% | 1/100; 100% | 15/100; 86% | False |
| JPetStore | 18 | 0.6757617098681219 | 0.75223809951890475 | False | 0 | True | False | True | 46/100; 55% | 1/100; 100% | 15/100; 86% | False |
| JPetStore | 19 | 0.7036872501110617 | 0.7940266288044211 | False | 0 | False | False | False | 37/100; 64% | 1/100; 100% | 48/100; 53% | False |
| JPetStore | 20 | 0.79199638254578342 | 0.83627251870834529 | False | 0 | True | False | True | 44/100; 57% | 1/100; 100% | 15/100; 86% | False |
| JPetStore | 21 | 0.6757617098681219 | 0.75223809951890475 | False | 0 | True | False | True | 54/100; 47% | 1/100; 100% | 16/100; 85% | False |
| JPetStore | 22 | 0.6757617098681219 | 0.75223809951890475 | False | 0 | True | False | True | 65/100; 36% | 1/100; 100% | 18/100; 83% | False |
| JPetStore | 23 | 0.6757617098681219 | 0.75223809951890475 | False | 0 | True | False | True | 45/100; 56% | 1/100; 100% | 14/100; 87% | False |
| JPetStore | 24 | 0.89599819127289171 | 0.91839376973982279 | False | 0 | True | False | True | 51/100; 50% | 1/100; 100% | 15/100; 86% | False |
| JPetStore | 25 | 0.78035470668485674 | 0.83415102130756402 | False | 0 | True | False | True | 44/100; 57% | 1/100; 100% | 16/100; 85% | False |
| JPetStore | 26 | 0.6757617098681219 | 0.75223809951890475 | False | 0 | True | False | True | 40/100; 61% | 1/100; 100% | 16/100; 85% | False |
| JPetStore | 27 | 0.78035470668485674 | 0.83415102130756402 | False | 0 | True | False | True | 65/100; 36% | 1/100; 100% | 17/100; 84% | False |
| JPetStore | 28 | 0.6757617098681219 | 0.75223809951890475 | False | 0 | True | False | True | 52/100; 49% | 1/100; 100% | 19/100; 82% | False |
| JPetStore | 29 | 0.78035470668485674 | 0.83415102130756402 | False | 0 | True | True | True | 49/100; 52% | 1/100; 100% | 24/100; 77% | False |
| DayTrader | 0 | 0.46391690875524272 | 0.66676100365975688 | False | -2 | False | False | False | 65/100; 36% | 3/100; 98% | 31/100; 70% | False |
| DayTrader | 1 | 0.02742174103850626 | 0.3246585309278901 | False | 0 | False | False | False | 19/100; 82% | 1/100; 100% | 49/100; 52% | False |
| DayTrader | 2 | 0.77322589918466145 | 0.83759038264784103 | False | -1 | False | False | False | 18/100; 83% | 1/100; 100% | 42/100; 59% | False |
| DayTrader | 3 | 0.015455118324551568 | 0.1293220191634582 | False | -1 | False | False | False | 32/100; 69% | 1/100; 100% | 29/100; 72% | False |
| DayTrader | 4 | 0.76432668526022207 | 0.84520904122384022 | False | 1 | False | False | False | 67/100; 34% | 1/100; 100% | 73/100; 28% | False |
| DayTrader | 5 | 0.15597169422246904 | 0.48433656918554024 | False | 2 | False | False | False | 28/100; 73% | 1/100; 100% | 52/100; 49% | False |
| DayTrader | 6 | 0.83954966360260652 | 0.89524240068265182 | False | 2 | False | False | False | 17/99; 83.838383838383834% | 1/99; 100% | 45/99; 55.555555555555557% | False |
| DayTrader | 7 | 0.35127597019035184 | 0.59563097121797903 | False | 3 | False | False | False | 12/100; 89% | 1/100; 100% | 58/100; 43% | False |
| DayTrader | 8 | 0.1485622198720854 | 0.40635866445913049 | False | 0 | False | False | False | 66/100; 35% | 1/100; 100% | 47/100; 54% | False |
| DayTrader | 9 | 0.51397876787052166 | 0.7079450207204192 | False | 1 | False | False | False | 15/100; 86% | 1/100; 100% | 51/100; 50% | False |
| DayTrader | 10 | 0.57001208873216691 | 0.72394403014719788 | False | -2 | False | False | False | 9/100; 92% | 1/100; 100% | 40/100; 61% | False |
| DayTrader | 11 | 0.13226360867022363 | 0.3408644437471352 | False | 3 | False | False | False | 17/100; 84% | 1/100; 100% | 47/100; 54% | False |
| DayTrader | 12 | 0.68907286583694283 | 0.79490873645379301 | False | 3 | False | False | False | 22/100; 79% | 1/100; 100% | 66/100; 35% | False |
| DayTrader | 13 | 0.82519130826206166 | 0.87599243591539977 | False | 0 | False | False | False | 31/100; 70% | 1/100; 100% | 52/100; 49% | False |
| DayTrader | 14 | 0.84371590255806583 | 0.89074256708248978 | False | 1 | False | False | False | 17/100; 84% | 1/100; 100% | 52/100; 49% | False |
| DayTrader | 15 | 0.42090102319047601 | 0.63809091815785812 | False | 3 | False | False | False | 8/100; 93% | 1/100; 100% | 65/100; 36% | False |
| DayTrader | 16 | 0.69768433656878304 | 0.82721863822142161 | False | 2 | False | False | False | 18/100; 83% | 1/100; 100% | 58/100; 43% | False |
| DayTrader | 17 | 0.73477019395503285 | 0.81966357198754225 | False | 0 | False | False | False | 10/100; 91% | 1/100; 100% | 61/100; 40% | False |
| DayTrader | 18 | 0.78358038768529081 | 0.88668847513829319 | False | 1 | False | False | False | 13/100; 88% | 1/100; 100% | 56/100; 45% | False |
| DayTrader | 19 | 0.55378901274226822 | 0.69024050800593295 | False | 2 | False | False | False | 24/100; 77% | 1/100; 100% | 53/100; 48% | False |
| DayTrader | 20 | 0.095026310757899468 | 0.45068010160748279 | False | 2 | False | False | False | 60/100; 41% | 1/100; 100% | 64/100; 37% | False |
| DayTrader | 21 | 0.8012225766932729 | 0.86859263808340914 | False | 0 | False | False | False | 23/100; 78% | 1/100; 100% | 53/100; 48% | False |
| DayTrader | 22 | 0.087819947043248012 | 0.41506105539982652 | False | -1 | False | False | False | 70/100; 31% | 2/100; 99% | 53/100; 48% | False |
| DayTrader | 23 | 0.17917810096181294 | 0.4139305048307817 | False | 3 | False | False | False | 17/100; 84% | 1/100; 100% | 56/100; 45% | False |
| DayTrader | 24 | 0.79952054824266161 | 0.86289039156625402 | False | 0 | False | False | False | 41/100; 60% | 1/100; 100% | 51/100; 50% | False |
| DayTrader | 25 | 0.90822936805524723 | 0.91389434367258082 | False | -1 | False | False | False | 16/100; 85% | 1/100; 100% | 57/100; 44% | False |
| DayTrader | 26 | 0.076201698826533118 | 0.28699674515035439 | False | 3 | False | False | False | 15/100; 86% | 1/100; 100% | 58/100; 43% | False |
| DayTrader | 27 | 0.8414588546610291 | 0.85763249068173697 | False | -1 | False | False | False | 24/100; 77% | 2/100; 99% | 54/100; 47% | False |
| DayTrader | 28 | 0.31806136457967499 | 0.53802338195922295 | False | -2 | False | False | False | 77/100; 24% | 2/100; 99% | 25/100; 76% | False |
| DayTrader | 29 | 0.089706224537685217 | 0.35910680699591802 | False | -2 | False | False | False | 88/100; 13% | 3/100; 98% | 38/100; 63% | False |
| Xerces-J | 0 | 0.96710323949056753 | 0.95949592308873655 | False | 3 | False | False | False | 1/100; 100% | 1/100; 100% | 73/100; 28% | True |
| Xerces-J | 1 | 0.96466139993304834 | 0.95168743874947204 | False | 1 | False | False | False | 1/100; 100% | 1/100; 100% | 72/100; 29% | True |
| Xerces-J | 2 | 0.94631688514733858 | 0.94085205698476859 | False | 2 | False | False | False | 1/100; 100% | 1/100; 100% | 74/100; 27% | True |
| Xerces-J | 3 | 0.92918552173041269 | 0.94678113005379883 | False | 2 | False | False | False | 1/100; 100% | 1/100; 100% | 74/100; 27% | True |
| Xerces-J | 4 | 0.93569493626740474 | 0.92649729212014365 | False | 2 | False | False | False | 1/100; 100% | 1/100; 100% | 72/100; 29% | True |
| Xerces-J | 5 | 0.94389641941012115 | 0.93860612880658556 | False | 2 | False | False | False | 1/100; 100% | 1/100; 100% | 73/100; 28% | True |
| Xerces-J | 6 | 0.97334913664595413 | 0.96714351561646272 | False | 3 | False | False | False | 2/100; 99% | 1/100; 100% | 61/100; 40% | False |
| Xerces-J | 7 | 0.94140561250629384 | 0.94318014188496357 | False | 2 | False | False | False | 1/100; 100% | 1/100; 100% | 79/100; 22% | True |
| Xerces-J | 8 | 0.95175386160490327 | 0.94349079790317203 | False | 2 | False | False | False | 1/100; 100% | 1/100; 100% | 83/100; 18% | True |
| Xerces-J | 9 | 0.97426444368866305 | 0.97409342716300484 | False | 3 | False | False | False | 1/100; 100% | 1/100; 100% | 68/100; 33% | True |
| Xerces-J | 10 | 0.95925654436709429 | 0.96256824138854968 | False | 2 | False | False | False | 1/100; 100% | 1/100; 100% | 69/100; 32% | True |
| Xerces-J | 11 | 0.94842331033580496 | 0.95703571948915689 | False | 2 | True | False | True | 2/100; 99% | 1/100; 100% | 75/100; 26% | False |
| Xerces-J | 12 | 0.97004856718947108 | 0.961248979587353 | False | 2 | False | False | False | 2/100; 99% | 1/100; 100% | 69/100; 32% | False |
| Xerces-J | 13 | 0.96656079500624392 | 0.94229888573990639 | False | 1 | False | False | False | 1/100; 100% | 1/100; 100% | 69/100; 32% | True |
| Xerces-J | 14 | 0.95273223486247272 | 0.95383153317080727 | False | 1 | False | False | False | 1/100; 100% | 1/100; 100% | 67/100; 34% | True |
| Xerces-J | 15 | 0.94395922978988001 | 0.9539242245149453 | False | 2 | False | False | False | 2/100; 99% | 1/100; 100% | 82/100; 19% | False |
| Xerces-J | 16 | 0.95739630423359723 | 0.95901566988268783 | False | 3 | False | False | False | 1/100; 100% | 1/100; 100% | 66/100; 35% | True |
| Xerces-J | 17 | 0.98726635309432165 | 0.98556926718435389 | False | 2 | True | False | True | 2/100; 99% | 1/100; 100% | 78/100; 23% | False |
| Xerces-J | 18 | 0.96009850364256655 | 0.95223559617322817 | False | 0 | False | False | False | 1/100; 100% | 1/100; 100% | 66/100; 35% | True |
| Xerces-J | 19 | 0.96958871304828176 | 0.96354143831797401 | False | 2 | False | False | False | 1/100; 100% | 1/100; 100% | 81/100; 20% | True |
| Xerces-J | 20 | 0.94219386176106634 | 0.94096804949100998 | False | 3 | False | False | False | 1/100; 100% | 1/100; 100% | 80/100; 21% | True |
| Xerces-J | 21 | 0.9502511028207834 | 0.95451516228763666 | False | 2 | False | False | False | 1/100; 100% | 1/100; 100% | 67/100; 34% | True |
| Xerces-J | 22 | 0.95696168371798085 | 0.96133833210726138 | False | 1 | False | False | False | 1/100; 100% | 1/100; 100% | 82/100; 19% | True |
| Xerces-J | 23 | 0.96803345145609454 | 0.96660972177837601 | False | 0 | False | False | False | 2/100; 99% | 1/100; 100% | 75/100; 26% | False |
| Xerces-J | 24 | 0.96312362107376304 | 0.96690654197830339 | False | 0 | False | False | False | 1/100; 100% | 1/100; 100% | 80/100; 21% | True |
| Xerces-J | 25 | 0.95579559121598268 | 0.95967881639021435 | False | 2 | True | False | True | 2/100; 99% | 1/100; 100% | 87/100; 14% | False |
| Xerces-J | 26 | 0.95474920328105972 | 0.95960477034746539 | False | 1 | False | False | False | 1/100; 100% | 1/100; 100% | 61/100; 40% | True |
| Xerces-J | 27 | 0.96639358034588652 | 0.96520106477814427 | False | 3 | False | False | False | 1/100; 100% | 1/100; 100% | 68/100; 33% | True |
| Xerces-J | 28 | 0.92575012858357342 | 0.9388467710135906 | False | 1 | False | False | False | 1/100; 100% | 1/100; 100% | 73/100; 28% | True |
| Xerces-J | 29 | 0.94873393838505116 | 0.94823781050893852 | False | 2 | False | False | False | 1/100; 100% | 1/100; 100% | 73/100; 28% | True |

## 11. DayTrader reference comparison

> **Value provenance.** `data/references/daytrader_reference_services.csv; active Stage 2 and formal Stage 3 selected labels; src/evo_ms/evaluation/reference_metrics.py` — **recomputed from accepted mapping**. The mapping has 53/53 extracted classes mapped, 0 unmatched, coverage 1.0. No labels are added or inferred.

**Per-seed values.** Column order within each stage is `MoJoFM/precision/recall/F1/ARI/NMI/coverage`.

| Seed | Stage 2 values | Stage 3 values |
|---|---|---|
| 0 | 28.260869565217394/0.18857142857142858/0.18333333333333332/0.18591549295774648/0.065576386118867167/0.42738794767539839/1 | 26.086956521739136/0.15957446808510639/0.16666666666666666/0.16304347826086954/0.034135595688901829/0.37208211249829998/1 |
| 1 | 19.565217391304344/0.1377245508982036/0.12777777777777777/0.1325648414985591/0.0078173215387780243/0.3643217426148383/1 | 26.086956521739136/0.16748768472906403/0.18888888888888888/0.17754569190600519/0.045357977013112109/0.39601766720693987/1 |
| 2 | 23.913043478260864/0.17061611374407584/0.20000000000000001/0.18414322250639387/0.050246522541364358/0.40268003653141166/1 | 26.086956521739136/0.16161616161616163/0.17777777777777778/0.16931216931216933/0.037615323707084453/0.38112094433170829/1 |
| 3 | 17.391304347826086/0.14117647058823529/0.20000000000000001/0.16551724137931034/0.014609065658058046/0.27416281361966099/1 | 21.739130434782606/0.17379679144385027/0.3611111111111111/0.23465703971119137/0.070772871565527723/0.30876064408118847/1 |
| 4 | 23.913043478260864/0.16190476190476191/0.18888888888888888/0.17435897435897438/0.039201420466848547/0.39187065216030653/1 | 26.086956521739136/0.16666666666666666/0.16111111111111112/0.16384180790960454/0.040651783278296778/0.43384397606991359/1 |
| 5 | 23.913043478260864/0.13733905579399142/0.17777777777777778/0.15496368038740921/0.0088864341740273693/0.36223655321701431/1 | 26.086956521739136/0.1891891891891892/0.19444444444444445/0.19178082191780821/0.068428168755872307/0.44539260397639135/1 |
| 6 | 23.913043478260864/0.15714285714285714/0.18333333333333332/0.16923076923076921/0.033233727426269968/0.37695610790973011/1 | 26.086956521739136/0.16753926701570682/0.17777777777777778/0.1725067385444744/0.043916307703433841/0.43164621796885766/1 |
| 7 | 21.739130434782606/0.14285714285714285/0.13333333333333333/0.13793103448275859/0.013515835290075018/0.35928449313097138/1 | 23.913043478260864/0.16666666666666666/0.19444444444444445/0.17948717948717949/0.045169113507427125/0.42843628629625896/1 |
| 8 | 26.086956521739136/0.17370892018779344/0.20555555555555555/0.18829516539440203/0.054406140158408514/0.39013452643872504/1 | 19.565217391304344/0.11538461538461539/0.14999999999999999/0.13043478260869565/-0.020211742059672768/0.29690546195789685/1 |
| 9 | 26.086956521739136/0.16042780748663102/0.16666666666666666/0.16348773841961853/0.035036016842835173/0.39899054291199798/1 | 23.913043478260864/0.17676767676767677/0.19444444444444445/0.1851851851851852/0.056004839814592394/0.42004255993766232/1 |
| 10 | 26.086956521739136/0.15432098765432098/0.1388888888888889/0.14619883040935674/0.025620162922926407/0.3973670848341036/1 | 26.086956521739136/0.17937219730941703/0.22222222222222221/0.19851116625310172/0.063066514543609772/0.38804343773371924/1 |
| 11 | 15.217391304347828/0.11604095563139932/0.18888888888888888/0.14376321353065541/-0.021555369256508149/0.22572975506337561/1 | 30.434782608695656/0.19587628865979381/0.21111111111111111/0.20320855614973263/0.078306384277672531/0.44650036232072782/1 |
| 12 | 28.260869565217394/0.17435897435897435/0.18888888888888888/0.18133333333333332/0.052634643377001446/0.39587126316527355/1 | 23.913043478260864/0.14423076923076922/0.16666666666666666/0.15463917525773194/0.016964487672472287/0.38519582098138178/1 |
| 13 | 23.913043478260864/0.16203703703703703/0.19444444444444445/0.17676767676767674/0.039963413174676436/0.39837909539312877/1 | 23.913043478260864/0.15346534653465346/0.17222222222222222/0.162303664921466/0.028028813514490509/0.39826158807311007/1 |
| 14 | 23.913043478260864/0.15525114155251141/0.18888888888888888/0.17042606516290726/0.03155959251096644/0.36081858099197583/1 | 23.913043478260864/0.16591928251121077/0.20555555555555555/0.18362282878411912/0.045662177352469399/0.39388345884337533/1 |
| 15 | 21.739130434782606/0.12334801762114538/0.15555555555555556/0.13759213759213756/-0.0095006324014977328/0.33737848376464047/1 | 23.913043478260864/0.16666666666666666/0.19444444444444445/0.17948717948717949/0.045169113507427125/0.42843628629625896/1 |
| 16 | 19.565217391304344/0.13615023474178403/0.16111111111111112/0.1475826972010178/0.0069782349625920085/0.35666857014855974/1 | 26.086956521739136/0.17156862745098039/0.19444444444444445/0.18229166666666669/0.050514359946632961/0.42379714310882843/1 |
| 17 | 28.260869565217394/0.18032786885245902/0.18333333333333332/0.18181818181818182/0.057715951318570498/0.39973732434502357/1 | 26.086956521739136/0.16972477064220184/0.20555555555555555/0.185929648241206/0.049986807500148937/0.40346362368593436/1 |
| 18 | 21.739130434782606/0.16037735849056603/0.18888888888888888/0.17346938775510204/0.037477148080438748/0.40867389326689485/1 | 26.086956521739136/0.18784530386740331/0.18888888888888888/0.18836565096952912/0.06602852661821243/0.45433979120514167/1 |
| 19 | 26.086956521739136/0.15463917525773196/0.16666666666666666/0.16042780748663102/0.02881947873553414/0.3636109852172954/1 | 26.086956521739136/0.18407960199004975/0.20555555555555555/0.1942257217847769/0.065418041877090424/0.43380035799700101/1 |
| 20 | 26.086956521739136/0.16666666666666666/0.20000000000000001/0.1818181818181818/0.045853208185874746/0.41123326024298873/1 | 19.565217391304344/0.10824742268041238/0.11666666666666667/0.11229946524064172/-0.026853289999371543/0.35437829417338457/1 |
| 21 | 23.913043478260864/0.17129629629629631/0.20555555555555555/0.18686868686868688/0.051743003197073048/0.41585774724674951/1 | 23.913043478260864/0.16753926701570682/0.17777777777777778/0.1725067385444744/0.043916307703433841/0.4106600465040427/1 |
| 22 | 23.913043478260864/0.16666666666666666/0.17777777777777778/0.17204301075268819/0.043003770045276613/0.42832512967876524/1 | 17.391304347826086/0.091346153846153841/0.10555555555555556/0.097938144329896892/-0.048970821081203354/0.28853358666412959/1 |
| 23 | 15.217391304347828/0.10970464135021098/0.14444444444444443/0.12470023980815347/-0.027925265580229966/0.28070624511487352/1 | 23.913043478260864/0.16818181818181818/0.20555555555555555/0.18500000000000003/0.048245762711864405/0.41033492097524948/1 |
| 24 | 23.913043478260864/0.16748768472906403/0.18888888888888888/0.17754569190600519/0.045357977013112109/0.42103708599805811/1 | 28.260869565217394/0.16666666666666666/0.17222222222222222/0.16939890710382513/0.042241671010635855/0.42334081526275724/1 |
| 25 | 28.260869565217394/0.18226600985221675/0.20555555555555555/0.19321148825065274/0.063541634593814733/0.41111018575332836/1 | 28.260869565217394/0.1891891891891892/0.23333333333333334/0.20895522388059701/0.075589195757284247/0.4070254361528709/1 |
| 26 | 10.869565217391308/0.097165991902834009/0.13333333333333333/0.11241217798594848/-0.045598875644162186/0.20977637866104906/1 | 23.913043478260864/0.16355140186915887/0.19444444444444445/0.17766497461928935/0.041683480291569715/0.3971169031792563/1 |
| 27 | 26.086956521739136/0.16097560975609757/0.18333333333333332/0.17142857142857143/0.037545157970792366/0.40497407942790181/1 | 23.913043478260864/0.14691943127962084/0.17222222222222222/0.15856777493606136/0.02047368625739459/0.36324309594145332/1 |
| 28 | 21.739130434782606/0.15706806282722513/0.16666666666666666/0.16172506738544473/0.031459191191426462/0.39346438895067415/1 | 19.565217391304344/0.11363636363636363/0.1111111111111111/0.11235955056179774/-0.01928802831407652/0.30955828572935667/1 |
| 29 | 23.913043478260864/0.15686274509803921/0.17777777777777778/0.16666666666666666/0.032371322238606837/0.38791671775464609/1 | 15.217391304347828/0.11158798283261803/0.14444444444444443/0.12590799031476999/-0.025191969235461659/0.26611466137438672/1 |

**Metric medians and paired median differences.**

| Metric | Stage 2 median | Stage 3 median | Paired median Δ |
|---|---|---|---|
| mojofm_vs_reference | 23.913043478260864 | 23.913043478260864 | 0 |
| pairwise_precision | 0.15876010781671157 | 0.16666666666666666 | 0.0086597946049110641 |
| pairwise_recall | 0.18333333333333332 | 0.18888888888888888 | 0.0083333333333333315 |
| pairwise_f1 | 0.16982841719683822 | 0.17760533326264727 | 0.0086541150221180196 |
| ari_vs_reference | 0.034134872134552574 | 0.044542710605430483 | 0.011365070720316693 |
| nmi_vs_reference | 0.39266752055549037 | 0.40086260587952222 | 0.012389158183287563 |
| reference_coverage_ratio | 1 | 1 | 0 |

**Requested MoJoFM/F1 tests.** Paired two-sided Wilcoxon; report-only exploratory Holm correction within this two-row family, α=0.05.

| Metric | Stage 2 median | Stage 3 median | Paired median Δ | Better/tie/worse | Raw p | Holm p | Corrected result |
|---|---|---|---|---|---|---|---|
| mojofm_vs_reference | 23.913043478260864 | 23.913043478260864 | 0 | 14/6/10 | 0.32278757468928099 | 0.64557514937856197 | not significant |
| pairwise_f1 | 0.16982841719683822 | 0.17760533326264727 | 0.0086541150221180196 | 17/0/13 | 0.34921137988567352 | 0.64557514937856197 | not significant |

Reference coverage is exactly 1 for every seed and stage; mapped/unmatched counts are 53/0. No new or inferred reference labels were created.

## 12. Sensitivity and design checks

> **Value provenance.** `results/stage3/cross_subject/preference_analysis/budget_response/stage3_semantic/per_seed.csv and profile_comparison/per_seed.csv` — **direct read plus conditional median recomputation**. For status=selected rows, Δ structural metric is selected minus same-seed conservative baseline; semantic improvement is stored `baseline_fsem−selected_fsem`; change count compares solution IDs. These are exploratory retained-front capabilities, not rerun experiments or new formal selections.

| Subject | Modularity budget | Availability | Median realised Q loss | Median fsem improvement | Median Δ coupling | Median Δ cohesion | Median Δ imbalance | Changed solution |
|---|---|---|---|---|---|---|---|---|
| DayTrader | 0 | 4/30 (0.13333333333333333) | 0 | 0.0068373203740933501 | 0 | 0 | 0 | 1/4 available |
| DayTrader | 0.0050000000000000001 | 6/30 (0.20000000000000001) | 0 | 0.0068373203740933501 | 0 | 0 | 0 | 1/6 available |
| DayTrader | 0.01 | 9/30 (0.29999999999999999) | 0.0038219086274786001 | 0.0143842481526697 | 0 | 0 | 0 | 1/9 available |
| DayTrader | 0.025000000000000001 | 10/30 (0.33333333333333331) | 0.0041886309524785496 | 0.0230926662928179 | 0 | 0 | 0 | 1/10 available |
| DayTrader | 0.050000000000000003 | 19/30 (0.6333333333333333) | 0.029593082417483301 | 0.011146279900722301 | 0 | 0 | 0 | 7/19 available |
| DayTrader | 0.10000000000000001 | 24/30 (0.80000000000000004) | 0.035822446093620605 | 0.0054695767327629001 | 0 | 0 | 0 | 8/24 available |
| DayTrader | 0.14999999999999991 | 25/30 (0.83333333333333337) | 0.070389712111504604 | 0.029433016078935899 | 0 | 0 | 0 | 14/25 available |
| DayTrader | 0.20000000000000001 | 26/30 (0.8666666666666667) | 0.075890710848131343 | 0.027185138292362798 | 0.011300738007380101 | 0 | 0 | 17/26 available |
| JPetStore | 0 | 26/30 (0.8666666666666667) | 0 | 0 | 0 | 0 | 0 | 0/26 available |
| JPetStore | 0.0050000000000000001 | 28/30 (0.93333333333333335) | 0.0048820515649455999 | 0.00028568306551810001 | 0.0024691358024689913 | 1.1815476190476186 | 0.10768063699923042 | 15/28 available |
| JPetStore | 0.01 | 29/30 (0.96666666666666667) | 0.0048820515649455999 | 0.00028568306551810001 | 0.0024691358024689913 | 1.1815476190476186 | 0.10768063699923042 | 15/29 available |
| JPetStore | 0.025000000000000001 | 30/30 (1) | 0.0113431847801352 | 0.090951864225554097 | 0 | -0.50833333333333286 | -0.037457478565264685 | 25/30 available |
| JPetStore | 0.050000000000000003 | 30/30 (1) | 0.0268340447245571 | 0.090951864225554097 | 0.014814814814814781 | -0.34226190476190421 | 0.059398993115433618 | 30/30 available |
| JPetStore | 0.10000000000000001 | 30/30 (1) | 0.060932554595541255 | 0.12995893088697791 | 0.064197530864197494 | 0.19047619047619069 | 0 | 30/30 available |
| JPetStore | 0.14999999999999991 | 30/30 (1) | 0.1123906192896201 | 0.17855055121054786 | 0.064197530864197494 | 0.19047619047619069 | 0 | 30/30 available |
| JPetStore | 0.20000000000000001 | 30/30 (1) | 0.16061811737610401 | 0.21950171208793523 | 0.064197530864197494 | -0.45952380952380878 | 0 | 30/30 available |
| Xerces-J | 0 | 8/30 (0.26666666666666666) | 0 | 0.00065066808185275003 | 0 | 0 | 0 | 0/8 available |
| Xerces-J | 0.0050000000000000001 | 27/30 (0.90000000000000002) | 0.00047066815656360002 | 0.0039122318684995001 | 0 | 0 | 0 | 4/27 available |
| Xerces-J | 0.01 | 29/30 (0.96666666666666667) | 0.001087408284208 | 0.0042443786361536003 | 0 | 0 | 0 | 5/29 available |
| Xerces-J | 0.025000000000000001 | 30/30 (1) | 0.0013571090394113002 | 0.0043541037580756003 | 0 | 0 | 0 | 6/30 available |
| Xerces-J | 0.050000000000000003 | 30/30 (1) | 0.0013571090394113002 | 0.0044707882130384999 | 0 | 0 | 0 | 7/30 available |
| Xerces-J | 0.10000000000000001 | 30/30 (1) | 0.0013571090394113002 | 0.0044707882130384999 | 0 | 0 | 0 | 7/30 available |
| Xerces-J | 0.14999999999999991 | 30/30 (1) | 0.0013571090394113002 | 0.0044707882130384999 | 0 | 0 | 0 | 7/30 available |
| Xerces-J | 0.20000000000000001 | 30/30 (1) | 0.0013571090394113002 | 0.0044707882130384999 | 0 | 0 | 0 | 7/30 available |

## 13. Convergence and computational cost

> **Value provenance.** `Stage 2/Stage 3 per-seed run_metrics.json/run_metadata.json; embedding_generation_manifest.json; method_body_input_manifest.json; semantic_graph_generation_manifest.json; results/stage3/provenance/environment/historical_stage3_requirements_lock.txt` — **direct read plus sums/descriptive recomputation**. Runtime totals are sums of saved per-run elapsed values, not parallel wall-clock measurements.

**Convergence.** No generation-by-generation Stage 3 trajectory is present in the final Declaration + Method Body artifacts. Therefore representative Stage 3 trajectories, plateau/near-plateau classification, and the count still improving at generation 100 are **missing**. The only stored `convergence_diagnostic` directories belong to Stage 2 and cannot establish Stage 3 convergence. The defensible statement is fixed-budget completion: every Stage 3 run used 100 generations and 10,000 evaluations; convergence beyond that budget is unknown.

**Optimizer runtime (seconds; mean/median/sample-std/sum).**

| Subject | S2 mean | S2 median | S2 std | S2 sum | S3 mean | S3 median | S3 std | S3 sum |
|---|---|---|---|---|---|---|---|---|
| JPetStore | 6.5758453070011456 | 6.5583476044994313 | 0.065609259424102187 | 197.27535921003437 | 8.073272147235306 | 8.0304112915182486 | 0.31189755705644817 | 242.19816441705916 |
| DayTrader | 9.9575983027966384 | 9.9270303334633354 | 0.1452223671296452 | 298.72794908389915 | 10.490724979240136 | 10.506488541490398 | 0.31901385016699491 | 314.72174937720411 |
| Xerces-J | 99.788630687394956 | 99.772172062512254 | 12.227233411530216 | 2993.6589206218487 | 75.178414906961066 | 75.599136582983192 | 1.5027343127740411 | 2255.352447208832 |

Across all 90 runs per stage: Stage 2 sum = **3489.6622289157822 s**; Stage 3 sum = **2812.2723610030953 s**; combined saved-run sum = **6301.9345899188775 s**.

**Semantic preparation cost.** The input manifest records generation and validation timestamps but no elapsed duration, so semantic-input time is unavailable. Canonical embedding model load = **30.892432791995816 s**; encoding times are:

| Subject | Canonical encoding seconds |
|---|---|
| JPetStore | 9.2797609170665964 |
| DayTrader | 25.630149874952622 |
| Xerces-J | 242.87654379196465 |

The graph-generation manifest has no elapsed-time fields; semantic-graph time is unavailable.

**Frozen environment.** Apple Silicon MPS (arm64), runtime float16, stored vectors float32, batch 8; Python 3.13.7; numpy 2.4.4; scipy 1.16.3; torch 2.13.0; transformers 5.14.1; sentence-transformers 5.6.0; pandas 2.2.3; pymoo 0.6.2; scikit-learn 1.9.0. These versions come from the embedding manifest and the historical Stage 3 lock retained under `results/stage3/provenance/environment/`; the current supported Stage 1–3 environment is `pyproject.toml` plus `uv.lock`. Optimizer run metadata does not independently freeze a CPU/model identifier.

## 14. Candidate Chapter 4.3 tables

All values in Tables A–F are copied or aggregated from Sections 4–13; their per-table provenance and formulas therefore remain those stated in the originating section.

### Table A — Stage 3 semantic evidence validity

| Subject | Semantic edges | Structural overlap | Novel edge proportion | Model tokenizer truncations | Body-budget affected classes | Random mean | Observed-minus-random |
|---|---|---|---|---|---|---|---|
| JPetStore | 47 | 0.53191489361702127 | 0.46808510638297873 | 0 | 0 | 0.19323404255319149 | 0.33868085106382978 |
| DayTrader | 112 | 0.4375 | 0.5625 | 0 | 1 | 0.11719642857142856 | 0.32030357142857147 |
| Xerces-J | 1681 | 0.3491969066032124 | 0.65080309339678766 | 0 | 7 | 0.011392028554431884 | 0.33780487804878051 |

### Table B — Stage 2 versus Stage 3 Pareto-front quality

| Subject | Stage 2 HV | Stage 3 projected HV | Difference | Better/Tie/Worse | Corrected result |
|---|---|---|---|---|---|
| JPetStore | 0.40125400666028949 | 0.38758006611154999 | -0.013673940548739494 | 4/0/26 | significant |
| DayTrader | 0.18483216694142079 | 0.18981781771150022 | 0.004985650770079425 | 16/0/14 | not significant |
| Xerces-J | 0.13442197970616959 | 0.13688409486984865 | 0.0024621151636790573 | 13/0/17 | not significant |

### Table C — Median selected-profile values

| Subject | Stage | Modularity | Coupling | Cohesion | Imbalance | f_semantic | Clusters |
|---|---|---|---|---|---|---|---|
| JPetStore | Stage 2 | 0.42773662551440361 | 0.27407407407407408 | 4.9000000000000004 | 0 | 0.50760005590338708 | 4 |
| JPetStore | Stage 3 | 0.44206980643194632 | 0.25185185185185183 | 5.477380952380952 | 0.2041241452319312 | 0.51226006853751815 | 4 |
| DayTrader | Stage 2 | 0.29435788592203266 | 0.43657749077490771 | 7.1010356310356313 | 0.67615287822089476 | 0.62379575004781762 | 9 |
| DayTrader | Stage 3 | 0.31117867999482574 | 0.43404059040590387 | 7.1909174159174158 | 0.75712804578095305 | 0.58661188730012315 | 10 |
| Xerces-J | Stage 2 | 0.63507329577376481 | 0.23844716031631913 | 8.2509595710142207 | 1.2101941782348129 | 0.41677548770153944 | 29 |
| Xerces-J | Stage 3 | 0.6612134091967603 | 0.20911574406901501 | 8.0696162029868432 | 1.3144549791672442 | 0.38725947469944244 | 31 |

### Table D — Selected-profile changes

| Subject | Semantic change | Modularity change | Coupling change | Cohesion change | Imbalance change | ARI/NMI | Non-identical pair proportion |
|---|---|---|---|---|---|---|---|
| JPetStore | 0.0046600126341310721 | 0.010737692424935052 | -0.022222222222222254 | 0.57738095238095166 | 0.2041241452319312 | 0.73610712002350898/0.81282037916065997 | 1.0 (30/30 non-identical) |
| DayTrader | -0.021442132227829147 | 0.012121709518525092 | -8.3266726846886741e-17 | 0.06914428485952584 | 0.078066160780511651 | 0.53388389030639494/0.69909276436317613 | 1.0 (30/30 non-identical) |
| Xerces-J | -0.029560631084392219 | 0.024305788934827544 | -0.028152408339324336 | -0.051369855086192295 | 0.091112249388071276 | 0.95637863746698182/0.95577544088839672 | 1.0 (30/30 non-identical) |

### Table E — DayTrader reference comparison

| Metric | Stage 2 | Stage 3 | Difference | p-value | Corrected result | Coverage |
|---|---|---|---|---|---|---|
| mojofm_vs_reference | 23.913043478260864 | 23.913043478260864 | 0 | 0.32278757468928099 | not significant (Holm p=0.64557514937856197) | 1.0 (53/53) |
| pairwise_f1 | 0.16982841719683822 | 0.17760533326264727 | 0.0086541150221180196 | 0.34921137988567352 | not significant (Holm p=0.64557514937856197) | 1.0 (53/53) |

### Table F — Stage 3 front and execution validity

| Subject | Valid runs | Front size | Projected front size | Plateau status | Fallbacks |
|---|---|---|---|---|---|
| JPetStore | 30/30 | 99.966666666666669 | 52 | not recorded | 0 |
| DayTrader | 30/30 | 99.966666666666669 | 68.766666666666666 | not recorded | 0 |
| Xerces-J | 30/30 | 100 | 84.033333333333331 | not recorded | 0 |

## 15. Source artifact inventory

**Configuration.**

- `configs/experiments/05_stage3_declaration_method_body.yml`
- `configs/experiments/02_stage2_nsga_structure_only.yml`
- `configs/experiments/stage2_robustness_bounds.yml`
- `pyproject.toml`, `uv.lock`, and `results/stage3/provenance/environment/historical_stage3_requirements_lock.txt`

**Structural input and baseline.**

- `data/extracted/<subject>/{class_nodes.csv,structural_dependencies.csv,ssa_flow_edges.csv}`
- `results/stage1/subjects/<subject>/leiden_baseline/{raw_reference_leiden,ssa_selected_leiden}/clustering/stage1_clusters.csv`
- `src/evo_ms/graph/raw_graph_builder.py`

**Semantic text.**

- `data/semantic_text/declaration_method_body/<subject>/class_semantic_inputs.csv`
- `results/stage3/data_quality/semantic_input/input_quality_per_class.csv`
- `results/stage3/provenance/inputs/method_body_input_manifest.json`

**Embeddings.**

- `data/embeddings/declaration_method_body/<subject>/{embeddings.npy,class_ids.csv,embedding_metadata.json}`
- `results/stage3/data_quality/embedding/embedding_quality_per_subject.csv`
- `results/stage3/provenance/embedding_generation_manifest.json`

**Semantic graphs.**

- `data/semantic_graphs/declaration_method_body/<subject>/{semantic_edges.csv,class_mapping.csv,graph_metadata.json}`
- `results/stage3/data_quality/semantic_graph/semantic_graph_quality_per_subject.csv`
- `results/stage3/provenance/semantic_graph_generation_manifest.json`
- `results/stage3/provenance/final_graph_compatibility_contract.json`

**Stage 2 formal results.**

- `results/stage2/subjects/<stage2-subject>/nsga/robustness_final_30seeds/seed_00..29/{pareto_front.csv,run_metrics.json,run_metadata.json}`
- `results/stage2/cross_subject/operating_profile/canonical_operating_solution_per_seed.csv`

**Stage 3 formal results.**

- `results/stage3/subjects/<stage3-subject>/declaration_method_body/{validation/seed_00,formal/seed_01..29}/{pareto_front_4d.csv,projected_front_3d.csv,posthoc_metrics.csv,selected_solution.json,objective_redundancy.json,run_metadata.json}`
- `src/evo_ms/optimization/{selection.py,problem.py,stage3_problem.py}`

**Projected-HV analysis.**

- `results/stage3/cross_subject/stage2_comparison/paired_per_seed.csv`
- `results/stage3/subjects/<stage3-subject>/declaration_method_body/{validation,formal}/seed_*/projected_hypervolume.json`

**Statistics.**

- `results/stage3/cross_subject/formal_statistics/{formal_summary.csv,formal_statistical_tests.csv,formal_selected_fsemantic_per_seed.csv,formal_partition_similarity_per_seed.csv,formal_partition_similarity_summary.csv}`
- `results/stage3/provenance/legacy_statistics/` (historical, never current input)

**Reference metrics.**

- `data/references/daytrader_reference_services.csv`
- `results/pre_experiment/subjects/daytrader/calibration/reference_mapping_validation.csv`
- `src/evo_ms/evaluation/reference_metrics.py`

**Sensitivity.**

- `results/stage3/cross_subject/preference_analysis/budget_response/stage3_semantic/{per_seed.csv,summary.csv}`
- `results/stage3/cross_subject/preference_analysis/profile_comparison/per_seed.csv`
- `results/stage3/cross_subject/preference_analysis/manifest/analysis_manifest.json`

**Convergence/runtime.**

- `results/stage2/subjects/<stage2-subject>/nsga/convergence_diagnostic/* (Stage 2 only)`
- `per-seed Stage 2 run_metrics.json and Stage 3 run_metadata.json`
- `results/stage3/provenance/embedding_generation_manifest.json`

**Provenance.**

- `results/stage3/provenance/{formal_experiment_manifest.json,final_stage3_provenance.json,current_report_locator.json}`
- `results/stage3/reproducibility_checks/{input,embedding,semantic_graph,formal_runs}/`

## 16. Missing or inconsistent data

### Fully available

- Exact 30-seed paired inventory, validity/front health, class-universe equality, final setup, semantic-input/embedding/graph validity, structural overlap and deterministic random baseline, objective redundancy, projected 3D HV, active selected profiles, partition similarity/selector diagnostics, DayTrader reference metrics, preference-response budgets, and per-run optimizer elapsed times.

### Exploratory-only evidence

- Supporting fsem correlations with modularity/cohesion/imbalance, the two-row DayTrader Holm family, selector ranks/percentiles, and semantic-budget response are post-hoc recomputations. They do not replace the accepted six-row primary family or change scientific conclusions.

### Missing

- A canonical 4D-HV reference point/normalization and per-seed 4D-HV values; final Stage 3 generation-level convergence histories and plateau labels; semantic-input elapsed duration; semantic-graph elapsed duration; an independently frozen optimizer hardware identifier; canonical empirical random-baseline p-values; JPetStore and Xerces-J external reference mappings.

### Conflicts and canonical resolutions

1. The earlier four-metric Bonferroni config block has been replaced by the reporting-only six-row Wilcoxon/Holm contract. Historical generation hashes remain provenance and are not presented as hashes of the corrected config bytes.
2. `stage2_vs_stage3/paired_per_seed.csv` remains authoritative only for its accepted projected-HV columns. Its older selected-semantic columns are historical. Current selected-`f_semantic` statistics come from `formal_selected_fsemantic_per_seed.csv`, using the active 5% modularity-band Stage 2 profile.
3. Some accepted run metadata records `base_config_path=configs/experiments/04_stage3_semantic.yml` and historical generation hashes. This is provenance only. Runtime identity is resolved by `configs/experiments/05_stage3_declaration_method_body.yml`, `provenance/final_stage3_provenance.json`, and `provenance/final_graph_compatibility_contract.json`; no legacy declaration-only artifact is used here.
4. Current config bytes have changed during repository finalization, so their current file SHA-256 is not the original generation hash recorded in old run metadata. Scientific artifact identity must be taken from the final provenance/compatibility ledgers and per-artifact hashes, not by demanding equality to the current config-file byte hash.
5. Historical manifests name `reports/stage3` as their original report root, while current canonical human-readable results live under `docs/stage3/findings`. Use `provenance/current_report_locator.json` for migrated report locations and `results/stage3` for machine-readable authority.

### Legacy files that must not be used

- Old `stage3-semantic` / declaration-only experiment results, the `stage3-declaration-final` tag as a current result source, generic Stage 3 fallbacks, Stage 3A semantic text/embedding/graph directories, and historical failed/experimental Stage 2 result directories. The only Stage 3 scientific source in this report is `05_stage3_declaration_method_body` plus `data/*/declaration_method_body`.

## 17. Canonical reporting contract

<!-- BEGIN GENERATED: canonical_reporting_contract -->
- Active Stage 2 profile: `results/stage2/cross_subject/operating_profile/canonical_operating_solution_per_seed.csv`.
- Stage 3 profile: final matching-seed `selected_solution.json` from the projected-front operating selector.
- Projected-HV source: `results/stage3/cross_subject/stage2_comparison/paired_per_seed.csv`; its accepted HV columns are unchanged.
- Selected `f_semantic`: recomputed for both selected partitions on `data/semantic_graphs/declaration_method_body/<subject>/semantic_edges.csv`.
- Confirmatory family: three subjects × projected_hypervolume/selected_f_semantic; paired two-sided Wilcoxon; Holm over exactly six rows; alpha 0.05.
- Structural selected-profile tests and preference-response analyses are separate exploratory families.
- Partition terminology: `non_identical_pair_proportion` is pair-level; `changed_partition_ratio` is class-level.
- Token controls: model tokenizer truncation count is zero; the independent method-body evidence budget is 256 tokens.
- No experiment, embedding, semantic graph, Pareto front, projected front, or selected solution was regenerated.
<!-- END GENERATED: canonical_reporting_contract -->

---

**Non-mutation statement.** This report was generated through read-only inspection and deterministic calculations on accepted files. No accepted semantic input, embedding, semantic graph, NSGA-II run, Pareto front, projected front, selected solution, tag, remote branch, or scientific conclusion was changed; only reporting outputs and reporting provenance were corrected.
