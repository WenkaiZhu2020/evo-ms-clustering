# Stage 3 Semantic Method Contract

## 1. Purpose and frozen scope

MiniLM identifier experiments are preliminary lexical-semantic diagnostics. They are not the formal Stage 3 model. Formal Stage 3 uses Nomic Embed Code, revision `9a0457648f060c4279d4a3982d2d27a4df6fac59`, to produce one embedding for each class-level declaration. The semantic graph is built after embedding. Nomic produces class-level embeddings; it does not directly produce the graph.

The semantic channel receives only the frozen class-declaration input. It does not receive constructed structural edges, cluster labels, or reference labels.

## 2. Frozen model contract

The model is `nomic-ai/nomic-embed-code` at revision `9a0457648f060c4279d4a3982d2d27a4df6fac59`. Embeddings use last-token pooling and L2 normalization. No query prompt is used for class-to-class embedding. Model execution itself is not implemented today, but this model contract is frozen for the formal run.

The exact tokenizer is the tokenizer shipped at the same pinned revision. Its
verified `model_max_length` is `32768`, matching the model config's
`max_position_embeddings` value. Token counting uses truncation disabled and
`add_special_tokens=true`.

When token count exceeds `32768`, truncation is triggered explicitly. The
entity header—kind, class name, meaningful superclass, annotations, and
interfaces—is always preserved. Methods retain the frozen sorted order and the
longest stable prefix that fits within the token limit. Silent truncation is
forbidden; every dropped method is recorded in `truncated_method_count`.

## Formal embedding runtime

The pinned Nomic repository is distributed in Sentence Transformers format. The
formal pipeline therefore uses `SentenceTransformer` from the
`sentence_transformers` package. The packaged model supplies the Qwen2Model
transformer, last-token pooling, and vector normalization. Formal execution
does not use a custom pooling implementation or manually reimplement pooling.

No query prompt is supplied because the task is class-to-class similarity, not
natural-language-query-to-code retrieval. Each embedding is expected to
contain 3584 values, and cosine similarity is used. Formal input encoding uses
the `semantic_text` column with truncation disabled; tokenizer length control is
handled by the frozen Day 2 input contract.

The formal runtime backend, loader, packaged pooling/normalization sources,
and output dimension are frozen now. Device, dtype, and batch size remain
execution metadata and will be frozen after the Day 3 full-model smoke test.
Formal embeddings cannot be generated until those runtime values are recorded.

## 3. Frozen class-declaration input

The input contains the entity kind, class name, meaningful superclass, class-level annotations exposed by bytecode, interfaces, method names, return types, parameter types, and private self-declared methods. Package paths, fields, method bodies, parameter names, comments, structural edges, cluster labels, and reference labels are excluded.

Method signatures provide richer responsibility information than method identifiers alone. Class-level annotations are included only when bytecode exposes them. All type, annotation, interface, and superclass names are reduced to simple names. Private self-declared methods remain included. Method visibility and other method modifiers are stripped. Inherited methods are excluded.

For example, a declaration may be rendered as:

```text
@Service
public class TradeServiceImpl implements TradeService {
    OrderDataBean buy(String, String, double);
    QuoteDataBean getQuote(String);
    OrderDataBean sell(String, Integer);
}
```

## 4. Deterministic rendering contract

CSV rows are sorted by `class_id`. Within a declaration, annotations and interfaces are sorted lexicographically. Methods are sorted first by method name and then by their normalized complete signature. Rendering uses UTF-8, LF line endings, no trailing spaces, and exactly one final newline. The SHA-256 input hash is computed over the exact UTF-8 bytes of `semantic_text`, including that final newline.

Every subject uses this fixed CSV schema, in this exact order:

```text
subject,class_id,class_name,kind,superclass_present,semantic_text,method_count,annotation_count,interface_count,truncated_method_count,input_hash
```

