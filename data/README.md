# Data

This directory contains the input data used by the Stage 1 clustering pipeline.

- `raw_projects/`: local Java subject checkouts used to compile classes for extraction.
- `extracted/`: normalized Soot/Shimple CSVs produced by the extractor and consumed by the Python pipeline.
- `references/`: optional reference or ground-truth material.

Experiment outputs are written under `results/<subject>/<stage>/`.
