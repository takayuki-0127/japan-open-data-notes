"""02 整形：市区町村の表を整え、3種類のグラフ（隣接・近い6区域・通勤）の辺のリストを作る"""
import numpy as np
import pandas as pd
from common import DATA, RES, load_topo, to_km

X = ["young_f", "income", "commute_out", "nursery", "tertiary", "density", "unmarried", "aged"]

df = pd.read_csv(DATA / "municipal_2018_22.csv", dtype={"code": str, "pref": str})
df = df[df["pop"] > 0].replace([np.inf, -np.inf], np.nan)
rings, used = load_topo()
df = df[df["code"].isin(rings.keys())].dropna(subset=["tfr"] + X).reset_index(drop=True)
codes = list(df["code"])
idx = {c: i for i, c in enumerate(codes)}
cent = np.array([np.vstack(rings[c]).mean(axis=0) for c in codes])
kx, ky = to_km(cent[:, 0], cent[:, 1])
df["x_km"], df["y_km"] = kx, ky
df.to_csv(DATA / "nodes.csv", index=False)
print("市区町村", len(df))

# 1) 隣接（境界の弧を共有する＝Queen に近い）。接する区域がない島は、いちばん近い1区域とつなぐ
owner = {}
for c in codes:
    for a in used[c]:
        owner.setdefault(a, set()).add(c)
E = set()
for s in owner.values():
    s = [c for c in s if c in idx]
    for a in s:
        for b in s:
            if a < b:
                E.add((idx[a], idx[b]))
deg = np.zeros(len(codes), int)
for a, b in E:
    deg[a] += 1; deg[b] += 1
P = np.c_[kx, ky]
n_island = 0
for i in np.where(deg == 0)[0]:
    d = np.hypot(*(P - P[i]).T); d[i] = np.inf
    j = int(np.argmin(d)); E.add((min(i, j), max(i, j))); n_island += 1
pd.DataFrame(sorted(E), columns=["i", "j"]).to_csv(DATA / "edges_adjacent.csv", index=False)
print("隣接の辺", len(E), "島をつないだ数", n_island)

# 2) 近い6区域（重心の距離）
K = set()
for i in range(len(codes)):
    d = np.hypot(*(P - P[i]).T); d[i] = np.inf
    for j in np.argsort(d)[:6]:
        K.add((min(i, int(j)), max(i, int(j))))
pd.DataFrame(sorted(K), columns=["i", "j"]).to_csv(DATA / "edges_knn6.csv", index=False)
print("近い6区域の辺", len(K))

# 3) 通勤（1都3県だけ。F10 と同じ国勢調査2020の通勤表。両方向を足し、出発地の就業者の1%以上の流れだけを辺にする）
od = pd.read_csv(DATA / "commute_od.csv", dtype={"res": str, "work": str})
od = od[(od.res != od.work) & od.res.isin(idx) & od.work.isin(idx)]
od["a"] = od[["res", "work"]].min(axis=1); od["b"] = od[["res", "work"]].max(axis=1)
w = od.groupby(["a", "b"])["n"].sum().reset_index()
pop = df.set_index("code")["pop"]
w["share"] = w["n"] / np.minimum(pop[w.a].values, pop[w.b].values)
w["i"] = w.a.map(idx); w["j"] = w.b.map(idx)
w[["i", "j", "n", "share"]].to_csv(DATA / "edges_commute_all.csv", index=False)
sub = sorted(set(od.res) | set(od.work))
print("通勤のある市区町村", len(sub), "通勤の辺（すべて）", len(w))
