# Stage 3A final closure

## Status

Stage 3A is the completed declaration-level semantic experiment. Its formal
30-seed results, validation records, paired Stage 2 comparison, and saved-
partition external evaluation are frozen. This closure is local only; nothing
was pushed.

The final Stage 3A sealing commit is the commit containing this report and is
the target of the local annotated tag `stage3-declaration-final`. The preceding
scientific artifact commit is `bf42a01` (`reports(stage3): complete Stage 2
versus Stage 3 external comparison`).

## Formal inventory and result paths

| subject | classes | valid seeds | formal results |
|---|---:|---:|---|
| JPetStore | 24 | 30 | `results/jpetstore/04_stage3_semantic/` |
| DayTrader | 53 | 30 | `results/daytrader/04_stage3_semantic/` |
| Xerces | 814 | 30 | `results/xerces/04_stage3_semantic/` |

Stage 2 comparison roots are the frozen `results/*/03_stage2_nsga/robustness_final_30seeds/`
directories. Stage 3A paired outputs are under `reports/stage3/`.

## Frozen identity

| artifact | JPetStore | DayTrader | Xerces |
|---|---|---|---|
| semantic input aggregate | `1ecdb9083a37668fd07388454095a317268c8b736e6fd45957ab16bf87f6ad23` | `ab09380f87119e4fe4621efbbdd8fdfd8cfc92cd383ed812169e2427a35eae44` | `f81d0f9bda5aa0fcdf3a35c75876cc73c8b419eccfb8c9e00634ec13fad4d60a` |
| embedding aggregate | `0ae28938fef7b0c0295a5b1d33527708af7493b4f43d524436ffbf258db8802a` | `c7d2cbeec9d4c6ff5f9054b7d66563e98cffc6774771d5727030248299b7756e` | `9504e21bb305a60cdfce58421b64240d1af893fd549b40b9441a00bf0fee8cb1` |
| semantic graph aggregate | `8a51077ba7f852eae7a7fe9d8f5393bed9aef9eb8e5ca269fc01e6b96f2cb275` | `699f3d1f4df32c44f9c30954e1a1cc144127d4ce7a9d8d99608478d562fa6590` | `ab6fc959bfe41ce46fbcfcbbec083a89b7db9d7d302b96877183ff3c8c2a3be9` |

Frozen model: `nomic-ai/nomic-embed-code`, revision
`9a0457648f060c4279d4a3982d2d27a4df6fac59`, dimension 3584, true cosine,
top-k 3, OR symmetrisation, and the frozen four-objective selection pipeline.

Configuration and manifest hashes:

- `configs/experiments/04_stage3_semantic.yml`: `eddbb3674dacabfac2925f4ef6887bb86c9030f629a231230d6a889e1c28cc27`
- `docs/stage3/method_contract.md`: `da10b4208dc0262f5c41a8537a49e86dd754db49781565586e66ac4474a8dffd`
- `reports/stage3/formal_run_manifest.json`: `c0872bfea516180be21925e5349094dee63a90003f139b2b178498a5c6e4379b`

## External saved-partition evaluation

The evaluation used `src/evo_ms/evaluation/reference_metrics.py` without
reselecting either Stage 2 or Stage 3A representatives. DayTrader used the
complete mapping at `data/references/daytrader_reference_services.csv` with
53/53 class coverage. JPetStore and Xerces have no frozen compatible external
reference mapping and remain explicitly unavailable.

For DayTrader, Stage 3A minus Stage 2 mean deltas were:

| metric | mean delta | Holm-adjusted p | conclusion |
|---|---:|---:|---|
| MoJoFM | +1.666667 | 0.483221 | not statistically supported |
| Pairwise F1 | +0.013838 | 0.227219 | not statistically supported |
| reference ARI | +0.015670 | 0.417609 | not statistically supported |
| reference NMI | +0.026123 | 0.266866 | not statistically supported |

Thus, the available external evidence does not establish a statistically
supported Stage 3A external-quality improvement. JPetStore and Xerces remain
N/A rather than being imputed.

## Paired analysis outputs

- `reports/stage3/stage2_vs_stage3_paired_seed_metrics.csv` — SHA-256
  `1dc4df5151a2b271081df7ed73adc850d2b21f10283a7b246ab856a7d24d9276`
- `reports/stage3/stage2_vs_stage3_paired_descriptive_summary.csv` — SHA-256
  `59533801a700c21def844736c3d02b118ae83d725d604822fbc1a68b97e4d184`
- `reports/stage3/stage2_vs_stage3_paired_statistical_tests.csv` — SHA-256
  `e2be988881cc1f025a513cb04454a1441438c381815274e8549f2f278c57138d`
- `reports/stage3/stage2_vs_stage3_external_metric_evaluation.csv` — SHA-256
  `828d24408b59b7f8114e3518e83fa65504235315f39b37e1fe8a4baf97808b1d`
- `reports/stage3/stage2_vs_stage3_paired_analysis.md` — SHA-256
  `071a57ed1dc1563293b90c2bb0340a4bc1a6a5309b7207f04ca3bb2e26f4428d`

The primary projected-HV result remains unchanged: Stage 3A did not establish
overall superiority over Stage 2. DayTrader external improvements were
descriptive only, and were not used to select a representative.

## Validation and limitations

- Formal seed inventory: 30/30 valid for all three subjects.
- Saved Stage 2 and Stage 3A partitions: exact seed and class-scope alignment.
- Stage 2 HV and Stage 3A projected-HV independent recomputation: passed.
- Stage 2 semantic-cut evaluation and Stage 3A semantic round-trip: passed.
- External recomputation against saved Stage 2 DayTrader values: passed within `1e-12`.
- Focused paired-analysis and reference-metric tests: passed.
- Full Python suite: 211 passed, 1 preserved legacy scaffold failure, 3 warnings.
  The failure is the pre-existing test that rejects the already-present
  `docs/stage3` directory; it was not changed or weakened.

Stage 3A is frozen. Future Stage 3B work must use isolated `reports/stage3_method_body/`,
`data/semantic_text/declaration_method_body/`, and Stage 3B result paths. It must
not overwrite Stage 3A semantic inputs, embeddings, graphs, formal results,
validation reports, or paired-analysis outputs.
