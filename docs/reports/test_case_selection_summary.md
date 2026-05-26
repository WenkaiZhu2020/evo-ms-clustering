# Test Case Selection Summary

This document records the rationale for selecting benchmark subjects for the Stage 1 experiment.

## Subject Roles

- JPetStore: lightweight pipeline validation and debugging subject. It keeps the extraction and graph pipeline easy to inspect.
- DayTrader7: calibration subject for Stage 1 weight-sweep sensitivity analysis. It has a reference-service mapping for external comparison.
- Xerces-J: larger technical remodularization benchmark. It checks whether the Stage 1 pipeline scales beyond small business systems.

## Excluded subjects

- PiggyMetrics is not used as an input subject because it is already a microservice demo rather than a monolithic system for decomposition.

## Selection Rationale

The three-subject design separates smoke testing, calibration, and transfer validation. JPetStore keeps early failures cheap to diagnose. DayTrader supports reference-based calibration. Xerces-J is larger and more technical, so it is useful for checking whether Stage 1 findings hold outside small business examples.
