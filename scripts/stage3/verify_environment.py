#!/usr/bin/env python3
"""Verify the pinned Python environment and tokenizer contract."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata as metadata
import json
import re
import sys
from pathlib import Path

import yaml


IMPORT_NAMES = {
    "numpy": "numpy",
    "pandas": "pandas",
    "networkx": "networkx",
    "igraph": "igraph",
    "leidenalg": "leidenalg",
    "pymoo": "pymoo",
    "scipy": "scipy",
    "matplotlib": "matplotlib",
    "PyYAML": "yaml",
    "transformers": "transformers",
    "torch": "torch",
    "sentence-transformers": "sentence_transformers",
    "pytest": "pytest",
}
PIN_PATTERN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s]+)$")
FORBIDDEN_LOCK_PATTERNS = (
    re.compile(r"^-e\s"),
    re.compile(r"@\s*file:"),
    re.compile(r"/Users/"),
    re.compile(r"git\+[^\s]+@(main|master|develop|dev)(?:#|$)", re.IGNORECASE),
)


def read_pins(path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = PIN_PATTERN.fullmatch(line)
        if not match:
            raise ValueError(f"requirements line is not an exact pin: {raw_line!r}")
        pins[match.group(1)] = match.group(2)
    return pins


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--requirements",
        type=Path,
        default=Path("requirements.txt"),
    )
    parser.add_argument(
        "--model",
        default="nomic-ai/nomic-embed-code",
    )
    parser.add_argument(
        "--revision",
        default="9a0457648f060c4279d4a3982d2d27a4df6fac59",
    )
    parser.add_argument("--max-sequence-length", type=int, default=32768)
    parser.add_argument("--config", type=Path, default=Path("configs/experiments/04_stage3_semantic.yml"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/stage3/formal_run_manifest.json"))
    parser.add_argument("--lock", type=Path, default=Path("requirements-stage3-lock.txt"))
    args = parser.parse_args()

    pins = read_pins(args.requirements)
    missing_mappings = sorted(set(pins) - set(IMPORT_NAMES))
    if missing_mappings:
        raise SystemExit(f"no import mapping for pinned packages: {missing_mappings}")

    failed = False
    print("package\texpected\tactual\tstatus")
    for package_name, import_name in IMPORT_NAMES.items():
        expected = pins.get(package_name)
        if expected is None:
            print(f"{package_name}\tMISSING_PIN\t-\tFAIL")
            failed = True
            continue
        try:
            importlib.import_module(import_name)
            actual = metadata.version(package_name)
            status = "PASS" if actual == expected else "FAIL"
        except (ImportError, metadata.PackageNotFoundError) as exc:
            actual = f"ERROR:{exc}"
            status = "FAIL"
        print(f"{package_name}\t{expected}\t{actual}\t{status}")
        failed |= status != "PASS"

    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401
        print("formal_loader\tSentenceTransformer\timported\tPASS")
    except ImportError as exc:
        print(f"formal_loader\tSentenceTransformer\tERROR:{exc}\tFAIL")
        failed = True

    from transformers import AutoTokenizer

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            args.model,
            revision=args.revision,
            use_fast=True,
            trust_remote_code=False,
        )
        actual_max_length = int(tokenizer.model_max_length)
        tokenizer_status = "PASS" if actual_max_length == args.max_sequence_length else "FAIL"
        print(
            "tokenizer\t"
            f"revision={args.revision};max_length={args.max_sequence_length}\t"
            f"model_max_length={actual_max_length}\t{tokenizer_status}"
        )
        failed |= tokenizer_status != "PASS"
    except Exception as exc:  # pragma: no cover - diagnostic failure path
        print(f"tokenizer\t{args.revision}\tERROR:{exc}\tFAIL")
        failed = True

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    runtime = config.get("embedding_runtime", {})
    runtime_checks = {
        "backend": "sentence_transformers",
        "loader": "SentenceTransformer",
        "formal_custom_pooling_implementation": False,
        "pooling": "last_token",
        "l2_normalize": True,
        "output_dimension": 3584,
        "query_prompt_used": False,
        "formal_truncation": False,
        "max_sequence_length": 32768,
        "input_column": "semantic_text",
    }
    for key, expected in runtime_checks.items():
        actual = runtime.get(key)
        status = "PASS" if actual == expected else "FAIL"
        print(f"config.{key}\t{expected}\t{actual}\t{status}")
        failed |= status != "PASS"

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    manifest_runtime = manifest.get("embedding_runtime", {})
    manifest_checks = {
        "backend": "sentence_transformers",
        "loader": "SentenceTransformer",
        "custom_pooling": False,
        "pooling": "last_token",
        "l2_normalize": True,
        "output_dimension": 3584,
        "query_prompt_used": False,
        "formal_truncation": False,
        "max_sequence_length": 32768,
        "input_column": "semantic_text",
        "device": None,
        "dtype": None,
        "batch_size": None,
        "runtime_frozen": False,
    }
    for key, expected in manifest_checks.items():
        actual = manifest_runtime.get(key)
        status = "PASS" if actual == expected else "FAIL"
        print(f"manifest.embedding_runtime.{key}\t{expected}\t{actual}\t{status}")
        failed |= status != "PASS"

    lock_status = "PASS"
    if not args.lock.is_file():
        print(f"lock_file\t{args.lock}\tMISSING\tFAIL")
        failed = True
    else:
        lock_text = args.lock.read_text(encoding="utf-8")
        offending = [
            line for line in lock_text.splitlines()
            if any(pattern.search(line) for pattern in FORBIDDEN_LOCK_PATTERNS)
        ]
        if offending:
            lock_status = "FAIL"
            failed = True
            print(f"lock_forbidden_entries\t0\t{offending}\tFAIL")
        else:
            print("lock_forbidden_entries\t0\t0\tPASS")
        actual_sha = hashlib.sha256(lock_text.encode("utf-8")).hexdigest()
        recorded_sha = manifest.get("stage3_lock", {}).get("sha256")
        sha_status = "PASS" if recorded_sha == actual_sha else "FAIL"
        print(f"lock_sha256\t{recorded_sha}\t{actual_sha}\t{sha_status}")
        failed |= sha_status != "PASS"

    if failed:
        return 1
    print("No full model weights were loaded; no embeddings were generated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
