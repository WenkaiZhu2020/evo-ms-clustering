# Xerces-J Extraction Notes

## Source

| Item | Value |
| --- | --- |
| Local source path | `data/raw_projects/xerces-j` |
| Upstream repository | `https://github.com/apache/xerces2-j.git` |
| Local source revision | `cf0c517a4` |

## Build Requirements

The full upstream Ant `compile` target does not complete on Java 17 because the legacy HTML DOM implementation does not match the current JDK DOM HTML interfaces.

For this reason, the staged bytecode uses:

- the existing Xerces-J preparation step;
- a focused `javac --release 8` compile;
- only the in-scope application packages.

Compiled classes are staged under:

```text
data/raw_projects/xerces-j/target/classes
````

## Extraction Scope

Included package prefixes:

```text
org.apache.xerces
org.apache.xml
```

Excluded from the staged application scope:

```text
samples/
tests/
tools/
design/
org.apache.html
org.w3c.dom
```

Generated build support outside the staged Xerces-J packages is also excluded.

`org.w3c.dom` is treated as external API or library surface rather than as application code.

## Normalized Outputs

The extraction step writes:

```text
data/extracted/xerces-j/
  class_nodes.csv
  structural_dependencies.csv
  ssa_flow_edges.csv
```

## Reproduction Commands

Prepare the staged classes, then run:

```bash
bash scripts/extract_soot_xerces_j.sh
bash scripts/run_pre_xerces_j.sh
bash scripts/run_xerces_j_sensitivity.sh
bash scripts/run_stage1_xerces_j.sh
```

## Notes

Xerces-J is used as a larger-scale technical case.

It is not treated as a business microservice ground-truth subject.
