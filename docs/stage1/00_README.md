
# Stage 1 Documentation

Stage 1 covers class-level extraction, graph construction, diagnostic analysis, and formal Leiden baseline profiles.

## Reading Order

| File | Topic |
| --- | --- |
| `01_stage1_overview.md` | Stage 1 scope, subject roles, and experiment layers |
| `02_soot_extraction.md` | Soot and Shimple extraction process |
| `03_data_schema.md` | normalized input and output schemas |
| `04_graph_construction.md` | `G_raw`, `G_ssa`, evidence weights, and aggregation rules |
| `05_metric_definitions.md` | Stage 1 metrics |
| `06_xerces-j_extraction_notes.md` | Xerces-J build and extraction notes |

## Pipeline

```text
compiled Java classes
-> Soot / Shimple extraction
-> normalized CSVs under data/extracted/<subject>/
-> Pre-experiment diagnostics
   -> raw-vs-SSA comparison
   -> DayTrader calibration, where applicable
   -> Xerces-J sensitivity analysis, where applicable
-> formal Stage 1 Leiden profiles
-> later Stage 2 NSGA-II comparison
```

## Active Subjects

| Subject     | Role                             |
| ----------- | -------------------------------- |
| `jpetstore` | small pipeline-validation case   |
| `daytrader` | constrained calibration case with reference-based sanity checks |
| `xerces-j`  | larger-scale sensitivity case    |

Research-facing summaries are stored under `docs/stage1/findings/`; shared
Pre-experiment selection and calibration notes are under
`docs/pre_experiment/findings/`.
