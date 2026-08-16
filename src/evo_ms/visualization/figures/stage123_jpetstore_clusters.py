"""Appendix comparison of JPetStore cluster modularity contributions."""

from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
import tempfile

import pandas as pd

from evo_ms.visualization.dot import write_dot
from evo_ms.visualization.figures.stage123_daytrader_clusters import (
    BoundaryAggregate,
    BoundaryConnection,
    ClusterProfile,
    FigureData,
    _canonical_partition,
    _relative,
    boundary_aggregation_csv,
    figure_dot,
    profiles_csv,
    selected_csv,
)
from evo_ms.visualization.layout import render_graphviz
from evo_ms.visualization.model import GraphvizRenderRequest, GraphvizRenderResult, VisualizationConfig
from evo_ms.visualization.operating_preference import (
    balance_partition_medoid,
    fixed_balance_selection,
    representative_provenance,
)
from evo_ms.visualization.provenance import build_provenance, sha256_file, write_json_atomic

FIGURE_ID = "stage123_jpetstore_highest_lowest_clusters"
BASENAME = "jpetstore_highest_lowest_clusters"
DIRECTORY = "cross_stage"
EXPECTED_CLASSES = 24
STAGE2_SEED = 1
STAGE2_SOLUTION = "seed1_solution007"
STAGE3_SEED = 4
STAGE3_SOLUTION = "seed4_solution000"


def _partitions(root: Path):
    stage1_path = "results/stage1/subjects/jpetstore/leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv"
    stage1 = pd.read_csv(root / stage1_path)
    q1 = float(pd.read_csv(root / "results/stage1/subjects/jpetstore/leiden_baseline/raw_reference_leiden/metrics/stage1_metrics.csv").iloc[0].modularity)
    stage2 = fixed_balance_selection(root, "jpetstore", "stage2", STAGE2_SEED)
    stage3 = balance_partition_medoid(root, "jpetstore", "stage3")
    if stage2.solution_id != STAGE2_SOLUTION:
        raise ValueError("expected JPetStore Stage 2 primary Balance-preference representative changed")
    if (stage3.seed, stage3.solution_id) != (STAGE3_SEED, STAGE3_SOLUTION):
        raise ValueError("expected JPetStore Stage 3 primary Balance-preference medoid changed")
    return ((1, 42, "stage1_seed42", stage1_path, stage1, q1),
            (2, stage2.seed, stage2.solution_id, stage2.partition_source, stage2.partition, stage2.weighted_modularity),
            (3, stage3.seed, stage3.solution_id, stage3.partition_source, stage3.partition, stage3.weighted_modularity))


