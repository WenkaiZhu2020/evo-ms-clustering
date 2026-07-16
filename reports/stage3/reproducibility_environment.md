# Stage 3 Reproducibility Environment

## 1. Purpose

This checkpoint freezes the software environment after deterministic Stage 3
input generation and before Nomic embedding generation. It does not generate
model embeddings, semantic graphs, or Stage 3 optimisation results.

## 2. Repository state

| Item | Value |
| --- | --- |
| Branch | `stage3-semantic` |
| Starting commit | `db14a04a679c6ec03f54415b6291bb12eae0fa79` |
| Working tree before checkpoint | clean |
| Operating system | macOS 26.5 |
| Architecture | Apple Silicon `arm64` |

The four Day 2 commits were present before this checkpoint. The Day 2 CSV
files, aggregate hashes, method parameters, and experimental settings are
preserved.

## 3. Python dependency contract

The canonical Python installation contract is
[`requirements.txt`](../../requirements.txt). No `pyproject.toml`, setup file,
Pipfile, Poetry lock, uv lock, Conda file, Maven wrapper, or CI dependency
installation file is used by this repository. The existing requirements-file
approach is preserved.

Before this checkpoint, the canonical file already contained exact pins for
all listed runtime, analysis, tokenizer, and test packages. The only
requirements change in this checkpoint is the addition of
`torch==2.13.0` for the planned Day 3 Nomic embedding runtime.

The active validated environment is:

| Item | Value |
| --- | --- |
| Python | `3.13.7` |
| Python executable | `/Users/zhuwenkai/Desktop/evo-ms-clustering-stage2-formal/.venv/bin/python3` |
| pip | `26.1.2` |
| Virtual environment | `/Users/zhuwenkai/Desktop/evo-ms-clustering-stage2-formal/.venv` |
| `pip check` | passed: no broken requirements |

Exact direct pins:

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
transformers==5.14.1
torch==2.13.0
pytest==9.1.1
```

The canonical requirements file contains required direct dependencies for the
existing Stage 1/Stage 2 code, the frozen Stage 3 tokenizer pipeline, and
tests. The complete active environment snapshot, including transitive
packages, is stored in
[`python_environment_freeze.txt`](python_environment_freeze.txt). It is an
audit and reconstruction record, not a replacement for the minimal contract.

The global `python3` initially had no project dependencies. The explicit
compatible pins were installed into the ignored repo-local `.venv`; all direct
imports and versions were then verified there.

`tokenizers==0.22.2`, `huggingface-hub==1.23.0`, and
`safetensors==0.8.0` are installed transitively for Transformers and are
recorded in the full freeze snapshot; they are not direct repository imports.

## 4. Java and Soot extraction environment

The validated extractor toolchain uses Java 17:

| Item | Value |
| --- | --- |
| Java runtime vendor | Homebrew OpenJDK |
| Java runtime | `17.0.19` |
| Java compiler | `javac 17.0.19` |
| Maven | Apache Maven `3.9.11` |
| Maven Java home | `/opt/homebrew/Cellar/openjdk@17/17.0.19/libexec/openjdk.jdk/Contents/Home` |
| Maven wrapper | absent and not used |
| Soot | `org.soot-oss:soot:4.5.0` |
| JUnit | `org.junit.jupiter:junit-jupiter:5.11.4` |
| Maven compiler plugin | `3.13.0`, release/toolchain 17 |
| Maven Surefire plugin | `3.5.2`, toolchain 17 |
| Maven exec plugin | `3.5.0` |

The default workstation JDK is OpenJDK 25.0.1, but the extractor is validated
with Java 17 because the Maven configuration requires release 17 and Soot's
ASM path is not the validated path on Java 25.

## 5. Frozen Nomic contract

| Item | Frozen value |
| --- | --- |
| Model | `nomic-ai/nomic-embed-code` |
| Model revision | `9a0457648f060c4279d4a3982d2d27a4df6fac59` |
| Tokenizer revision | `9a0457648f060c4279d4a3982d2d27a4df6fac59` |
| Pooling | `last_token` |
| L2 normalization | `true` |
| Maximum sequence length | `32768` |
| Query prompt | not used |

The exact tokenizer loaded successfully from the pinned revision and reported
`model_max_length=32768`. Full Nomic model weights were not loaded, and no
embeddings were generated.

## 6. Verified Day 2 inputs

| Subject | Classes | Maximum tokens | Truncation |
| --- | ---: | ---: | --- |
| JPetStore | 24 | 386 | none |
| DayTrader | 53 | 678 | none |
| Xerces | 814 | 1501 | none |

Both extraction runs per subject produced identical `semantic_text` and
`input_hash` values. The Day 2 aggregate hashes remain:

```text
jpetstore = 1ecdb9083a37668fd07388454095a317268c8b736e6fd45957ab16bf87f6ad23
daytrader = ab09380f87119e4fe4621efbbdd8fdfd8cfc92cd383ed812169e2427a35eae44
xerces    = f81d0f9bda5aa0fcdf3a35c75876cc73c8b419eccfb8c9e00634ec13fad4d60a
```

This version-lock task must not alter any Day 2 CSV or aggregate hash.

## 7. Reproduction commands

The following commands were executed and validated:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt
source .venv/bin/activate
python3 -m pip check
python3 scripts/stage3/verify_environment.py
```

The exact tokenizer verification is included in
[`verify_environment.py`](../../scripts/stage3/verify_environment.py). It
loads only `AutoTokenizer` from the pinned revision and does not load a model.

Java extractor tests:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
export PATH="$JAVA_HOME/bin:$PATH"
mvn -q -f tools/soot_extractor/pom.xml test
```

Focused Stage 3 Python tests:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/test_subject_extraction_config.py \
  tests/test_stage3_class_declaration_input.py -q
```

Full Python suite:

```bash
PYTHONPATH=src python3 -m pytest -q
```

## 8. Platform limitations

The validated platform is Apple Silicon `arm64`. PyTorch reports MPS built
and available; CUDA is unavailable. No MPS, CUDA, or CPU embedding run was
performed in this checkpoint. Input extraction and input hashing are
deterministic, but bitwise-identical floating-point embeddings across MPS,
CUDA, and CPU are not assumed. Day 3 must record the actual device, dtype,
batch size, and library versions in embedding metadata.

## 9. Current Stage 3 status

Completed:

- Method contract frozen.
- Exact Nomic model and tokenizer revisions pinned.
- Deterministic declaration extractor implemented.
- All three subject inputs generated.
- Scope and double-run determinism validated.
- No class required truncation.
- Input hashes stored in the manifest.

Not yet completed:

- Full Nomic model loading.
- Embedding generation.
- Nearest-neighbour checks.
- Semantic graph construction.
- Semantic objective integration.
- Stage 3 formal multi-seed runs.

## 10. Known legacy test conflict

The existing scaffold test rejects `docs/stage3`, even though Stage 3 now
requires that directory. The test remains unchanged and its failure is
reported as a legacy scaffold conflict, not a dependency-lock failure.
