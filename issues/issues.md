# Prototype Development and Validation Issues

This document records implementation and validation issues identified during development of the three-stage prototype. It distinguishes changes to experimental evidence from later corrections to derived reporting. Recording an issue does not imply that the final formal result was invalid; where only derived reporting changed, frozen optimisation outputs remained unchanged.

## 1. Issue Index

| ID | Stage | Short title | Category | Scientific impact | Final status | Dissertation relevance |
|---|---|---|---|---|---|---|
| S1-01 | Stage 1 | Subject scope and class-universe correction | Input / extraction | Pre-freeze formal-pipeline affecting | Resolved | HIGH |
| S1-02 | Stage 1 | Class-level SSA flow aggregation | Graph construction | Pre-freeze formal-pipeline affecting | Resolved | HIGH |
| S1-03 | Stage 1 | Raw/SSA weight and lambda-zero identity | Configuration | Validation/reproducibility only | Validated | MEDIUM |
| S1-04 | Stage 1 | Calibration and frozen-profile mismatch | Configuration | Pre-freeze formal-pipeline affecting | Resolved | HIGH |
| S1-05 | Stage 1 | Calibration guardrails and high-lambda scope | Configuration | Pre-freeze formal-pipeline affecting | Validated | MEDIUM |
| S1-06 | Stage 1 | Reference metric definition and interpretation | Statistical/reporting | Derived-reporting affecting | Resolved | HIGH |
| S1-07 | Stage 1 | Partition change versus Leiden seed variation | Reproducibility | Derived-reporting affecting | Validated | HIGH |
| S1-08 | Stage 1 | SSA-edge validity against random graphs | Graph construction | Validation/reproducibility only | Validated | MEDIUM |
| S2-01 | Stage 2 | Canonical partition encoding and identity | Optimisation | Validation/reproducibility only | Validated | MEDIUM |
| S2-02 | Stage 2 | Objective direction and structure-only boundary | Optimisation | Pre-freeze formal-pipeline affecting | Resolved | HIGH |
| S2-03 | Stage 2 | Constraint and repair contract correction | Constraint handling | Pre-freeze formal-pipeline affecting | Resolved | HIGH |
| S2-04 | Stage 2 | Empirical Hypervolume bounds failed | Validation | Pre-freeze formal-pipeline affecting | Resolved | HIGH |
| S2-05 | Stage 2 | Robustness experimental unit was pooled | Statistical/reporting | Pre-freeze formal-pipeline affecting | Resolved | HIGH |
| S2-06 | Stage 2 | Initialisation-bias diagnostic | Initialisation | Development-only | Validated | MEDIUM |
| S2-07 | Stage 2 | Convergence evidence added after budget choice | Validation | Validation/reproducibility only | Validated | MEDIUM |
| S2-08 | Stage 2 | Representative-selector lineage | Selection | Derived-reporting affecting | Superseded | HIGH |
| S2-09 | Stage 2 | Statistical-family and repeated-run correction | Statistical/reporting | Derived-reporting affecting | Resolved | HIGH |
| S3-01 | Stage 3 | Semantic representation expanded beyond identifiers | Semantic representation | Pre-freeze formal-pipeline affecting | Superseded | HIGH |
| S3-02 | Stage 3 | Method-body leakage and scope controls | Semantic representation | Pre-freeze formal-pipeline affecting | Validated | HIGH |
| S3-03 | Stage 3 | Lexical body budget versus model context | Semantic representation | Derived-reporting affecting | Resolved | MEDIUM |
| S3-04 | Stage 3 | Per-subject embedding generation and cache guards | Reproducibility | Pre-freeze formal-pipeline affecting | Resolved | HIGH |
| S3-05 | Stage 3 | Saved-vector dot product was not true cosine | Embedding validation | Pre-freeze formal-pipeline affecting | Resolved | HIGH |
| S3-06 | Stage 3 | Semantic graph sparsity and symmetrisation contract | Graph construction | Pre-freeze formal-pipeline affecting | Validated | HIGH |
| S3-07 | Stage 3 | Stage 3A and Stage 3B artefact isolation | Provenance | Pre-freeze formal-pipeline affecting | Resolved | HIGH |
| S3-08 | Stage 3 | Four-objective integration regression gate | Optimisation | Validation/reproducibility only | Validated | HIGH |
| S3-09 | Stage 3 | Formal CSV precision and schema drift | Reproducibility | Derived-reporting affecting | Resolved | HIGH |
| S3-10 | Stage 3 | Stage 2 representatives leaked into Stage 3 reporting | Statistical/reporting | Derived-reporting affecting | Resolved | HIGH |
| XS-01 | Cross-stage | Branch, worktree and authority ambiguity | Provenance | Validation/reproducibility only | Resolved | MEDIUM |
| XS-02 | Cross-stage | Historical and canonical result-layout separation | Provenance | Derived-reporting affecting | Resolved | MEDIUM |
| XS-03 | Cross-stage | Visualisations followed stale representative partitions | Visualisation | Derived-reporting affecting | Resolved | HIGH |
| XS-04 | Cross-stage | Final 5% BALANCE operating-preference correction | Selection | Derived-reporting affecting | Resolved | HIGH |
| XS-05 | Cross-stage | Supplementary operating-preference alignment | Selection | Derived-reporting affecting | Validated | MEDIUM |

## 2. Stage 1 Issues

### [S1-01] Subject scope and class-universe correction

**Stage:** Stage 1  
**Category:** Input / extraction  
**Detected during:** Subject preparation and formal-scope consolidation  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Early subject configurations and reports did not yet provide a stable, consistently counted application-class universe. Subject roles also changed: CargoTracker was initially present, while the eventual formal set used JPetStore, DayTrader and Xerces-J.

**Root cause**  
Package inclusion/exclusion rules and the experimental role of each subject were still being established during extraction development. The precise reason for abandoning CargoTracker was not fully established; Git proves the scope replacement, not a measured CargoTracker failure.

**Resolution**  
Application-package and exclusion rules were consolidated, retained class lists became explicit inputs, and the three formal subject roles were frozen. Later runners validate label/vector lengths against these class lists.

