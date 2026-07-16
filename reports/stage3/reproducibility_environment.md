# Stage 3 Reproducibility Environment

## 1. Purpose

This checkpoint freezes the software environment before Nomic embedding
generation and Stage 3 formal execution. It records the canonical Python
installation contract, the active workstation environment, and the Java
toolchain used by the Soot declaration extractor.

## 2. Repository state

| Item | Value |
| --- | --- |
| Branch | `stage3-semantic` |
| Commit before this checkpoint | `1724498b79dcd39980caf52b39512dcd4c3373ab` |
| Working tree before this checkpoint | clean |
| Operating system | macOS 26.5 |
| Architecture | Apple Silicon, `arm64` |
| Kernel evidence | `Darwin ... 25.5.0 ... RELEASE_ARM64_T6050 arm64` |

No experimental logic, model setting, extraction behaviour, output data,
objective definition, graph parameter, seed, or frozen contract value is
changed by this checkpoint.

## 3. Python environment

The repository has one canonical Python dependency file:

```text
requirements.txt
```

No `pyproject.toml`, `setup.py`, `setup.cfg`, Pipfile, Poetry lock, uv lock,
Conda environment file, Maven wrapper, or CI dependency-installation file is
present. The existing dependency-management approach is therefore preserved.

The active workstation `python3` reports:

| Item | Value |
| --- | --- |
| Python | `3.13.7` |
| pip | `26.0.1` |
| `python3 -m pip check` | `No broken requirements found.` |

The active workstation interpreter does not contain the project's direct
Python packages; its `pip freeze` is a Codex-tooling environment snapshot,
not an install of this repository. It is preserved in
[`python_environment_freeze.txt`](python_environment_freeze.txt). The clean
pin-install validation environment described below contains every canonical
dependency.

The exact pinned direct dependencies are:

```text
pandas==2.2.3
numpy==2.4.4
networkx==3.6.1
igraph==1.0.0
leidenalg==0.12.0
pymoo==0.6.2
scipy==1.16.3
matplotlib==3.10.8
PyYAML==6.0.3
pytest==9.1.1
```

`numpy==2.4.4` and `pymoo==0.6.2` preserve the versions recorded in the
formal Stage 2 manifests. The remaining direct pins are verified by a clean
Python 3.13 installation from `requirements.txt`. SciPy is directly imported
by the Stage 2 robustness analysis; Matplotlib is directly imported by the
Stage 2 convergence diagnostic. Torch, Transformers, Sentence Transformers,
Hugging Face Hub, and Safetensors are not added because Nomic execution code
has not yet been implemented in the repository.

## 4. Java extraction environment

The default workstation Java is Homebrew OpenJDK `25.0.1`, and the default
Maven invocation reports Java 25. The extractor is validated with Homebrew
OpenJDK `17.0.19`, matching the Maven compiler and Surefire toolchain settings
in `tools/soot_extractor/pom.xml`:

| Item | Value |
| --- | --- |
| Validated Java runtime | OpenJDK `17.0.19`, Homebrew |
| Validated Java compiler | `javac 17.0.19` |
| Maven | Apache Maven `3.9.11` |
| Maven home | `/opt/homebrew/Cellar/maven/3.9.11/libexec` |
| Maven Java home used for validation | `/opt/homebrew/Cellar/openjdk@17/17.0.19/libexec/openjdk.jdk/Contents/Home` |
| Soot | `org.soot-oss:soot:4.5.0` |
| JUnit | `org.junit.jupiter:junit-jupiter:5.11.4` |
| Maven compiler plugin | `3.13.0`, release/toolchain 17 |
| Maven Surefire plugin | `3.5.2`, toolchain 17 |
| Maven exec plugin | `3.5.0` |
| Maven wrapper | None |

The extractor is not validated on Java 25. Soot's ASM path previously rejected
Java 25 class-file major version 69, so Java 17 is the required extraction
runtime for this repository.

## 5. Nomic model contract

The frozen Stage 3 configuration and manifest agree on:

| Item | Frozen value |
| --- | --- |
| Model | `nomic-ai/nomic-embed-code` |
| Revision | `9a0457648f060c4279d4a3982d2d27a4df6fac59` |
| Pooling | `last_token` |
| L2 normalization | `true` |

Day 1 contains no Nomic embedding-generation implementation or formal model
run. There is no repository evidence that model weights were generated or
cached during Day 1.

## 6. Reproduction commands

The following commands were run successfully for the pinned Python
environment:

```bash
python3 -m venv /tmp/stage3-repro-from-requirements-20260716
/tmp/stage3-repro-from-requirements-20260716/bin/python -m pip install --quiet --upgrade pip
/tmp/stage3-repro-from-requirements-20260716/bin/python -m pip install --quiet -r requirements.txt
/tmp/stage3-repro-from-requirements-20260716/bin/python -m pip check
```

Import/version verification was run with:

```bash
/tmp/stage3-repro-from-requirements-20260716/bin/python - <<'PY'
import importlib.metadata as md
packages = ['numpy', 'pandas', 'networkx', 'igraph', 'leidenalg', 'pymoo',
            'scipy', 'matplotlib', 'PyYAML', 'pytest']
for name in packages:
    print(f'{name}=={md.version(name)}')
PY
```

The printed versions matched every exact requirement pin, and `pip check`
reported no broken requirements.

Java extractor tests use Java 17:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
export PATH="$JAVA_HOME/bin:$PATH"
mvn -q -f tools/soot_extractor/pom.xml test
```

Focused Stage 3 Python tests:

```bash
PYTHONPATH=src /tmp/stage3-repro-from-requirements-20260716/bin/python -m pytest \
  tests/test_subject_extraction_config.py \
  tests/test_stage3_class_declaration_input.py -q
```

Existing full Python suite:

```bash
PYTHONPATH=src /tmp/stage3-repro-from-requirements-20260716/bin/python -m pytest -q
```

## 7. Platform notes

This checkpoint was captured on Apple Silicon (`arm64`). No CUDA execution was
used. No MPS, CUDA, or CPU embedding run has been performed, so cross-hardware
bitwise equality is not claimed. The verified deterministic property is the
construction of the class-declaration input, including its exact bytes and
hashes.

Java 17 is required for the validated Soot extractor path. The default Java 25
installation should not be used for extraction until compatibility is
explicitly verified.

## 8. Current Stage 3 status

- Method contract frozen.
- Exact Nomic revision pinned.
- Deterministic declaration extractor implemented.
- JPetStore declaration input generated.
- Exact 24-class Stage 2 scope validated.
- Deterministic double-run completed; current CSV hash is
  `b9bcafa575b44b13984b043d4244351bc71c2bfcc9744fceeb49260bfbfc765b`.
- Java extractor tests: 6 passed.
- Focused Stage 3 Python tests: 6 passed.
- Full Python suite: 130 passed, 1 failed because the legacy
  `test_no_stage3_or_semantics_scaffold` still rejects the now-required
  `docs/stage3` directory. That test was not weakened or deleted; this is a
  legacy test-contract conflict, not a Stage 3 implementation failure.
- `ssa_flow_edges.csv` is only a shared-extractor by-product and is not a
  semantic input.
- DayTrader declarations, Xerces declarations, Nomic embeddings, the semantic
  graph, fourth-objective integration, and formal Stage 3 runs are not yet
  complete.
