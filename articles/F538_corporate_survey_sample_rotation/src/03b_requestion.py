"""03b_requestion.py（問い直し、結果を見てから足した）：
4〜6月期のとびは、上向き・下向きのどちらかにかたよっているのか。
あわせて、母集団の法人数（4〜6月期に更新される）で割った1社あたりの値でも、4〜6月期のとびが残るかを見る。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
J = pd.read_csv(R / "yoy_jumps.csv")
d = pd.read_csv(ROOT / "data" / "quarterly_long.csv")
d["t"] = d["year"] * 4 + d["q"] - 1

rows = []
for it in ["sales", "employees"]:
    for sz in "BD":
        for per, (y0, y1) in {"pre_1990_2008": (1990, 2008), "post_2010_2026": (2010, 2026)}.items():
            s = J[(J["item"] == it) & (J["industry"] == "all_ex_fin") & (J["size"] == sz) & (J["q"] == 2) & (J["year"].between(y0, y1))]["jump"].dropna()
            k = int((s > 0).sum()); n = len(s)
            rows.append(dict(item=it, size=sz, period=per, n=n, n_up=k, mean_signed=round(float(s.mean()), 3),
                             p_sign=round(float(stats.binomtest(k, n, 0.5).pvalue), 4)))
S = pd.DataFrame(rows)
S.to_csv(R / "requestion_sign.csv", index=False)

# 1社あたり（母集団の法人数で割る）
corp = d[(d["item"] == "corporations") & (d["industry"] == "all_ex_fin")][["size", "t", "value"]].rename(columns={"value": "corp"})
pc_rows = []
for it in ["sales", "employees"]:
    for sz in "D":
        g = d[(d["item"] == it) & (d["industry"] == "all_ex_fin") & (d["size"] == sz)].merge(corp, on=["size", "t"]).sort_values("t")
        assert (np.diff(g["t"].values) == 1).all()
        v = g["value"].values / g["corp"].values
        yoy = 100 * (v[4:] / v[:-4] - 1)
        g = g.iloc[4:].copy(); g["yoy"] = yoy; g["jump"] = g["yoy"].diff()
        for per, (y0, y1) in {"pre_1990_2008": (1990, 2008), "post_2010_2026": (2010, 2026)}.items():
            s = g[g["year"].between(y0, y1)]
            a = s.loc[s["q"] == 2, "jump"].abs().mean(); b = s.loc[s["q"] != 2, "jump"].abs().mean()
            pc_rows.append(dict(item=it, size=sz, period=per, q2=round(a, 3), other=round(b, 3), ratio=round(a / b, 3)))
P = pd.DataFrame(pc_rows)
P.to_csv(R / "requestion_per_corp.csv", index=False)
out = {"sign": S.to_dict(orient="records"), "per_corp": P.to_dict(orient="records")}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(S.to_string()); print(P.to_string())
