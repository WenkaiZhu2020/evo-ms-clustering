"""Safe Graphviz executable discovery and rendering."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from .model import GraphvizRenderRequest, GraphvizRenderResult


class GraphvizError(RuntimeError):
    """Raised when a Graphviz executable cannot be located or run."""


def find_graphviz(engine: str) -> Path:
    if engine not in {"dot", "neato", "sfdp"}:
        raise GraphvizError(f"unsupported Graphviz engine: {engine}")
    executable = shutil.which(engine)
    if executable is None:
        raise GraphvizError(f"Graphviz engine is not available on PATH: {engine}")
    # Preserve the requested executable name rather than resolving Graphviz's
    # engine symlinks to the shared `dot` binary.
    return Path(executable).absolute()


def graphviz_version(engine: str) -> str:
    executable = find_graphviz(engine)
    command = [str(executable), "-V"]
    environment = {**os.environ, "SOURCE_DATE_EPOCH": "0"}
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    output = (completed.stderr or completed.stdout).strip()
    if completed.returncode != 0:
        raise GraphvizError(f"Graphviz version query failed for {engine}: {' '.join(command)}: {output}")
    return output


def render_graphviz(request: GraphvizRenderRequest) -> GraphvizRenderResult:
    dot_path = request.dot_path.resolve()
    output_path = request.output_path.resolve()
    if dot_path == output_path:
        raise GraphvizError("Graphviz output must not overwrite its DOT input")
    if not dot_path.is_file():
        raise GraphvizError(f"Graphviz input does not exist: {dot_path}")

    executable = find_graphviz(request.engine)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    command = [str(executable)]
    if request.fixed_coordinates:
        command.append("-n2")
    command.extend([f"-T{request.output_format}", str(dot_path), "-o", str(temporary_path)])
    environment = {**os.environ, "SOURCE_DATE_EPOCH": "0"}
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    if completed.returncode != 0:
        temporary_path.unlink(missing_ok=True)
        detail = (completed.stderr or completed.stdout).strip()
        raise GraphvizError(
            f"Graphviz render failed for engine {request.engine}: {' '.join(command)}: {detail}"
        )
    if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
        temporary_path.unlink(missing_ok=True)
        raise GraphvizError(f"Graphviz engine {request.engine} produced no output: {' '.join(command)}")
    os.replace(temporary_path, output_path)

    display_command = [request.engine]
    if request.fixed_coordinates:
        display_command.append("-n2")
    display_command.extend(
        [f"-T{request.output_format}", str(dot_path), "-o", str(output_path)]
    )
    return GraphvizRenderResult(
        output_path=output_path,
        engine=request.engine,
        version=graphviz_version(request.engine),
        command=tuple(display_command),
    )
