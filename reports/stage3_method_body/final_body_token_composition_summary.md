# Final Stage 3B body-token composition

Counts are computed from the final appended `[METHOD_BODY]` token sequence, not raw extraction occurrence counts. A deterministic replay of the frozen Body V1 candidate ordering was aligned byte-for-byte with each saved body section before aggregation.

| Subject | Final body tokens | Invoked methods | Fields | Locals | Exceptions | Strings | Operations | Dominant source |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| jpetstore | 507 | 276 (54.4%) | 96 (18.9%) | 0 (0.0%) | 2 (0.4%) | 56 (11.0%) | 77 (15.2%) | invoked_method |
| daytrader | 2464 | 848 (34.4%) | 479 (19.4%) | 25 (1.0%) | 36 (1.5%) | 786 (31.9%) | 290 (11.8%) | invoked_method |
| xerces | 27952 | 9149 (32.7%) | 9470 (33.9%) | 1270 (4.5%) | 1035 (3.7%) | 3017 (10.8%) | 4011 (14.3%) | field |

The dominant final evidence type is reported descriptively and does not change weights or filtering. Body-budget removals and deterministic filter/repetition removals are recorded in the CSV.
