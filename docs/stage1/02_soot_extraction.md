
# Soot Extraction

The Java extractor is stored under `tools/soot_extractor/`. It reads compiled Java classes, applies package filters, and writes normalized class-level CSV files.

## Inputs

| CLI Option | Meaning |
| --- | --- |
| `--subject` | subject identifier |
| `--classes-dir` | compiled application classes |
| `--classpath` | Soot classpath |
| `--app-packages` | included application package prefixes |
| `--exclude-packages` | optional excluded package prefixes |
| `--out-dir` | normalized CSV output directory |

Only configured application classes are emitted as graph nodes. External libraries and excluded packages are not treated as application classes.

## Extracted Files

```text
data/extracted/<subject>/
  class_nodes.csv
  structural_dependencies.csv
  ssa_flow_edges.csv
```

## Structural Evidence

The extractor records the following structural evidence types:

| Evidence Kind                     | Meaning                                                       |
| --------------------------------- | ------------------------------------------------------------- |
| `extends_type_reference`          | one application class extends another class                   |
| `implements_type_reference`       | one application class implements an in-scope interface        |
| `field_type_reference`            | a field type refers to another application class              |
| `method_parameter_type_reference` | a method parameter refers to another application class        |
| `method_return_type_reference`    | a method return type refers to another application class      |
| `method_call`                     | a method calls a method declared in another application class |

The first five evidence kinds are grouped as type dependencies. Method calls are recorded separately.

## SSA-Derived Flow Evidence

Concrete method bodies are converted into Shimple form for scoped SSA analysis.

The current implementation records:

| Flow Type               | Meaning                                                                     |
| ----------------------- | --------------------------------------------------------------------------- |
| `return_value_flow`     | a returned value is passed from one application class to another            |
| `argument_passing_flow` | a value associated with one class is passed as an argument to another class |

The SSA scope is intentionally limited.

The extractor does not emit:

* phi-related flow as graph evidence;
* local-variable-level graph nodes;
* full pointer-analysis results;
* shared-domain-object evidence.

The final graph remains class-level.

## Subject Wrappers

```bash
bash scripts/extraction/extract_soot_jpetstore.sh
bash scripts/extraction/extract_soot_daytrader.sh
bash scripts/extraction/extract_soot_xerces_j.sh
```

Use Java 17 for extractor tests:

```bash
mvn -f tools/soot_extractor/pom.xml test
```

## Xerces-J Scope

Xerces-J uses staged Java 8-compatible bytecode under Java 17.

The active application scope is centered on:

```text
org.apache.xerces
org.apache.xml
```

Tests, samples, tools, `org.apache.html`, and `org.w3c.dom` are excluded from the application graph.
