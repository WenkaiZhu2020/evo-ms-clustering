# Stage 3B method-body input contract — Body V1

## Status and identity

This is a post-hoc exploratory extension. Stage 3A remains the frozen
confirmatory declaration-only experiment. The input construction is frozen
after the validation gates in this report; no downstream effectiveness claim
is made. The representation identity is `declaration_method_body_v1` and the
experiment name is `stage3_declaration_method_body`.

For every class, the semantic text is exactly:

```text
[DECLARATION]
<exact Stage 3A semantic_text bytes>
[METHOD_BODY]
<normalized body evidence or <EMPTY>>
```

The declaration section is read from the frozen CSVs in `data/semantic_inputs/`.
It is not regenerated or reserialized.

## Evidence source and boundary

The source is the shared Soot extractor over the compiled subject classes. It
records concrete method bodies as Shimple text in an isolated temporary
directory. Raw Shimple is a parsing source only; it is never embedded.

Included lexical evidence is:

* invoked method simple names;
* field simple names in Shimple field references;
* non-synthetic, non-temporary lower-case local identifiers when genuinely
  present in the body text;
* exception names ending in `Exception`, `Error`, or `Throwable`;
* controlled operation words (`invoke`, `branch`, `jump`, `return`, `throw`,
  `create`, `cast`, and `measure`);
* accepted string-literal tokens.

The extractor does not provide reliable source-level local-variable metadata
for this protocol. Synthetic Jimple locals are therefore unavailable as
meaningful locals and are rejected. Abstract and native methods have no
concrete body evidence and remain represented by the declaration plus an
empty body section. Constructors and static initializers are scanned, but
their generic names are not added as tokens. Compiler-marked synthetic
methods are retained in extraction metadata and excluded from body tokens.

The body never retains package paths, FQNs, invocation owners, declaring
classes, source paths, imports, dependency edges, caller/callee pairs, JVM
descriptors, raw signatures, line numbers, bytecode offsets, labels, Soot
identifiers, or Jimple temporary locals. Type-context names after `new`,
`instanceof`, or `cast`, and owner/signature regions, are removed before the
general lexical pass. This prevents duplicating the declaration type graph.

## Normalization

Body V1 applies Unicode NFKC normalization, lowercasing, punctuation
separation, camelCase/PascalCase splitting, acronym splitting, and
snake_case/kebab-case splitting. Accepted tokens match `[a-z][a-z0-9]*` and
have at least two characters. Java keywords and generic stopwords are
removed. Generic methods `toString`, `hashCode`, `equals`, `init`, `clinit`,
`main`, and `run` are removed completely.

Getter/setter policy is fixed: leading `get`, `set`, and `is` are removed, but
the remaining meaningful words are retained. Thus `getCustomer` contributes
`customer`, and `setPaymentStatus` contributes `payment status`. A method
whose complete name is only a generic accessor contributes no method-name
token.

Within each method, the priority order is method/action tokens, accepted
literal and exception tokens, then permitted local/operation tokens. Within a
priority level source order is retained. Duplicate tokens are removed within
each method. At class level, methods are sorted by `(method_name,
method_signature)` and each token may occur at most twice. Body tokens are
then capped at 256 normalized tokens. The declaration is never truncated.

String literals are accepted only when they are 2–80 characters after
decoding and normalization, and contain meaningful lexical tokens. Empty,
numeric, timestamp-only, UUID, hash, URL, namespace-URI, filesystem-path,
classpath/resource-path, encoded/binary-looking, format-only, boilerplate,
and no-token literals are rejected. Original literal values are not written
to audit reports; only decisions and normalized token previews are recorded.

Generated-code source metadata is not available in the compiled-class scope.
Classes remain in scope. Compiler synthetic-method flags are recorded, and a
class is not selectively excluded because its body is repetitive. The report
records the resulting generated-code evidence concentration.

The extraction version is `soot_shimple_method_body_v1`. The complete
isolated extraction is run with the repository Soot/Shimple toolchain under
the fixed Java 17 runtime selected by the extractor wrapper. The raw
extraction directory is temporary and is not a scientific artifact.

## Length and determinism

The exact frozen tokenizer is the Nomic tokenizer at revision
`9a0457648f060c4279d4a3982d2d27a4df6fac59`, with maximum sequence length
`32768`, special tokens enabled, and tokenizer truncation disabled. The
normalized body budget is 256 tokens before model encoding. If the final text
would exceed the model limit, only the body token prefix is shortened in the
fixed priority order; declaration truncation is forbidden. The reason and
count are recorded per class.

Rows and methods are sorted deterministically. UTF-8 and LF are required.
The input hash is SHA-256 over the final semantic-text bytes.

## Scope, paths, and gates

Expected classes are JPetStore 24, DayTrader 53, and Xerces 814. Final inputs
are isolated under `data/semantic_text/declaration_method_body/`; reports are
under `reports/stage3_method_body/`. No embeddings, graphs, optimization
results, or seed outputs are part of this contract.

Acceptance requires exact class scope, 100% byte-level declaration
preservation, zero declaration truncation, no prohibited leakage, deterministic
regeneration, recorded aggregate hashes, and passing focused plus extractor
tests. Stage 3A model, graph, objective, optimizer, seeds, and evaluation
settings remain unchanged downstream.

## Frozen aggregate input hashes

The canonical aggregate is SHA-256 over sorted lines of
`class_id<TAB>input_hash<LF>`:

| Subject | Classes | Aggregate input SHA-256 |
| --- | ---: | --- |
| jpetstore | 24 | `2d9007f75a14f4a4ed6152563241b898837b6c12b66a98a2464b4cc3f969a921` |
| daytrader | 53 | `da53d434b820e3c25bc69df63ced807cd0113d412fa36acc9694d1a97631d655` |
| xerces | 814 | `65488944220cc3a503994d6f2289e0f7bdc06c619351a2e8243bca243538c8a3` |

The source declaration files are recorded in
`stage3a_declaration_source_manifest.json`. The final semantic inputs are
under `data/semantic_text/declaration_method_body/<subject>/`; no embedding,
graph, result, or optimization artifact is created by this task.
