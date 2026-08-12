from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from evo_ms.visualization import layout
from evo_ms.visualization.model import GraphvizRenderRequest


MINIMAL_DOT = 'graph "G" { "a" -- "b"; }\n'
FIXED_DOT = 'graph "G" { "a" [pos="0,0!", pin=true]; "b" [pos="72,0!", pin=true]; "a" -- "b"; }\n'


@pytest.mark.parametrize("engine", ["dot", "neato", "sfdp"])
def test_graphviz_executables_are_discovered(engine: str) -> None:
    assert layout.find_graphviz(engine).is_file()
    assert "graphviz version" in layout.graphviz_version(engine)


def test_minimal_dot_renders_to_svg(tmp_path: Path) -> None:
    source = tmp_path / "graph.dot"
    source.write_text(MINIMAL_DOT, encoding="utf-8")
    output = tmp_path / "graph.svg"
    result = layout.render_graphviz(GraphvizRenderRequest(source, output, "svg", "dot"))
    assert output.read_text(encoding="utf-8").lstrip().startswith("<?xml")
    assert result.output_path == output.resolve()


def test_fixed_coordinates_render_with_neato_n2(tmp_path: Path) -> None:
    source = tmp_path / "fixed.dot"
    source.write_text(FIXED_DOT, encoding="utf-8")
    output = tmp_path / "fixed.svg"
    result = layout.render_graphviz(GraphvizRenderRequest(source, output, "svg", "neato", True))
    assert "-n2" in result.command
    assert output.stat().st_size > 0


def test_pdf_rendering_succeeds(tmp_path: Path) -> None:
    source = tmp_path / "graph.dot"
    source.write_text(MINIMAL_DOT, encoding="utf-8")
    output = tmp_path / "graph.pdf"
    layout.render_graphviz(GraphvizRenderRequest(source, output, "pdf", "dot"))
    assert output.read_bytes().startswith(b"%PDF")


def test_render_error_identifies_engine_and_command(tmp_path: Path) -> None:
    source = tmp_path / "invalid.dot"
    source.write_text("not valid DOT\n", encoding="utf-8")
    with pytest.raises(layout.GraphvizError, match=r"engine dot: .*dot.*-Tsvg"):
        layout.render_graphviz(GraphvizRenderRequest(source, tmp_path / "bad.svg", "svg", "dot"))


def test_subprocess_commands_are_argument_lists_without_shell_interpolation(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "graph.dot"
    source.write_text(MINIMAL_DOT, encoding="utf-8")
    calls: list[tuple[list[str], dict]] = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if "-V" in command:
            return subprocess.CompletedProcess(command, 0, "", "neato - graphviz version test")
        Path(command[-1]).write_text("synthetic svg", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(layout, "find_graphviz", lambda engine: Path("/usr/bin/neato"))
    monkeypatch.setattr(layout.subprocess, "run", fake_run)
    layout.render_graphviz(
        GraphvizRenderRequest(source, tmp_path / "out.svg", "svg", "neato", True)
    )
    assert calls
    assert all(isinstance(command, list) for command, _kwargs in calls)
    assert all("shell" not in kwargs for _command, kwargs in calls)


def test_render_never_overwrites_input(tmp_path: Path) -> None:
    source = tmp_path / "graph.dot"
    source.write_text(MINIMAL_DOT, encoding="utf-8")
    with pytest.raises(layout.GraphvizError, match="must not overwrite"):
        layout.render_graphviz(GraphvizRenderRequest(source, source, "svg", "dot"))
