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
        from scripts.stage3_method_body.prepare_inputs import main as operation
    elif args.operation == "embeddings":
        from scripts.stage3_method_body.generate_embeddings import main as operation
    elif args.operation == "graph":
        from scripts.stage3_method_body.build_semantic_graphs import main as operation
    elif args.operation == "validate":
        from scripts.stage3_method_body.validate_seed00_optimizer import main as operation
    elif args.operation == "formal":
        from scripts.stage3_method_body.run_formal_stage3b import main as operation
    else:
        from scripts.stage3_method_body.analyze_formal_stage3b import main as operation
    return int(operation(remainder) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