**Verification**  
Extraction tests check application-class filtering and saved class counts. Formal manifests, graphs and partitions use the same class universes.

**Effect on final evidence**  
Formal Stage 1 evidence was regenerated after scope correction. CargoTracker outputs are exploratory and outside the final study.

**Repository evidence**  
Commits `6c335cc`, `be0d44d`, `e6510d5`; `configs/subjects/`; `scripts/subject_extraction_config.py`; `tests/test_subject_extraction_config.py`.

### [S1-02] Class-level SSA flow aggregation

**Stage:** Stage 1  
**Category:** Graph construction  
**Detected during:** Raw-versus-SSA graph validation  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Method-level return-value and argument-passing records could map repeatedly to the same undirected class pair. Treating rows as independent class edges would misstate edge counts or weights, while self-loops added no decomposition boundary evidence.

**Root cause**  
Distinct method-level flow channels often coincide after aggregation to classes. In the retained extractor, a returned value passed to another application call can generate both channel records for the same class pair.

**Resolution**  
SSA records are normalized to class identifiers, self-loops are removed, and all records for an undirected class pair are aggregated before lambda scaling and merger with the raw graph.

**Verification**  
Graph-builder tests cover duplicated/reversed pairs, self-loops, SSA-only edges and deterministic totals. Calibration notes document why coincident channels are a granularity limitation rather than duplicate extractor evidence.

**Effect on final evidence**  
Canonical SSA graphs and dependent Stage 1 partitions use the corrected aggregate weights.

**Repository evidence**  
`src/evo_ms/evidence/ssa_flow_evidence.py`; `src/evo_ms/graph/ssa_graph_builder.py`; `tests/test_graph_builder.py`; `docs/pre_experiment/findings/ssa_calibration_notes.md`.

### [S1-03] Raw/SSA weight and lambda-zero identity

**Stage:** Stage 1  
**Category:** Configuration  
**Detected during:** Graph-construction regression testing  
**Scientific impact:** Validation/reproducibility only  
**Dissertation relevance:** MEDIUM

**Observed problem**  
Raw weights, extracted SSA row weights and the lambda multiplier could be confused, creating uncertainty over whether `lambda=0` truly reproduced the raw graph and what a nominal lambda value meant.

**Root cause**  
SSA return/argument rows carry base weights, while lambda is applied only during class-graph construction. Changing a YAML base weight cannot retroactively change already normalized extracted CSV rows.

**Resolution**  
The implementation records raw weight, unscaled SSA evidence, lambda-scaled SSA contribution and final `G_ssa` weight separately. Lambda zero suppresses all SSA contribution while preserving raw pair weights.

**Verification**  
Unit tests assert lambda-zero equivalence and correct handling of SSA-only pairs. Metadata and calibration notes record the effective formula.

**Effect on final evidence**  
No later scientific output changed; the weight contract and reproducibility claim were verified.

**Repository evidence**  
`src/evo_ms/graph/weight_calculator.py`; `src/evo_ms/graph/ssa_graph_builder.py`; `tests/test_graph_builder.py`; `tests/test_pre_experiment_runner.py`.

### [S1-04] Calibration and frozen-profile mismatch

**Stage:** Stage 1  
**Category:** Configuration  
**Detected during:** DayTrader calibration freeze  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
At intermediate revisions, selected-profile output, experiment configuration and formal Stage 1 results did not identify the same DayTrader raw/SSA settings. Earlier reference-heavy ranking also selected different comparison profiles.

**Root cause**  
Calibration ranking and admissibility rules evolved after generated selection files and formal configuration had already been produced.

**Resolution**  
Ranking was changed to internal structural evidence first, reference metrics were demoted to sanity/tie-break evidence, and configuration plus selected-profile metadata were synchronized. Final profiles are raw `(lambda=0, resolution=1.0)` and SSA `(lambda=0.25, resolution=1.0)`, seed 42.

**Verification**  
Formal-run tests compare configuration against selected-profile metadata and input hashes. Formal outputs were regenerated after synchronization.

**Effect on final evidence**  
Stage 1 formal partitions changed during development; the final frozen outputs consistently use the corrected profiles.

**Repository evidence**  
Commits `92f6e16`, `e6510d5`, `bd9c210`, `12a5b6a`, `b3b89ae`; `tests/test_daytrader_calibration.py`; `tests/test_stage1_runner.py`.

### [S1-05] Calibration guardrails and high-lambda scope

**Stage:** Stage 1  
**Category:** Configuration  
**Detected during:** DayTrader and Xerces sensitivity analysis  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** MEDIUM

**Observed problem**  
Low resolution and large lambda values could produce dominant clusters and increasingly SSA-dominated graphs. A high-lambda candidate could appear attractive on one metric without being an appropriate formal operating point.

**Root cause**  
Effective SSA contribution equals the stored base flow weight multiplied by lambda. With base weight 3, lambda values 2, 3 and 4 imply contributions 6, 9 and 12 per flow record.

**Resolution**  
Formal eligibility was limited to `0 < lambda <= 1`; lambda 2--4 remained stress tests. Maximum-cluster ratio was tightened to 0.40, singleton ratio to 0.15, reference coverage required 0.80, and an extreme cluster-count screen was retained. Resolution 1.0 was selected after testing 0.50--1.50.

**Verification**  
In the DayTrader sweep, max-cluster screening rejected eight of 35 rows, while singleton, coverage and cluster-count screens were non-binding.

**Effect on final evidence**  
The formal profiles use the restricted range. High-lambda outputs remain diagnostic, not confirmatory.

**Repository evidence**  
Commit `b3b89ae`; `docs/pre_experiment/findings/ssa_calibration_notes.md`; DayTrader/Xerces sweep summaries.

### [S1-06] Reference metric definition and interpretation

**Stage:** Stage 1  
**Category:** Statistical/reporting  
**Detected during:** Metric validation and calibration review  
**Scientific impact:** Derived-reporting affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Reference metrics required corrected directional definitions and careful interpretation. A reference-heavy calibration score could turn proxy service labels into an unintended optimization target.

