# Inherited Stage 3A file audit

The branch intentionally inherits the completed Stage 3A implementation and
evidence. Inheritance is not treated as Stage 3B output. The complete
machine-readable classification is in
`reports/stage3_method_body/inherited_stage3a_file_audit.csv`; hard-coded path
references are in `stage3a_path_reference_audit.csv`.

## Classification policy

| Group | Meaning | Stage 3B policy |
| --- | --- | --- |
| A | Reusable pipeline implementation and common tests | Reuse unchanged, except for explicit identity/path guards. |
| B | Frozen Stage 3A scientific artifacts and provenance | Read-only; declaration CSV is the only current-input exception. |
| C | Stage 3A-specific code/config with fixed `04_stage3_semantic` or `reports/stage3` routes | Do not call with Stage 3B paths; use the explicit Stage 3B adapter/config. |
| D | Stage 3B source, routing, contracts, and audits | May write only to the Stage 3B namespaces. |

Major inherited paths:

* Reusable implementation: `src/evo_ms/`, shared tests, and the validated
  Soot/optimization components.
* Frozen Stage 3A evidence: `data/semantic_inputs/`,
  `results/*/04_stage3_semantic/`, and `reports/stage3/`.
* Stage 3A-specific routes: `experiments/04_stage3_semantic/`,
  `scripts/stage3/`, and `configs/experiments/04_stage3_semantic.yml`.
* Stage 3B namespace: `reports/stage3_method_body/`,
  `scripts/stage3_method_body/`, and the explicit `05_stage3...` config.

The audit CSV classifies 2,282 repository files: 1,378 Group A files, 871
Group B files, 18 Group C files, and 15 Group D files. The path-reference CSV
contains 1,424 matched references. Its 83 high-risk matches are the known
hard-coded Stage 3A routes in `experiments/04_stage3_semantic/`,
`scripts/stage3/`, and the frozen Stage 3A tests/configuration. They are not
called by the new Stage 3B input layer; later embedding, graph, and optimizer
adapters must resolve the explicit Stage 3B config and pass the identity guards
before those components are used.

The only initially modified source was the Soot extractor, which adds an
isolated `method_bodies.csv` output and leaves the existing declaration,
structural, and SSA output contracts untouched. No unknown or generated Stage
3B artifact was found.

## Process and filesystem snapshot

At audit start, the only repository-related process was a `tail -f` viewer on
`results/xerces/04_stage3_semantic/formal/seed_29/run.log` (PID 88676). It was
not a runner and was not stopped. No method-body, embedding, graph, pilot, or
formal process was active. No lock or PID file was present. No partial Stage
3B output directory existed. Disk space was sufficient for later isolated
work (approximately 697 GiB available at audit time).
