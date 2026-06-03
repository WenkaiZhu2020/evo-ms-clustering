# Evolutionary Software Clustering for Microservice Identification

This repository supports a master's dissertation experiment on class-level software clustering for monolith-to-microservices migration. The current implementation covers Stage 1 only:

```text
Soot/Shimple extraction
-> normalized CSVs
-> Pre-experiment diagnostics
-> two formal Stage 1 Leiden profiles
-> result tables
```

`G_raw` uses type and call dependency evidence with `raw_weight`. `G_ssa` adds scoped Soot/Shimple return-value and argument-passing flow evidence with `g_ssa_weight`.

## Subjects

- `jpetstore`: small smoke-test subject for validating the extraction and graph pipeline.
- `daytrader`: calibration subject with a reference-service mapping and SSA weight/resolution sweep outputs.
- `xerces-j`: larger technical remodularization benchmark for transfer and scalability checks.

PiggyMetrics is not used as an input subject.

## Repository Layout

```text
configs/      Experiment and subject configuration.
data/         Input data only: raw Java projects, normalized extracted CSVs, and references.
docs/stage1/ Stage 1 technical documentation and reading guide.
docs/reports/ Human-readable experiment reports and benchmark evidence.
experiments/ Runnable experiment entrypoints.
results/      Generated experiment outputs.
scripts/      Thin command wrappers for current subjects.
src/          Python package implementation.
tests/        Python tests and fixtures.
tools/        Java/Soot extractor.
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The Java extractor is a Maven project under `tools/soot_extractor/`. Use Java 17:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
```

## Run Order

Each subject has thin wrappers under `scripts/`. Raw Java source and build output stay under `data/raw_projects/<subject>/`.

Core runs:

```bash
bash scripts/extract_soot_jpetstore.sh
bash scripts/run_pre_jpetstore.sh
bash scripts/run_stage1_jpetstore.sh

bash scripts/extract_soot_daytrader.sh
bash scripts/run_pre_daytrader.sh
bash scripts/run_stage1_daytrader.sh
bash scripts/run_daytrader_calibration.sh

bash scripts/extract_soot_xerces_j.sh
bash scripts/run_pre_xerces_j.sh
bash scripts/run_xerces_j_sensitivity.sh
bash scripts/run_stage1_xerces_j.sh
```

The Stage 1 Leiden runner reads normalized extracted CSVs directly from:

```text
data/extracted/<subject>/
```

Formal Stage 1 writes two frozen profiles:

- `raw_reference_leiden`: strongest admissible raw structural reference from DayTrader calibration.
- `ssa_selected_leiden`: selected non-zero SSA-informed profile retained for controlled comparison.

## Validation

Run Python tests with:

```bash
.venv/bin/python -m pytest
```

Run the Java/Soot extractor tests with:

```bash
mvn -f tools/soot_extractor/pom.xml test
```

The Maven project is configured to use a Java 17 toolchain for compilation and tests.

## Data Policy

Raw Java subject systems stay under `data/raw_projects/<subject>/` and are local research inputs. Raw projects are ignored by Git. Normalized extractor outputs live under `data/extracted/<subject>/`. Generated experiment outputs live only under `results/<subject>/<stage>/`.