**Root cause**  
MoJoFM is directional and sensitive to candidate/reference orientation; singleton join/move cases also require exact handling. The DayTrader service decomposition is external proxy evidence, not the formal structural objective.

**Resolution**  
MoJo distance and normalization were implemented with an explicit candidate-to-reference direction and tested against small oracles. MoJoFM and pairwise F1 remained reported sanity checks but were removed from primary profile ranking.

**Verification**  
Brute-force and hand-constructed tests cover singleton candidate and reference clusters. Frozen notes show ARI near zero across the calibration grid and no material reference-alignment improvement from SSA.

**Effect on final evidence**  
Reference-based tables and interpretation changed; final structural graphs remain governed by internal evidence.

**Repository evidence**  
Commit `e6510d5`; `src/evo_ms/evaluation/reference_metrics.py`; `tests/test_reference_metrics.py`; `docs/pre_experiment/findings/ssa_calibration_notes.md`.

### [S1-07] Partition change versus Leiden seed variation

**Stage:** Stage 1  
**Category:** Reproducibility  
**Detected during:** Frozen Stage 1 robustness control  
**Scientific impact:** Derived-reporting affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
A fixed-seed raw/SSA partition difference could be attributed to SSA even when ordinary Leiden reseeding produced changes of similar magnitude. Partition change also did not establish partition improvement.

**Root cause**  
Leiden stochasticity differed substantially by subject and had not been separated from the graph-change effect in the initial fixed-seed comparison.

**Resolution**  
Thirty raw and SSA seed runs were compared per subject. Reporting was qualified: DayTrader and Xerces SSA movement is on the same order as raw seed variability, whereas JPetStore raw Leiden is seed-stable but still changes under SSA.

**Verification**  
DayTrader SSA distance was 0.1086 versus raw variation `0.0655 ± 0.1445`; Xerces was 0.2825 versus `0.2158 ± 0.1089`; JPetStore had zero raw variation and non-zero SSA distance 0.1234.

**Effect on final evidence**  
Frozen partitions did not change. The strength and scope of the scientific interpretation changed.

**Repository evidence**  
Commit `78f9e13`; `experiments/01_stage1_leiden_baseline/run_seed_robustness.py`; subject robustness summaries.

### [S1-08] SSA-edge validity against random graphs

**Stage:** Stage 1  
**Category:** Graph construction  
**Detected during:** Additional evidence-validity validation  
**Scientific impact:** Validation/reproducibility only  
**Dissertation relevance:** MEDIUM

**Observed problem**  
Raw/SSA edge overlap alone could not show whether SSA evidence contained non-random structural signal.

**Root cause**  
The original overlap report had no same-size random-graph reference distribution.

**Resolution**  
Each observed SSA graph was compared with 1,000 uniform simple undirected graphs having the same nodes and edge count. This is an edge-count-matched, not degree-preserving, null.

**Verification**  
Observed overlap exceeded all 1,000 draws for JPetStore, DayTrader and Xerces-J. Raw samples, summary and manifest are frozen on the validation branch.

**Effect on final evidence**  
No Stage 1 graph or partition changed. The validation strengthens evidence validity but is not a new confirmatory test family.

**Repository evidence**  
Commit `8592d0a`; `results/cross_subject/01_stage1_ssa_random_baseline/`.

## 3. Stage 2 Issues

### [S2-01] Canonical partition encoding and identity

**Stage:** Stage 2  
**Category:** Optimisation  
**Detected during:** NSGA-II problem construction  
**Scientific impact:** Validation/reproducibility only  
**Dissertation relevance:** MEDIUM

**Observed problem**  
Different integer label vectors can represent the same partition, producing false duplicates and unstable identifiers. Vectors with the wrong class order or length could also be evaluated against the wrong nodes.

**Root cause**  
Cluster labels are nominal rather than ordinal, while generic evolutionary operators manipulate raw integers.

**Resolution**  
Every vector is canonicalized by first occurrence against the frozen class-node order before identity, duplicate elimination, selection or output. Length mismatches fail immediately.

**Verification**  
Encoding tests cover equivalent relabellings, deterministic IDs, class-order mapping and invalid lengths. Stage 3 later reuses the same canonical identity.

**Effect on final evidence**  
No post-freeze scientific output changed; the representation prevents invalid or duplicate candidates.

**Repository evidence**  
Commit `131587f`; `src/evo_ms/optimization/encoding.py`; `tests/test_stage2_scaffold.py`; `tests/test_stage3_provenance.py`.

### [S2-02] Objective direction and structure-only boundary

**Stage:** Stage 2  
**Category:** Optimisation  
**Detected during:** Formal Stage 2 implementation review  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Coupling and imbalance are minimized while cohesion is maximized, but the optimizer requires a consistent minimization vector. Weighted modularity and reference metrics were at risk of being interpreted as optimized objectives.

**Root cause**  
The reporting schema combined objective and post-hoc fields, while cohesion's natural direction differs from the other two objectives.

**Resolution**  
The formal vector became coupling, negative cohesion and imbalance. Weighted modularity, Hypervolume, MoJoFM and pairwise F1 were explicitly post-hoc. Stage 2 consumes only the raw structural graph; semantic values added later are post-hoc evaluation.

**Verification**  
Objective unit tests check signs, singleton cohesion, known partitions and vectorized evaluation. Workflow documentation names the three formal objectives separately from reported metrics.

**Effect on final evidence**  
Formal Stage 2 results use the corrected three-objective problem definition.

**Repository evidence**  
Commits `adb632c`, `131587f`, `2bbd94c`; `src/evo_ms/optimization/objectives.py`; `experiments/02_stage2_nsga_structure_only/README.md`; `tests/test_stage2_scaffold.py`.

### [S2-03] Constraint and repair contract correction

**Stage:** Stage 2  
**Category:** Constraint handling  
**Detected during:** Constraint ablation and documentation audit  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
The initial design treated maximum-cluster ratio, singleton ratio and minimum cluster count as hard constraints. Documentation also claimed `2 <= k <= n-1`, although the implementation only guaranteed `k >= 2` plus maximum-cluster repair.

