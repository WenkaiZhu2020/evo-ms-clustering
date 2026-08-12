# Final Stage 3 declaration-method-body reports

This is the human-readable report entry point for the final
`stage3_declaration_method_body` experiment using
`declaration_method_body_v1`.

Human-readable findings, explanations, and thesis figures are kept here as the
single Stage 3 documentation entry point. Machine-readable tables, analysis
data, provenance, and validation evidence are stored under:

```text
results/stage3/
```

The formal Stage 3 results for each subject remain under:

```text
results/stage3/subjects/<subject>/declaration_method_body/
```

Current selector-dependent dissertation reporting is authoritative under
`results/stage3/cross_subject/operating_preference_analysis/`. `BALANCE` is
the primary operating preference: candidates are admitted within 5%
proportional modularity loss from the current front-best `Q_best`, then
minimum imbalance is selected. `MODULARITY_ANCHOR` (MAX-Q) is a reference;
`COUPLING`, `COHESION`, and `SEMANTIC` are descriptive sensitivity profiles.
Modularity loss relative to Leiden is a separate descriptive comparison.

[`chapter4_3_data_pack.md`](chapter4_3_data_pack.md) and the older
`formal_statistics/` tables are retained as historical runtime MAX-Q
reporting/provenance. Runtime `selected_solution.json` and
`selected_partition.csv` files likewise preserve the historical
maximum-modularity selections; they are not the current BALANCE-selected
dissertation authority.

The former `reports/stage3/` directory was a mixed legacy root and has been
retired. Historical provenance files may still contain that path because they
record the original generation environment.
