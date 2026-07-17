# Stage 3 Reproducibility Environment

## 1. Purpose

This checkpoint records the pinned environment used for Stage 3 artifacts and
diagnostics. It does not claim cross-device bit-exact floating-point
reproduction.

## 2. Repository state

| Item | Value |
| --- | --- |
| Branch | `stage3-semantic` |
| Starting commit | `b05e094476783e3451feafa2e8899b6dfcd5eeea` |
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
`sentence-transformers==5.6.0` for the planned Day 3 Nomic embedding runtime;
the existing `torch==2.13.0` pin is unchanged.

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
sentence-transformers==5.6.0
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

The exact installable Stage 3 environment is
[`requirements-stage3-lock.txt`](../../requirements-stage3-lock.txt). It
contains 70 deterministically sorted packages and has SHA-256:

```text
f390c0dcef98c921f7367733b8169ea7664c03f1f5fafff6e99345512abb2a8f
```

The lock contains no editable installs, local paths, or mutable Git references.
Resolver dry-run validation passed. A full clean installation was not
performed because it would require downloading the large Torch wheel again;
the current repo-local environment was fully installed and passed `pip check`.

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
`model_max_length=32768`. The full Nomic model was loaded for the Day 3 smoke
test; formal subject embeddings have not yet been generated.

## Formal Nomic runtime

The pinned repository is packaged for Sentence Transformers. Formal embedding
generation will use `SentenceTransformer` from `sentence_transformers`, with
the model-packaged Qwen2Model, last-token pooling, and normalization. No custom
pooling implementation or query prompt is used. The input is the
`semantic_text` column, formal truncation is disabled, expected output
dimension is 3584, and cosine similarity is used.

The Day 3 full-model smoke test froze the inference runtime as MPS,
`float16`, and batch size 8. The selected model device is Apple Silicon MPS.
Embeddings are stored as `float32`; the runtime uses evaluation mode,
`torch.inference_mode()`, and a fixed random seed of 42. The full smoke-test
record is in [`nomic_runtime_smoke_test.md`](nomic_runtime_smoke_test.md).

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

The clean resolver check was executed in a temporary environment with:

```bash
python3 -m venv /tmp/stage3-lock-verify-20260716
source /tmp/stage3-lock-verify-20260716/bin/activate
python -m pip install --upgrade pip
python -m pip install --dry-run -r requirements-stage3-lock.txt
```

The dry-run passed. The temporary environment was not used to load model
weights or generate embeddings.

Validation results for this checkpoint were:

- `python3 -m pip check`: passed with no broken requirements.
- `scripts/stage3/verify_environment.py`: passed all dependency, tokenizer,
  runtime-path, and lock-integrity checks.
- Java 17 Maven extractor tests: passed.
- Focused Stage 3 Python tests: 6 passed.
- Full Python suite: 130 passed and 1 failed only because the unchanged legacy
  scaffold test rejects the required `docs/stage3` directory.

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

Bit-exact embedding reproduction was demonstrated only under the pinned
current environment: macOS, Apple Silicon MPS, a float16 runtime, batch size
8, and the exact locked library versions. Bit-exact equality across CPU,
CUDA, other hardware, or other library versions is not claimed. Model, input,
embedding, and graph hashes detect environment or artifact drift. Algorithmic
rules remain reproducible across platforms, but final floating values may
differ in their least significant digits.

## 9. Current Stage 3 status

Completed:

- Method contract frozen.
- Exact Nomic model and tokenizer revisions pinned.
- Official SentenceTransformer runtime path and exact Stage 3 lock recorded.
- Full-model smoke test passed; MPS/float16/batch-8 inference runtime frozen.
- Deterministic declaration extractor implemented.
- All three subject inputs generated.
- Scope and double-run determinism validated.
- No class required truncation.
- Input hashes stored in the manifest.

Not yet completed:

- Semantic objective integration.
- Stage 3 formal multi-seed runs.

## 10. Known legacy test conflict

The existing scaffold test rejects `docs/stage3`, even though Stage 3 now
requires that directory. The test remains unchanged and its failure is
reported as a legacy scaffold conflict, not a dependency-lock failure.
