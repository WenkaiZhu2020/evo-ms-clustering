# Xerces collision resolution assessment

The 11 duplicate full-text and duplicate-embedding groups contain 55 retained classes. No class, input, embedding, or edge was removed.

Classification counts: {'C': 11}.

`C` means permitted-view-equivalent: raw Jimple bodies differ across package/owner copies, while the frozen normalized body evidence is identical. These package, owner, and type differences are deliberately excluded from Body V1.

| Group | Members | Classification | Raw body equivalent | Normalized evidence equivalent | Structural neighbourhood similarity | Intra edges | External edges |
|---|---:|---|---|---|---:|---:|---:|
| collision_01 | 5 | C | false | true | 0.000000 | 9 | 0 |
| collision_02 | 5 | C | false | true | 0.000000 | 9 | 0 |
| collision_03 | 5 | C | false | true | 0.000000 | 9 | 0 |
| collision_04 | 5 | C | false | true | 0.000000 | 9 | 0 |
| collision_05 | 5 | C | false | true | 0.000000 | 9 | 0 |
| collision_06 | 5 | C | false | true | 0.000000 | 9 | 0 |
| collision_07 | 5 | C | false | true | 0.000000 | 9 | 3 |
| collision_08 | 5 | C | false | true | 0.000000 | 9 | 0 |
| collision_09 | 5 | C | false | true | 0.000000 | 9 | 0 |
| collision_10 | 5 | C | false | true | 0.000000 | 9 | 1 |
| collision_11 | 5 | C | false | true | 0.000000 | 9 | 0 |

## Structural-context diagnostic

Mean pairwise raw structural-neighbour Jaccard is 0.000000 (minimum 0.000000, maximum 0.000000). The collision groups therefore occupy different structural neighbourhoods in this diagnostic; that is a known limitation of a declaration-plus-permitted-lexical representation, not evidence that the frozen semantic inputs are corrupted.

## Graph impact

Collision classes: 55 / 814; final edges involving collision classes: 103 / 1681; intra-group edges: 99; external edges: 4.
Components primarily explained by collision groups: 10.

No over-normalization, extraction-failure, or unresolved collision group was found by this audit.