**Root cause**  
Singleton control duplicated other anti-degeneracy behaviour, and the prose generalized beyond the implemented feasible-set check.

**Resolution**  
Singleton ratio was removed from formal feasibility and retained only as a diagnostic. Repair canonicalizes labels, splits clusters larger than `floor(0.40n)`, and ensures at least two clusters after initialization and variation.

**Verification**  
Tests assert singleton is absent from the constraint configuration, repair preserves every class, maximum size is respected and `k>=2`. A reported A/B/C ablation motivated removal, but no retained quantitative singleton-HV table was found.

**Effect on final evidence**  
Formal feasibility changed before the accepted 30-seed result family. The maximum-cluster guard remained active.

**Repository evidence**  
Commits `131587f`, `2bbd94c`, `2da4408`; `docs/stage2/experiment_design.md`; `tests/test_stage2_scaffold.py`.

### [S2-04] Empirical Hypervolume bounds failed

**Stage:** Stage 2  
**Category:** Validation  
**Detected during:** Formal robustness execution  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
JPetStore seed 12 produced negative cohesion approximately `-3.495833`, outside the pilot-derived endpoint around `-3.700555`. Hypervolume normalization based on ten pilot seeds was therefore unsafe for formal runs.

**Root cause**  
Empirical extrema plus a 10% observed-range margin were treated as bounds on future stochastic search outcomes.

**Resolution**  
The run failed fast, the empirical configuration was archived as rejected, and theoretical bounds were derived from objective definitions: coupling `[0,1]`, negative cohesion from maximum raw edge weight to zero, and an exact feasible imbalance extreme. Formal runners reject empirical-bound provenance.

**Verification**  
Tests compare the analytical imbalance bound with brute force for small class counts, reject empirical configurations and validate metadata on resume. The final 90 primary runs remained inside theoretical bounds.

**Effect on final evidence**  
The incomplete seed was not accepted. Final Hypervolume values use the theoretical normalization contract.

**Repository evidence**  
Commit `77d29d2`; `configs/experiments/archive/stage2_robustness_bounds_empirical_failed.yml`; `configs/experiments/stage2_robustness_bounds.yml`; `tests/test_stage2_robustness.py`.

### [S2-05] Robustness experimental unit was pooled

**Stage:** Stage 2  
**Category:** Statistical/reporting  
**Detected during:** Robustness-run redesign  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
An early runner combined solutions from multiple seeds and selected one representative from the pooled set. This did not yield one independent observation per stochastic run.

**Root cause**  
Search replication and post-search selection were initially implemented as one aggregate workflow.

**Resolution**  
Each seed became an independent NSGA-II execution with its own feasible front, representative solution, partition, metrics and Hypervolume. The formal unit is one run/seed, giving 30 observations per primary subject.

**Verification**  
The robustness runner writes isolated seed directories and a manifest inventory. Statistical scripts read per-seed rows and check seed completeness rather than pooling fronts.

**Effect on final evidence**  
The accepted robustness family was generated under the corrected experimental-unit design; pooled results are historical only.

**Repository evidence**  
Historical `experiments/02_stage2_nsga_structure_only/run.py`; commit `77d29d2`; `run_robustness.py`; per-seed robustness manifests.

### [S2-06] Initialisation-bias diagnostic

**Stage:** Stage 2  
**Category:** Initialisation  
**Detected during:** Post-formal initialization ablation  
**Scientific impact:** Development-only  
**Dissertation relevance:** MEDIUM

**Observed problem**  
The structure-aware population might over-preserve the Leiden basin; conversely, fully random populations might be infeasible or unable to reach useful structural regions.

**Root cause**  
The formal population mixes one Leiden partition, 20 small perturbations, graph-aware groupings and random fill, so initialization meaningfully shapes finite-budget search.

**Resolution**  
A separate diagnostic branch compared warm and random-only populations and tested random repair plus a larger Xerces budget. Formal runs were not rewritten after observing the diagnostic.

**Verification**  
DayTrader random fronts were non-degenerate and had higher normalized HV in all ten pairs but substantially lower modularity. Xerces random HV remained far below seeded HV even after 500 generations; repair changed initial feasibility from zero to complete.

**Effect on final evidence**  
No formal output changed. Results document sensitivity of the search mechanism and remain outside the confirmatory family.

**Repository evidence**  
Commits `205a701`, `a5cc08e`; `results/daytrader/03_stage2_nsga/diagnostics/initialisation_ablation/`; Xerces random-repair and budget-chase directories.

### [S2-07] Convergence evidence added after budget choice

**Stage:** Stage 2  
**Category:** Validation  
**Detected during:** Formal-budget review  
**Scientific impact:** Validation/reproducibility only  
**Dissertation relevance:** MEDIUM

**Observed problem**  
Population 100 and 100 generations were pragmatic settings without retained evidence that every run had fully converged.

**Root cause**  
The initial formal design fixed a feasible computational budget before per-generation convergence reporting existed.

**Resolution**  
Per-generation Hypervolume diagnostics were added for eight runs across all three subjects.

**Verification**  
All eight reached within 1% of their final HV by generation 94. Six improved by less than 2% over the final 20 generations; two retained gains of approximately 2.77% and 4.27%.

**Effect on final evidence**  
No optimizer output changed. The evidence supports budget adequacy but is not reported as proof of universal convergence.

**Repository evidence**  
Commit `4f11707`; `experiments/02_stage2_nsga_structure_only/run_convergence_diagnostic.py`; subject convergence summaries.

### [S2-08] Representative-selector lineage

**Stage:** Stage 2  
**Category:** Selection  
**Detected during:** Post-search operating-profile analysis  
**Scientific impact:** Derived-reporting affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Maximum weighted modularity preserved a conservative reference but did not express the intended balance preference. A later budget relative to Leiden was unavailable in some fronts, and exploratory knee/extreme profiles could be mistaken for formal representatives.

