# Stage 3B semantic graph quality summary

This report covers isolated top-3 graph construction, graph correctness, structural/random diagnostics, and descriptive Stage 3A comparison only. No NSGA-II, seed, Hypervolume, representative selection, or decomposition-quality analysis was run.

Frozen graph contract: true cosine; all non-self candidates; top-3; cosine descending then class_id lexicographic ascending; OR symmetrisation; no edge threshold; self-loops and duplicate final edges forbidden.

| Subject | Nodes | Directed rows | Final edges | Components | Isolated | Weight min/mean/median/std/max | Degree min/mean/median/std/max |
|---|---:|---:|---:|---:|---:|---|---|
| jpetstore | 24 | 72 | 47 | 1 | 0 | 0.504740168/0.647380488/0.640603478/0.074647673/0.827444058 | 3/3.916667/4.000000/1.187317/7 |
| daytrader | 53 | 159 | 112 | 1 | 0 | 0.320331185/0.597278080/0.612567134/0.124187751/0.864117179 | 3/4.226415/4.000000/1.449027/8 |
| xerces | 814 | 2442 | 1681 | 12 | 0 | 0.432573037/0.723570982/0.715479496/0.116296531/1.000000000 | 3/4.130221/4.000000/1.373761/14 |

## Structural overlap and random baseline

| Subject | Observed overlap | Novel edge share | Random mean | Random p95 | Random max | Observed-minus-random mean | GO |
|---|---:|---:|---:|---:|---:|---:|---|
| jpetstore | 0.531914894 | 0.468085106 | 0.193234043 | 0.276595745 | 0.404255319 | 0.338680851 | true |
| daytrader | 0.437500000 | 0.562500000 | 0.117196429 | 0.160714286 | 0.205357143 | 0.320303571 | true |
| xerces | 0.349196907 | 0.650803093 | 0.011392029 | 0.015466984 | 0.020226056 | 0.337804878 | true |

## Stage 3A versus Stage 3B graph change

| Subject | Shared | Stage 3B-only | Jaccard | Mean retention | Zero retention | All retained |
|---|---:|---:|---:|---:|---:|---:|
| jpetstore | 38 | 9 | 0.666666667 | 0.833333333 | 0 | 12 |
| daytrader | 81 | 31 | 0.570422535 | 0.742138365 | 1 | 20 |
| xerces | 1274 | 407 | 0.612500000 | 0.756347256 | 9 | 333 |

## Empty versus non-empty body

Changes for empty-body classes can include section-marker and explicit-empty-template effects; they are not attributed solely to lexical method-body content.

* jpetstore / empty: n=7; mean retention=0.8571428571428571; median=1.0; zero-retention=0; all-retained=4; mean embedding shift=0.2078822981912857; mean degree change=0.0
* jpetstore / non_empty: n=17; mean retention=0.8235294117647058; median=0.6666666666666666; zero-retention=0; all-retained=8; mean embedding shift=0.20391813525311767; mean degree change=-0.11764705882352941
* daytrader / empty: n=4; mean retention=0.75; median=0.8333333333333333; zero-retention=0; all-retained=2; mean embedding shift=0.12406171958074999; mean degree change=-1.0
* daytrader / non_empty: n=49; mean retention=0.7414965986394557; median=0.6666666666666666; zero-retention=1; all-retained=18; mean embedding shift=0.1886881181427551; mean degree change=0.12244897959183673
* xerces / empty: n=120; mean retention=0.7527777777777778; median=0.6666666666666666; zero-retention=1; all-retained=44; mean embedding shift=0.11010501787423334; mean degree change=-0.31666666666666665
* xerces / non_empty: n=694; mean retention=0.7569644572526417; median=0.6666666666666666; zero-retention=8; all-retained=289; mean embedding shift=0.19011652320513975; mean degree change=0.07780979827089338

## Evidence-composition correlations

Spearman values are descriptive associations only and are not causal claims.

* jpetstore: body_token_count_vs_neighbour_change=-0.030483271712477958; embedding_shift_vs_neighbour_change=0.4935819976516537; field_proportion_vs_neighbour_change=-0.08533413211098875; invoked_method_proportion_vs_neighbour_change=0.042667066055494376; string_proportion_vs_neighbour_change=-0.2510266983652955
* daytrader: body_token_count_vs_neighbour_change=-0.10734971334088798; embedding_shift_vs_neighbour_change=0.14314692002170343; field_proportion_vs_neighbour_change=-0.0321510071048033; invoked_method_proportion_vs_neighbour_change=-0.1404634961784833; string_proportion_vs_neighbour_change=-0.05585763837747422
* xerces: body_token_count_vs_neighbour_change=0.004211736373035744; embedding_shift_vs_neighbour_change=0.042307751071670174; field_proportion_vs_neighbour_change=0.05141264824546364; invoked_method_proportion_vs_neighbour_change=-0.02368645461655625; string_proportion_vs_neighbour_change=0.04115543052431069

## Graph gates

* All expected nodes are covered; no self-loops or duplicate final edges were found.
* All edge weights are finite; no threshold or post-hoc collision filtering was applied.
* Canonical and independent temporary graph generations were byte-identical.
* Structural GO is evaluated with strict observed > random p95 using the preregistered 1000-repetition baseline.
* The task stops before optimization.
