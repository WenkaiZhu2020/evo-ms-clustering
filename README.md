# Evolutionary Software Clustering for Microservice Identification in Monolith-to-Microservices Migration:
# A Multi-Objective Search Approach Guided by LLM-Derived Semantic Embeddings

This repository supports dissertation research on software clustering for identifying candidate microservices from Java monolithic systems.

The current `stage1-baseline` branch supports only the early pipeline:

- `00` Pre-experiment
- `01` Stage 1 Leiden baseline

## Current Pipeline

```text
Java project
-> dependency extraction
-> raw class graph
-> Soot/Shimple-derived SSA flow extraction
-> G_ssa class graph
-> pre-experiment comparison
-> Leiden community detection baseline
```

## Current Stages

`00` Pre-experiment validates whether Soot-based scoped SSA flow evidence improves the class dependency graph by comparing `G_raw` and `G_ssa`.

`01` Stage 1 Leiden baseline runs Leiden community detection on `G_ssa` to produce a structural baseline.

## Later Dissertation Stages

Stage 2 is planned as structure-only NSGA-II in a later branch.

Stage 3 is planned as LLM-derived semantic embeddings with NSGA-II in a later branch.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Placeholder Runs

```bash
bash scripts/run_pre_jpetstore.sh
bash scripts/run_pre_acmeair.sh
bash scripts/run_stage1_jpetstore.sh
bash scripts/run_stage1_acmeair.sh
```

## Data

Large raw Java projects are local research inputs and are excluded from version control.
Place local subject systems under `data/raw_projects/`.