**Root cause**  
Several distinct preference questions were implemented while the authoritative dissertation operating point was still evolving.

**Resolution**  
Selection progressed from runtime MAX-Q, through exploratory conservative/budget/knee/extreme profiles, to a 5% band relative to each current front's `Q_best`, selecting minimum imbalance within the band. Sensitivity at 1%, 3%, 5% and 10% supported 5% as the retained compromise.

**Verification**  
Selector tests validate deterministic tie-breaking and band membership. Sensitivity outputs report subject-specific balance gains and structural costs.

**Effect on final evidence**  
Frozen fronts did not change. Representative-dependent derived reporting changed and was later finalized by XS-04.

**Repository evidence**  
Commits `356d02a`, `e7a22e6`, `c7fb309`, `fdcc5d0`; `docs/stage2/modularity_band_selection.md`; `src/evo_ms/analysis/preference.py`.

### [S2-09] Statistical-family and repeated-run correction

**Stage:** Stage 2  
**Category:** Statistical/reporting  
**Detected during:** Final Stage 2 analysis audit  
**Scientific impact:** Derived-reporting affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Historical analysis mixed obsolete result directories, repeated-run summaries and statistical families whose multiplicity boundaries were not consistently stated.

**Root cause**  
Diagnostic and final 30-seed inventories coexisted while downstream scripts evolved. The older `robustness/` inventory contained 2,994 front rows versus 2,980 in the accepted frozen source.

**Resolution**  
The accepted source was fixed to `robustness_final_30seeds`, statistical families and Holm correction scopes were made explicit, source inventories/hashes were recorded, and obsolete selector-derived outputs were removed or marked historical.

**Verification**  
Analysis manifests check seed counts, source hashes and expected family sizes. Current reports replay from the accepted front inventory without rerunning NSGA-II.

**Effect on final evidence**  
Only derived statistics and reporting authority changed; accepted formal fronts remained frozen.

**Repository evidence**  
Commits `a3db0d9`, `f228ff6`, `ec7de95`; `docs/stage2/reproducibility.md`; Stage 2 analysis manifests.

## 4. Stage 3 Issues

### [S3-01] Semantic representation expanded beyond identifiers

**Stage:** Stage 3  
**Category:** Semantic representation  
**Detected during:** Semantic-probe and Stage 3A review  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
The preliminary semantic probe relied on class/identifier/package/annotation text and a generic MiniLM model. Formal Stage 3A declaration text still omitted behavioral evidence from method bodies.

**Root cause**  
The first probe was designed to establish pipeline feasibility, not to be the final code-semantic representation.

**Resolution**  
Stage 3A froze declaration-only inputs with a pinned code-oriented Nomic model. After Stage 3A was closed, Stage 3B created an isolated representation containing declarations plus selected normalized method-body evidence.

**Verification**  
Input-contract tests validate exact class scope, representation identifier, text hashes and deterministic extraction. Quality reports compare input composition and empty-body coverage.

**Effect on final evidence**  
Stage 3A is superseded exploratory/formal-development evidence. Final Stage 3 uses declaration plus method-body inputs; no comparative model bake-off is claimed.

**Repository evidence**  
Commits `900d023`, `423243c`, `7fa31fe`, `f1c59ec`, `0f8155c`, `f126984`; `tests/test_stage3_input_contract.py`.

### [S3-02] Method-body leakage and scope controls

**Stage:** Stage 3  
**Category:** Semantic representation  
**Detected during:** Stage 3B input-contract design  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Unfiltered bodies could encode package/decomposition labels, compiler artefacts, literals or identifiers outside the frozen application class universe, weakening the claim that the semantic objective used controlled source evidence.

**Root cause**  
Raw method bodies contain more information than the declared experimental construct and can leak naming or scope cues.

**Resolution**  
The final extractor normalizes selected body evidence, enforces the application-class contract, excludes prohibited text categories, records empty bodies/collisions and builds one deterministic text row per retained class.

**Verification**  
Tests cover declaration/body construction, leakage exclusions, exact class identity, deterministic ordering and input hashes. Quality and collision reports check empty bodies and duplicate texts.

**Effect on final evidence**  
Final embeddings were generated from the controlled Stage 3B inputs. Earlier representation artefacts are not used as final evidence.

**Repository evidence**  
Commits `8555465`, `582080f`, `8a21192`, `188dbd4`; `src/evo_ms/semantic/input_contract.py`; Stage 3 input-quality reports.

### [S3-03] Lexical body budget versus model context

**Stage:** Stage 3  
**Category:** Semantic representation  
**Detected during:** Token-budget audit  
**Scientific impact:** Derived-reporting affecting  
**Dissertation relevance:** MEDIUM

**Observed problem**  
The 256-item method-body budget could be described incorrectly as the model tokenizer limit or as model truncation.

**Root cause**  
The pipeline uses two units: deterministic lexical evidence items for body selection and model tokenizer tokens for the complete encoded input.

**Resolution**  
Documentation and metadata distinguish the 256 lexical-item cap from the Nomic context length of 32,768 tokenizer tokens. Model-side truncation remained disabled.

**Verification**  
Eight classes reached the lexical cap—one DayTrader and seven Xerces classes—but complete model inputs used only 754--1,833 tokenizer tokens, at most about 5.59% of context. No input exceeded the model limit.

**Effect on final evidence**  
Embeddings did not change. The correction concerns terminology and interpretation of retained preprocessing.

**Repository evidence**  
Commit `d2ba96d`; `docs/stage3/findings/method_body_quality_summary.md`; Stage 3 input and embedding manifests.

### [S3-04] Per-subject embedding generation and cache guards

**Stage:** Stage 3  
**Category:** Reproducibility  
**Detected during:** Embedding-pipeline validation  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Earlier generation logic risked treating a single existing output as proof that every subject was complete. A broadly scoped `generate_once()` could skip missing per-subject embeddings or reuse an artefact from another representation.

**Root cause**  
Completion and cache identity were initially checked at a coarser scope than subject, representation, model revision and input hash.

