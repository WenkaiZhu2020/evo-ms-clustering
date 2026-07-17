# Stage 3 Day 5 single-seed validation

The frozen four-objective Stage 3 runner was validated with seed `0` for all
three formal subjects. The implementation commit used by every run was
`d819b2d0c0418a7c0e5de427f55879d9c8fb7aef`.

| subject | classes | runtime (s) | 4D front | projected 3D front | `f_semantic` min–max | projected HV | selected solution | structural invariance |
|---|---:|---:|---:|---:|---:|---:|---|---|
| JPetStore | 24 | 7.642406 | 100 | 44 | 0.149554–0.847204 | 0.38086979683420186 | `seed0_solution000` | PASS |
| DayTrader | 53 | 9.687392 | 100 | 70 | 0.483808–0.937326 | 0.20543425788623890 | `seed0_solution028` | PASS |
| Xerces | 814 | 70.860656 | 100 | 76 | 0.381077–0.943873 | 0.14399716267130458 | `seed0_solution014` | PASS |

## Validation evidence

- The first three objective values were independently recomputed from each
  saved partition with the unchanged Stage 2 structural evaluator.
- The fourth value was independently recomputed from the frozen semantic edge
  table. All saved rows matched within absolute tolerance `1e-12`.
- The final four-dimensional fronts were rechecked for non-dominance and
  `f_semantic` was finite, within `[0, 1]`, and nonconstant for every subject.
- The projected fronts were re-filtered independently in the original three
  objectives. Stored and independently recomputed Hypervolume agreed within
  `1e-12` for every subject.
- Representative selection used the exact Stage 2 selection schema and did
  not include the semantic objective as a selection field.
- Fixed Leiden, all-one, and deterministic two-cluster partitions produced
  identical Stage 2 and Stage 3 values for coupling, cohesion, and imbalance
  for every subject.
- The runner loaded the frozen raw graph and semantic edge table separately;
  it did not load model weights, generate embeddings, or create a fused graph.

## Comparison metadata

The same-seed Stage 2 Hypervolume values were loaded from the frozen Stage 2
robustness records:

| subject | Stage 2 seed-0 HV |
|---|---:|
| JPetStore | 0.38853439926036243 |
| DayTrader | 0.17477107919460103 |
| Xerces | 0.13450421313218270 |

These are descriptive validation metadata only. No result-dependent conclusion
or statistical claim is made at this checkpoint.
