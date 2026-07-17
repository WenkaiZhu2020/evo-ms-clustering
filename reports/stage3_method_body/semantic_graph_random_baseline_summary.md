# Stage 3B semantic graph random-baseline summary

The preregistered baseline is uniform simple undirected G(n,m), with 1000 repetitions, exact observed edge count, fixed subject seed bases, and `numpy.quantile(method='higher')`. GO uses strict observed > random p95.

| Subject | Observed structural overlap | Random mean | Random median | Random p95 | Random maximum | Observed-minus-random mean | GO |
|---|---:|---:|---:|---:|---:|---:|---|
| jpetstore | 0.531914894 | 0.193234043 | 0.191489362 | 0.276595745 | 0.404255319 | 0.338680851 | true |
| daytrader | 0.437500000 | 0.117196429 | 0.116071429 | 0.160714286 | 0.205357143 | 0.320303571 | true |
| xerces | 0.349196907 | 0.011392029 | 0.011302796 | 0.015466984 | 0.020226056 | 0.337804878 | true |

The random result is a graph-signal diagnostic, not decomposition-quality evidence.