def prepare_figure_data(config: VisualizationConfig) -> FigureData:
    root = config.repository_root
    nodes = pd.read_csv(root / "data/extracted/jpetstore/class_nodes.csv")
    expected = set(nodes.class_id.astype(str))
    if len(nodes) != EXPECTED_CLASSES or len(expected) != EXPECTED_CLASSES:
        raise ValueError("JPetStore scope must contain exactly 24 unique classes")
    edges = pd.read_csv(root / "results/stage1/subjects/jpetstore/leiden_baseline/raw_reference_leiden/graph/stage1_edges.csv")
    pairs = [tuple(sorted((str(row.source), str(row.target)))) for row in edges.itertuples()]
    if any(a == b for a, b in pairs) or len(pairs) != len(set(pairs)):
        raise ValueError("JPetStore raw graph contains a self-loop or duplicate undirected edge")
    total = float(edges.raw_weight.sum())
    degree = {class_id: 0.0 for class_id in expected}
    for row in edges.itertuples():
        degree[str(row.source)] += float(row.raw_weight); degree[str(row.target)] += float(row.raw_weight)
    profiles=[]; formal=[]
    for stage, seed, solution, source, raw_partition, formal_q in _partitions(root):
        ids = raw_partition.class_id.astype(str)
        if ids.duplicated().any() or set(ids) != expected:
            raise ValueError(f"JPetStore Stage {stage} partition does not cover all 24 classes exactly once")
        partition = _canonical_partition(raw_partition)
        if not partition.equals(_canonical_partition(raw_partition.sample(frac=1, random_state=42))):
            raise ValueError("JPetStore cluster canonicalisation is not deterministic")
        cluster_by_class = dict(zip(partition.class_id.astype(str), partition.cluster_id.astype(str), strict=True))
        for cluster_id, group in partition.groupby("cluster_id", sort=True):
            members=tuple(sorted(group.class_id.astype(str))); member_set=set(members)
            internal=tuple(sorted((min(str(e.source),str(e.target)),max(str(e.source),str(e.target)),float(e.raw_weight)) for e in edges.itertuples() if str(e.source) in member_set and str(e.target) in member_set))
            boundary=tuple(sorted((min(str(e.source),str(e.target)),max(str(e.source),str(e.target)),float(e.raw_weight)) for e in edges.itertuples() if (str(e.source) in member_set) ^ (str(e.target) in member_set)))
            external=tuple(sorted({node for left,right,_weight in boundary for node in (left,right)}-member_set))
            grouped: dict[str,list[tuple[str,str,float]]]={}
            for left,right,weight in boundary:
                focal,outside=(left,right) if left in member_set else (right,left)
                grouped.setdefault(cluster_by_class[outside],[]).append((focal,outside,weight))
            aggregates=[]
            for external_cluster_id in sorted(grouped):
                records=grouped[external_cluster_id]; by_focal: dict[str,list[tuple[str,float]]]={}
                for focal,outside,weight in records: by_focal.setdefault(focal,[]).append((outside,weight))
                connections=tuple(BoundaryConnection(focal,tuple(sorted({outside for outside,_weight in by_focal[focal]})),len(by_focal[focal]),sum(weight for _outside,weight in by_focal[focal])) for focal in sorted(by_focal))
                aggregates.append(BoundaryAggregate(external_cluster_id,tuple(sorted({outside for _focal,outside,_weight in records})),len(records),sum(weight for _focal,_outside,weight in records),tuple(sorted(by_focal)),connections))
            iw=sum(e[2] for e in internal); bw=sum(e[2] for e in boundary); strength=sum(degree[class_id] for class_id in members)
            q=iw/total-(strength/(2*total))**2
            profiles.append(ClusterProfile(stage,seed,solution,source,str(cluster_id),members,internal,boundary,external,iw,bw,strength,q,tuple(aggregates)))
        if abs(sum(profile.contribution for profile in profiles if profile.stage==stage)-formal_q)>1e-12:
            raise ValueError(f"JPetStore Stage {stage} contributions do not reconstruct formal modularity")
        formal.append((stage,formal_q))
    selected=[]
    for stage in (1,2,3):
        candidates=[profile for profile in profiles if profile.stage==stage]
        selected.extend((("highest",sorted(candidates,key=lambda p:(-p.contribution,p.rank_key))[0]),("lowest",sorted(candidates,key=lambda p:(p.contribution,p.rank_key))[0])))
    return FigureData(tuple(profiles),tuple(selected),tuple(formal))


def _targets(config: VisualizationConfig, output_root: Path | None):
    if output_root is None:
        targets={"profiles":config.output.data/DIRECTORY/"jpetstore_cluster_profiles.csv","selected":config.output.data/DIRECTORY/"jpetstore_highest_lowest_clusters.csv","aggregation":config.output.data/DIRECTORY/"jpetstore_boundary_aggregation.csv","dot":config.output.dot/DIRECTORY/f"{BASENAME}.dot","svg":config.output.svg/DIRECTORY/f"{BASENAME}.svg","pdf":config.output.pdf/DIRECTORY/f"{BASENAME}.pdf","provenance":config.output.data/DIRECTORY/f"{BASENAME}.provenance.json"}
        return targets,config.repository_root/"reports/figures/manifest.json",None
    root=output_root.resolve(); targets={"profiles":root/"data"/DIRECTORY/"jpetstore_cluster_profiles.csv","selected":root/"data"/DIRECTORY/"jpetstore_highest_lowest_clusters.csv","aggregation":root/"data"/DIRECTORY/"jpetstore_boundary_aggregation.csv","dot":root/"source"/DIRECTORY/f"{BASENAME}.dot","svg":root/"preview"/DIRECTORY/f"{BASENAME}.svg","pdf":root/"pdf"/DIRECTORY/f"{BASENAME}.pdf","provenance":root/"data"/DIRECTORY/f"{BASENAME}.provenance.json"}
    return targets,root/"manifest.json",root


