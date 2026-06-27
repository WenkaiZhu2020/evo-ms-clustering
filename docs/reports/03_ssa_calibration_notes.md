# SSA Calibration Notes

## 1. Purpose

`ssa_lambda` controls the overall contribution of SSA-derived flow evidence after extraction. The embedded row weights are fixed in the normalized CSV rows; lambda scales their aggregate contribution during graph construction.

DayTrader is used for constrained internal-primary calibration with reference-based sanity checks. Its service mapping is a domain-informed proxy reference, not an independent validation oracle.

## 2. Evidence Weights and Formula

| Evidence Channel | Embedded Row Weight |
| --- | ---: |
| Type dependency | 1.0 |
| Method call | 2.0 |
| Return-value flow | 3.0 |
| Argument-passing flow | 3.0 |

```text
raw_ssa_flow_sum = return_flow_weight + argument_flow_weight
ssa_flow_weight = ssa_lambda * raw_ssa_flow_sum
g_ssa_weight = raw_weight + ssa_flow_weight
```

`expected_extracted_evidence_weights` is a validation check only. Changing YAML does not reweight an existing extracted dataset.

## 3. Sweep Space

| Item | Values |
| --- | --- |
| Lambda sweep | 0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0 |
| Calibration lambda regime | 0.0 for raw; 0.0 < lambda <= 1.0 for SSA |
| Stress-testing regime | lambda > 1.0 |
| Resolution grid | 0.5, 0.75, 1.0, 1.25, 1.5 |
| Seed | 42 |

Values above 1.0 are retained in the sweep output for sensitivity and stress testing, but they are not eligible for selecting the formal SSA calibration profile.

## 4. Selection Rule

Candidates must pass these filters:

* non-extreme cluster count;
* `max_cluster_ratio <= 0.4`;
* `singleton_ratio <= 0.15`;
* `reference_coverage_ratio >= 0.8`;
* for SSA candidates, `ssa_lambda <= 1.0`.

Raw candidates use `ssa_lambda = 0.0` and are ranked by weighted modularity, internal edge weight ratio, balance metrics, resolution proximity to 1.0, then reference metrics.

SSA candidates use `0.0 < ssa_lambda <= 1.0`. The rule first keeps candidates within 0.005 weighted-modularity points of the best admissible SSA candidate, then chooses the lowest non-zero lambda in that near-best band. Internal edge weight ratio, balance metrics, resolution proximity, and reference metrics break ties.

MoJoFM and pairwise F1 remain in the output as reference-based sanity checks. They are not primary ranking signals.

Lambda is not a modularity optimum. At resolution 1.0, weighted modularity increases monotonically with lambda (0.3246 at lambda=0.0 to 0.3717 at lambda=4.0; within the admissible `0 < lambda <= 1` range it rises only from 0.3252 at lambda=0.25 to 0.3296 at lambda=1.0, a spread of about 0.0044). The 0.005 near-best tolerance is wider than that in-band spread, so the modularity filter does no discriminating work among admissible non-zero lambdas and the rule degenerates to "keep the smallest non-zero lambda." `ssa_lambda = 0.25` is therefore a conservative minimum-effective policy choice, deliberately avoiding overstatement of the SSA contribution; it is not the modularity-maximising setting (internal modularity would favour larger lambda).

## 5. Selected Profiles

| Profile | Graph Type | Lambda | Resolution | Seed | Role |
| --- | --- | ---: | ---: | ---: | --- |
| `raw_reference_leiden` | raw | 0.0 | 1.0 | 42 | internal-primary raw structural reference |
| `ssa_selected_leiden` | ssa | 0.25 | 1.0 | 42 | minimum-effective non-zero SSA comparison profile |

All 53 retained DayTrader classes are mapped to reference services, so reference coverage is 53 / 53 = 100%. The service-label rationale is documented in `../../data/references/daytrader_reference_services.md`.

The selected profiles are representative controlled-comparison settings. They are not universal optima. The formal Leiden profiles use a fixed seed of 42 for reproducibility; Stage 1 does not claim multi-seed stability.

## 6. SSA Flow Channel Limitation

The two SSA flow channels are not independent evidence at class granularity. Across all three subjects, the set of `return_value_flow` class-pairs is a strict subset of the `argument_passing_flow` class-pairs (set difference = 0):

| Subject | return_value_flow pairs | argument_passing_flow pairs | return-only pairs |
| --- | ---: | ---: | ---: |
| JPetStore | 13 | 20 | 0 |
| DayTrader | 46 | 61 | 0 |
| Xerces-J | 426 | 1456 | 0 |

The same Shimple statement fires both channels, and each adds its embedded row weight, so a single dataflow fact is counted twice (once as return-value flow at weight 3, once as argument-passing flow at weight 3). The two channels are therefore effectively one channel plus its subset, not two independent signals.

Mechanism. At method level the two patterns are genuinely distinct: argument-passing records a value flowing *into* a callee method (`source -> m`), while return-value records a value flowing *out of* a producer method (`m -> sink`). They coincide once methods are aggregated to classes, because `return_value_flow` is only emitted when a call result is itself passed as an argument to a further application call — exactly the situation in which `argument_passing_flow` also fires on that same statement, resolving to the identical class pair. The canonical shape is the intra-object getter/then-use pattern (`x = a.get(); b.use(x)`): when producer and consumer resolve to the same class the relation is an intra-object self-loop that is dropped (it crosses no class boundary and carries no decomposition signal), and when they differ both channels emit the same cross-class edge.

This is a granularity limitation of class-level aggregation, not a defect in the SSA extraction — the distinction the two channels encode is real at method level. It is therefore evidence for treating richer SSA dataflow as method-level future work rather than for adding further SSA channels at class level.

## 7. Reference Alignment

The Leiden partitions do not align with the DayTrader proxy reference. Across the full calibration sweep, `ari_vs_reference` ranges from about -0.015 to 0.105 — that is, indistinguishable from zero — and `pairwise_f1` stays in the 0.13-0.22 band. At the frozen settings the values are essentially unchanged between graphs: raw `ari_vs_reference` = 0.045, ssa = 0.047. SSA does not move reference alignment.

This near-zero alignment is expected and should not be read as a pipeline failure. It reflects a granularity mismatch between two different objectives. Leiden maximises structural modularity over type-and-call edges at class level, so it groups classes that are tightly call-coupled. The proxy reference instead groups classes by business responsibility, which routinely splits structurally-coupled classes across services (for example a service facade and the entities it calls) and unites structurally-distant classes that share a responsibility. A structural class-level partition therefore has no reason to recover a responsibility-level DDD decomposition, and it does not.

Accordingly the reference metrics are reported here as a measured negative result, not merely as a passing "sanity check": at class granularity the structural objective and the responsibility objective are not aligned, which is itself part of the motivation for richer, finer-grained evidence in later stages.
