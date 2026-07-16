# Stage 3 Nomic Runtime Smoke Test

## Runtime decision

| Item | Result |
| --- | --- |
| Branch | `stage3-semantic` |
| Starting commit | `a8b03d0cdb59ef8dc227078e204dcefe9429cb21` |
| Platform | macOS 26.5, Apple Silicon `arm64` |
| Torch | `2.13.0` |
| Transformers | `5.14.1` |
| Sentence Transformers | `5.6.0` |
| Model | `nomic-ai/nomic-embed-code` |
| Revision | `9a0457648f060c4279d4a3982d2d27a4df6fac59` |
| Cache location | `/Users/zhuwenkai/.cache/huggingface` |
| Disk available before download | `783087247360` bytes |
| Disk available after download | `751476977664` bytes |
| Model-load duration | `796.3523469580105` seconds |
| Available devices | MPS, CPU; CUDA unavailable |
| Selected device | `mps` |
| Device name | Apple Silicon MPS (arm64) |
| Selected dtype | `float16` |
| Selected batch size | `8` |
| Storage dtype | `float32` |
| Output dimension | `3584` |

The model was loaded with the official `SentenceTransformer` path. The
packaged pooling and normalization modules were used. No query prompt and no
custom pooling implementation were used. The model was put in evaluation mode
and encoding used `torch.inference_mode()` through the formal runner.

## Predeclared probe

The first available device in the declared order was MPS. The first dtype
candidate, MPS `float16`, passed, so `float32` was not tested. Batch sizes 1,
2, 4, and 8 all passed the technical checks; batch size 8 was selected as the
largest passing candidate. No candidate configuration failed.

| Dtype | Batch size | Result | Maximum norm | Minimum norm |
| --- | ---: | --- | ---: | ---: |
| float16 | 1 | pass | 1.0001410 | 1.0001410 |
| float16 | 2 | pass | 1.0001409 | 0.9998524 |
| float16 | 4 | pass | 1.0002255 | 0.9998524 |
| float16 | 8 | pass | 1.0002255 | 0.9998524 |

All probe outputs had zero NaN, zero infinite values, and zero all-zero
vectors.

## Fixed smoke set

The smoke set contained 10 distinct inputs, selected deterministically from
the three longest inputs and the requested interface, zero-method,
annotated, and abstract categories. Its shape was `(10, 3584)`.

The first run had minimum, mean, and maximum vector norms of
`0.9997590`, `1.0000433`, and `1.0002255`. The repeated run had the same
statistics. Both runs had zero NaN, infinite, and all-zero vectors. Diagonal
cosine validation was approximately 1, and the embeddings were not all
identical.

| Check | Result |
| --- | --- |
| Exact repeated-run byte equality | pass; all 10 vectors equal |
| Maximum absolute element difference | `0.0` |
| Minimum corresponding-vector cosine | `0.9999999999999998` |
| Stability thresholds | pass |
| First smoke encoding | `9.850399415940046` seconds |
| Second smoke encoding | `9.864023166941479` seconds |

The probe metadata is also stored in
`reports/stage3/day3_runtime_probe.json`. This checkpoint freezes the runtime
only; formal embeddings are generated in the next commit unit.
