"""Three landscape Xerces-J cluster-contribution appendix pages."""

from __future__ import annotations

from collections.abc import Callable
import csv
import json
import math
import os
from pathlib import Path
import tempfile

import pandas as pd

from evo_ms.visualization.dot import dot_quote, stable_attributes, write_dot
from evo_ms.visualization.figures.stage123_daytrader_clusters import (
    BoundaryAggregate, BoundaryConnection, ClusterProfile, FigureData,
    _canonical_partition, _relative, profiles_csv, selected_csv,
)
from evo_ms.visualization.layout import render_graphviz
from evo_ms.visualization.model import GraphvizRenderRequest, GraphvizRenderResult, VisualizationConfig
from evo_ms.visualization.provenance import build_provenance, sha256_file, write_json_atomic, write_provenance

FIGURE_IDS={1:"stage1_xerces_highest_lowest_clusters",2:"stage2_xerces_highest_lowest_clusters",3:"stage3_xerces_highest_lowest_clusters"}
BASENAMES={stage:f"xerces_stage{stage}_highest_lowest_clusters" for stage in FIGURE_IDS}
EXPECTED={1:(42,"stage1_seed42","C11",118,624,"C07",1,12),2:(21,"seed21_solution022","C13",115,570,"C27",2,16),3:(22,"seed22_solution015","C11",118,624,"C07",1,12)}
DIRECTORY="cross_stage"


def _partitions(root: Path):
    p1="results/stage1/subjects/xerces-j/leiden_baseline/raw_reference_leiden/clustering/stage1_clusters.csv"
    p2="results/stage2/subjects/xerces-j/nsga/robustness_final_30seeds/seed_21/pareto_labels.csv.xz"
    p3="results/stage3/subjects/xerces-j/declaration_method_body/formal/seed_22/selected_partition.csv"
    stage1=pd.read_csv(root/p1); q1=float(pd.read_csv(root/"results/stage1/subjects/xerces-j/leiden_baseline/raw_reference_leiden/metrics/stage1_metrics.csv").iloc[0].modularity)
    canonical=pd.read_csv(root/"results/stage2/cross_subject/operating_profile/canonical_operating_solution_per_seed.csv")
    record=canonical.loc[(canonical.subject=="xerces-j")&(canonical.seed==21)]
    if len(record)!=1 or str(record.iloc[0].solution_id)!="seed21_solution022": raise ValueError("Xerces-J Stage 2 representative changed")
    labels=pd.read_csv(root/p2); stage2=labels.loc[labels.solution_id=="seed21_solution022",["class_id","class_name","cluster_id"]].copy()
    payload=json.loads((root/"results/stage3/subjects/xerces-j/declaration_method_body/formal/seed_22/selected_solution.json").read_text())
    if int(payload["seed"])!=22 or payload["selected_four_objective_row"]["solution_id"]!="seed22_solution015": raise ValueError("Xerces-J Stage 3 representative changed")
    stage3=pd.read_csv(root/p3); posthoc=pd.read_csv(root/"results/stage3/subjects/xerces-j/declaration_method_body/formal/seed_22/posthoc_metrics.csv")
    q3=posthoc.loc[posthoc.solution_id=="seed22_solution015","weighted_modularity"]
    if len(q3)!=1: raise ValueError("Xerces-J Stage 3 modularity is not unique")
    return ((1,42,"stage1_seed42",p1,stage1,q1),(2,21,"seed21_solution022",p2,stage2,float(record.iloc[0].weighted_modularity)),(3,22,"seed22_solution015",p3,stage3,float(q3.iloc[0])))


