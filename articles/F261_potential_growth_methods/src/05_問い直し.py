"""F261 問いの立て直し（最初の結果を見てから追加）。

H4 で「直近の潜在成長率」は、あとで平均 0.7ポイント近く書き換わった。そこで次の問いを立てた。
  直近の推計は、データが何四半期分増えれば落ち着くのか？
  書き換わる向きは、その後の実際の成長で説明できるのか？

方法：最新の公表回（2026年4-6月期2次）の前期比から作った系列を使い（03 の H4 と同じ）、
対象の四半期 e（2004Q1〜2021Q2、全部で70）ごとに、e+h までのデータで HP1600・UC・HAM・CF を推計し、
e の潜在成長率（前年同期比）が、全期間で推計した値とどれだけ違うかを h=0〜20 で測る。
「落ち着いた」は、全期間の値との差が 0.2ポイント以内とする（この線は結果を見る前に決めた）。
出力：results/reask_convergence.csv、results/reask.json
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("m", ROOT / "src" / "zz_f261_methods.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

PROC, RES = ROOT / "data" / "processed", ROOT / "results"
VL = pd.read_csv(PROC / "vintage_levels.csv.gz")
rel = pd.read_csv(ROOT / "data" / "raw" / "f50_releases.csv")
latest = VL[VL.rid == rel.rid.iloc[-1]]
lq = latest.quarter.tolist()
ll = np.log(latest.level.values)

FUNCS = {"HP1600": m.tr_hp, "UC": m.tr_uc, "HAM": m.tr_ham, "CF": m.tr_cf}
final = {k: m.yoy(f(ll)) for k, f in FUNCS.items()}
E = [q for q in lq if "2004Q1" <= q <= "2021Q2"]
H = list(range(0, 21))
rows = []
for e in E:
    k = lq.index(e)
    for h in H:
        x = ll[: k + h + 1]
        for name, f in FUNCS.items():
            est = m.yoy(f(x))[k]
            rows.append({"ref": e, "h": h, "method": name, "est": est, "final": final[name][k]})
C = pd.DataFrame(rows)
C["diff"] = C.est - C.final
C.round(4).to_csv(RES / "reask_convergence.csv", index=False)

out = {"n_ref": len(E), "ref_range": [E[0], E[-1]], "by_method": {}}
for name, g in C.groupby("method"):
    t = g.groupby("h")["diff"].agg(mad=lambda s: s.abs().mean(), within02=lambda s: (s.abs() <= 0.2).mean())
    # 初めて「平均の差 0.2 以内」になる h
    first = next((int(h) for h, r in t.iterrows() if r.mad <= 0.2), None)
    first80 = next((int(h) for h, r in t.iterrows() if r.within02 >= 0.8), None)
    out["by_method"][name] = {
        "mad_by_h": t["mad"].round(3).to_dict(),
        "within02_by_h": t["within02"].round(3).to_dict(),
        "first_h_mad_le_0.2": first,
        "first_h_80pct_within_0.2": first80,
    }

# 書き換わりの向きと、その後8四半期の実際の成長（年率）の関係：HP1600、h=0
g0 = C[(C.method == "HP1600") & (C.h == 0)].set_index("ref")
fut = []
for e in g0.index:
    k = lq.index(e)
    if k + 8 < len(ll):
        fut.append((e, 100 * (np.exp((ll[k + 8] - ll[k]) / 2) - 1)))
F = pd.Series(dict(fut))
rev = -(g0["diff"].reindex(F.index))  # あとでの書き換わり＝最終−当初
out["revision_vs_future_growth_hp"] = {
    "n": int(len(F)),
    "corr": round(float(np.corrcoef(rev, F)[0, 1]), 3),
    "slope_pt_per_pt": round(float(np.polyfit(F.values, rev.values, 1)[0]), 3),
}
(RES / "reask.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float))
for k, v in out["by_method"].items():
    print(k, v["first_h_mad_le_0.2"], v["first_h_80pct_within_0.2"], {h: v["mad_by_h"][h] for h in (0, 4, 8, 12, 16, 20)})
print(out["revision_vs_future_growth_hp"])
