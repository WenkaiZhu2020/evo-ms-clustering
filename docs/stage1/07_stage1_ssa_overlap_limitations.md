# Stage 1 SSA Overlap Limitations

## 1. Implementation Summary

The Stage 1 prototype uses Shimple-based intraprocedural def-use tracking. It extracts two restricted SSA-derived patterns. The first pattern is return-value flow: a value returned by one application call is passed to another application call inside the same method. The second pattern is argument-passing flow: an argument or locally defined value is passed to an invoked application class. This is not complete interprocedural transitive data flow. The extractor does not follow values through a chain of method calls across different methods. It also does not explicitly export phi-node merge evidence. The extracted CSV rows are directed, with `source` and `target`, but the Python graph-building layer later aggregates them into undirected class-level pairs for `G_ssa`.

This means the current SSA evidence should be read as a small class-level signal. It is useful for checking whether local data-flow patterns add information to the raw structural graph. It should not be described as a full program-wide SSA analysis.

## 2. Limitation 1 — Overlap with Structural Evidence

Many SSA-derived class pairs already exist in the raw graph through method-call or type-reference evidence. This matters because `G_raw` already contains class-level structural relations, and `G_ssa` adds SSA flow weight on top of that representation. When an SSA pair is already present in `G_raw`, SSA often reweights an existing class pair instead of adding a new pair.

SSA is not simply a duplicate of method-call evidence. A return-value flow can create a producer-consumer pair that is not itself a direct call edge. For example, if class `A` calls `B.create()` and then passes the returned value to `C.save(...)`, the normal call evidence may include `A -> B` and `A -> C`, while the return-value flow records `B -> C`. This is why overlap must be measured directly instead of inferred only from method-call edges.

The table below uses undirected class pairs, matching the graph-construction representation. `SSA pairs` is the number of distinct SSA-derived class pairs. `Already in raw graph` is the number of those pairs that already exist through type or call evidence in `G_raw`. `Raw overlap` uses `SSA pairs` as the denominator. `Unique SSA pairs` is the number of SSA pairs not present in `G_raw`.

| Subject   | SSA pairs | Already in raw graph | Raw overlap | Unique SSA pairs |
| --------- | --------: | -------------------: | ----------: | ---------------: |
| JPetStore |        20 |                   13 |       65.0% |                7 |
| DayTrader |        61 |                   53 |       86.9% |                8 |
| Xerces-J  |      1456 |                 1088 |       74.7% |              368 |

The result shows that most SSA pairs overlap with existing raw structural pairs. Therefore, SSA often increases the weight of a relation that is already present, instead of creating a new relation. The overlap is strongest on DayTrader, where 86.9% of SSA pairs are already in the raw graph. However, some unique SSA pairs still exist in every subject, so it is also wrong to say that all SSA edges are duplicates.

Safe claim:

> At class level, most SSA-derived pairs overlap with existing structural pairs, so the SSA channel contributes limited new topology.

## 3. Limitation 2 — Overlap Between SSA Flow Types

Return-value flow and argument-passing flow are extracted separately. They represent different local patterns in the extractor. However, after undirected class-level aggregation, they often point to the same class pairs. This reduces how much independent topology the two SSA channels contribute to the final graph.

The table below again uses undirected class pairs. `Return pairs` is the number of distinct pairs with return-value flow. `Argument pairs` is the number of distinct pairs with argument-passing flow. `Common pairs` is their intersection. `Return covered by argument` is `Common pairs / Return pairs`. `Return-only pairs` is the number of return-flow pairs not present in argument-flow pairs.

| Subject   | Return pairs | Argument pairs | Common pairs | Return covered by argument | Return-only pairs |
| --------- | -----------: | -------------: | -----------: | -------------------------: | ----------------: |
| JPetStore |           13 |             20 |           13 |                     100.0% |                 0 |
| DayTrader |           46 |             61 |           46 |                     100.0% |                 0 |
| Xerces-J  |          426 |           1456 |          426 |                     100.0% |                 0 |

In the current extracted data, every measured return-flow pair is also present as an argument-flow pair after undirected class-level aggregation. This means return flow adds no new class-pair topology beyond argument flow in these three subjects. Argument flow still contains many additional pairs, especially on Xerces-J. The relationship is a measured property of these subjects and this implementation output. It is not a universal logical rule of SSA.


## 4. Conclusion

The two main limitations point in the same direction. First, many SSA-derived class pairs already exist in the raw structural graph. Second, all measured return-flow pairs are already covered by argument-flow pairs after undirected class-level aggregation. Together, this means the current SSA representation has limited independent information at class level.

The current SSA representation changes graph weights and can change Leiden partitions, but much of its class-level evidence repeats relations that are already present in the raw graph or in the other SSA channel. This helps explain why the Stage 1 experiments did not show a clearly stronger or more stable decomposition signal. The result is a limitation of the current restricted, undirected class-level representation, not evidence that SSA is useless in general.
