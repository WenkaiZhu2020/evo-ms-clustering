# Stage 3A versus Stage 3B paired and cross-semantic evaluation

Stage 3A and Stage 3B use the same frozen optimizer contract. The cross-semantic columns evaluate saved partitions on the other frozen semantic graph; no representative was reselected.

| subject | metric | Stage 3A mean | Stage 3B mean | mean delta | wins/ties/losses |
|---|---|---:|---:|---:|---:|
| jpetstore | projected_hv | 0.377585 | 0.387580 | 0.009995 | 24/0/6 |
| jpetstore | selected_f_semantic | 0.598908 | 0.512095 | -0.086813 | 30/0/0 |
| daytrader | projected_hv | 0.183180 | 0.189818 | 0.006638 | 17/0/13 |
| daytrader | selected_f_semantic | 0.588306 | 0.614876 | 0.026570 | 15/0/15 |
| xerces | projected_hv | 0.135618 | 0.136884 | 0.001266 | 13/0/17 |
| xerces | selected_f_semantic | 0.382959 | 0.387322 | 0.004363 | 2/0/28 |
