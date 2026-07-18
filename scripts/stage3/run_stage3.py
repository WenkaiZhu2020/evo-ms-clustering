"""Thin CLI for the final Stage 3 experiment."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a selected final Stage 3 operation")
    parser.add_argument("operation", nargs="?", choices=("input", "embeddings", "graph", "validate", "formal", "analyze"))
    args, remainder = parser.parse_known_args(argv)
    if args.operation is None:
        parser.print_help()
        return 0
    if args.operation == "input":
        parser.error("input preparation is frozen; use the validated semantic-text manifest")
    elif args.operation == "embeddings":
        from scripts.stage3.final_generate_embeddings import main as operation
    elif args.operation == "graph":
        from scripts.stage3.final_build_semantic_graphs import main as operation
    elif args.operation == "validate":
        from scripts.stage3.final_validate_seed00 import main as operation
    elif args.operation == "formal":
        from scripts.stage3.final_formal_stage3 import main as operation
    else:
        from scripts.stage3.final_analyze import main as operation
    return int(operation(remainder) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
