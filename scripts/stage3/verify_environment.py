#!/usr/bin/env python3
"""Verify the pinned Python environment and tokenizer contract."""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata as metadata
import re
import sys
from pathlib import Path


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
    "pytest": "pytest",
}
PIN_PATTERN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s]+)$")


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

    if failed:
        return 1
    print("No full model weights were loaded; no embeddings were generated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
