# Stage 2 versus final Stage 3 paired summary

All rows use matching seeds 0–29. Projected Hypervolume uses the already
accepted pairs in `stage2_vs_stage3/paired_per_seed.csv`. The selected semantic
rows use the active Stage 2 5% modularity-band profile, not the historical
representative columns retained in that HV source file. Both selected
partitions are evaluated on the same final Declaration + Method Body semantic
graph.

| subject | metric | Stage 2 mean | Stage 3 mean | paired median delta | better/tie/worse |
|---|---|---:|---:|---:|---:|
| jpetstore | projected_hypervolume | 0.401254 | 0.387580 | -0.015953 | 4/0/26 |
| jpetstore | selected_f_semantic | 0.524396 | 0.512095 | 0.004660 | 13/0/17 |
| daytrader | projected_hypervolume | 0.184832 | 0.189818 | 0.001710 | 16/0/14 |
| daytrader | selected_f_semantic | 0.647044 | 0.614876 | -0.021442 | 16/0/14 |
| xerces | projected_hypervolume | 0.134422 | 0.136884 | -0.000655 | 13/0/17 |
| xerces | selected_f_semantic | 0.418530 | 0.387322 | -0.029561 | 30/0/0 |

For Hypervolume, higher is better. For `selected_f_semantic`, lower is better.
The current semantic pairs are recorded in
`formal_statistics/formal_selected_fsemantic_per_seed.csv`.
