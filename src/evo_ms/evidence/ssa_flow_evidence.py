"""Aggregate SSA-derived flow evidence into class-pair weights."""

import pandas as pd

ALLOWED_SSA_FLOW_TYPES = frozenset({"return_value_flow", "argument_passing_flow"})
SSA_FLOW_WEIGHT_COLUMNS = {
    "return_value_flow": "return_flow_weight",
    "argument_passing_flow": "argument_flow_weight",
}
SSA_FLOW_AGGREGATE_COLUMNS = [
    "source",
    "target",
    "return_flow_weight",
    "argument_flow_weight",
]


def validate_ssa_flow_type(flow_type: str) -> str:
    """Validate that a flow type is one of the two Stage 1 SSA channels."""
    if flow_type not in ALLOWED_SSA_FLOW_TYPES:
        allowed = ", ".join(sorted(ALLOWED_SSA_FLOW_TYPES))
        raise ValueError(f"unsupported SSA flow type: {flow_type}; expected one of: {allowed}")
    return flow_type


def aggregate_ssa_flow_weights(
    class_nodes: pd.DataFrame,
    ssa_flow_edges: pd.DataFrame,
) -> pd.DataFrame:
    """Sum return-value and argument-passing flow by class pair."""
    _validate_required_columns(class_nodes, ["class_id"], "class_nodes")
    _validate_required_columns(
        ssa_flow_edges,
        ["source", "target", "flow_type", "weight"],
        "ssa_flow_edges",
    )

    flows = ssa_flow_edges.loc[:, ["source", "target", "flow_type", "weight"]].copy()
    flows["source"] = flows["source"].astype("string")
    flows["target"] = flows["target"].astype("string")
    flows["flow_type"] = flows["flow_type"].astype("string")
    flows["weight"] = pd.to_numeric(flows["weight"], errors="coerce")

    _validate_flow_types(flows)
    _validate_weights(flows)
    _validate_node_references(class_nodes, flows)

    if flows.empty:
        return pd.DataFrame(columns=SSA_FLOW_AGGREGATE_COLUMNS)

    flows = _with_undirected_endpoints(flows)

    # One column per accepted flow type makes the graph builder simpler.
    grouped = (
        flows.groupby(["source", "target", "flow_type"], as_index=False)["weight"]
        .sum()
        .pivot(index=["source", "target"], columns="flow_type", values="weight")
        .fillna(0.0)
        .reset_index()
    )
    grouped.columns.name = None

    for flow_type, weight_column in SSA_FLOW_WEIGHT_COLUMNS.items():
        if flow_type not in grouped:
            grouped[flow_type] = 0.0
        grouped[weight_column] = grouped[flow_type]

    return grouped.loc[:, SSA_FLOW_AGGREGATE_COLUMNS].sort_values(
        ["source", "target"],
    ).reset_index(drop=True)


def _with_undirected_endpoints(edges: pd.DataFrame) -> pd.DataFrame:
    edges = edges.copy()
    source = edges["source"].astype(str)
    target = edges["target"].astype(str)
    source_first = source <= target
    edges["source"] = source.where(source_first, target)
    edges["target"] = target.where(source_first, source)
    return edges


def _validate_required_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {', '.join(missing)}")


def _validate_flow_types(flows: pd.DataFrame) -> None:
    observed = set(flows["flow_type"].dropna().astype(str))
    invalid = sorted(observed - ALLOWED_SSA_FLOW_TYPES)
    if invalid:
        allowed = ", ".join(sorted(ALLOWED_SSA_FLOW_TYPES))
        raise ValueError(
            f"ssa_flow_edges contains unsupported flow_type values: "
            f"{', '.join(invalid)}; expected one of: {allowed}"
        )


def _validate_weights(flows: pd.DataFrame) -> None:
    if flows["weight"].isna().any():
        raise ValueError("ssa_flow_edges contains non-numeric weight values")
    if (flows["weight"] < 0).any():
        raise ValueError("ssa_flow_edges contains negative weight values")


def _validate_node_references(class_nodes: pd.DataFrame, flows: pd.DataFrame) -> None:
    class_ids = set(class_nodes["class_id"].dropna().astype(str))
    sources = set(flows["source"].dropna().astype(str))
    targets = set(flows["target"].dropna().astype(str))
    missing = sorted((sources | targets) - class_ids)
    if missing:
        raise ValueError(
            "ssa_flow_edges contains source/target values not present in "
            f"class_nodes.csv: {', '.join(missing)}"
        )
