"""686 単位をそろえずに Lasso をかけると、どの変数が選ばれやすくなるのか

架空の店のデータ（200件）。説明変数は10個で、5個が効く・5個が効かない。
効く5個は、標準化した尺度ではどれも同じ効き目（係数0.25）だが、単位が違う：
  ×0.01・×0.1・×1・×10・×100（例：同じ量を「百万円」「十万円」「万円」「千円」「百円」で入れたもの）
効かない5個も同じ5通りの単位。
Lasso（強さは5-fold の交差検証で選ぶ）を、標準化してからかける場合と、そのままかける場合で、
各変数が選ばれる割合を300回のくり返しで数える。新しいデータでの予測誤差も比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LassoCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 686）"
rng = np.random.default_rng(686)
N, NT, REPS, B = 200, 5000, 300, 0.25
SCALES = np.array([0.01, 0.1, 1, 10, 100])
LAB = ["×0.01", "×0.1", "×1", "×10", "×100"]
P = 10
beta_std = np.r_[np.full(5, B), np.zeros(5)]
scale_all = np.r_[SCALES, SCALES]


def draw(n):
    Z = rng.normal(0, 1, (n, P))
    Z[:, 5:] = 0.5 * Z[:, :5] + np.sqrt(1 - 0.25) * Z[:, 5:]     # 効かない列は効く列と相関0.5
    y = Z @ beta_std + rng.normal(0, 1, n)
    return Z * scale_all, y                                      # 単位を変えた値で渡す


rows = []
Xt, yt = draw(NT)
for r in range(REPS):
    X, y = draw(N)
    for name, model in [("scaled", make_pipeline(StandardScaler(), LassoCV(cv=5, alphas=60, max_iter=20000))),
                        ("raw", LassoCV(cv=5, alphas=60, max_iter=20000))]:
        model.fit(X, y)
        coef = model[-1].coef_ if name == "scaled" else model.coef_
        sel = np.abs(coef) > 1e-10
        rec = {"rep": r, "method": name, "mse": float(np.mean((model.predict(Xt) - yt) ** 2))}
        for j in range(P):
            rec[f"sel_{j}"] = int(sel[j])
        rows.append(rec)
D = pd.DataFrame(rows); D.to_csv(RES / "reps.csv.gz", index=False, float_format="%.6g", compression={"method": "gzip", "mtime": 0})
S = D.groupby("method").mean().drop(columns="rep")
sel = {m: {"effective": [round(S.loc[m, f"sel_{j}"] * 100, 1) for j in range(5)],
           "null": [round(S.loc[m, f"sel_{j}"] * 100, 1) for j in range(5, 10)]} for m in ["scaled", "raw"]}
tab = pd.DataFrame({"unit": LAB, "scaled_effective": sel["scaled"]["effective"], "raw_effective": sel["raw"]["effective"],
                    "scaled_null": sel["scaled"]["null"], "raw_null": sel["raw"]["null"]})
tab.to_csv(RES / "selection_rate.csv", index=False)
out = {"n": N, "reps": REPS, "beta_std": B, "selection_pct": sel,
       "mse": {m: round(float(S.loc[m, "mse"]), 4) for m in ["scaled", "raw"]}, "noise_var": 1.0,
       "raw_effective_selected_mean": round(float(np.mean(sel["raw"]["effective"])), 1),
       "scaled_effective_selected_mean": round(float(np.mean(sel["scaled"]["effective"])), 1)}
json.dump(out, open(RES / "a686_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：効く変数が選ばれる割合（単位ごと）
x = np.arange(5); w = 0.38
fig, ax = plt.subplots(figsize=(8.5, 4))
b1 = ax.bar(x - w / 2, sel["scaled"]["effective"], w, color=BLUE, label="標準化してから")
b2 = ax.bar(x + w / 2, sel["raw"]["effective"], w, color=ORANGE, label="そのまま")
for bars in (b1, b2):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{b.get_height():.0f}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"単位 {l}" for l in LAB]); ax.set_ylabel("選ばれた割合（%）"); ax.set_ylim(0, 110)
ax.legend(frameon=False, loc="upper left"); ax.set_title("同じ効き目の5つの変数：そのままだと、数字の小さい単位の変数が落ちる")
save(fig, "a686_effective.png", SRC)

# 図2：効かない変数が選ばれる割合
fig, ax = plt.subplots(figsize=(8.5, 4))
b1 = ax.bar(x - w / 2, sel["scaled"]["null"], w, color=BLUE, label="標準化してから")
b2 = ax.bar(x + w / 2, sel["raw"]["null"], w, color=ORANGE, label="そのまま")
for bars in (b1, b2):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{b.get_height():.0f}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"単位 {l}" for l in LAB]); ax.set_ylabel("選ばれた割合（%）"); ax.set_ylim(0, 110)
ax.legend(frameon=False, loc="upper left"); ax.set_title("効かない5つの変数：そのままだと、数字の大きい単位の変数が残りやすい")
save(fig, "a686_null.png", SRC)

# 図3：予測誤差
fig, ax = plt.subplots(figsize=(7, 3.6))
for i, (m, c, l) in enumerate([("scaled", BLUE, "標準化してから"), ("raw", ORANGE, "そのまま")]):
    v = D[D.method == m]["mse"]
    ax.hist(v, bins=30, color=c, alpha=0.6, label=f"{l}（平均 {v.mean():.3f}）")
ax.axvline(1.0, color=INK, ls="--", lw=0.8); ax.text(1.0, ax.get_ylim()[1] * 0.95, " 誤差だけの下限 1.0", fontsize=8.5, va="top")
ax.set_xlabel("新しいデータでの予測の二乗誤差"); ax.set_ylabel("回数"); ax.legend(frameon=False)
ax.set_title("予測の誤差も、そのままのほうが大きい")
save(fig, "a686_mse.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
