"""Pinned Nomic inference primitives shared by the final Stage 3 wrapper."""

from __future__ import annotations

import gc
import hashlib
import platform
import time
from typing import Any

import numpy as np
import torch

EXPECTED_MODEL = "nomic-ai/nomic-embed-code"
MODEL_REVISION = "9a0457648f060c4279d4a3982d2d27a4df6fac59"
EXPECTED_DIMENSION = 3584
MAX_SEQUENCE_LENGTH = 32768
SEED = 42


def vector_hash(vector: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(vector, dtype="<f4").tobytes()).hexdigest()


def dtype_name(dtype: torch.dtype) -> str:
    return str(dtype).removeprefix("torch.")


def dtype_from_name(name: str) -> torch.dtype:
    values = {"float16": torch.float16, "float32": torch.float32, "bfloat16": torch.bfloat16}
    if name not in values:
        raise ValueError(f"unsupported frozen dtype: {name}")
    return values[name]


def dtype_candidates(device: str) -> list[torch.dtype]:
    if device == "mps":
        return [torch.float16, torch.float32]
    if device == "cuda":
        candidates: list[torch.dtype] = []
        if torch.cuda.is_bf16_supported():
            candidates.append(torch.bfloat16)
        return candidates + [torch.float16, torch.float32]
    return [torch.float32]


def load_model(device: str, dtype: torch.dtype):
    from sentence_transformers import SentenceTransformer

    started = time.perf_counter()
    model = SentenceTransformer(
        EXPECTED_MODEL,
        revision=MODEL_REVISION,
        device=device,
        trust_remote_code=False,
        model_kwargs={"torch_dtype": dtype},
        config_kwargs={"revision": MODEL_REVISION},
    )
    model.eval()
    if int(model.max_seq_length) != MAX_SEQUENCE_LENGTH:
        raise RuntimeError(f"loaded model max_seq_length={model.max_seq_length}, expected {MAX_SEQUENCE_LENGTH}")
    return model, time.perf_counter() - started


def clear_model(model: Any) -> None:
    del model
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def encode_texts(model: Any, texts: list[str], batch_size: int) -> np.ndarray:
    encoded = model.encode(
        texts,
        batch_size=batch_size,
        prompt_name=None,
        prompt=None,
        output_value="sentence_embedding",
        precision="float32",
        convert_to_numpy=True,
        convert_to_tensor=False,
        normalize_embeddings=False,
        show_progress_bar=False,
    )
    array = np.asarray(encoded, dtype="<f4")
    if array.ndim != 2 or array.shape[1] != EXPECTED_DIMENSION:
        raise ValueError(f"unexpected embedding shape {array.shape}")
    return np.ascontiguousarray(array, dtype="<f4")


def validate_vectors(array: np.ndarray) -> dict[str, Any]:
    values = np.asarray(array)
    if values.ndim != 2 or values.shape[1] != EXPECTED_DIMENSION:
        raise ValueError(f"unexpected vector shape {values.shape}")
    nan_count = int(np.isnan(values).sum())
    inf_count = int(np.isinf(values).sum())
    norms = np.linalg.norm(values.astype(np.float64), axis=1)
    zero_count = int(np.all(values == 0, axis=1).sum())
    if nan_count or inf_count or zero_count:
        raise ValueError(f"invalid vectors: nan={nan_count}, inf={inf_count}, zero={zero_count}")
    if np.any((norms < 0.999) | (norms > 1.001)):
        raise ValueError(f"vector norm outside [0.999, 1.001]: min={norms.min()}, max={norms.max()}")
    return {
        "minimum_norm": float(norms.min()),
        "mean_norm": float(norms.mean()),
        "maximum_norm": float(norms.max()),
        "nan_count": nan_count,
        "inf_count": inf_count,
        "all_zero_vector_count": zero_count,
    }


def select_device() -> tuple[str, list[str], str]:
    available: list[str] = []
    if torch.backends.mps.is_available():
        available.append("mps")
    if torch.cuda.is_available():
        available.append("cuda")
    available.append("cpu")
    device = available[0]
    if device == "mps":
        name = f"Apple Silicon MPS ({platform.machine()})"
    elif device == "cuda":
        name = torch.cuda.get_device_name(0)
    else:
        name = platform.processor() or platform.machine()
    return device, available, name