def build_figure(config: VisualizationConfig, *, output_root: str|Path|None=None, manifest_path: str|Path|None=None, generated_at: str|None=None, git_commit: str|None=None, git_dirty: bool|None=None, renderer: Callable[[GraphvizRenderRequest],GraphvizRenderResult]=render_graphviz) -> dict[str,Path]:
    spec=config.figures.get(FIGURE_ID)
    if spec is None or not spec.enabled or spec.formats != ("dot","svg","pdf"): raise ValueError(f"figure is not correctly registered: {FIGURE_ID}")
    targets,default_manifest,artifact_root=_targets(config,None if output_root is None else Path(output_root)); manifest=default_manifest if manifest_path is None else Path(manifest_path)
    for path in (*targets.values(),manifest): path.parent.mkdir(parents=True,exist_ok=True)
    data=prepare_figure_data(config); staging_parent=artifact_root or config.repository_root/"reports/figures"
    with tempfile.TemporaryDirectory(prefix=f".{FIGURE_ID}.",dir=staging_parent) as temporary:
        stage=Path(temporary); staged={name:stage/f"figure.{name}" for name in targets}; staged["provenance"]=stage/"figure.provenance.json"
        staged["profiles"].write_text(profiles_csv(data),encoding="utf-8",newline="\n"); staged["selected"].write_text(selected_csv(data),encoding="utf-8",newline="\n"); staged["aggregation"].write_text(boundary_aggregation_csv(data),encoding="utf-8",newline="\n")
        write_dot(staged["dot"],figure_dot(config,data,figure_id=FIGURE_ID,comparison_note="Stage 2 and Stage 3 representatives use the primary Balance preference."))
        renders=[renderer(GraphvizRenderRequest(staged["dot"],staged[fmt],fmt,"neato",fixed_coordinates=True)) for fmt in ("svg","pdf")]
        for name in ("profiles","selected","aggregation","dot","svg","pdf"):
            if not staged[name].is_file() or not staged[name].stat().st_size: raise ValueError(f"missing staged {name}")
        commands=tuple(("neato","-n2",f"-T{fmt}",str(targets["dot"]),"-o",str(targets[fmt])) for fmt in ("svg","pdf"))
        record=build_provenance(figure_id=FIGURE_ID,stage=spec.stage,generator="src/"+spec.generator.replace(".","/")+".py",repository_root=config.repository_root,input_files=(config.repository_root/path for path in spec.inputs),config_files=(config.figures_config_path,config.style_config_path),dot_path=staged["dot"],graphviz_engine="neato",graphviz_version=renders[0].version,render_commands=commands,generated_outputs=targets.values(),artifact_root=artifact_root,generated_at=generated_at,git_commit=git_commit,git_dirty=git_dirty)
        write_json_atomic(staged["provenance"], {
            **record.as_dict(),
            "operating_profile_representatives": representative_provenance(
                fixed_balance_selection(config.repository_root, "jpetstore", "stage2", STAGE2_SEED),
                balance_partition_medoid(config.repository_root, "jpetstore", "stage3"),
            ),
        })
        document=json.loads(manifest.read_text()) if manifest.exists() else {"schema_version":1,"figures":{}}
        if document.get("schema_version")!=1 or not isinstance(document.get("figures"),dict): raise ValueError("invalid figure manifest")
        document["figures"][FIGURE_ID]={"destination":spec.destination,"formats":list(spec.formats),"generated_at":record.generated_at,"generator":spec.generator,"inputs":list(spec.inputs),"metadata":dict(spec.metadata or {}),"outputs":{name:_relative(path,config.repository_root,artifact_root) for name,path in sorted(targets.items())},"sha256":{name:sha256_file(path) for name,path in sorted(staged.items())},"stage":spec.stage,"title":spec.title}
        staged_manifest=stage/"manifest.json"; write_json_atomic(staged_manifest,document)
        for name in targets: os.replace(staged[name],targets[name])
        os.replace(staged_manifest,manifest)
    return targets
