# Vectorized/reference equivalence

The production vectorized metrics were compared with the slow direct reference
implementation for all three subjects, all three stages, seeds 0, 7, and 29,
and deterministic selected/first/last plus available budgeted, knee, and
extreme candidate IDs. Selection equivalence was checked for modularity,
balance at 0% and 5%, semantic at 5%, and projected structural balance at 5%.

- metric and semantic rows: 2126
- maximum absolute difference: 2.3425705819590803e-14
- metric/semantic mismatches: 0
- selection mismatches: 0
- q-loss/eligibility and row ordering: checked through the same fixed candidate ordering and `q_loss <= budget + 1e-12`

Result: **PASS**. No production scientific report was rewritten.
