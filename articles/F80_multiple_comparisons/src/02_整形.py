"""指標の表を作る。

- 2026年版の各指標について最新年の値を取り、47都道府県がそろうものだけ残す
- 比率・1人当たり・割合など「規模に左右されない」指標に絞る（総数や件数そのものは除く）
- ほぼ同じ動きの指標（相関の絶対値が0.95超）は、コードの若いほうだけ残す
- 2015年版で同じコードがあれば、その最新年の値も作る（頑健性用）
"""
import re
import numpy as np
import pandas as pd
from common import RAW, DATA

raw = pd.read_csv(RAW / "ssds_pref_indicators.csv")
names = pd.read_csv(RAW / "indicator_names_2026.tsv", sep="\t")
names["code"] = names["code"].str.lstrip("#")
P = [f"p{i:02d}" for i in range(1, 48)]

RATIO = re.compile(r"当たり|割合|率|比率|指数|密度|平均|対|／|/")
def is_ratio(name, unit):
    if RATIO.search(str(name)):
        return True
    return str(unit) in ("％", "－")

def latest(ed):
    x = raw[raw.edition == ed].dropna(subset=P)
    x = x.sort_values("year").groupby("code").tail(1)
    return x.set_index("code")

l26 = latest(2026)
meta = names.set_index("code").reindex(l26.index)
ok = [c for c in l26.index if is_ratio(meta.loc[c, "name"], meta.loc[c, "unit"])]
mat = l26.loc[ok, P].astype(float)
mat = mat[mat.std(axis=1) > 0]

# ほぼ重複する指標を落とす
z = mat.sub(mat.mean(1), axis=0).div(mat.std(1), axis=0)
keep = []
for c in z.index:
    if all(abs(np.corrcoef(z.loc[c], z.loc[k])[0, 1]) <= 0.95 for k in keep):
        keep.append(c)
mat = mat.loc[keep]
out = mat.T.copy()
out.index = range(1, 48)
out.index.name = "pref_code"
out.to_csv(DATA / "indicators_2026.csv")
m = meta.loc[keep, ["name", "unit"]].copy()
m["year"] = l26.loc[keep, "year"].astype(int)
m.to_csv(DATA / "indicator_meta.csv")

l15 = latest(2015)
c15 = [c for c in keep if c in l15.index]
o15 = l15.loc[c15, P].astype(float).T
o15.index = range(1, 48); o15.index.name = "pref_code"
o15.to_csv(DATA / "indicators_2015ed.csv")

# 隣接（境界を共有）。北海道―青森、山口―福岡、鹿児島―沖縄は海を挟むが、つながりを保つために足す
pr = pd.read_csv(RAW / "pref_pairs_f33.csv")
adj = pr[(pr.adj == 1) & (pr.o < pr.d)][["o", "d"]]
adj = pd.concat([adj, pd.DataFrame({"o": [1, 35, 46], "d": [2, 40, 47]})]).drop_duplicates()
adj.to_csv(DATA / "adjacency.csv", index=False)
print("比率型で47県そろう指標:", len(ok), "→ 重複を除いて", len(keep), "／2015年版にもある:", len(c15), "／隣接の組:", len(adj))