**Resolution**  
Generation became per subject and fail-fast. Existing artefacts are accepted only when class scope, representation ID, input aggregate hash, model revision, embedding dimension and per-row hashes match.

**Verification**  
Embedding tests validate all subject manifests, aggregate hashes, dimensions, finite vectors and exact class IDs. Preparation code rejects incomplete or incompatible caches.

**Effect on final evidence**  
Final Stage 3B embeddings were regenerated under the corrected isolated contract; formal optimization outputs use those frozen embeddings.

**Repository evidence**  
Commits `c4c8e92`, `c94f0e7`, `d527a9e`, `6f59520`; `experiments/05_stage3_declaration_method_body/prepare_semantic.py`; `tests/test_stage3_provenance.py`.

### [S3-05] Saved-vector dot product was not true cosine

**Stage:** Stage 3  
**Category:** Embedding validation  
**Detected during:** Nearest-neighbour validation  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Similarity was initially computed as a dot product on saved reduced-precision vectors assumed to remain unit-normalized. Their stored norms were not exactly one, so the value was not true cosine similarity.

**Root cause**  
Normalization occurred before serialization, but floating-point storage altered vector norms slightly.

**Resolution**  
Cosine is computed from the saved vectors using explicit norms. Neighbour and similarity outputs were refreshed before formal graph freeze.

**Verification**  
Tests compare implementation values with independent normalized cosine calculations and check deterministic neighbour order.

**Effect on final evidence**  
Semantic graph inputs were corrected before formal four-objective runs. The frozen final graph contains the corrected similarities.

**Repository evidence**  
Commit `2343862`; Stage 3 embedding-quality diagnostics; semantic graph construction tests.

### [S3-06] Semantic graph sparsity and symmetrisation contract

**Stage:** Stage 3  
**Category:** Graph construction  
**Detected during:** Semantic-graph preregistration and go/no-go validation  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
A full similarity graph was too dense, while one global threshold was not comparable across subjects with different similarity distributions. Directed nearest-neighbour output also required a deterministic undirected conversion.

**Root cause**  
Semantic similarity is dense and subject-dependent; the optimization objective requires a sparse undirected graph.

**Resolution**  
Before formal graph generation, the contract fixed top-3 neighbours and OR symmetrisation: an undirected edge exists if either endpoint selects the other. Self-loops are forbidden, duplicate edges collapse, and ties use cosine then lexical class ID.

**Verification**  
All final graphs have full class coverage, zero isolates and byte-identical replay. Structural-overlap and 1,000 edge-count-matched random-graph checks show the graphs are neither random nor mere copies of the raw graph.

**Effect on final evidence**  
Formal Stage 3 uses the validated top-3 graphs. No claim is made that k=3 was proven optimal.

**Repository evidence**  
Commits `e876755`, `7b8062c`, `9f9c7fe`, `f0cec25`; semantic graph metadata and tests.

### [S3-07] Stage 3A and Stage 3B artefact isolation

**Stage:** Stage 3  
**Category:** Provenance  
**Detected during:** Stage 3B branch audit  
**Scientific impact:** Pre-freeze formal-pipeline affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Declaration-only inputs, embeddings, graphs and selected solutions shared similar names and could be mistaken for declaration-plus-body artefacts.

**Root cause**  
Stage 3B evolved from the frozen Stage 3A pipeline, leaving compatible-looking caches and historical report paths.

**Resolution**  
Stage 3B received separate representation IDs, directories, manifests, preparation code and formal result roots. Architecture tests prohibit Stage 3A paths in final Stage 3 provenance; obsolete active Stage 3A artefacts were retired.

**Verification**  
Boundary tests check input, embedding, graph and optimizer roots. Hash chains connect every Stage 3B run to the declaration-plus-body graph rather than Stage 3A caches.

**Effect on final evidence**  
Final Stage 3 evidence is self-contained. Stage 3A remains historical and does not supply final candidate data.

**Repository evidence**  
Commits `43cad6f`, `18ac6ba`, `1ca1012`, `4ae9086`, `054d11b`, `a844713`; `tests/test_stage3_provenance.py`.

### [S3-08] Four-objective integration regression gate

**Stage:** Stage 3  
**Category:** Optimisation  
**Detected during:** Pre-formal Stage 3B seed-zero integration  
**Scientific impact:** Validation/reproducibility only  
**Dissertation relevance:** HIGH

**Observed problem**  
Adding semantic cohesion could accidentally alter the inherited structural objectives, label scope, 4D front, 3D projection, Hypervolume or representative selection.

**Root cause**  
Stage 3 introduced a new graph, objective and adapter around the Stage 2 optimization API.

**Resolution**  
One seed per subject was run as an explicit go/no-go gate before launching the remaining formal seeds.

**Verification**  
All 321 recomputed structural-objective checks had zero difference. Semantic values were finite and non-constant; 4D fronts were nondominated; projected fronts, class labels, Hypervolume and selector output reproduced; eight output files per subject replayed byte-identically.

**Effect on final evidence**  
The gate changed no accepted result. It authorized the controlled 30-seed execution and demonstrates inheritance fidelity.

**Repository evidence**  
Commits `fac74e5`, `a922df3`; historical `reports/stage3_method_body/seed00_optimizer_validation_summary.md`; structural regression and reproducibility CSVs.

### [S3-09] Formal CSV precision and schema drift

**Stage:** Stage 3  
**Category:** Reproducibility  
**Detected during:** Incremental formal-seed validation  
**Scientific impact:** Derived-reporting affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Adjacent objective values could collapse under insufficient CSV precision, and `run.py`/`run_robustness.py` outputs did not initially expose identical provenance/reporting fields. Validators could therefore disagree although the underlying solution was unchanged.

**Root cause**  
Serialization defaults and separately evolved single-run and robustness schemas were not strict enough for exact replay.

**Resolution**  
Formal objective serialization was increased to preserve distinct floats, validator fingerprints explicitly accepted serialization-only corrections, and shared provenance fields were aligned across runners and analysis.

**Verification**  
Affected seeds were revalidated against in-memory objective values and partition hashes. Regression tests check formal schemas, fingerprints and provenance completeness.