`method_count` is the number of methods after filtering and signature
deduplication but before tokenizer truncation. `truncated_method_count` is the
number of methods dropped by the explicit length rule. The number of methods
present in `semantic_text` is therefore
`method_count - truncated_method_count`. `input_hash` is SHA-256 over the
post-truncation `semantic_text` UTF-8 bytes, including its final newline.

The declaration is source-like. `public` is retained only for public entities; non-public visibility is omitted. The kind is one of `class`, `abstract class`, `interface`, or `enum`. Classes use `extends` for a meaningful superclass and `implements` for interfaces. Interfaces use `extends` for parent interfaces. Implicit `java.lang.Object` and `java.lang.Enum` are omitted. The method format is:

```text
ReturnType methodName(ParameterType1, ParameterType2);
```

There are no method bodies, parameter names, throws clauses, fields, or method modifiers. Nested type identity uses `$`, not `.`. Primitive and array forms are preserved, while package qualification is removed. Generic type reduction is applied only when generic signatures are already available through the existing bytecode pipeline; no new parser is added to recover generic source syntax.

An entity with no methods still renders its declaration and an empty body, for example:

```text
public interface Marker {
}
```

## 5. Semantic graph construction

Cosine similarity is calculated between class embeddings. Each class selects its three highest-ranked distinct neighbours. Exact ties are resolved by lexicographic `class_id` order. Self-loops are removed. OR symmetrization keeps an undirected edge if either endpoint selected the other. Cosine similarity is stored as the edge weight.

The frozen sparsity parameter is:

```text
k = 3
```

This is a preregistered sparsity parameter, not a proven optimum.

## 6. Three-option graph-construction justification

Option A, the full similarity graph, is rejected because every class would connect to every other class. Weak similarities would create a dense graph, the semantic objective would lose selectivity, and computational cost would increase.

Option B, a global epsilon or percentile threshold, is rejected as the formal rule because similarity distributions can differ across subjects. One threshold can produce a sparse graph for one subject and a dense graph for another. Threshold selection would create another calibration problem.

Option C, the symmetrized top-k graph, is selected because every node receives a fixed outgoing neighbour budget and the strongest local semantic relations are retained. One shared `k` supports controlled cross-subject execution. OR symmetrization prevents a valid one-way nearest-neighbour relation from being discarded. The choice does not claim that `k=3` is optimal.

## 7. Semantic objective

For a partition (P), let (E_{\mathrm{sem}}) be the undirected semantic edge set and (w_{ij}) the stored cosine-similarity weight.

$$
W_{\mathrm{in}}(P)
=
\sum_{(i,j)\in E_{\mathrm{sem}}}
w_{ij}\,\mathbf{1}[c_i=c_j]
$$

$$
W_{\mathrm{all}}
=
\sum_{(i,j)\in E_{\mathrm{sem}}}
w_{ij}
$$

$$
S(P)
=
\frac{W_{\mathrm{in}}(P)}{W_{\mathrm{all}}}
$$

$$
f_{\mathrm{sem}}(P)
=
1-S(P)
=
1-
\frac{W_{\mathrm{in}}(P)}{W_{\mathrm{all}}}
$$

$$
0
\le
f_{\mathrm{sem}}(P)
\le
1
$$

Zero means all semantic-edge weight remains inside clusters. One means all semantic-edge weight is cut across clusters. Lower is better. An empty semantic graph returns 1 defensively, but it is treated as a pipeline failure before formal execution.

## 8. Coupling-redundancy diagnostic

Structural coupling and semantic cut both penalise cross-cluster relations, but they operate on different graphs. Spearman correlation is preregistered on each final four-objective Pareto front:

$$
\rho
=
\operatorname{Spearman}
\left(
f_{\mathrm{coupling}},
f_{\mathrm{sem}}
\right)
$$

A high correlation suggests that the semantic channel may be repeating information already represented by structural coupling. A low correlation suggests that the semantic channel contributes a different signal. Either result affects interpretation of a null result: a high correlation makes a null semantic effect less surprising, while a low correlation makes a null effect more informative about the usefulness of that distinct signal. This diagnostic is explanatory and cannot be used to retune the graph or objective.

## 9. Representative-solution projection

