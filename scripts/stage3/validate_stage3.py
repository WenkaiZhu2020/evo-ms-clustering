"""Thin validation CLI for the final Stage 3 experiment."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate final Stage 3 saved artifacts")
    parser.add_argument("--seed0", action="store_true", help="validate the controlled seed-0 output")
    parser.add_argument("--formal", action="store_true", help="validate saved formal seeds")
    args, remainder = parser.parse_known_args(argv)
    if not args.seed0 and not args.formal:
        parser.print_help()
        return 0
    if args.seed0:
        from scripts.stage3.final_validate_seed00 import main as operation
    else:
        from scripts.stage3.final_formal_stage3 import main as operation
    return int(operation(remainder) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
