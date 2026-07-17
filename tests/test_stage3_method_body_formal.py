"""Focused tests for the Stage 3B formal seed runner boundary."""

from __future__ import annotations

import pytest

from scripts.stage3_method_body.run_formal_stage3b import (
    FORMAL_SEEDS,
    formal_output_dir,
    parse_seeds,
)


def test_formal_seed_parser_excludes_authoritative_seed_zero() -> None:
    assert parse_seeds("1-3,7,29") == [1, 2, 3, 7, 29]
    assert parse_seeds(None) == list(range(1, 30))
    with pytest.raises(ValueError, match="only seeds 1..29"):
        parse_seeds("0,1")
    with pytest.raises(ValueError, match="only seeds 1..29"):
        parse_seeds("30")


def test_formal_paths_are_isolated_and_seed_zero_is_not_formal() -> None:
    path = formal_output_dir("jpetstore", 1)
    assert path.name == "seed_01"
    assert path.parent.name == "formal"
    assert "05_stage3_declaration_method_body" in str(path)
    assert "04_stage3_semantic" not in str(path)
    with pytest.raises(ValueError, match="1..29 only"):
        formal_output_dir("jpetstore", 0)


def test_formal_seed_set_is_exactly_one_through_twenty_nine() -> None:
    assert FORMAL_SEEDS == tuple(range(1, 30))
