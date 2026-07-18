# Final Stage 3 legacy-reference allowlist

The final runtime uses `stage3_declaration_method_body` with representation
`declaration_method_body_v1`. The following remaining strings are retained as
frozen provenance or as negative-test inputs; they are not runtime data
sources, scientific settings, or fallback implementations.

| Location | Reference | Reason retained |
| --- | --- | --- |
| `configs/experiments/05_stage3_declaration_method_body.yml` | historical source-config path/hash and explicit boundary guard names | The final configuration records the historical source identity and states that it is not loaded at runtime. |
| `data/semantic_text/declaration_method_body/*/manifest.json` | declaration-source path/commit/hash fields | Frozen semantic-input provenance; the final loader reads only the semantic-text content and its final identity. |
| `data/semantic_text/declaration_method_body/*/class_semantic_inputs.csv` | declaration-source provenance columns | Frozen accepted input artifacts; changing these rows would violate the scientific byte-integrity gate. |
| `results/*/05_stage3_declaration_method_body/**/config_snapshot.yml` | historical routing and boundary fields | Frozen run snapshots from the accepted formal experiment; they are not used to select a current experiment. |
| `results/*/05_stage3_declaration_method_body/**/run_metadata.json` | historical base-config provenance fields | Frozen run metadata preserved byte-for-byte under the scientific non-change policy. |
| `results/*/05_stage3_declaration_method_body/**/graph_provenance.json` | historical graph-generation labels | Frozen per-seed provenance preserved byte-for-byte; current graph loading uses the final representation identity and hashes. |
| `tests/test_stage3_provenance.py`, `tests/test_stage3_no_legacy_fallback.py`, `tests/test_stage3_input_contract.py`, `tests/test_stage3_preference_analysis.py`, `tests/test_preference_analysis_audit.py` | obsolete representation/path strings | Negative tests proving that legacy identities are rejected or never read. |
| `tools/soot_extractor/src/test/java/org/evomicro/sootextractor/SootExtractorCliTest.java` | `stage3b/method_bodies.csv` temporary fixture directory | A test-only temporary output label; it is not a repository artifact path or a runtime dependency. |

No remaining occurrence is an import, dynamic loader, current artifact root,
config inheritance operation, or fallback path used by the final Stage 3
implementation. The old Stage 3A config, semantic-input CSVs, result tree,
mixed report trees, comparison scripts, and method-body orchestration package
were removed in this cleanup commit.
