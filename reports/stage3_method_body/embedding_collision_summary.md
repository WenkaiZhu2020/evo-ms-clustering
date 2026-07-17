# Stage 3B embedding collision summary

This is an input and numerical collision diagnostic only. It does not claim semantic quality improvement and does not deduplicate classes.

| Subject | Duplicate text groups | Duplicate embedding groups | Non-identical-text duplicate embeddings |
|---|---:|---:|---:|
| jpetstore | 0 | 0 | 0 |
| daytrader | 0 | 0 | 0 |
| xerces | 11 | 11 | 0 |

Xerces has exactly 11 duplicate-text groups under the frozen simple-name input contract. These duplicate classes and their embeddings were retained unchanged in scope.
Non-identical Stage 3B semantic texts did not produce duplicate embedding byte sequences.
