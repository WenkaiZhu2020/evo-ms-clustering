# Evolutionary Software Clustering (Stage 1)

This repository contains the Stage 1 code and outputs for a Java software clustering experiment.

Stage 1 compares two class-level graph representations:

* `G_raw`: a structural graph built from type and method-call dependencies.
* `G_ssa`: an SSA-enriched graph that adds selected return-value and argument-passing flow evidence.

Both graphs are clustered with Leiden. The goal is to check whether SSA-derived evidence changes the graph and the resulting class partitions.

Stage 1 is limited to the Leiden baseline. Later NSGA-II and semantic embedding stages are not included here.

## 1. Stage 1 Flow

The Stage 1 workflow is:

```text
Java extraction with Soot / Shimple
→ normalized CSV files
→ CSV loading and validation
→ G_raw / G_ssa graph construction
→ pre-experiment runs
→ DayTrader calibration
→ Xerces-J sensitivity analysis
→ fixed formal Leiden profiles
→ formal Stage 1 outputs
```

There are two main result layers:

* `00_pre_experiment`: diagnostics, calibration, and sensitivity analysis.
* `01_stage1_leiden_baseline`: final Stage 1 outputs generated after the formal profiles are fixed.

## 2. Subject Systems

Three Java systems are used.

### JPetStore

JPetStore is the small subject. It is mainly used to check that the full pipeline works on a compact system.

It checks:

* extraction
* CSV loading
* graph construction
* Leiden clustering
* metric generation

### DayTrader

DayTrader is the calibration subject.

It has a reference-service mapping for the retained application classes, so it is used to select the formal raw and SSA Leiden profiles.

DayTrader is used for:

* default pre-experiment diagnostics
* lambda and resolution calibration
* reference-based comparison during calibration

The DayTrader reference metrics are used as calibration evidence, not as independent validation.

### Xerces-J

Xerces-J is the larger subject.

It is used to check larger-scale behaviour and parameter sensitivity. It does not provide a reference decomposition in this project.

Xerces-J is used for:

* default pre-experiment diagnostics
* larger-scale feasibility checking
* lambda sensitivity analysis
* resolution sensitivity analysis

## 3. Extracted Data

The Java extractor uses Soot and Shimple to process compiled Java classes.

Extractor outputs are stored under:

```text
data/extracted/<subject>/
```

The main CSV files are:

* `class_nodes.csv`
* `structural_dependencies.csv`
* `ssa_flow_edges.csv`

The Python pipeline loads and validates these files before graph construction.

## 4. Graphs

### G_raw

`G_raw` is the raw structural graph.

It uses:

* type dependency evidence
* method call evidence

Main weight column:

* `raw_weight`

### G_ssa

`G_ssa` starts from `G_raw` and adds selected SSA-derived flow evidence:

* return-value flow
* argument-passing flow

Main weight column:

* `g_ssa_weight`

The SSA contribution is controlled by `lambda`.

When `lambda = 0`, `G_ssa` is equivalent to `G_raw` in active edge weights.

## 5. CSV Validation

Before graph construction, the Python loader checks the normalized CSV files.

It validates:

* required columns
* allowed evidence values
* source and target class references
* embedded evidence weights

Main validation files:

* `src/evo_ms/extraction/dependency_extractor.py`
* `src/evo_ms/extraction/evidence_weight_validation.py`

## 6. Pre-experiment

The pre-experiment layer is not the final result layer.

It is used to check that each subject can pass through the full pipeline and to inspect the first effect of SSA-derived evidence.

For all subjects, the default pre-experiment run checks:

* whether the extracted CSVs can be loaded
* whether `G_raw` and `G_ssa` can be constructed
* whether Leiden can run
* whether metrics can be generated
* whether SSA-derived evidence changes the graph or partition

Additional pre-experiment analyses are subject-specific:

* JPetStore is mainly used for pipeline validation.
* DayTrader is used for calibration.
* Xerces-J is used for sensitivity analysis.

## 7. DayTrader Calibration

DayTrader calibration explores combinations of:

* SSA `lambda`
* Leiden resolution

The purpose is to select two formal Leiden profiles:

* `raw_reference_leiden`
* `ssa_selected_leiden`

These profiles are selected for controlled comparison. They are not claimed to be universally optimal.

## 8. Xerces-J Sensitivity Analysis

Xerces-J sensitivity analysis checks how the larger graph reacts when parameters change.

It examines:

* how SSA-weight share changes as `lambda` increases
* how raw and SSA partitions diverge
* how cluster count and modularity respond to parameter changes

This is a larger-scale sensitivity check, not reference-based validation.

## 9. Formal Stage 1

After calibration, two formal Leiden profiles are fixed:

### raw_reference_leiden

* graph: `G_raw`
* weight column: `raw_weight`
* lambda: `0.0`
* resolution: `1.0`
* seed: `42`

### ssa_selected_leiden

* graph: `G_ssa`
* weight column: `g_ssa_weight`
* lambda: `0.25`
* resolution: `1.0`
* seed: `42`

These two profiles are then applied to all three subjects:

* JPetStore
* DayTrader
* Xerces-J

Formal outputs are stored under:

```text
results/<subject>/01_stage1_leiden_baseline/
```

These outputs are the Stage 1 results used for dissertation analysis.

## 10. Repository Structure

```text
configs/      Subject and experiment configuration files.
data/         Raw projects, extracted CSV files, and reference data.
docs/         Stage 1 technical notes and experiment reports.
experiments/  Python experiment entrypoints.
results/      Generated experiment outputs.
scripts/      Shell wrappers for extraction and experiment runs.
src/          Core Python implementation.
tests/        Python tests and fixtures.
tools/        Java Soot extractor.
```

## 11. Main Run Order

Prepare or build the Java subject first, then run extraction.

Extraction:

```bash
bash scripts/extract_soot_jpetstore.sh
bash scripts/extract_soot_daytrader.sh
bash scripts/extract_soot_xerces_j.sh
```

Default pre-experiment diagnostics:

```bash
bash scripts/run_pre_jpetstore.sh
bash scripts/run_pre_daytrader.sh
bash scripts/run_pre_xerces_j.sh
```

Additional pre-experiment analysis:

```bash
bash scripts/run_daytrader_calibration.sh
bash scripts/run_xerces_j_sensitivity.sh
```

Formal Stage 1 outputs:

```bash
bash scripts/run_stage1_jpetstore.sh
bash scripts/run_stage1_daytrader.sh
bash scripts/run_stage1_xerces_j.sh
```

## 12. Testing

Python tests:

```bash
pytest
```

Java extractor tests:

```bash
mvn -f tools/soot_extractor/pom.xml test
```

## 13. Data Policy

Raw Java projects are local research inputs and are not committed.

Normalized extraction outputs are stored under:

```text
data/extracted/
```

Generated experiment outputs are stored under:

```text
results/
```

Final Stage 1 outputs are identified by the frozen Git snapshot and the formal Stage 1 result folders.