**Effect on final evidence**  
Numerical storage and derived validation records changed; the corresponding candidate partitions and optimization searches were not rerun.

**Repository evidence**  
Commits `d7caca6`, `85db403`, `804d86f`, `649c7d1`; Stage 3 run metadata and formal-run tests.

### [S3-10] Stage 2 representatives leaked into Stage 3 reporting

**Stage:** Stage 3  
**Category:** Statistical/reporting  
**Detected during:** Cross-stage analysis and reporting audit  
**Scientific impact:** Derived-reporting affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Some Stage 3 statistics and comparison tables used historical Stage 2 representative data or runtime MAX-Q selections when the intended comparison required the same operating preference on both stages. `run.py` and robustness-derived schemas also encouraged accidental source substitution.

**Root cause**  
Cross-stage scripts consumed similarly named selected-solution files whose authority changed over time. Exact cause for every stale row was not fully established.

**Resolution**  
Source inventories were added, formal Stage 2 and Stage 3 candidate pools were separated, and selector-dependent comparisons were rebuilt under one declared operating preference. Selector-independent projected-HV rows remained attached to their frozen front sources.

**Verification**  
Per-seed solution IDs, canonical partitions, hashes and source files are recorded and cross-checked. Statistical-family manifests restrict confirmatory rows to the declared three-subject by two-metric family.

**Effect on final evidence**  
Only cross-stage derived reporting changed. Stage 2 fronts, Stage 3 4D fronts, embeddings and graphs remained frozen.

**Repository evidence**  
Commits `74dca15`, `9109a67`, `6222ebf`, `2e0fcff`; `results/stage3/cross_subject/operating_preference_analysis/13_stale_reporting_inventory.csv`.

## 5. Cross-Stage, Reporting and Finalisation Issues

### [XS-01] Branch, worktree and authority ambiguity

**Stage:** Cross-stage  
**Category:** Provenance  
**Detected during:** Repository freeze and historical audit  
**Scientific impact:** Validation/reproducibility only  
**Dissertation relevance:** MEDIUM

**Observed problem**  
Stage branches, validation worktrees, backup refs, a stale local `main` and similarly named result roots made the authoritative development line difficult to infer from checkout state alone.

**Root cause**  
Stages and supplementary validations were developed concurrently in separate worktrees and merged at different times.

**Resolution**  
The authoritative primary branch/HEAD and frozen validation tags are stated explicitly in repository documentation and manifests. Source inventories identify branch/commit and hashes instead of relying on directory names.

**Verification**  
Branch containment, tags, worktree records and pushed commit identities were compared. The primary authority for this record is `stage3-Declaration+Method-Body` at `2e0fcff`.

**Effect on final evidence**  
No scientific output changed; provenance and navigation were clarified.

**Repository evidence**  
`README.md`; `docs/stage2/reproducibility.md`; Stage 3 reproducibility documentation; tags `stage1-validation-frozen`, `stage2-validation-frozen`, `stage3-validation-frozen`.

### [XS-02] Historical and canonical result-layout separation

**Stage:** Cross-stage  
**Category:** Provenance  
**Detected during:** Repository restructuring and report migration  
**Scientific impact:** Derived-reporting affecting  
**Dissertation relevance:** MEDIUM

**Observed problem**  
Historical manifests referred to old report roots while current human-readable and machine-readable authorities had moved. Old selector and diagnostic directories remained plausible citation targets.

**Root cause**  
The repository evolved from stage-local reports to a unified `results/stage*/...`, `docs/...` and reproducible-figure layout.

**Resolution**  
Report ownership, migration maps, deprecation notices and canonical machine-readable roots were documented. Historical outputs were retained for provenance but marked superseded where their selector or source inventory was obsolete.

**Verification**  
Migration tests and provenance locators check that current reports resolve to retained sources. Canonical analysis manifests hash their complete input inventories.

**Effect on final evidence**  
Only location and reporting authority changed; frozen experimental artefacts were not regenerated.

**Repository evidence**  
Commits `e8113c2`, `fb6b01e`, `bf30b26`, `ed7ecca`, `c5dab21`, `9afa566`; `provenance/current_report_locator.json`; deprecation notes.

### [XS-03] Visualisations followed stale representative partitions

**Stage:** Cross-stage  
**Category:** Visualisation  
**Detected during:** Final operating-preference and figure review  
**Scientific impact:** Derived-reporting affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Some cross-stage partition and Xerces cluster-contribution figures were generated from historical MAX-Q or pre-final selector partitions rather than the current BALANCE representatives.

**Root cause**  
Figure exporters consumed earlier selected-partition tables whose authority changed after the operating-preference correction.

**Resolution**  
Selector-dependent figure data were rebuilt from the BALANCE profile table; provenance JSON and the figure manifest were refreshed. Historical cross-stage figure data were marked deprecated.

**Verification**  
Figure tests validate selected identities, class membership, aggregate boundary weights and deterministic output. Provenance files point to the current operating-preference bundle.

**Effect on final evidence**  
Only figures and their derived data changed. No graph, front, embedding or optimizer output changed.

**Repository evidence**  
Commits `fbf396d`, `bd3d579`, `2e0fcff`; `reports/figures/data/cross_stage/DEPRECATED.md`; `tests/test_stage123_xerces_clusters.py`.

### [XS-04] Final 5% BALANCE operating-preference correction

**Stage:** Cross-stage  
**Category:** Selection  
**Detected during:** Final dissertation reporting audit  
**Scientific impact:** Derived-reporting affecting  
**Dissertation relevance:** HIGH

**Observed problem**  
Historical runtime `selected_solution.json` and `selected_partition.csv` recorded MAX-Q, while later reporting intended BALANCE. Earlier selector-dependent reports were inconsistent or stale, and a temporary `selector_5pct_canonical` bundle remained an active-looking dependency. The modularity-loss reference was also liable to be confused with loss relative to Leiden.

**Root cause**  
The operating-preference definition evolved after formal runs, but reporting sources did not all migrate together. Root cause for every stale downstream table was not fully established.