Applying the old selection rule directly to a four-objective front would be incorrect because the added semantic coordinate could change Pareto membership and could implicitly affect which solution is selected. The controlled procedure is:

1. Take the final four-objective front.
2. Remove the semantic-objective coordinate.
3. Recompute non-dominance in the original three-objective space.
4. Remove duplicate projected objective vectors.
5. Apply the exact Stage 2 selection rule from `experiments/02_stage2_nsga_structure_only/run.py:_select_solution`.
6. Apply the exact Stage 2 deterministic tie-break.
7. Do not use semantic performance as an extra tie-break.

The Stage 2 rule is highest weighted modularity among feasible Pareto solutions, with its documented fallback when no feasible candidate is available. The exact tie-break tuple is `(-weighted_modularity, is_injected_seed, coupling, -cohesion, imbalance, _label_tuple_from_row)`. This projection controls the comparison by keeping representative selection in the original three-objective decision space.

## 10. Hypervolume comparability

Stage 2 three-dimensional Hypervolume and Stage 3 four-dimensional Hypervolume are not directly comparable. Stage 3 4D Hypervolume is an internal diagnostic only. Formal Stage 2 versus Stage 3 comparison uses the Stage 3 front projected into the original three-objective space, re-filters that projected front, and reuses the Stage 2 theoretical bounds and reference point. The bounds are defined in `configs/experiments/stage2_robustness_bounds.yml` and generated by `experiments/02_stage2_nsga_structure_only/run_robustness.py:generate_theoretical_bounds`. The reference point mechanism is `REFERENCE_POINT = np.full(3, 1.1)` in that runner, giving `[1.1, 1.1, 1.1]`.

## 11. Go/no-go thresholds

The frozen technical thresholds are embedding coverage of 1.0, no NaN or infinite vectors, total semantic weight greater than 0, node coverage of at least 0.95, isolated-node ratio no greater than 0.05, and exact equality between the semantic class scope and the formal class scope.

The novel edge ratio is:

$$
\text{Novel edge ratio}
=
\frac{|E_{\mathrm{sem}}\setminus E_{\mathrm{raw}}|}{|E_{\mathrm{sem}}|}
$$

The minimum is:

$$
\text{Novel edge ratio}\ge 0.20
$$

For the random baseline, a subject passes an evidence check when either listed metric, structural overlap or same-reference ratio, is above the 95th percentile threshold. At least two of the three subjects must pass one of these checks. Failure does not prevent a controlled negative experiment, but it reduces the strength of the semantic-evidence claim.

## 12. Statistical family declaration

The preregistered Stage 3 primary family contains MoJoFM, Pairwise F1, structural modularity, and imbalance.

$$
\alpha_{\mathrm{adjusted}}
=
\frac{0.05}{4}
=
0.0125
$$

This differs from the broader 12-test Stage 2 family because Stage 3 declares four primary metrics for the controlled semantic comparison. Secondary metrics remain descriptive only.

## 13. Xerces early-start and invalidation rule

Xerces may start early only after one full configuration-matching seed passes on Day 5. Any later correctness bug affecting objectives, repair, Pareto membership, projection, Hypervolume, representative selection, metrics, or partitions invalidates all completed Xerces Stage 3 seeds. Those results must be invalidated and rerun; cost-based retention is forbidden.

## 14. Limitations placeholders

The following are explicit future reporting placeholders and are not result-dependent conclusions:

- Future sensitivity report: `k=3` is not sensitivity-tested in formal Stage 3.
- Future interpretation note: type signatures contain limited local structural information.
- Future assumption note: transferring `k` from the MiniLM diagnostic setting to Nomic is an assumption.
- Future normalization note: simple-name normalization can collapse distinct fully qualified types with the same simple name.
- Future extraction note: bytecode-visible annotations may differ across projects.
- Future interpretation note: declaration-level embeddings do not equal complete business semantics.
- Future model-limit note: Nomic is trained for code retrieval rather than microservice decomposition.

No result-dependent conclusion is filled in today.
