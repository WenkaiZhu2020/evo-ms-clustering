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

The preference-response material is post-hoc exploratory analysis. It must
not be interpreted as a replacement for the preregistered formal comparison.

The canonical Dissertation Section 4.3 data pack is
[`chapter4_3_data_pack.md`](chapter4_3_data_pack.md). Its reporting-only
outputs are regenerated and byte-checked with:

```text
python experiments/05_stage3_declaration_method_body/analyze.py --write-reporting
python experiments/05_stage3_declaration_method_body/analyze.py --check-reporting
```

Neither command runs an experiment or regenerates semantic evidence.

The former `reports/stage3/` directory was a mixed legacy root and has been
retired. Historical provenance files may still contain that path because they
record the original generation environment.
