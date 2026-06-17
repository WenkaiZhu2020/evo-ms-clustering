"""Build G_ssa by adding scoped SSA flow evidence to G_raw edges."""

import pandas as pd

from evo_ms.evidence.ssa_flow_evidence import aggregate_ssa_flow_weights
from evo_ms.graph.weight_calculator import calculate_stage1_edge_weights


SSA_EDGE_COLUMNS = [
    "source",
    "target",
    "type_weight",
    "call_weight",
    "return_flow_weight",
    "argument_flow_weight",
    "ssa_flow_weight",
    "g_ssa_weight",
]


def build_ssa_edges(
    class_nodes: pd.DataFrame,
    raw_edges: pd.DataFrame,
    ssa_flow_edges: pd.DataFrame,
    ssa_lambda: float = 1.0,
) -> pd.DataFrame:
    """Merge raw weights with SSA flow; ssa_flow_weight is lambda-scaled."""
    _validate_required_columns(class_nodes, ["class_id"], "class_nodes")
    _validate_required_columns(
        raw_edges,
        ["source", "target", "type_weight", "call_weight"],
        "raw_edges",
    )

    raw = raw_edges.loc[:, ["source", "target", "type_weight", "call_weight"]].copy()
    raw["source"] = raw["source"].astype("string")
    raw["target"] = raw["target"].astype("string")
    raw["type_weight"] = pd.to_numeric(raw["type_weight"], errors="coerce")
    raw["call_weight"] = pd.to_numeric(raw["call_weight"], errors="coerce")
    _validate_component_weights(raw, ["type_weight", "call_weight"], "raw_edges")
    _validate_node_references(class_nodes, raw, "raw_edges")
    raw = _aggregate_undirected_raw_edges(raw)
    raw = _drop_self_loops(raw)

    flow_weights = _drop_self_loops(aggregate_ssa_flow_weights(class_nodes, ssa_flow_edges))
    # Outer join keeps SSA-only edges instead of dropping them.
    combined = raw.merge(flow_weights, on=["source", "target"], how="outer")
    if combined.empty:
        return pd.DataFrame(columns=SSA_EDGE_COLUMNS)

    for column in ["type_weight", "call_weight", "return_flow_weight", "argument_flow_weight"]:
        if column not in combined:
            combined[column] = 0.0
        combined[column] = combined[column].fillna(0.0)

    weights = combined.apply(
        lambda row: calculate_stage1_edge_weights(
            {
                "type_weight": row["type_weight"],
                "call_weight": row["call_weight"],
                "return_flow_weight": row["return_flow_weight"],
                "argument_flow_weight": row["argument_flow_weight"],
            },
            ssa_lambda=ssa_lambda,
        ),
        axis=1,
        result_type="expand",
    )
    # The public CSV column stores the lambda-scaled SSA contribution.
    combined["ssa_flow_weight"] = weights["ssa_flow_weight"]
    combined["g_ssa_weight"] = weights["g_ssa_weight"]
    combined = combined.loc[combined["g_ssa_weight"] > 0].copy()

    return combined.loc[:, SSA_EDGE_COLUMNS].sort_values(["source", "target"]).reset_index(
        drop=True,
    )


def build_g_ssa_graph(
    class_nodes: pd.DataFrame,
    raw_edges: pd.DataFrame,
    ssa_flow_edges: pd.DataFrame,
    ssa_lambda: float = 1.0,
):
    """Build the weighted NetworkX view used by later clustering."""
    import networkx as nx

    graph = nx.Graph()
    for row in class_nodes.to_dict("records"):
        graph.add_node(
            str(row["class_id"]),
            class_name=row.get("class_name"),
            package=row.get("package"),
            class_file_path=row.get("class_file_path"),
        )

    for row in build_ssa_edges(class_nodes, raw_edges, ssa_flow_edges, ssa_lambda=ssa_lambda).to_dict("records"):
        graph.add_edge(
            row["source"],
            row["target"],
            type_weight=float(row["type_weight"]),
            call_weight=float(row["call_weight"]),
            return_flow_weight=float(row["return_flow_weight"]),
            argument_flow_weight=float(row["argument_flow_weight"]),
            ssa_flow_weight=float(row["ssa_flow_weight"]),
            g_ssa_weight=float(row["g_ssa_weight"]),
        )
    return graph


def _aggregate_undirected_raw_edges(raw_edges: pd.DataFrame) -> pd.DataFrame:
    if raw_edges.empty:
        return raw_edges
    raw = raw_edges.copy()
    source = raw["source"].astype(str)
    target = raw["target"].astype(str)
    source_first = source <= target
    raw["source"] = source.where(source_first, target)
    raw["target"] = target.where(source_first, source)
    return (
        raw.groupby(["source", "target"], as_index=False)[["type_weight", "call_weight"]]
        .sum()
        .loc[:, ["source", "target", "type_weight", "call_weight"]]
    )


def _drop_self_loops(edges: pd.DataFrame) -> pd.DataFrame:
    if edges.empty:
        return edges
    return edges.loc[edges["source"].astype(str) != edges["target"].astype(str)].copy()


def _validate_required_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {', '.join(missing)}")


def _validate_component_weights(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    for column in columns:
        if frame[column].isna().any():
            raise ValueError(f"{name} contains non-numeric {column} values")
        if (frame[column] < 0).any():
            raise ValueError(f"{name} contains negative {column} values")


def _validate_node_references(class_nodes: pd.DataFrame, edges: pd.DataFrame, name: str) -> None:
    class_ids = set(class_nodes["class_id"].dropna().astype(str))
    sources = set(edges["source"].dropna().astype(str))
    targets = set(edges["target"].dropna().astype(str))
    missing = sorted((sources | targets) - class_ids)
    if missing:
        raise ValueError(
            f"{name} contains source/target values not present in class_nodes.csv: "
            f"{', '.join(missing)}"
        )
