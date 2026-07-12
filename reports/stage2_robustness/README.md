# Stage 2：基于原始结构图的 NSGA-II

本阶段只使用 `G_raw`。输入为 `class_nodes.csv` 与 `structural_dependencies.csv`，通过 `build_raw_edges` 聚合为无向加权图；不会读取或使用 SSA 边、`G_ssa` 或 SSA lambda。

## 算法

优化器为 pymoo NSGA-II，正式配置固定为 population size `100`、generations `100`、crossover probability `0.9`、mutation probability `1.0`、`eliminate_duplicates=True`。每个正式 seed 独立创建 problem、algorithm、population 与 RNG；正式 seeds 为 `0..29`。

优化目标为：最小化 coupling `W_external / W_total`，最大化 cohesion（簇内加权密度的簇均值），最小化 imbalance `std(cluster_sizes) / mean(cluster_sizes)`。pymoo 采用最小化空间，因此内部第二目标为 negative cohesion。weighted modularity、Hypervolume 和 DayTrader 的参考分区指标均为 post-hoc 指标，不参与优化。

repair 与约束保持 `cluster_count >= 2`、`max_cluster_ratio <= 0.4`、`singleton_ratio <= 0.15`。初始种群采用 `structure_aware_seeded`，保留 Stage 1 `raw_reference_leiden` 注入及其确定性扰动。

## Front 与最终解

正式 robustness 输出优先采用最终 feasible population 的重新计算非支配集。每个 seed 在自己的 front 内选择最终解：先选择 feasible 解，再最大化 weighted modularity；并列时依次偏好非注入解、更低 coupling、更高 cohesion、更低 imbalance，最后以 canonical label vector 排序。不会合并 30 个 front 后再选一个解。

Hypervolume 使用理论 bounds，并在 pymoo 最小化目标顺序 `[coupling, negative_cohesion, imbalance]` 中归一化；reference point 固定为 `[1.1, 1.1, 1.1]`。正式运行只接受 `bounds_source: theoretical` 与 `calibration_status: not_required`。

## 操作脚本

所有脚本位于 `scripts/02_stage2_nsga_structure_only/`，默认使用已知的锁定 Codex runtime；也可以通过 `PYTHON` 或 `STAGE2_PYTHON` 显式覆盖。脚本会校验 Python、numpy、pandas、pymoo、igraph 与 leidenalg 的版本，并要求在 `stage2-nsga` worktree 执行。

```bash
scripts/02_stage2_nsga_structure_only/check_environment.sh
scripts/02_stage2_nsga_structure_only/generate_theoretical_bounds.sh daytrader
scripts/02_stage2_nsga_structure_only/verify_seed.sh daytrader 0
scripts/02_stage2_nsga_structure_only/run_smoke_subject.sh daytrader 0,1
scripts/02_stage2_nsga_structure_only/run_formal_subject.sh jpetstore --resume
scripts/02_stage2_nsga_structure_only/run_tests.sh
```

formal 输出写入 `results/<subject>/03_stage2_nsga/robustness/`；smoke 输出明确写入 `robustness_smoke/`，不会覆盖正式结果。每个正式 seed 保存 complete Pareto front、压缩 label 分区、selected solution、selected partition、run metrics 和 metadata。
