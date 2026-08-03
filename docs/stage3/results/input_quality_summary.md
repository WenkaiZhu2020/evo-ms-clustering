# Stage 3B input quality summary

This report is limited to semantic-input construction. It does not evaluate embeddings, graphs, optimization, or decomposition quality.

| Subject | Classes | Empty body | Method-body budget affected | Model tokenizer truncation | Declaration tokens min/mean/median/std/max | Body tokens min/mean/median/std/max | Total tokens min/mean/median/std/max | Aggregate input SHA-256 |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| jpetstore | 24 | 7 | 0 | 0 | 16/78.46/53.00/80.18/386 | 0/21.12/13.50/20.42/67 | 27/110.29/73.00/97.74/466 | `2d9007f75a14f4a4ed6152563241b898837b6c12b66a98a2464b4cc3f969a921` |
| daytrader | 53 | 4 | 1 | 0 | 7/116.08/53/128.61/678 | 0/46.49/33/50.90/256 | 29/174.68/114/178.42/975 | `da53d434b820e3c25bc69df63ced807cd0113d412fa36acc9694d1a97631d655` |
| xerces | 814 | 120 | 7 | 0 | 5/86.16/43.00/134.24/1501 | 0/34.34/20.00/45.76/256 | 15/136.25/75.00/187.09/1833 | `65488944220cc3a503994d6f2289e0f7bdc06c619351a2e8243bca243538c8a3` |

No semantic input reached the embedding model's 32,768-token context limit;
tokenizer truncation was disabled and the observed model tokenizer truncation
count is zero for every subject. The independent 256-token method-body evidence
budget affected 0 JPetStore, 1 DayTrader, and 7 Xerces-J classes.

## Fixed gates

* Scope is compared against the frozen Stage 3A class IDs.
* Declaration preservation is byte-level and recorded in `declaration_preservation.csv`.
* Declaration truncation is forbidden and must remain zero.
* Method-body budget capping is deterministic and body-only under the independent 256-token evidence budget.
* Embedding-model tokenizer truncation is a separate control and remained zero.
* Raw Shimple, FQNs, owner names, type contexts, paths, and graph edges are excluded.

## Feature and generated-code policy

See `body_feature_availability.csv` and the per-class CSV. Source-level local-variable metadata was not reliable; synthetic locals were rejected. No class was removed for repetitive content; compiler synthetic-method evidence is reported.

## Collision comparison

* jpetstore: 0 Stage 3A collision groups; statuses: {}; 0 Stage 3B full-text collision groups; 0 new Stage 3B groups.
* daytrader: 0 Stage 3A collision groups; statuses: {}; 0 Stage 3B full-text collision groups; 0 new Stage 3B groups.
* xerces: 11 Stage 3A collision groups; statuses: {"unchanged": 11}; 11 Stage 3B full-text collision groups; 0 new Stage 3B groups.

## Leakage gate

Automated failures: 0. Any confirmed prohibited leakage blocks input acceptance.
