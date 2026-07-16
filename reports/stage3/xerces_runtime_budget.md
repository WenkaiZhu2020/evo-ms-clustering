# Xerces-J Stage 2 Runtime Budget

## Evidence and method

Reliable per-seed timing is available for all 30 completed formal Xerces-J Stage 2 seeds. The source is `results/xerces-j/03_stage2_nsga/robustness_final_30seeds/seed_00/run_metrics.json` through `seed_29/run_metrics.json`, using the `runtime_sec` field. The runner records this field in `experiments/02_stage2_nsga_structure_only/run_robustness.py:_run_one_seed`: the timer starts immediately before `_run_seed_in_memory(...)` and stops after the full configuration-matching seed computation returns. Each seed reports `run_type: formal`, `class_count: 814`, and a passing front validation flag.

The top-level manifest is also `results/xerces-j/03_stage2_nsga/robustness_final_30seeds/robustness_manifest.json`. Its start and end timestamps have only one-second precision and are equal, so they were not used for the estimate. The per-seed `runtime_sec` values are the reliable timing evidence.

Stage 2 runs serially in one process. The evidence is the sequential `for seed in seeds` loop in `run_robustness.py:run_robustness`; there is no worker pool or process executor in the formal runner. The estimate therefore uses serial seed totals.

## Valid timed seeds

All 30 formal seeds were valid and included:

| Seed | Seconds |
|---:|---:|
| 0 | 113.524793707998 |
| 1 | 114.076109832968 |
| 2 | 114.836320833012 |
| 3 | 114.505138832959 |
| 4 | 113.047527707997 |
| 5 | 101.193598708021 |
| 6 | 84.809527500009 |
| 7 | 87.773067625007 |
| 8 | 88.846490165975 |
| 9 | 99.566789500008 |
| 10 | 95.450304125028 |
| 11 | 113.574470916996 |
| 12 | 113.286898540973 |
| 13 | 112.132910082990 |
| 14 | 101.116562332958 |
| 15 | 83.261179416033 |
| 16 | 86.858010374999 |
| 17 | 87.370034499967 |
| 18 | 97.447792833962 |
| 19 | 94.102385625010 |
| 20 | 114.572501000017 |
| 21 | 114.531225541956 |
| 22 | 113.146268874989 |
| 23 | 101.032009207993 |
| 24 | 84.765393042006 |
| 25 | 87.626418791013 |
| 26 | 89.213736417005 |
| 27 | 99.977554625017 |
| 28 | 95.352789916971 |
| 29 | 76.661110042012 |

The mean is `99.788630687395` seconds per seed. The median is `99.772172062512` seconds. The minimum is `76.661110042012` seconds for seed 29, and the maximum is `114.836320833012` seconds for seed 2. The observed total for all 30 timed seeds is `2993.658920621849` seconds.

## Estimates

The estimated serial Stage 2 total for 30 seeds is:

$$
T_{\mathrm{Stage2,30}}
=
30\times99.788630687395
=
2993.658920621849\ \mathrm{s}
$$

The conservative Stage 3 estimate is:

$$
T_{\mathrm{Stage3,estimated}}
=
1.5
\times
T_{\mathrm{Stage2,mean}}
=
1.5\times99.788630687395
=
149.682946031092\ \mathrm{s/seed}
$$

$$
T_{\mathrm{Stage3,30}}
=
30
\times
T_{\mathrm{Stage3,estimated}}
=
4490.488380932773\ \mathrm{s}
$$

This is approximately 74.84 minutes, or 1.25 hours, for one serial 30-seed Stage 3 Xerces run. The estimate is a budget, not a measured Stage 3 runtime. It will be updated after Day 5's first complete configuration-matching Xerces seed.
