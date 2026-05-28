# Soot Extraction

Stage 1 uses a standalone Maven-based Java extraction tool to prepare normalized class-level CSV files for graph construction.

The Java extractor lives under `tools/soot_extractor/`. It validates the compiled class directory, limits discovery to configured application package prefixes, creates the output directory, and writes normalized Stage 1 CSV files.

The current implementation uses Soot class metadata and Jimple method bodies to extract class nodes, structural type dependencies, and call dependencies. It also converts selected method bodies to Shimple form and extracts scoped SSA-derived flow evidence for return_value flow and argument_passing flow. It does not run graph construction or Leiden clustering.

Structural evidence kinds are normalized as:

- `extends_type_reference`
- `implements_type_reference`
- `field_type_reference`
- `method_parameter_type_reference`
- `method_return_type_reference`
- `method_call`

## Inputs

- `--subject`: subject identifier.
- `--classes-dir`: compiled application classes directory.
- `--classpath`: classpath used by Soot analysis.
- `--app-packages`: comma-separated application package prefixes to include.
- `--out-dir`: output directory for normalized CSV files.

Only compiled classes under the configured application packages are considered in scope.

## Outputs

The extractor creates:

- `class_nodes.csv`
- `structural_dependencies.csv`
- `ssa_flow_edges.csv`

All three files contain extracted data when evidence is present. `ssa_flow_edges.csv` is limited to:

- `return_value_flow`
- `argument_passing_flow`

Phi-related flow is not emitted as graph evidence.

## Subject Wrappers

The current repository provides thin extraction wrappers for the active Stage 1 subjects:

```bash
bash scripts/extract_soot_jpetstore.sh
bash scripts/extract_soot_daytrader.sh
bash scripts/extract_soot_xerces_j.sh
```

These wrappers keep subject-specific source paths, compiled class directories, classpaths, package filters, and output directories out of the Java extractor itself.

## JPetStore Example

```bash
JAVA_HOME=$(/usr/libexec/java_home -v 17) mvn -f tools/soot_extractor/pom.xml test
bash scripts/extract_soot_jpetstore.sh
```

The JPetStore wrapper expects classes under:

```text
data/raw_projects/jpetstore/target/classes
```

## Xerces-J Note

Xerces-J is the larger technical remodularization benchmark in Stage 1. Its extraction may require scoped preparation because the project includes tools, samples, tests, and external-looking packages that are not part of the intended application graph.

The current Xerces-J wrapper uses the existing preparation and extraction scripts, with package scope centered on the Xerces/XML implementation packages recorded in the subject config and extraction notes. The goal is to extract normalized class-level evidence for `G_raw` and `G_ssa`, not to include every auxiliary source file in the upstream project.
