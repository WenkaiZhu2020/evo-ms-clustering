# Test Case Selection Summary

This document records the rationale for selecting benchmark subjects for the Stage 1 experiment.

## Current role of subjects

- CargoTracker: primary experimental subject.
- JPetStore: lightweight pipeline validation and debugging subject.

## Excluded subjects

- DayTrader7 was removed from the repository because the extracted results were noisy and did not provide a meaningful scale advantage.
- PiggyMetrics is not used as an input subject because it is already a microservice demo rather than a monolithic system for decomposition.

## Notes to complete

- Explain why CargoTracker is suitable as the main subject.
- Explain why JPetStore is kept as a small sanity-check subject.
- Record any final ground-truth or reference-boundary considerations.
