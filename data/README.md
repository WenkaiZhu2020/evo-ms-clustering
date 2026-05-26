# Data

This directory contains the input data used by the Stage 1 clustering pipeline.

- `raw_projects/`: local Java subject checkouts used to compile classes for extraction. These directories are local inputs and are not versioned.
- `extracted/`: normalized Soot/Shimple CSVs produced by the extractor and consumed by the Python graph pipeline.
- `references/`: optional reference or ground-truth material, currently used for DayTrader calibration.

Experiment outputs are written under `results/<subject>/<stage>/`.
