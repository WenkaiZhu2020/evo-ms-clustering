# Xerces-J Extraction Notes

## Source

- Source path: `data/raw_projects/xerces-j`
- Source repository: `https://github.com/apache/xerces2-j.git`
- Source revision used locally: `cf0c517a4`

## Build / Bytecode Staging

The full upstream Ant `compile` target does not complete on Java 17 because the legacy HTML DOM implementation no longer matches the JDK DOM HTML interfaces. The staged bytecode therefore uses the existing Xerces build preparation step plus a focused `javac --release 8` compile for in-scope application packages.

Staged class output:

- `data/raw_projects/xerces-j/target/classes`

## Package Filters

Included application package prefixes:

- `org.apache.xerces`
- `org.apache.xml`

Excluded from the staged extraction scope:

- `samples/`
- `tests/`
- `tools/`
- `design/`
- generated build support outside the staged `org.apache.xerces` and `org.apache.xml` packages
- `org.apache.html`
- `org.w3c.dom`

`org.w3c.dom` was not included as an application package because it is treated as external API/JDK/library surface for this run.

## Extraction Counts

- Class count: 814
- Structural dependency evidence rows: 20,184
- SSA evidence rows: 7,668

## Graph Counts

Pre-experiment graph outputs were generated under `results/xerces-j/00_pre_experiment/`.

- Raw edge count: 3,780
- G_ssa edge count: 4,148
- New SSA edge count: 368

## Generated Files

Normalized extraction outputs:

- `data/extracted/xerces-j/class_nodes.csv`
- `data/extracted/xerces-j/structural_dependencies.csv`
- `data/extracted/xerces-j/ssa_flow_edges.csv`

Weighted graph outputs:

- `results/xerces-j/00_pre_experiment/graph/raw_edges.csv`
- `results/xerces-j/00_pre_experiment/graph/ssa_edges.csv`
- `results/xerces-j/00_pre_experiment/comparison/metrics_summary.csv`
