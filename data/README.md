# Data

This directory contains the input data used by the Stage 1 clustering pipeline.

- `raw_projects/`: local Java subject checkouts used to compile classes for extraction. These directories are local inputs and are not versioned.
- `extracted/`: normalized Soot/Shimple CSVs produced by the extractor and consumed by the Python graph pipeline.
- `references/`: optional domain-informed proxy reference material, currently used for DayTrader calibration sanity checks. See `references/daytrader_reference_services.md` for the DayTrader reference-partition rationale.

Experiment outputs are written under `results/<subject>/<stage>/`.
