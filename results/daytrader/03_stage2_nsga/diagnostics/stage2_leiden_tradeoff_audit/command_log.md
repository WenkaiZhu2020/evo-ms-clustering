# Command Log

## Superseded Diagnostic

This audit used the earlier `robustness/` outputs and a 2,994-row DayTrader
front, not `robustness_final_30seeds/`. It is retained only as superseded
provenance and is not used in final Stage 2 conclusions. The final-aligned
diagnostics under `results/cross_subject/03_stage2_nsga/final_statistics/`
are authoritative.

This file records the data-generation commands and the shell command classes
used to inspect definitions, inputs, outputs, and the worktree. Read-only
inline Python checks are summarized as `...`; they did not create or modify
data. All data generation used the specified Codex Python interpreter.

```bash
git -C /Users/zhuwenkai/Desktop/evo-ms-clustering-stage2-rawonly status --short --branch
git -C /Users/zhuwenkai/Desktop/evo-ms-clustering-stage2-rawonly branch --show-current
git -C /Users/zhuwenkai/Desktop/evo-ms-clustering-stage2-rawonly rev-parse HEAD
sed -n '1,520p' /Users/zhuwenkai/.codex/attachments/1bd55852-805b-4a41-b966-082cdbc55aed/pasted-text.txt
find results/daytrader/03_stage2_nsga -maxdepth 3 -type f | sort
find results -type f \( -iname '*leiden*' -o -iname '*sweep*' -o -iname '*calib*' -o -iname '*resolution*' \) | sort
rg -n "def (evaluate_structural_objectives|weighted_modularity|calculate_reference_metrics|run_leiden_baseline)|weighted_modularity|negative_cohesion|admissibility_violation" src experiments/01_stage1_leiden_baseline experiments/02_stage2_nsga_structure_only
find results/stage2_robustness -maxdepth 2 -type f | sort
find results/daytrader/00_pre_experiment results/daytrader/01_stage1_leiden_baseline results/daytrader/02_stage1_seed_robustness -maxdepth 4 -type f | sort
python3 - <<'PY' ... inspect CSV headers ... PY
sed -n '1,190p' src/evo_ms/optimization/objectives.py
sed -n '630,710p' src/evo_ms/evaluation/partition_metrics.py
sed -n '1,130p' src/evo_ms/clustering/leiden_baseline.py
sed -n '330,530p' experiments/02_stage2_nsga_structure_only/run.py
sed -n '1,205p' experiments/02_stage2_nsga_structure_only/run_robustness.py
git show stage1-baseline:results/daytrader/02_stage1_seed_robustness/per_seed_partitions/leiden_seed_00.csv
git ls-tree -r --name-only stage1-baseline -- results/daytrader/02_stage1_seed_robustness/per_seed_partitions
rg -n "resolution|leiden|seed|sweep" experiments configs/experiments scripts src/evo_ms --glob '*.py' --glob '*.yml' --glob '*.yaml'
git log --oneline --all -- results/daytrader/00_pre_experiment/calibration/weight_sweep_summary.csv results/daytrader/02_stage1_seed_robustness
/Users/zhuwenkai/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ... inspect input/result CSV schemas and values ... PY
sed -n '1,340p' experiments/01_stage1_leiden_baseline/run_seed_robustness.py
sed -n '1,150p' src/evo_ms/graph/raw_graph_builder.py
sed -n '1,85p' configs/experiments/02_stage2_nsga_structure_only.yml
sed -n '180,210p' experiments/02_stage2_nsga_structure_only/run.py
cat results/daytrader/03_stage2_nsga/robustness/robustness_manifest.json
cat results/daytrader/03_stage2_nsga/robustness/seed_00/run_metadata.json
cat results/daytrader/03_stage2_nsga/robustness/seed_00/run_metrics.json
rg -n "save_history|history|Callback|callback|hypervolume|n_gen|n_iter" experiments/02_stage2_nsga_structure_only src/evo_ms/optimization tests --glob '*.py'
/Users/zhuwenkai/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 /tmp/stage2_leiden_tradeoff_audit.py --root /Users/zhuwenkai/Desktop/evo-ms-clustering-stage2-rawonly --output-dir /Users/zhuwenkai/Desktop/evo-ms-clustering-stage2-rawonly/results/daytrader/03_stage2_nsga/diagnostics/stage2_leiden_tradeoff_audit
/Users/zhuwenkai/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 /tmp/stage2_structural_sensitivity.py --root /Users/zhuwenkai/Desktop/evo-ms-clustering-stage2-rawonly --output-dir /Users/zhuwenkai/Desktop/evo-ms-clustering-stage2-rawonly/results/daytrader/03_stage2_nsga/diagnostics/stage2_leiden_tradeoff_audit
/Users/zhuwenkai/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ... validate output tables, direct paired statistics, input hashes, and front counts ... PY
git status --short --branch
git diff --stat
git diff --name-only
```

The analysis runner was created outside the repository at:

```text
/tmp/stage2_leiden_tradeoff_audit.py
```

It was used only to create the files in this diagnostic directory.  No formal
result, source-code, configuration, or Git-history file was modified.
