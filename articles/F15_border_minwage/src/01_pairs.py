"""県境をはさんで接する市区町村のペアを作る。

TopoJSON（国土数値情報 行政区域 2021 をもとにした簡略版、smartnews-smri/japan-topography、CC BY 4.0）は
隣どうしの市区町村が同じ「弧（arc）」を共有するので、同じ弧を使う2つの市区町村を「接している」とみなす
（簡略化で隙間ができる心配がない）。政令市の区は市にまとめる（SSDSE は市単位のため）。
あわせて、県境をまたぐ「中心どうしが20km以内」のペアも作る（頑健性チェック用）。
"""
import json
import urllib.request
from collections import defaultdict

import numpy as np
import pandas as pd

from common import RAW, DATA

url = ("https://raw.githubusercontent.com/smartnews-smri/japan-topography/main/"
       "data/municipality/topojson/s0010/N03-21_210101.json")
dst = RAW / "N03-21_210101.json"
if not dst.exists():
    urllib.request.urlretrieve(url, dst)
topo = json.load(open(dst, encoding="utf-8"))
geoms = list(topo["objects"].values())[0]["geometries"]
sc, tr = topo["transform"]["scale"], topo["transform"]["translate"]

# 弧を座標に戻す（差分符号化）
arcs_xy = []
for arc in topo["arcs"]:
    x = y = 0
    pts = []
    for dx, dy in arc:
        x += dx
        y += dy
        pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
    arcs_xy.append(np.array(pts))

# SSDSE の市区町村コード（政令市の区を市に寄せるため）
ss = pd.read_csv(RAW / "SSDSE-A-2026.csv", encoding="cp932", header=None, skiprows=3, usecols=[0])
codes = sorted(int(str(c)[1:]) for c in ss[0])


def to_city(code: int) -> int:
    if code in codes:
        return code
    cand = [c for c in codes if c < code and c // 1000 == code // 1000]
    return max(cand) if cand else code


def flat(a):
    if isinstance(a, int):
        return [a]
    out = []
    for b in a:
        out += flat(b)
    return out


arc_owner = defaultdict(set)
pts_by = defaultdict(list)
for g in geoms:
    p = g.get("properties", {})
    c = p.get("N03_007")
    if not c or g.get("arcs") is None:
        continue
    city = to_city(int(c))
    for i in flat(g["arcs"]):
        k = i if i >= 0 else ~i
        arc_owner[k].add(city)
        pts_by[city].append(arcs_xy[k])

pairs = set()
for k, s in arc_owner.items():
    s = sorted(s)
    for i in range(len(s)):
        for j in range(i + 1, len(s)):
            a, b = s[i], s[j]
            if a // 1000 != b // 1000:      # 県が違う
                pairs.add((a, b))

# 中心（境界の点の平均で近似）と距離
cent = {c: np.vstack(v).mean(axis=0) for c, v in pts_by.items()}


def dist_km(a, b):
    (x1, y1), (x2, y2) = cent[a], cent[b]
    kx = 111.32 * np.cos(np.radians((y1 + y2) / 2))
    return float(np.hypot((x1 - x2) * kx, (y1 - y2) * 110.57))


rows = [(a, b, "touch", dist_km(a, b)) for a, b in sorted(pairs)]
# 20km 以内（接していなくてもよい）の県境ペア
cl = sorted(cent)
for i, a in enumerate(cl):
    for b in cl[i + 1:]:
        if a // 1000 != b // 1000 and (a, b) not in pairs:
            d = dist_km(a, b)
            if d <= 20:
                rows.append((a, b, "near20", d))
out = pd.DataFrame(rows, columns=["code_a", "code_b", "kind", "dist_km"])
out.to_csv(DATA / "pairs.csv", index=False)
cen = pd.DataFrame([(c, *xy) for c, xy in cent.items()], columns=["code", "lon", "lat"])
cen.to_csv(DATA / "centroids.csv", index=False)
print(out.kind.value_counts().to_dict(), "municipalities on borders:",
      len(set(out.query('kind=="touch"').code_a) | set(out.query('kind=="touch"').code_b)))
