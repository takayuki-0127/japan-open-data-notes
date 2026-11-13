"""640 傾向スコアのマッチングで、キャリパーの幅を変えると、効果の推定はどう変わるのか

本当の効果が分かっている架空のデータ（2,000件、施策を受けた人は約3割。受けやすさは3つの特徴で決まり、
結果も同じ特徴で決まる）で、傾向スコア（ロジスティック回帰、ロジットの値）の最近傍1対1マッチング（対照は戻して使う）を
キャリパー（相手との距離の上限、ロジットの標準偏差の倍数）なし・1・0.5・0.2・0.1・0.05 で行い、
施策を受けた人での効果（ATT）の推定の偏り・ばらつき・相手が見つからず捨てた人の割合を比べる。各300回。
効果が一定（2）の場合と、受けやすい人ほど効果が大きい場合の2通り。数字は置いた前提で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 640）"
rng = np.random.default_rng(640)
N, REPS = 2000, 300
CALS = [None, 1.0, 0.5, 0.2, 0.1, 0.05, 0.01]


def draw(hetero):
    X = rng.standard_normal((N, 3))
    lin = -1.0 + 2.2 * X[:, 0] + 1.2 * X[:, 1] - 0.6 * X[:, 2]
    T = rng.random(N) < 1 / (1 + np.exp(-lin))
    tau = 2 + (1.5 * np.tanh((lin + 1.0) / 2) if hetero else np.zeros(N))
    y0 = 1 + 2 * X[:, 0] + X[:, 0] ** 2 + 1.5 * X[:, 1] + rng.standard_normal(N)
    y = y0 + tau * T
    return X, T, y, tau


def att_match(X, T, y, cal):
    ps = LogisticRegression(C=1e6, max_iter=1000).fit(X, T).decision_function(X)
    sd = ps.std()
    nn = NearestNeighbors(n_neighbors=1).fit(ps[~T].reshape(-1, 1))
    d, j = nn.kneighbors(ps[T].reshape(-1, 1))
    d = d[:, 0]; j = j[:, 0]
    keep = np.ones(T.sum(), bool) if cal is None else d <= cal * sd
    yt = y[T][keep]; yc = y[~T][j[keep]]
    return float(np.mean(yt - yc)) if keep.sum() else np.nan, float(1 - keep.mean()), keep


rows = []
for hetero in [False, True]:
    for r in range(REPS):
        X, T, y, tau = draw(hetero)
        att_all = float(tau[T].mean())
        naive = float(y[T].mean() - y[~T].mean())
        for cal in CALS:
            est, drop, keep = att_match(X, T, y, cal)
            att_kept = float(tau[T][keep].mean())
            rows.append({"hetero": hetero, "rep": r, "caliper": "なし" if cal is None else str(cal), "est": est, "drop": drop,
                         "att_all": att_all, "att_kept": att_kept, "naive": naive})
D = pd.DataFrame(rows); D.to_csv(RES / "reps.csv.gz", index=False, float_format="%.6g", compression={"method": "gzip", "mtime": 0})
order = ["なし", "1.0", "0.5", "0.2", "0.1", "0.05", "0.01"]
S = D.groupby(["hetero", "caliper"]).apply(lambda g: pd.Series({
    "mean_est": g.est.mean(), "bias_vs_all": (g.est - g.att_all).mean(), "bias_vs_kept": (g.est - g.att_kept).mean(),
    "sd": g.est.std(), "rmse_vs_all": np.sqrt(((g.est - g.att_all) ** 2).mean()), "drop_pct": g["drop"].mean() * 100,
    "att_all": g.att_all.mean(), "att_kept": g.att_kept.mean(), "naive": g.naive.mean()})).round(4)
S = S.reindex(pd.MultiIndex.from_product([[False, True], order], names=["hetero", "caliper"]))
S.to_csv(RES / "summary.csv")
out = {"n": N, "reps": REPS, "treated_share": None,
       "constant": S.loc[False].to_dict(orient="index"), "hetero": S.loc[True].to_dict(orient="index")}
X, T, y, tau = draw(False)
out["treated_share"] = round(float(T.mean() * 100), 1)
json.dump(out, open(RES / "a640_main.json", "w"), ensure_ascii=False, indent=1)

lab = ["なし", "1SD", "0.5SD", "0.2SD", "0.1SD", "0.05SD", "0.01SD"]
s0 = S.loc[False]
# 図1：偏りとばらつき（効果一定）
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"wspace": 0.3})
ax[0].bar(lab, s0.bias_vs_all, color=ORANGE); ax[0].axhline(0, color=GRAY, lw=0.8)
for i, v in enumerate(s0.bias_vs_all):
    ax[0].text(i, v, f"{v:+.3f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
ax[0].set_title("推定の偏り（本当の効果2との差の平均）", fontsize=11); ax[0].set_xlabel("キャリパー（傾向スコアのロジットの標準偏差の倍数）")
ax[1].bar(lab, s0.sd, color=BLUE)
for i, v in enumerate(s0.sd):
    ax[1].text(i, v, f"{v:.3f}", ha="center", va="bottom", fontsize=8)
ax[1].set_title("推定のばらつき（標準偏差）", fontsize=11); ax[1].set_xlabel("キャリパー")
save(fig, "a640_bias_sd.png", SRC, y=-0.08)

# 図2：捨てた人の割合とRMSE（効果一定・効果が人で違う）
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.bar(lab, s0.drop_pct, color=LIGHT, label="相手が見つからず捨てた人（%、効果一定）")
for i, v in enumerate(s0.drop_pct):
    ax.text(i, v, f"{v:.1f}%", ha="center", va="bottom", fontsize=8)
s1 = S.loc[True]
ax2 = ax.twinx()
ax2.plot(lab, s0.rmse_vs_all, marker="o", color=INK, label="誤差（効果一定、右の目盛）")
ax2.plot(lab, s1.rmse_vs_all, marker="s", color=ORANGE, label="誤差（効果が人で違う、右の目盛）")
ax2.spines["right"].set_visible(True); ax.set_ylabel("捨てた人の割合（%）"); ax2.set_ylabel("受けた人全体の効果との誤差（RMSE）")
ax2.set_ylim(0, max(s0.rmse_vs_all.max(), s1.rmse_vs_all.max()) * 1.25)
ax.set_xlabel("キャリパー"); ax.set_title("狭めるほど捨てる人が増える。効果が人で違うと、誤差は0.05SDで底を打つ")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8.5, loc="upper center")
save(fig, "a640_drop_rmse.png", SRC)

# 図3：効果が人で違う場合：推定値・受けた人全体の効果・残った人の効果
s1 = S.loc[True]
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(lab, s1.mean_est, marker="o", color=ORANGE, label="推定値の平均")
ax.plot(lab, s1.att_all, marker="s", color=GRAY, ls="--", label="受けた人全体の本当の効果")
ax.plot(lab, s1.att_kept, marker="^", color=GREEN, label="残った人の本当の効果")
ax.set_xlabel("キャリパー"); ax.set_ylabel("効果"); ax.legend(frameon=False, fontsize=9)
ax.set_title("効果が人で違うと、狭めるほど「残った人の効果」に変わる")
save(fig, "a640_hetero.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