**Resolution**  
`results/stage3/cross_subject/operating_preference_analysis/` became the authority. For each subject/stage/seed it computes current feasible-front `Q_best`, admits `(Q_best-Q)/|Q_best| <= 0.05 + 1e-12`, then BALANCE minimizes imbalance with ties by higher modularity, lower coupling, higher cohesion and deterministic solution ID. MAX-Q is reference-only; COUPLING, COHESION and SEMANTIC are descriptive. Stage 3 BALANCE is recomputed directly from frozen candidate pools, removing active dependence on the superseded bundle.

**Verification**  
All 90 Stage 3 BALANCE solution IDs and all 90 partition hashes matched independent references; 900 profile rows were produced; `--check` passed. Hash comparison confirmed 2,081/2,081 frozen mainline artefacts unchanged.

**Effect on final evidence**  
Only selector-dependent derived reporting, statistics and figures changed. NSGA-II, Pareto fronts, projected fronts, embeddings and semantic graphs were not regenerated. Historical runtime MAX-Q files remain immutable provenance, not BALANCE authority.

**Repository evidence**  
Commits `9109a67`, `6222ebf`, `2e0fcff`; `results/stage3/cross_subject/operating_preference_analysis/01_selector_definitions.json`; `14_validation_report.md`; `manifest.json`.

### [XS-05] Supplementary operating-preference alignment

**Stage:** Cross-stage  
**Category:** Selection  
**Detected during:** Supplementary EasyMock/JFreeChart finalization  
**Scientific impact:** Derived-reporting affecting  
**Dissertation relevance:** MEDIUM

**Observed problem**  
EasyMock and JFreeChart had frozen Stage 2 and Stage 3 runs but lacked reporting under the same current-front 5% BALANCE contract used by the primary subjects. Their nonmatching seed ranges made a direct paired cross-stage test invalid.

**Root cause**  
Supplementary validations were produced on separate stage worktrees: Stage 2 seeds 0--9 and Stage 3 seeds 1--10.

**Resolution**  
The supplementary validation branch applies the same BALANCE definition within each frozen run. It explicitly sets `cross_stage_pairing=false` and `inferential_tests=false`; EasyMock and JFreeChart results are descriptive only.

**Verification**  
All 40 BALANCE selections and partition hashes matched; 200 profile rows were produced; 146/146 frozen supplementary source artefacts were unchanged; the supplementary `--check` passed at `cd6e00c`.

**Effect on final evidence**  
Only supplementary derived reporting was added. Ten retained runs per stage/subject remain frozen; no optimizer, embedding or graph was rerun. Plants is not part of the final study, and no system-size trend is inferred.

**Repository evidence**  
Supplementary validation branch commit `cd6e00c`; `results/stage3/cross_subject/operating_preference_analysis/supplementary/08_validation_report.md`; supplementary manifest.

## 6. Recommended Dissertation Issue Set

| ID | Stage | Problem detected | Correction | Verification | Why suitable for Chapter 4 |
|---|---|---|---|---|---|
| S1-01 | Stage 1 | Unstable subject/class scope | Frozen class universes and subject roles | Extraction tests and manifest counts | Shows input validity before experimentation |
| S1-02 | Stage 1 | Method flows duplicated at class level | Aggregate undirected pairs and drop self-loops | Graph-builder regression tests | Clear graph-construction diagnosis |
| S1-07 | Stage 1 | SSA change confounded with seed variation | Thirty-seed robustness control | Subject-level ARI distributions | Demonstrates correction of scientific interpretation |
| S2-03 | Stage 2 | Constraint prose and implementation diverged | Removed redundant singleton constraint; corrected repair contract | Constraint and repair tests | Shows design fidelity and ablation reasoning |
| S2-04 | Stage 2 | Pilot HV bound failed at seed 12 | Replaced empirical bounds with theoretical bounds | Fail-fast tests and 90-run range validation | Strong failure-to-redesign example |
| S2-05 | Stage 2 | Seeds pooled into one representative | Independent run/front/selection per seed | Per-seed manifests and inventory | Demonstrates correct experimental unit |
| S3-04 | Stage 3 | Cache scope could skip/mix subject embeddings | Per-subject identity and hash guards | Embedding manifest tests | Strong reproducibility control |
| S3-05 | Stage 3 | Dot product on stored vectors was not cosine | Explicit norm-based cosine | Independent similarity regression | Concise numerical bug and verification cycle |
| S3-06 | Stage 3 | Dense or thresholded semantic graphs lacked a stable cross-subject contract | Fixed top-3 OR-symmetrised graph construction | Coverage, isolate, replay and random-graph checks | Shows validation of semantic evidence structure |
| S3-07 | Stage 3 | Stage 3A caches could contaminate Stage 3B | Isolated paths, IDs and provenance chains | Architecture and hash-boundary tests | Shows protection against stale evidence |
| S3-08 | Stage 3 | New objective could alter inherited behavior | Seed-zero integration gate | 321 exact objective checks and byte replay | Demonstrates pre-run regression assurance |
| XS-04 | Cross-stage | Reporting mixed MAX-Q and BALANCE authority | Rebuilt BALANCE reporting from frozen fronts | 90/90 IDs and hashes; 2,081/2,081 unchanged | Critical final reporting correction without rerunning experiments |

## 7. Development and Validation Pattern

The record contains 32 meaningful issues: eight Stage 1, nine Stage 2, ten Stage 3 and five cross-stage/reporting issues. Twenty-two are marked HIGH, ten MEDIUM and none LOW. Fourteen affected the formal pipeline before the relevant result family was frozen, eleven affected derived reporting, six concern validation/reproducibility only, and one is development-only.

Across the prototype, the recurring engineering sequence was: specify a design contract; implement it; add tests, hashes or retained-data checks; observe unexpected behavior or inconsistency; isolate whether it affected formal evidence or only reporting; correct the smallest authoritative layer; and verify both the correction and the integrity of frozen upstream artefacts. Historical diagnostics remained separate from formal confirmatory outputs, and later reporting corrections did not silently trigger new optimization runs.
