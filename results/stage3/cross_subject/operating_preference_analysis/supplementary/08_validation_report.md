# Supplementary operating-preference validation

Status: **SUPPLEMENTARY DESCRIPTIVE VALIDATION ONLY**.

EasyMock uses Stage 2 seeds 0-9 and Stage 3 seeds 1-10. JFreeChart uses the same stage-specific ranges. No cross-stage pairing, inferential test, correction family, size-effect test, optimiser rerun, embedding regeneration, semantic-graph regeneration, or front regeneration was performed.

## Band size

| subject | stage | n_runs | median_band_size | q1_band_size | q3_band_size | iqr_band_size | min_band_size | max_band_size | band_size_one_count |
|---|---|---|---|---|---|---|---|---|---|
| easymock | stage2 | 10 | 4.5 | 3.25 | 5.0 | 1.75 | 2 | 7 | 0 |
| easymock | stage3 | 10 | 3.0 | 2.25 | 4.0 | 1.75 | 1 | 5 | 1 |
| jfreechart | stage2 | 10 | 2.0 | 1.25 | 3.75 | 2.5 | 1 | 7 | 3 |
| jfreechart | stage3 | 10 | 4.5 | 4.0 | 5.0 | 1.0 | 3 | 5 | 0 |

## BALANCE versus SEMANTIC within each stage

| subject | stage | n_within_stage_pairs | same_partition_count | different_partition_count | median_ari | median_nmi | balance_median_weighted_modularity | semantic_median_weighted_modularity | median_delta_weighted_modularity_semantic_minus_balance | balance_median_coupling | semantic_median_coupling | median_delta_coupling_semantic_minus_balance | balance_median_cohesion | semantic_median_cohesion | median_delta_cohesion_semantic_minus_balance | balance_median_imbalance | semantic_median_imbalance | median_delta_imbalance_semantic_minus_balance | balance_median_f_semantic | semantic_median_f_semantic | median_delta_f_semantic_semantic_minus_balance | balance_median_cluster_count | semantic_median_cluster_count | median_delta_cluster_count_semantic_minus_balance | balance_median_relative_modularity_loss | semantic_median_relative_modularity_loss | median_delta_relative_modularity_loss_semantic_minus_balance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| easymock | stage2 | 10 | 0 | 10 | 0.9069002302790181 | 0.9184291337292714 | 0.568668837360081 | 0.5918744133618934 | 0.022841012863132726 | 0.27292576419213976 | 0.24454148471615722 | -0.026928675400291105 | 1.9892639010820827 | 2.003585542809681 | -0.04917107767421236 | 0.7172995498695748 | 0.8229653180542608 | 0.11501000482049983 | 0.43744844546113065 | 0.4145557224503343 | -0.028159587791200036 | 11.0 | 12.0 | 1.0 | 0.042710770762217125 | 0.0 | -0.038300652259548096 |
| easymock | stage3 | 10 | 3 | 7 | 0.9294130752664493 | 0.9404572246662711 | 0.5702716968699211 | 0.5846463168131798 | 0.011280137042899208 | 0.2711062590975255 | 0.2529112081513828 | -0.012372634643377012 | 2.0231196294127325 | 2.005814618882801 | -0.0002747406914072048 | 0.7552774490432952 | 0.8042778281753793 | 0.06506688467438199 | 0.4290877501774722 | 0.4000808756127309 | -0.018964262054948722 | 12.0 | 12.0 | 0.0 | 0.025683527972034194 | 0.0 | -0.018914949565020045 |
| jfreechart | stage2 | 10 | 4 | 6 | 0.9552385716434387 | 0.9612042824417706 | 0.4882520054537086 | 0.5118187745836811 | 0.014339671205460786 | 0.3726878711350761 | 0.3511876322435329 | -0.014145792096102644 | 0.7692511559749946 | 0.7032075943897773 | -0.010491425848479896 | 1.0893331982140229 | 1.1714321738002247 | 0.07990206717943343 | 0.41432347125699703 | 0.3699897886261718 | -0.028457283479519924 | 20.0 | 21.0 | 0.5 | 0.03287252343202872 | 0.0 | -0.03287252343202872 |
| jfreechart | stage3 | 10 | 0 | 10 | 0.9660255623545426 | 0.9609023956163516 | 0.5013063828777287 | 0.5198203735313636 | 0.019084225794592236 | 0.36302982731554156 | 0.3419732441471572 | -0.021414920483243477 | 0.7839795976701276 | 0.6757099496976144 | -0.04410895832405898 | 1.0572836571391 | 1.2448556824714319 | 0.14435002863605229 | 0.388996539814222 | 0.3631156083831097 | -0.026523792547964886 | 19.5 | 22.5 | 2.5 | 0.03667390703517355 | 0.0 | -0.03667390703517355 |

## Mechanism summary

| Subject | Stage | Median band size | BALANCE f_semantic | SEMANTIC f_semantic | SEMANTIC-minus-BALANCE f_semantic | BALANCE cohesion | SEMANTIC cohesion | BALANCE-minus-SEMANTIC cohesion | same BALANCE/SEMANTIC partition count | median modularity loss under BALANCE | median modularity loss under SEMANTIC |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EasyMock | stage2 | 4.5 | 0.43744844546113065 | 0.4145557224503343 | -0.028159587791200036 | 1.9892639010820827 | 2.003585542809681 | -0.0143216417275982 | 0 | 0.042710770762217125 | 0.0 |
| EasyMock | stage3 | 3.0 | 0.4290877501774722 | 0.4000808756127309 | -0.018964262054948722 | 2.0231196294127325 | 2.005814618882801 | 0.017305010529931497 | 3 | 0.025683527972034194 | 0.0 |
| JFreeChart | stage2 | 2.0 | 0.41432347125699703 | 0.3699897886261718 | -0.028457283479519924 | 0.7692511559749946 | 0.7032075943897773 | 0.06604356158521729 | 4 | 0.03287252343202872 | 0.0 |
| JFreeChart | stage3 | 4.5 | 0.388996539814222 | 0.3631156083831097 | -0.026523792547964886 | 0.7839795976701276 | 0.6757099496976144 | 0.10826964797251315 | 0 | 0.03667390703517355 | 0.0 |

Stage 2 front-level f_semantic was newly evaluated from frozen partitions and frozen semantic graphs. No retained Stage 2 f_semantic reference values exist for these subjects; all 20 retained selected structural records were cross-checked instead. Stage 3 post-hoc metrics were evaluated in memory from frozen projected partitions and cross-checked against all 20 retained runtime selected-solution records.
