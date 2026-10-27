"""頑健性の図と、予測価格の5分位ごとの当たり方
結果：figures/f06_robustness.png、results/coverage_by_pred_quintile.csv"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

# 予測価格の5分位ごとの当たり方（場所で分ける／較正も場所で、目標90%）
P = pd.read_csv(RES / "conformal_points.csv.gz", dtype={"code": str})
g = P[P.setting == "外側:block20／較正:block20"].copy()
g["pred_quintile"] = pd.qcut(g["pred"], 5, labels=["1（安い）", "2", "3", "4", "5（高い）"])
rows = []
for m in ("split", "norm", "cqr"):
    c = (g["y"] >= g[f"{m}_lo90"]) & (g["y"] <= g[f"{m}_hi90"])
    for k, v in c.groupby(g["pred_quintile"], observed=True).mean().items():
        rows.append(dict(method=m, pred_quintile=k, coverage=v))
pd.DataFrame(rows).to_csv(RES / "coverage_by_pred_quintile.csv", index=False, float_format="%.4f")

R = pd.read_csv(RES / "coverage_robust.csv")
C = pd.read_csv(RES / "coverage_main.csv")
base = C[(C.setting == "外側:block20／較正:block20") & (C.target == 90)].assign(setting="基本（較正用25%・ブロック／ブロック）")
r9 = pd.concat([base[base.method.isin(["split", "norm"])], R[(R.target == 90)]])
order = ["基本（較正用25%・ブロック／ブロック）", "較正用 10%（ブロック／ブロック）", "較正用 40%（ブロック／ブロック）",
         "データ半分（random／random）", "データ半分（block20／block20）",
         "2016年で作った区間→2016年の価格", "2016年で作った区間→2026年の価格", "同上＋全国の中央値の変化だけずらす"]
fig, ax = plt.subplots(figsize=(9.5, 5.4))
for i, s in enumerate(order):
    for m, col, dy in (("split", LIGHT, -0.18), ("norm", BLUE, 0.18)):
        v = r9[(r9.setting == s) & (r9.method == m)]["coverage"]
        if len(v):
            ax.barh(i + dy, v.values[0] * 100, 0.34, color=col, label={"split": "分割", "norm": "正規化"}[m] if i == 0 else None)
            ax.text(v.values[0] * 100 + 0.3, i + dy, f"{v.values[0]*100:.1f}", va="center", fontsize=8)
ax.axvline(90, color=ORANGE, ls="--", lw=1.2)
ax.set_yticks(range(len(order))); ax.set_yticklabels([o.replace("（random／random）", "（ランダム／ランダム）").replace("（block20／block20）", "（ブロック／ブロック）") for o in order], fontsize=9); ax.invert_yaxis()
ax.set_xlim(40, 100); ax.set_xlabel("90%区間に入った割合（%）")
ax.set_title("設定を変えたときの当たり方（目標 90%）")
ax.legend(frameon=False, fontsize=9, loc="lower right")
save(fig, "f06_robustness.png")
print(r9.round(3).to_string())
