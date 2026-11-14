"""target/manifest.json（dbt build のあとにできる）から、モデルのつながりを figures/lineage.png に描く。
使い方: python3 tools/lineage.py   （graphviz の dot が要る）
"""
import json, os, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
m = json.load(open(os.path.join(ROOT, "target", "manifest.json"), encoding="utf-8"))
COL = {"source": "#e8e8e3", "stg": "#dbe8f3", "int": "#c4d9ec", "dim": "#f3e3c3", "fct": "#f0d29b", "rpt": "#d7ebd0", "exposure": "#ffffff"}


def kind(name, rtype):
    if rtype == "source": return "source"
    if rtype == "exposure": return "exposure"
    return name.split("_")[0]


nodes, edges = {}, []
for uid, n in {**m["nodes"], **m["sources"], **m["exposures"]}.items():
    if n["resource_type"] not in ("model", "source", "exposure"):
        continue
    nodes[uid] = (n["name"], kind(n["name"], n["resource_type"]))
    for p in n.get("depends_on", {}).get("nodes", []):
        edges.append((p, uid))
rank = ["source", "stg", "int", "dim", "fct", "rpt", "exposure"]
L = ['digraph G {', 'rankdir=LR; nodesep=0.12; ranksep=0.55;',
     'node [shape=box, style="rounded,filled", fontname="Noto Sans CJK JP", fontsize=10, color="#888888"];',
     'edge [color="#9a9a9a", arrowsize=0.5];']
for k in rank:
    ids = [u for u, (nm, kk) in nodes.items() if kk == k]
    if not ids: continue
    L.append("{ rank=same; " + " ".join(f'"{u}" [label="{nodes[u][0]}", fillcolor="{COL[k]}"];' for u in sorted(ids, key=lambda u: nodes[u][0])) + " }")
for a, b in edges:
    if a in nodes and b in nodes:
        L.append(f'"{a}" -> "{b}";')
L.append("}")
os.makedirs(os.path.join(ROOT, "figures"), exist_ok=True)
subprocess.run(["dot", "-Tpng", "-Gdpi=130", "-o", os.path.join(ROOT, "figures", "lineage.png")],
               input="\n".join(L), text=True, check=True)
print(len(nodes), "nodes", len(edges), "edges")
