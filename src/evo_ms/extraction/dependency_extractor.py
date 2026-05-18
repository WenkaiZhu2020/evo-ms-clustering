from pathlib import Path
from typing import Any

import pandas as pd


CLASS_NODES_COLUMNS = ["class_id", "class_name", "package", "class_file_path"]
STRUCTURAL_DEPENDENCY_COLUMNS = [
    "source",
    "target",
    "dependency_type",
    "weight",
    "evidence_kind",
    "evidence_location",
]
SSA_FLOW_COLUMNS = [
    "source",
    "target",
    "flow_type",
    "weight",
    "evidence_method",
    "evidence_statement",
]

ALLOWED_DEPENDENCY_TYPES = frozenset({"type", "call"})
ALLOWED_SSA_FLOW_TYPES = frozenset({"return_value_flow", "argument_passing_flow"})


def load_class_nodes_csv(path: str | Path) -> pd.DataFrame:
    """Read `class_nodes.csv` and keep the schema order stable."""
    frame = _read_required_columns(path, CLASS_NODES_COLUMNS)
    frame["class_id"] = _as_text(frame["class_id"])
    _validate_no_missing(frame, ["class_id", "class_name"], path)
    return frame


def load_structural_dependencies_csv(
    path: str | Path,
    class_nodes: pd.DataFrame,
) -> pd.DataFrame:
    """Read structural edges after checking node ids and dependency types."""
    frame = _read_required_columns(path, STRUCTURAL_DEPENDENCY_COLUMNS)
    frame["source"] = _as_text(frame["source"])
    frame["target"] = _as_text(frame["target"])
    frame["dependency_type"] = _as_text(frame["dependency_type"])
    frame["weight"] = _numeric_non_negative(frame["weight"], path)
    _validate_allowed_values(frame, "dependency_type", ALLOWED_DEPENDENCY_TYPES, path)
    _validate_edge_endpoints(frame, class_nodes, path)
    return frame


def load_ssa_flow_edges_csv(path: str | Path, class_nodes: pd.DataFrame) -> pd.DataFrame:
    """Read SSA flow edges after checking node ids and flow types."""
    frame = _read_required_columns(path, SSA_FLOW_COLUMNS)
    frame["source"] = _as_text(frame["source"])
    frame["target"] = _as_text(frame["target"])
    frame["flow_type"] = _as_text(frame["flow_type"])
    frame["weight"] = _numeric_non_negative(frame["weight"], path)
    _validate_allowed_values(frame, "flow_type", ALLOWED_SSA_FLOW_TYPES, path)
    _validate_edge_endpoints(frame, class_nodes, path)
    return frame


def load_extracted_subject(extracted_dir: str | Path) -> dict[str, pd.DataFrame]:
    root = Path(extracted_dir)
    class_nodes = load_class_nodes_csv(root / "class_nodes.csv")
    structural_dependencies = load_structural_dependencies_csv(
        root / "structural_dependencies.csv",
        class_nodes,
    )
    ssa_flow_edges = load_ssa_flow_edges_csv(root / "ssa_flow_edges.csv", class_nodes)
    return {
        "class_nodes": class_nodes,
        "structural_dependencies": structural_dependencies,
        "ssa_flow_edges": ssa_flow_edges,
    }


def _read_required_columns(path: str | Path, required_columns: list[str]) -> pd.DataFrame:
    csv_path = Path(path)
    frame = pd.read_csv(csv_path)
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{csv_path} is missing required columns: {', '.join(missing)}")
    return frame.loc[:, required_columns].copy()


def _as_text(series: pd.Series) -> pd.Series:
    return series.astype("string")


def _numeric_non_negative(series: pd.Series, path: str | Path) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.isna().any():
        raise ValueError(f"{Path(path)} contains non-numeric weight values")
    if (numeric < 0).any():
        raise ValueError(f"{Path(path)} contains negative weight values")
    return numeric.astype(float)


def _validate_no_missing(frame: pd.DataFrame, columns: list[str], path: str | Path) -> None:
    for column in columns:
        if frame[column].isna().any():
            raise ValueError(f"{Path(path)} contains missing values in {column}")


def _validate_allowed_values(
    frame: pd.DataFrame,
    column: str,
    allowed_values: frozenset[str],
    path: str | Path,
) -> None:
    observed = set(frame[column].dropna().astype(str))
    invalid = sorted(observed - allowed_values)
    if invalid:
        allowed = ", ".join(sorted(allowed_values))
        raise ValueError(
            f"{Path(path)} contains unsupported {column} values: "
            f"{', '.join(invalid)}; expected one of: {allowed}"
        )


def _validate_edge_endpoints(
    frame: pd.DataFrame,
    class_nodes: pd.DataFrame,
    path: str | Path,
) -> None:
    class_ids = set(class_nodes["class_id"].dropna().astype(str))
    sources = set(frame["source"].dropna().astype(str))
    targets = set(frame["target"].dropna().astype(str))
    missing = sorted((sources | targets) - class_ids)
    if missing:
        raise ValueError(
            f"{Path(path)} contains source/target values not present in class_nodes.csv: "
            f"{', '.join(missing)}"
        )


def extract_dependencies(project_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    return {
        "project_dir": str(project_dir),
        "output_dir": str(output_dir),
        "status": "not_implemented",
    }
