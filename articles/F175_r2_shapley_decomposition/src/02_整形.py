"""02 整形：グループの定義表と、グループどうしがどれだけ重なっているか

- data/groups.csv：変数→グループの対応（基本・粗い・細かい）
- results/group_overlap_*.csv：グループ A と B の変数どうしのスピアマン相関の絶対値の最大
- results/group_predictability_*.csv：グループの第1主成分を、ほかのグループの変数で線形回帰したときの R²
  （ほかで「代わりがきく」グループほど、1つだけ外しても精度が落ちない）
"""
import numpy as np, pandas as pd
from common import DATA, RES, L_GROUPS, L_GROUPS4, P_GROUPS, P_GROUPS4, P_GROUPS7, data_land, data_power
from shapley import linear_design

rows = []
for data, sets in (("地価", {"基本7": L_GROUPS, "粗い4": L_GROUPS4}),
                   ("電力需要", {"基本6": P_GROUPS, "細かい7": P_GROUPS7, "粗い4": P_GROUPS4})):
    for sname, g in sets.items():
        for gname, cs in g.items():
            for c in cs:
                rows.append({"データ": data, "まとめ方": sname, "グループ": gname, "変数": c})
pd.DataFrame(rows).to_csv(DATA / "groups.csv", index=False)

for name, (X, groups) in (("地価", (data_land()[0], L_GROUPS)), ("電力需要", (data_power()[0], P_GROUPS))):
    Z, owner = linear_design(X)
    Z = (Z - Z.mean()) / Z.std().replace(0, 1)
    num = X.select_dtypes("number")
    cor = num.rank().corr().abs()
    names = list(groups)
    M = pd.DataFrame(index=names, columns=names, dtype=float)
    for a in names:
        for b in names:
            ca = [c for c in groups[a] if c in cor]; cb = [c for c in groups[b] if c in cor]
            M.loc[a, b] = np.nan if a == b or not ca or not cb else cor.loc[ca, cb].values.max()
    M.round(3).to_csv(RES / f"group_overlap_{name}.csv")
    out = []
    for g in names:
        j = np.isin(owner, groups[g])
        A = Z.values[:, j]
        u = np.linalg.svd(A - A.mean(0), full_matrices=False)[0][:, 0]
        B = np.c_[np.ones(len(Z)), Z.values[:, ~j]]
        b = np.linalg.lstsq(B, u, rcond=None)[0]
        r2 = 1 - np.sum((u - B @ b) ** 2) / np.sum((u - u.mean()) ** 2)
        out.append({"グループ": g, "ほかのグループからの説明力R2": round(float(r2), 3)})
    pd.DataFrame(out).to_csv(RES / f"group_predictability_{name}.csv", index=False)
    print(name); print(M.round(2).to_string()); print(pd.DataFrame(out).to_string())