def prepare_figure_data(config: VisualizationConfig) -> FigureData:
    root=config.repository_root; nodes=pd.read_csv(root/"data/extracted/xerces-j/class_nodes.csv"); expected=set(nodes.class_id.astype(str))
    if len(nodes)!=814 or len(expected)!=814: raise ValueError("Xerces-J scope must contain 814 unique classes")
    edges=pd.read_csv(root/"results/stage1/subjects/xerces-j/leiden_baseline/raw_reference_leiden/graph/stage1_edges.csv")
    pairs=[tuple(sorted((str(e.source),str(e.target)))) for e in edges.itertuples()]
    if any(a==b for a,b in pairs) or len(pairs)!=len(set(pairs)): raise ValueError("Xerces-J raw graph has invalid undirected edges")
    total=float(edges.raw_weight.sum());degree={c:0.0 for c in expected}
    for e in edges.itertuples(): degree[str(e.source)]+=float(e.raw_weight);degree[str(e.target)]+=float(e.raw_weight)
    profiles=[];formal=[]
    for stage,seed,solution,source,raw,formal_q in _partitions(root):
        ids=raw.class_id.astype(str)
        if len(ids)!=814 or ids.duplicated().any() or set(ids)!=expected: raise ValueError(f"Xerces-J Stage {stage} scope changed")
        partition=_canonical_partition(raw); cmap=dict(zip(partition.class_id.astype(str),partition.cluster_id.astype(str),strict=True))
        for cid,group in partition.groupby("cluster_id",sort=True):
            members=tuple(sorted(group.class_id.astype(str)));member_set=set(members);internal=[];boundary=[]
            for e in edges.itertuples():
                a,b,w=str(e.source),str(e.target),float(e.raw_weight)
                if a in member_set and b in member_set: internal.append((min(a,b),max(a,b),w))
                elif (a in member_set)^(b in member_set): boundary.append((min(a,b),max(a,b),w))
            grouped={}
            for a,b,w in boundary:
                focal,outside=(a,b) if a in member_set else (b,a);grouped.setdefault(cmap[outside],[]).append((focal,outside,w))
            aggregates=[]
            for dest in sorted(grouped):
                records=grouped[dest];by_focal={}
                for focal,outside,w in records: by_focal.setdefault(focal,[]).append((outside,w))
                connections=tuple(BoundaryConnection(focal,tuple(sorted({outside for outside,_w in by_focal[focal]})),len(by_focal[focal]),sum(w for _outside,w in by_focal[focal])) for focal in sorted(by_focal))
                aggregates.append(BoundaryAggregate(dest,tuple(sorted({outside for _f,outside,_w in records})),len(records),sum(w for _f,_o,w in records),tuple(sorted(by_focal)),connections))
            iw=sum(x[2] for x in internal);bw=sum(x[2] for x in boundary);strength=sum(degree[c] for c in members);q=iw/total-(strength/(2*total))**2
            profiles.append(ClusterProfile(stage,seed,solution,source,str(cid),members,tuple(sorted(internal)),tuple(sorted(boundary)),tuple(sorted({x for a,b,_w in boundary for x in (a,b)}-member_set)),iw,bw,strength,q,tuple(aggregates)))
        if abs(sum(p.contribution for p in profiles if p.stage==stage)-formal_q)>1e-12: raise ValueError(f"Xerces-J Stage {stage} modularity reconstruction failed")
        formal.append((stage,formal_q))
    selected=[]
    for stage in (1,2,3):
        candidates=[p for p in profiles if p.stage==stage];selected.extend((("highest",sorted(candidates,key=lambda p:(-p.contribution,p.rank_key))[0]),("lowest",sorted(candidates,key=lambda p:(p.contribution,p.rank_key))[0])))
    data=FigureData(tuple(profiles),tuple(selected),tuple(formal))
    for stage,(seed,solution,hcid,hn,he,lcid,ln,destinations) in EXPECTED.items():
        chosen={role:p for role,p in data.selected if p.stage==stage};high=chosen["highest"];low=chosen["lowest"]
        if (high.seed,high.solution_id,high.cluster_id,len(high.members),len(high.internal_edges),low.cluster_id,len(low.members),len(high.boundary_aggregates))!=(seed,solution,hcid,hn,he,lcid,ln,destinations): raise ValueError(f"accepted Xerces-J Stage {stage} selection changed")
    return data


def focal_node_map(config: VisualizationConfig, stage: int, high: ClusterProfile):
    packages=pd.read_csv(config.repository_root/"data/extracted/xerces-j/class_nodes.csv").set_index("class_id")["package"].astype(str)
    return tuple({"stage":stage,"short_id":f"F{i:03d}","class_id":c,"simple_name":c.rsplit(".",1)[-1],"fully_qualified_name":c,"package":packages[c],"canonical_order":i} for i,c in enumerate(high.members,1))


