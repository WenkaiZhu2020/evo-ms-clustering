# Evolutionary Software Clustering (Stage 1)

This repository implements Stage 1 of a research prototype for class-level software modularization using structural dependencies and SSA-derived data-flow evidence.

The goal is to study how SSA enrichment affects Leiden clustering results on Java monolithic systems.

## 1. Stage 1 Scope

Stage 1 includes the full pipeline:

Soot / Shimple extraction  
→ normalized CSV generation  
→ graph construction (G_raw / G_ssa)  
→ Leiden clustering  
→ pre-experiment diagnostics  
→ DayTrader calibration  
→ Xerces-J sensitivity analysis  
→ formal Stage 1 outputs  

## 2. Subject Systems

- JPetStore  
  Small system used for pipeline validation and sanity checking.

- DayTrader  
  Calibration subject with reference mapping.  
  Used to select formal Leiden profiles.

- Xerces-J  
  Large-scale system used for sensitivity and scalability analysis.

## 3. Graph Construction

### G_raw (structural graph)

Built from:
- type dependencies
- method call dependencies

Weight column:
- raw_weight

### G_ssa (SSA-enriched graph)

Built from G_raw + SSA-derived data-flow evidence:

- return-value flow
- argument-passing flow

Weight column:
- g_ssa_weight
- scaled by lambda

If lambda = 0:

G_ssa == G_raw

## 4. SSA Evidence

SSA evidence is extracted using Soot / Shimple at method level.

It produces data-flow records which are aggregated into class-level edges.

Two types of SSA evidence:
- return flow
- argument flow

These are summed and injected into the graph as additional edge weights.

## 5. Experiment Pipeline

Extraction (Soot)  
→ CSV normalization  
→ G_raw / G_ssa construction  
→ Pre-experiment (diagnostic run)  
→ DayTrader calibration (lambda + resolution sweep)  
→ Formal profile selection  
→ Stage 1 formal runs (all subjects)  
→ Xerces-J sensitivity analysis  

## 6. Pre-experiment

Purpose:
- verify extraction correctness
- validate graph construction
- ensure Leiden execution works
- observe initial SSA impact

Not used for final results.

## 7. Calibration (DayTrader)

Used to select formal Leiden profiles:

- raw_reference_leiden
- ssa_selected_leiden

These are fixed for Stage 1.

## 8. Xerces-J Sensitivity

Used for:

- large-scale behavior check
- lambda sensitivity
- SSA impact at scale

Not reference-based.

## 9. Formal Stage 1

After calibration, both profiles are frozen and applied to:

- JPetStore
- DayTrader
- Xerces-J

These outputs are the final results used in Chapter 4.

## 10. Repository Structure

configs/      subject and experiment configuration  
data/         raw projects, extracted CSVs, reference data  
docs/         Stage 1 documentation and reports  
experiments/  runnable pipelines  
results/      generated outputs  
scripts/      execution wrappers  
src/          core implementation  
tests/        unit tests  
tools/        Soot extractor (Java/Maven)  

## 11. Execution

bash scripts/extract_soot_jpetstore.sh  
bash scripts/run_pre_jpetstore.sh  
bash scripts/run_stage1_jpetstore.sh  

bash scripts/extract_soot_daytrader.sh  
bash scripts/run_pre_daytrader.sh  
bash scripts/run_daytrader_calibration.sh  
bash scripts/run_stage1_daytrader.sh  

bash scripts/extract_soot_xerces_j.sh  
bash scripts/run_pre_xerces_j.sh  
bash scripts/run_xerces_j_sensitivity.sh  
bash scripts/run_stage1_xerces_j.sh  

## 12. Testing

pytest

mvn -f tools/soot_extractor/pom.xml test

## 13. Data Policy

data/raw_projects/ → ignored by git  
data/extracted/ → normalized CSV outputs  
results/ → experiment outputs (frozen via git tag)  

Only tagged Stage 1 outputs are considered final.