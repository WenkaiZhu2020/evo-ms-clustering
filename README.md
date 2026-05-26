# Evolutionary Software Clustering for Microservice Identification

This repository supports a master's dissertation experiment on class-level software clustering for monolith-to-microservices migration.

The current implementation is limited to the Stage 1 structural pipeline:

```text
Soot/Shimple extraction
-> normalized CSVs in data/extracted/<subject>/
-> G_raw and G_ssa construction
-> Leiden clustering
-> evaluation tables in results/<subject>/<stage>/
```

`G_raw` uses type and call dependency evidence with `raw_weight`.

`G_ssa` adds Soot/Shimple-derived return_value flow and argument_passing flow evidence with `g_ssa_weight`.

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
docs/archive/ Historical/deprecated notes only.
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

Each subject has a thin script wrapper under `scripts/`. Raw Java source and build output stay under `data/raw_projects/<subject>/`.

JPetStore expects compiled classes under:

```text
data/raw_projects/jpetstore/target/classes
```

Core runs:

```bash
bash scripts/extract_soot_jpetstore.sh
bash scripts/run_pre_jpetstore.sh
bash scripts/run_stage1_jpetstore.sh

bash scripts/extract_soot_daytrader.sh
bash scripts/run_pre_daytrader.sh
bash scripts/run_stage1_daytrader.sh
bash scripts/run_daytrader_weight_sweep.sh

bash scripts/extract_soot_xerces_j.sh
bash scripts/run_pre_xerces_j.sh
bash scripts/run_stage1_xerces_j.sh
```

The Stage 1 Leiden runner depends on the pre-experiment output:

```text
results/<subject>/00_pre_experiment/graph/ssa_edges.csv
```

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
