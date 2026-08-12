# Deprecated figure artefacts

The following committed files are retained only as historical figure provenance.
They are absent from `configs/visualization/figures.yml` and from the current
figure manifest, so the final visualisation command cannot regenerate them.

- `reports/figures/pdf/cross_stage/cross_stage_partition_overview.pdf`
- `reports/figures/preview/cross_stage/cross_stage_partition_overview.svg`
- `reports/figures/data/cross_stage/cross_stage_partition_overview.csv`
- `reports/figures/data/cross_stage/cross_stage_partition_overview.provenance.json`
- `reports/figures/pdf/cross_stage/xerces_stage13_shared_highest_lowest_clusters.pdf`
- `reports/figures/preview/cross_stage/xerces_stage13_shared_highest_lowest_clusters.svg`
- `reports/figures/data/cross_stage/xerces_stage13_shared_highest_lowest_clusters.provenance.json`
- `reports/figures/data/cross_stage/xerces_cluster_profiles.csv`
- `reports/figures/data/cross_stage/xerces_highest_lowest_clusters.csv`

`cross_stage_partition_overview` was abandoned after the operating-preference
reporting correction. The old Xerces-J Stage 1/Stage 3 figure is superseded by
`stage13_xerces_balance_highest_lowest_clusters`; its historical “shared
profile” framing is not valid for the corrected Stage 3 BALANCE selection.
The two generic Xerces CSVs predate the stage-specific output-path fix and are
retained only as historical derived artefacts; active figures use
`xerces_stage2_*` and `xerces_stage13_balance_*` source data.
