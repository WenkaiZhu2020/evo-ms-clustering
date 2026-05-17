"""Build G_raw class dependency graphs from structural dependencies."""

from collections.abc import Iterable
import warnings

import pandas as pd

from evo_ms.graph.weight_calculator import calculate_raw_weight


RAW_EDGE_COLUMNS = ["source", "target", "type_weight", "call_weight", "raw_weight"]
STRUCTURAL_DEPENDENCY_TYPES = frozenset({"type", "call"})


def build_raw_edges(
    class_nodes: pd.DataFrame,
    structural_dependencies: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate structural dependencies into raw class-level edge weights."""
    _validate_required_columns(class_nodes, ["class_id"], "class_nodes")
    _validate_required_columns(
        structural_dependencies,
        ["source", "target", "dependency_type", "weight"],
        "structural_dependencies",
    )

    dependencies = structural_dependencies.loc[
        :,
        ["source", "target", "dependency_type", "weight"],
    ].copy()
    dependencies["source"] = dependencies["source"].astype("string")
    dependencies["target"] = dependencies["target"].astype("string")
    dependencies["dependency_type"] = dependencies["dependency_type"].astype("string")
    dependencies["weight"] = pd.to_numeric(dependencies["weight"], errors="coerce")

    _validate_dependency_types(dependencies)
    _validate_weights(dependencies)
    _validate_node_references(class_nodes, dependencies)

    self_loop_mask = dependencies["source"] == dependencies["target"]
    if self_loop_mask.any():
        count = int(self_loop_mask.sum())
        warnings.warn(
            f"removed {count} self-loop structural dependencies from G_raw",
            RuntimeWarning,
            stacklevel=2,
        )
        dependencies = dependencies.loc[~self_loop_mask].copy()

    if dependencies.empty:
        return pd.DataFrame(columns=RAW_EDGE_COLUMNS)

    grouped = (
        dependencies.groupby(["source", "target", "dependency_type"], as_index=False)["weight"]
        .sum()
        .pivot(index=["source", "target"], columns="dependency_type", values="weight")
        .fillna(0.0)
        .reset_index()
    )
    grouped.columns.name = None

    if "type" not in grouped:
        grouped["type"] = 0.0
    if "call" not in grouped:
        grouped["call"] = 0.0

    raw_edges = grouped.rename(columns={"type": "type_weight", "call": "call_weight"})
    raw_edges["raw_weight"] = raw_edges.apply(
        lambda row: calculate_raw_weight(row["type_weight"], row["call_weight"]),
        axis=1,
    )
    return raw_edges.loc[:, RAW_EDGE_COLUMNS].sort_values(["source", "target"]).reset_index(
        drop=True,
    )


def build_raw_graph(
    edges_or_class_nodes: Iterable[tuple[str, str]] | pd.DataFrame,
    structural_dependencies: pd.DataFrame | None = None,
):
    """Create a directed G_raw graph.

    Passing only source-target tuples keeps compatibility with the initial
    placeholder API. Passing ``class_nodes`` plus ``structural_dependencies``
    builds weighted Stage 1 raw graph edges.
    """
    import networkx as nx

    graph = nx.DiGraph()
    if structural_dependencies is None:
        graph.add_edges_from(edges_or_class_nodes)
        return graph

    class_nodes = edges_or_class_nodes
    if not isinstance(class_nodes, pd.DataFrame):
        raise TypeError("class_nodes must be a pandas DataFrame when structural_dependencies is used")

    for row in class_nodes.to_dict("records"):
        graph.add_node(
            str(row["class_id"]),
            class_name=row.get("class_name"),
            package=row.get("package"),
            class_file_path=row.get("class_file_path"),
        )

    for row in build_raw_edges(class_nodes, structural_dependencies).to_dict("records"):
        graph.add_edge(
            row["source"],
            row["target"],
            type_weight=float(row["type_weight"]),
            call_weight=float(row["call_weight"]),
            raw_weight=float(row["raw_weight"]),
        )
    return graph


def _validate_required_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {', '.join(missing)}")


def _validate_dependency_types(dependencies: pd.DataFrame) -> None:
    observed = set(dependencies["dependency_type"].dropna().astype(str))
    invalid = sorted(observed - STRUCTURAL_DEPENDENCY_TYPES)
    if invalid:
        allowed = ", ".join(sorted(STRUCTURAL_DEPENDENCY_TYPES))
        raise ValueError(
            f"structural_dependencies contains unsupported dependency_type values: "
            f"{', '.join(invalid)}; expected one of: {allowed}"
        )


def _validate_weights(dependencies: pd.DataFrame) -> None:
    if dependencies["weight"].isna().any():
        raise ValueError("structural_dependencies contains non-numeric weight values")
    if (dependencies["weight"] < 0).any():
        raise ValueError("structural_dependencies contains negative weight values")


def _validate_node_references(class_nodes: pd.DataFrame, dependencies: pd.DataFrame) -> None:
    class_ids = set(class_nodes["class_id"].dropna().astype(str))
    sources = set(dependencies["source"].dropna().astype(str))
    targets = set(dependencies["target"].dropna().astype(str))
    missing = sorted((sources | targets) - class_ids)
    if missing:
        raise ValueError(
            "structural_dependencies contains source/target values not present in "
            f"class_nodes.csv: {', '.join(missing)}"
        )