def _csv(fields,rows):
    from io import StringIO
    buffer=StringIO(newline="");writer=csv.DictWriter(buffer,fieldnames=fields,lineterminator="\n");writer.writeheader();writer.writerows(rows);return buffer.getvalue()


def node_map_csv(rows): return _csv(("stage","short_id","class_id","simple_name","fully_qualified_name","package","canonical_order"),rows)


def boundary_csv(stage: int, selected):
    rows=[]
    for role,profile in selected:
        for a in profile.boundary_aggregates:
            rows.append({"stage":stage,"focal_cluster_id":profile.cluster_id,"external_cluster_id":a.external_cluster_id,"external_class_count":len(a.external_classes),"external_classes":json.dumps(a.external_classes,separators=(",",":")),"boundary_edge_count":a.boundary_edge_count,"boundary_weight":format(a.boundary_weight,".12g"),"connected_focal_classes":json.dumps(a.connected_focal_classes,separators=(",",":"))})
    return _csv(("stage","focal_cluster_id","external_cluster_id","external_class_count","external_classes","boundary_edge_count","boundary_weight","connected_focal_classes"),rows)


def _package_layout(mapping):
    packages={}
    for row in mapping: packages.setdefault(row["package"],[]).append(row)
    specs=[(package,tuple(rows),20+math.ceil(len(rows)/8)*15) for package,rows in packages.items()];columns=[[],[]];heights=[0,0]
    for item in sorted(specs,key=lambda x:(-x[2],x[0])):
        col=min(range(2),key=lambda x:(heights[x],x));columns[col].append(item);heights[col]+=item[2]+5
    positions={};regions=[]
    for col,items in enumerate(columns):
        x0=30+col*245;top=425;scale=min(1.0,330/sum(h+5 for _p,_r,h in items))
        for package,rows,height in items:
            h=height*scale;bottom=top-h;regions.append((package,x0+115,(top+bottom)/2,225,h));sy=max(11,min(15,(h-17)/max(1,math.ceil(len(rows)/8))))
            for i,row in enumerate(rows): positions[row["class_id"]]=(x0+12+(i%8)*26,top-14-(i//8)*sy)
            top=bottom-5
    return positions,regions


def _width(value,maximum): return 0.45+(2.2-0.45)*math.sqrt(value/maximum)


def figure_dot(config: VisualizationConfig, stage: int, high: ClusterProfile, low: ClusterProfile, mapping) -> str:
    spec=config.figures[FIGURE_IDS[stage]];pos,regions=_package_layout(mapping);short={r["class_id"]:r["short_id"] for r in mapping};summaries={a.external_cluster_id:(532+(i%2)*55,420-(i//2)*43) for i,a in enumerate(high.boundary_aggregates)}
    plain={"color":"transparent","fillcolor":"transparent","fontname":"Helvetica","shape":"plain","style":""}
    lines=[f"graph {dot_quote(spec.title)} {{","  graph "+stable_attributes({"bb":"0,0,800,540","bgcolor":"white","margin":0,"outputorder":"edgesfirst","overlap":True,"pad":0.03,"size":"11.111,7.5!","splines":"line","start":42})+";","  node "+stable_attributes({"fontname":"Helvetica","fontsize":5.2,"height":0.14,"margin":"0.015,0.008","shape":"box","style":"rounded,filled","width":0.22})+";","  edge "+stable_attributes({"fontname":"Helvetica","fontsize":5})+";",
      '  "page_title" '+stable_attributes({**plain,"fontsize":12,"label":spec.title,"pos":"400,520!"})+";",'  "main_title" '+stable_attributes({**plain,"fontsize":9,"label":f"Highest-contributing cluster {high.cluster_id}","pos":"310,493!"})+";",'  "main_metric" '+stable_attributes({**plain,"fontsize":7,"label":f"n = {len(high.members)}   q_c = {high.contribution:.6f}   W_in = {high.internal_weight:.0f}   W_boundary = {high.boundary_weight:.0f}","pos":"310,477!"})+";",'  "main_border" '+stable_attributes({"color":"#AFAFAF","fixedsize":True,"height":5.5,"label":"","pos":"310,265!","shape":"box","style":"solid","width":8.25})+";"]
    for i,(package,cx,cy,w,h) in enumerate(sorted(regions)):
        lines.extend((f'  "pkg_box_{i:02d}" '+stable_attributes({"color":"#D0D0D0","fixedsize":True,"height":h/72,"label":"","penwidth":0.5,"pos":f"{cx},{cy}!","shape":"box","style":"rounded","width":w/72})+";",f'  "pkg_label_{i:02d}" '+stable_attributes({**plain,"fontsize":5.3,"label":package.replace("org.apache.",""),"pos":f"{cx},{cy+h/2-6}!"})+";"))
    for row in mapping:
        x,y=pos[row["class_id"]];lines.append(f'  {dot_quote("f_"+row["short_id"])} '+stable_attributes({"color":"#0072B2","fillcolor":"#DCEAF7","label":row["short_id"],"penwidth":0.8,"pos":f"{x},{y}!","tooltip":f"{row['fully_qualified_name']} | package: {row['package']}"})+";")
    for a,b,w in high.internal_edges: lines.append(f'  {dot_quote("f_"+short[a])} -- {dot_quote("f_"+short[b])} '+stable_attributes({"color":"#4D4D4D35","penwidth":0.35,"style":"solid","tooltip":f"internal structural weight {w:g}"})+";")
    for a in high.boundary_aggregates:
        x,y=summaries[a.external_cluster_id];lines.append(f'  {dot_quote("x_"+a.external_cluster_id)} '+stable_attributes({"color":"#888888","fillcolor":"#F2F2F2","fontsize":5.2,"label":f"External {a.external_cluster_id}\n{len(a.external_classes)} classes","pos":f"{x},{y}!","shape":"box","style":"rounded,dashed,filled","tooltip":"; ".join(a.external_classes)})+";")
    maximum=max(c.boundary_weight for a in high.boundary_aggregates for c in a.connections)
    for a in high.boundary_aggregates:
        for c in a.connections: lines.append(f'  {dot_quote("f_"+short[c.focal_class])} -- {dot_quote("x_"+a.external_cluster_id)} '+stable_attributes({"color":"#88888870","penwidth":_width(c.boundary_weight,maximum),"style":"dashed","tooltip":f"{c.boundary_edge_count} boundary edges; weight {c.boundary_weight:g}"})+";")
    lines.extend(('  "inset_border" '+stable_attributes({"color":"#AFAFAF","fixedsize":True,"height":2.55,"label":"","pos":"708,386!","shape":"box","style":"solid","width":2.35})+";",'  "inset_title" '+stable_attributes({**plain,"fontsize":8,"label":f"Lowest-contributing cluster {low.cluster_id}","pos":"708,455!"})+";",'  "inset_metric" '+stable_attributes({**plain,"fontsize":6.5,"label":f"n = {len(low.members)}   q_c = {low.contribution:.6f}\nW_in = {low.internal_weight:.0f}   W_boundary = {low.boundary_weight:.0f}","pos":"708,437!"})+";"))
    low_ids={c:f"l_F{i:03d}" for i,c in enumerate(low.members,1)}
    if len(low.members)==1 and not low.boundary_edges:
        c=low.members[0];lines.extend((f'  {dot_quote(low_ids[c])} '+stable_attributes({"color":"#0072B2","fillcolor":"#DCEAF7","fontsize":7,"label":"F001","pos":"708,385!","tooltip":c})+";",'  "isolated_note" '+stable_attributes({**plain,"fontsize":6.5,"label":"Isolated singleton\nNo internal or boundary relations","pos":"708,340!"})+";"))
    else:
        for i,c in enumerate(low.members): lines.append(f'  {dot_quote(low_ids[c])} '+stable_attributes({"color":"#0072B2","fillcolor":"#DCEAF7","fontsize":7,"label":f"F{i+1:03d}","pos":f"665,{398-i*34}!","tooltip":c})+";")
        for i,a in enumerate(low.boundary_aggregates):
            sid="l_x_"+a.external_cluster_id;lines.append(f'  {dot_quote(sid)} '+stable_attributes({"color":"#888888","fillcolor":"#F2F2F2","fontsize":6,"label":f"External {a.external_cluster_id}\n{len(a.external_classes)} classes","pos":f"752,{410-i*48}!","shape":"box","style":"rounded,dashed,filled","tooltip":"; ".join(a.external_classes)})+";")
            for c in a.connections: lines.append(f'  {dot_quote(low_ids[c.focal_class])} -- {dot_quote(sid)} '+stable_attributes({"color":"#888888","penwidth":1.2,"style":"dashed","tooltip":f"{c.boundary_edge_count} edges; weight {c.boundary_weight:g}"})+";")
    lines.extend(('  "legend_title" '+stable_attributes({**plain,"fontsize":7,"label":"Legend","pos":"708,235!"})+";",'  "legend_focal" '+stable_attributes({"color":"#0072B2","fillcolor":"#DCEAF7","label":"F001","pos":"650,205!"})+";",'  "legend_focal_text" '+stable_attributes({**plain,"fontsize":6,"label":"Focal class node","pos":"716,205!"})+";",'  "legend_external" '+stable_attributes({"color":"#888888","fillcolor":"#F2F2F2","label":"External Cxx","pos":"650,178!","shape":"box","style":"rounded,dashed,filled"})+";",'  "legend_external_text" '+stable_attributes({**plain,"fontsize":6,"label":"External-cluster summary","pos":"733,178!"})+";",'  "li1" '+stable_attributes({"label":"","pos":"635,150!","shape":"point","width":0.03})+";",'  "li2" '+stable_attributes({"label":"","pos":"670,150!","shape":"point","width":0.03})+";",'  "li1" -- "li2" '+stable_attributes({"color":"#4D4D4D","style":"solid"})+";",'  "lit" '+stable_attributes({**plain,"fontsize":6,"label":"Solid internal relation","pos":"730,150!"})+";",'  "lb1" '+stable_attributes({"label":"","pos":"635,125!","shape":"point","width":0.03})+";",'  "lb2" '+stable_attributes({"label":"","pos":"670,125!","shape":"point","width":0.03})+";",'  "lb1" -- "lb2" '+stable_attributes({"color":"#888888","penwidth":1.8,"style":"dashed"})+";",'  "lbt" '+stable_attributes({**plain,"fontsize":6,"label":"Dashed aggregated boundary\nwidth = aggregated weight","pos":"735,121!"})+";",'  "map_note" '+stable_attributes({**plain,"fontsize":6.5,"label":f"Focal-node IDs F001-F{len(mapping):03d} map to full class names in the companion CSV.","pos":"400,28!"})+";","}"))
    return "\n".join(lines)+"\n"


def _targets(config,stage,output_root):
    base=BASENAMES[stage]
    if output_root is None:
        targets={"profiles":config.output.data/DIRECTORY/"xerces_cluster_profiles.csv","selected":config.output.data/DIRECTORY/"xerces_highest_lowest_clusters.csv","node_map":config.output.data/DIRECTORY/f"xerces_stage{stage}_focal_node_map.csv","aggregation":config.output.data/DIRECTORY/f"xerces_stage{stage}_boundary_aggregation.csv","dot":config.output.dot/DIRECTORY/f"{base}.dot","svg":config.output.svg/DIRECTORY/f"{base}.svg","pdf":config.output.pdf/DIRECTORY/f"{base}.pdf","provenance":config.output.data/DIRECTORY/f"{base}.provenance.json"};return targets,config.repository_root/"reports/figures/manifest.json",None
    root=output_root.resolve();targets={"profiles":root/"data"/DIRECTORY/"xerces_cluster_profiles.csv","selected":root/"data"/DIRECTORY/"xerces_highest_lowest_clusters.csv","node_map":root/"data"/DIRECTORY/f"xerces_stage{stage}_focal_node_map.csv","aggregation":root/"data"/DIRECTORY/f"xerces_stage{stage}_boundary_aggregation.csv","dot":root/"source"/DIRECTORY/f"{base}.dot","svg":root/"preview"/DIRECTORY/f"{base}.svg","pdf":root/"pdf"/DIRECTORY/f"{base}.pdf","provenance":root/"data"/DIRECTORY/f"{base}.provenance.json"};return targets,root/"manifest.json",root


def build_figure(config: VisualizationConfig, *, figure_id: str, output_root: str|Path|None=None, manifest_path: str|Path|None=None, generated_at: str|None=None, git_commit: str|None=None, git_dirty: bool|None=None, renderer: Callable[[GraphvizRenderRequest],GraphvizRenderResult]=render_graphviz):
    stage=next((s for s,fid in FIGURE_IDS.items() if fid==figure_id),None);spec=config.figures.get(figure_id)
    if stage is None or spec is None or not spec.enabled: raise ValueError(f"Xerces-J figure is not registered: {figure_id}")
    data=prepare_figure_data(config);chosen={role:p for role,p in data.selected if p.stage==stage};high,low=chosen["highest"],chosen["lowest"];mapping=focal_node_map(config,stage,high);stage_selected=tuple((role,p) for role,p in data.selected if p.stage==stage)
    targets,default_manifest,artifact_root=_targets(config,stage,None if output_root is None else Path(output_root));manifest=default_manifest if manifest_path is None else Path(manifest_path)
    for path in (*targets.values(),manifest): path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{figure_id}.",dir=artifact_root or config.repository_root/"reports/figures") as temporary:
        root=Path(temporary);staged={name:root/f"figure.{name}" for name in targets};staged["provenance"]=root/"figure.provenance.json"
        staged["profiles"].write_text(profiles_csv(data),encoding="utf-8",newline="\n");staged["selected"].write_text(selected_csv(data),encoding="utf-8",newline="\n");staged["node_map"].write_text(node_map_csv(mapping),encoding="utf-8",newline="\n");staged["aggregation"].write_text(boundary_csv(stage,stage_selected),encoding="utf-8",newline="\n");write_dot(staged["dot"],figure_dot(config,stage,high,low,mapping))
        renders=[renderer(GraphvizRenderRequest(staged["dot"],staged[fmt],fmt,"neato",fixed_coordinates=True)) for fmt in ("svg","pdf")]
        for name in ("profiles","selected","node_map","aggregation","dot","svg","pdf"):
            if not staged[name].is_file() or not staged[name].stat().st_size: raise ValueError(f"missing staged {name}")
        commands=tuple(("neato","-n2",f"-T{fmt}",str(targets["dot"]),"-o",str(targets[fmt])) for fmt in ("svg","pdf"))
        record=build_provenance(figure_id=figure_id,stage=spec.stage,generator="src/"+spec.generator.replace(".","/")+".py",repository_root=config.repository_root,input_files=(config.repository_root/path for path in spec.inputs),config_files=(config.figures_config_path,config.style_config_path),dot_path=staged["dot"],graphviz_engine="neato",graphviz_version=renders[0].version,render_commands=commands,generated_outputs=targets.values(),artifact_root=artifact_root,generated_at=generated_at,git_commit=git_commit,git_dirty=git_dirty);write_provenance(staged["provenance"],record)
        document=json.loads(manifest.read_text()) if manifest.exists() else {"schema_version":1,"figures":{}}
        if document.get("schema_version")!=1 or not isinstance(document.get("figures"),dict): raise ValueError("invalid figure manifest")
        document["figures"][figure_id]={"destination":spec.destination,"formats":list(spec.formats),"generated_at":record.generated_at,"generator":spec.generator,"inputs":list(spec.inputs),"metadata":dict(spec.metadata or {}),"outputs":{name:_relative(path,config.repository_root,artifact_root) for name,path in sorted(targets.items())},"sha256":{name:sha256_file(path) for name,path in sorted(staged.items())},"stage":spec.stage,"title":spec.title}
        staged_manifest=root/"manifest.json";write_json_atomic(staged_manifest,document)
        for name in targets: os.replace(staged[name],targets[name])
        os.replace(staged_manifest,manifest)
    return targets
