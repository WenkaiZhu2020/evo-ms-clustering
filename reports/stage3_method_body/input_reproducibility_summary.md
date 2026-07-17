# Stage 3B input reproducibility summary

The isolated Stage 3B input generation was run twice in the same fixed
environment. Each run used the Java 17 Soot/Shimple extractor and the exact
pinned Nomic tokenizer at revision
`9a0457648f060c4279d4a3982d2d27a4df6fac59`, with tokenizer truncation
disabled. The second run used a separate temporary extraction directory and
a separate temporary semantic-text/report destination.

Run 1 extraction and output were temporary evidence plus the accepted
repository output. Run 2 used:

* extraction: `/tmp/stage3b-method-body-run2.zHl9f6`
* semantic input destination: `/tmp/stage3b-semantic-final3-run2.u3sWj7`
* report destination: `/tmp/stage3b-reports-final3-run2.xNR1LD`

For every subject, the following files were compared byte-for-byte:

* `class_semantic_inputs.csv`;
* `class_ids.csv`;
* `quality_summary.json`.

The parsed class ordering, semantic-text bytes, per-class input hashes, class
mapping hashes, aggregate input hashes, tokenizer metadata, normalization
source hash, contract hash, and extraction version were also compared.

## Result

| Subject | Classes | Semantic CSV | Mapping CSV | Quality summary | Aggregate input SHA-256 |
| --- | ---: | --- | --- | --- | --- |
| jpetstore | 24 | byte-identical | byte-identical | byte-identical | `2d9007f75a14f4a4ed6152563241b898837b6c12b66a98a2464b4cc3f969a921` |
| daytrader | 53 | byte-identical | byte-identical | byte-identical | `da53d434b820e3c25bc69df63ced807cd0113d412fa36acc9694d1a97631d655` |
| xerces | 814 | byte-identical | byte-identical | byte-identical | `65488944220cc3a503994d6f2289e0f7bdc06c619351a2e8243bca243538c8a3` |

The result is a byte-identical regeneration pass. Timestamps in manifests are
metadata only and were excluded from the content comparison; all scientific
semantic-text and hash-bearing files matched exactly.

No embedding, nearest-neighbour file, semantic graph, optimization result,
seed output, or evaluation result was created or inspected.
