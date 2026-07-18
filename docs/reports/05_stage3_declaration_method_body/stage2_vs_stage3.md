# Stage 2 versus Stage 3 paired summary

All rows use the same seed IDs 0–29. Stage 3 seed 0 is the frozen validation output and seeds 1–29 are formal outputs. Hypervolume is the frozen projected 3D quantity; semantic values are evaluated on the Stage 3 graph. This is a paired result diagnostic, not decomposition-quality evidence.

| subject | metric | Stage 2 mean | Stage 3 mean | mean delta | wins/ties/losses |
|---|---|---:|---:|---:|---:|
| jpetstore | projected_hv | 0.401254 | 0.387580 | -0.013674 | 4/0/26 |
| jpetstore | selected_f_semantic | 0.512260 | 0.512095 | -0.000165 | 2/26/2 |
| daytrader | projected_hv | 0.184832 | 0.189818 | 0.004986 | 16/0/14 |
| daytrader | selected_f_semantic | 0.636301 | 0.614876 | -0.021426 | 15/0/15 |
| xerces | projected_hv | 0.134422 | 0.136884 | 0.002462 | 13/0/17 |
| xerces | selected_f_semantic | 0.390085 | 0.387322 | -0.002763 | 21/7/2 |
