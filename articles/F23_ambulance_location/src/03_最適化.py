"""救急車の待機場所（ここでは消防署の場所）を選び直す最適化。

- 需要：福井市の500mメッシュ人口（2020年）。重みは人口（頑健性で65歳以上・75歳以上）
- 距離：道路距離（OSRM、渋滞なし）。頑健性で直線距離
- p-median：p か所を選んで、人口で重みづけた「いちばん近い拠点までの平均距離」を最小にする
- 最大カバー：p か所で、道路で R 分以内に届く人口を最大にする
結果は results/ に CSV で保存する。
"""
import json
import time

import numpy as np
import pandas as pd

from common import DATA, RES
from opt import p_median, max_cover

d = pd.read_csv(DATA / "demand.csv")
c = pd.read_csv(DATA / "candidates.csv")
mx = np.load(DATA / "matrix.npz")
Dk, Dt, Dl = mx["road_km"], mx["road_min"], mx["line_km"]
w_pop = d["pop"].values.astype(float)
w_65 = d["pop65"].values.astype(float)
w_75 = d["pop75"].values.astype(float)
st = (c["type"] == "station").values
P = int(st.sum())
fs = json.load(open(DATA.parent / "data" / "raw" / "f23_firestations_p17_2012_fukui.json", encoding="utf-8"))
main_names = {r["P17_001"] for r in fs if r["P17_002"] == "18201" and r["P17_003"] in ("1", "2")}
main = st & c["name"].isin(main_names).values
TL = 240


def wmean(D, w, sel):
    return float((w * D[:, sel].min(axis=1)).sum() / w.sum())


def share_within(D, w, sel, R):
    return float(w[D[:, sel].min(axis=1) <= R].sum() / w.sum())


def summary(label, sel, w=w_pop):
    sel = np.asarray(sel)
    dk = Dk[:, sel].min(axis=1)
    return {"案": label, "拠点数": len(sel),
            "平均道路距離_km": wmean(Dk, w, sel), "平均所要時間_分": wmean(Dt, w, sel),
            "90パーセント点_km": float(np.quantile(np.repeat(dk, np.maximum(w.astype(int), 0)), 0.9)),
            "5分以内の割合": share_within(Dt, w, sel, 5.0), "8分以内の割合": share_within(Dt, w, sel, 8.0),
            "直線の平均_km": wmean(Dl, w, sel),
            "今の拠点を使う数": int(st[sel].sum())}


rows, sels = [], {}
cur = np.where(st)[0]
rows.append(summary("今の配置", cur)); sels["今の配置"] = cur
t0 = time.time()
sel, _, _ = p_median(Dk, w_pop, P, time_limit=TL)
rows.append(summary("全部を選び直す", sel)); sels["全部を選び直す"] = sel
sel, _, _ = p_median(Dk, w_pop, P, fixed=main, time_limit=TL)
rows.append(summary("本署は固定・ほかを選び直す", sel)); sels["本署は固定・ほかを選び直す"] = sel
for k in (1, 2, 3, 5):
    sel, _, _ = p_median(Dk, w_pop, P + k, fixed=st, time_limit=TL)
    rows.append(summary(f"今の配置＋{k}か所", sel)); sels[f"今の配置＋{k}か所"] = sel
# 最大カバー（道路で5分以内）
sel, cov, _ = max_cover(Dt, w_pop, P, 5.0, time_limit=TL)
rows.append(summary("5分カバーを最大にする", sel)); sels["5分カバーを最大にする"] = sel
summ = pd.DataFrame(rows)
summ.to_csv(RES / "summary.csv", index=False)
print(summ.round(3).to_string())
print("time", time.time() - t0)

# 拠点数を変えたとき（全部を選び直す）
curve = []
for p in [3, 5, 8, 10, 12, 15, 18, 21, 25, 30]:
    sel, m, _ = p_median(Dk, w_pop, p, time_limit=TL)
    _, cov5, _ = max_cover(Dt, w_pop, p, 5.0, time_limit=TL)
    curve.append({"拠点数": p, "平均道路距離_km": m, "5分以内の割合_最大": cov5})
    print(p, round(m, 3), round(cov5, 3))
pd.DataFrame(curve).to_csv(RES / "curve_p.csv", index=False)

# 頑健性
rob = []
def add(label, sel, w=w_pop):
    r = summary(label, sel, w); r["重み"] = "人口" if w is w_pop else ("65歳以上" if w is w_65 else "75歳以上"); rob.append(r)
base = sels["全部を選び直す"]
add("基本（道路距離・人口）", base)
sel, _, _ = p_median(Dl, w_pop, P, time_limit=TL); add("直線距離で解いて道路で評価", sel); sels["直線で解く"] = sel
sel, _, _ = p_median(Dt, w_pop, P, time_limit=TL); add("所要時間で解く", sel)
add("今の配置（65歳以上で評価）", cur, w_65)
sel, _, _ = p_median(Dk, w_65, P, time_limit=TL); add("65歳以上で重みづけ", sel, w_65); sels["65歳以上"] = sel
add("今の配置（75歳以上で評価）", cur, w_75)
sel, _, _ = p_median(Dk, w_75, P, time_limit=TL); add("75歳以上で重みづけ", sel, w_75)
sel, _, _ = p_median(Dk, w_pop, P, allowed=~st, time_limit=TL); add("候補地を格子だけにする", sel)
dense = (~st) & (c["name"].astype(str).map(dict(zip(d["mesh"].astype(str), d["pop"]))).fillna(0).values >= 300)
sel, _, _ = p_median(Dk, w_pop, P, allowed=st | dense, time_limit=TL); add("格子は人口300人以上だけ", sel)
robdf = pd.DataFrame(rob)
robdf.to_csv(RES / "robustness.csv", index=False)
print(robdf.round(3).to_string())

# 選ばれた地点の重なり
def overlap(a, b):
    A = set(np.asarray(a).tolist()); B = set(np.asarray(b).tolist()); return len(A & B)
ov = {k: overlap(v, base) for k, v in sels.items()}
json.dump({k: [int(x) for x in v] for k, v in sels.items()}, open(RES / "selected_sites.json", "w"), ensure_ascii=False, indent=1)
json.dump(ov, open(RES / "overlap_with_base.json", "w"), ensure_ascii=False, indent=1)
print(ov)
