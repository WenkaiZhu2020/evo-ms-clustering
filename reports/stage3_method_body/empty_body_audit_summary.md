# Empty Stage 3B method-body audit

The accepted Body V1 inputs were audited without regeneration. Soot/Jimple/Shimple outputs were produced in an isolated temporary directory.

Category definitions: A=no concrete body; B=concrete body with no permitted evidence; C=generated/template equivalent; D=meaningful candidates correctly filtered; E=suspected extraction failure; F=unresolved.

| Subject | Empty | A | B | C | D | E | F | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| jpetstore | 7 | 7 | 0 | 0 | 0 | 0 | 0 | EXPECTED / ACCEPTABLE |
| daytrader | 4 | 4 | 0 | 0 | 0 | 0 | 0 | EXPECTED / ACCEPTABLE |
| xerces | 120 | 116 | 0 | 4 | 0 | 0 | 0 | EXPECTED / ACCEPTABLE |

## Subject details

### jpetstore

* Total classes: 24; empty bodies: 7 (29.1667%).
* Categories A–F: {'A': 7, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0}; concrete classes with empty bodies: 0; body-loading failures: 0; permitted evidence unexpectedly missing: 0.
* Generated/template classes: 0; interfaces: 7; abstract classes: 7.
* Mean empty-body embedding shift (cosine distance): 0.207882298; mean neighbour retention: 0.857142857.
* Decision: **EXPECTED / ACCEPTABLE**.

### daytrader

* Total classes: 53; empty bodies: 4 (7.5472%).
* Categories A–F: {'A': 4, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0}; concrete classes with empty bodies: 0; body-loading failures: 0; permitted evidence unexpectedly missing: 0.
* Generated/template classes: 0; interfaces: 4; abstract classes: 4.
* Mean empty-body embedding shift (cosine distance): 0.124061720; mean neighbour retention: 0.750000000.
* Decision: **EXPECTED / ACCEPTABLE**.

### xerces

* Total classes: 814; empty bodies: 120 (14.7420%).
* Categories A–F: {'A': 116, 'B': 0, 'C': 4, 'D': 0, 'E': 0, 'F': 0}; concrete classes with empty bodies: 0; body-loading failures: 0; permitted evidence unexpectedly missing: 0.
* Generated/template classes: 4; interfaces: 116; abstract classes: 116.
* Mean empty-body embedding shift (cosine distance): 0.110105018; mean neighbour retention: 0.752777778.
* Decision: **EXPECTED / ACCEPTABLE**.

## Findings

* The Soot method-body extraction log contained no method-body retrieval or Shimple-conversion failure for an audited class.
* Interface and abstract-only classes are expected to have no concrete body rows. The four Xerces compiler-synthetic `$1` classes are retained and classified as generated/template-equivalent.
* Empty-body embeddings and neighbours can change because `[DECLARATION]`, `[METHOD_BODY]`, and `<EMPTY>` are part of the frozen text. These changes cannot be attributed to lexical method-body content.
* This audit does not alter the frozen `<EMPTY>` policy or any scientific artifact.
