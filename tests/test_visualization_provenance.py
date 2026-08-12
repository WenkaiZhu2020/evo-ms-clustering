from __future__ import annotations

import json
from pathlib import Path

from evo_ms.visualization.provenance import build_provenance, provenance_json, sha256_file, write_provenance


FIXED_TIME = "2026-08-06T12:00:00Z"


def _record(root: Path, *, dirty: bool = True):
    inputs = root / "inputs"
    configs = root / "configs"
    outputs = root / "outputs"
    inputs.mkdir(parents=True)
    configs.mkdir(parents=True)
    outputs.mkdir(parents=True)
    input_a = inputs / "a.csv"
    input_b = inputs / "b.csv"
    config = configs / "style.yml"
    dot = outputs / "figure.dot"
    svg = outputs / "figure.svg"
    input_a.write_text("a\n", encoding="utf-8")
    input_b.write_text("b\n", encoding="utf-8")
    config.write_text("schema_version: 1\n", encoding="utf-8")
    dot.write_text('graph "G" {}\n', encoding="utf-8")
    svg.write_text("<svg/>\n", encoding="utf-8")
    return build_provenance(
        figure_id="fixture",
        stage="synthetic",
        generator="scripts/visualization/build_figures.py",
        repository_root=root,
        input_files=(input_b, input_a),
        config_files=(config,),
        dot_path=dot,
        graphviz_engine="neato",
        graphviz_version="neato - graphviz version test",
        render_commands=(("/opt/homebrew/bin/neato", "-n2", "-Tsvg", str(dot), "-o", str(svg)),),
        generated_outputs=(svg, dot),
        generated_at=FIXED_TIME,
        git_commit="abc123",
        git_dirty=dirty,
    )


def test_paths_and_mappings_are_repository_relative_and_sorted(tmp_path: Path) -> None:
    record = _record(tmp_path)
    assert record.input_files == ("inputs/a.csv", "inputs/b.csv")
    assert tuple(path for path, _digest in record.input_sha256) == record.input_files
    assert record.generated_outputs == ("outputs/figure.dot", "outputs/figure.svg")
    assert record.render_command[0][0] == "neato"
    assert record.render_command[0][-1] == "outputs/figure.svg"


def test_hashes_are_stable_and_dirty_state_is_injected(tmp_path: Path) -> None:
    record = _record(tmp_path, dirty=True)
    assert record.git_dirty is True
    assert dict(record.input_sha256)["inputs/a.csv"] == sha256_file(tmp_path / "inputs/a.csv")
    assert record.dot_sha256 == sha256_file(tmp_path / "outputs/figure.dot")


def test_fixed_timestamp_produces_byte_identical_json(tmp_path: Path) -> None:
    first = _record(tmp_path / "one")
    second = _record(tmp_path / "two")
    assert provenance_json(first) == provenance_json(second)
    first_path = write_provenance(tmp_path / "first.json", first)
    second_path = write_provenance(tmp_path / "second.json", second)
    assert first_path.read_bytes() == second_path.read_bytes()


def test_provenance_contains_no_machine_specific_paths(tmp_path: Path) -> None:
    text = provenance_json(_record(tmp_path))
    assert "/Users/" not in text
    assert "/private/" not in text
    assert "/tmp/" not in text
    document = json.loads(text)
    assert document["generated_at"] == FIXED_TIME
    assert document["git_commit"] == "abc123"
