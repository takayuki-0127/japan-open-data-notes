from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
FIG = ROOT / "figures"
RES = ROOT / "results"
for p in (FIG, RES):
    p.mkdir(parents=True, exist_ok=True)

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSansJP" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
SEED = 27


def load_topo():
    """簡略版 TopoJSON（国土数値情報 行政区域 2021）を読み、区域コード → 輪郭（リングのリスト）と、
    区域コード → 使っている弧の番号 の2つを返す。"""
    import json
    import numpy as np
    topo = json.load(open(RAW / "N03-21_210101.json", encoding="utf-8"))
    geoms = list(topo["objects"].values())[0]["geometries"]
    sc, tr = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        a = np.cumsum(np.array(arc, dtype=float), axis=0)
        arcs.append(np.c_[a[:, 0] * sc[0] + tr[0], a[:, 1] * sc[1] + tr[1]])

    def ring(idx):
        pts = []
        for i in idx:
            seg = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.append(seg if not pts else seg[1:])
        return np.vstack(pts)

    rings, used = {}, {}
    for g in geoms:
        code = g["properties"].get("N03_007")
        if not code:
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]] if g["type"] == "Polygon" else []
        for poly in polys:
            for r in poly:
                rings.setdefault(code, []).append(ring(r))
                used.setdefault(code, set()).update(i if i >= 0 else ~i for i in r)
    return rings, used


def to_km(lon, lat):
    import numpy as np
    return (np.asarray(lon) - 137.0) * 111.32 * np.cos(np.radians(36.0)), (np.asarray(lat) - 36.0) * 110.57
