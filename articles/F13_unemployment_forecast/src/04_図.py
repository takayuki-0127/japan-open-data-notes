"""04 図"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import RES, FIG, COLORS

FIG.mkdir(exist_ok=True)
fc = pd.read_csv(RES / "forecasts.csv", index_col=0, parse_dates=True)
met = pd.read_csv(RES / "metrics.csv")
rob = pd.read_csv(RES / "robustness.csv")
imp = pd.read_csv(RES / "importance.csv", index_col=0)
ORDER = ["前月の値（ナイーブ）", "AR（失業率だけ）", "SARIMAX", "ElasticNet", "LightGBM", "平均（3モデル）"]
KEY = {"naive": "前月の値（ナイーブ）", "ElasticNet": "ElasticNet", "LightGBM": "LightGBM", "SARIMAX": "SARIMAX"}


def levels(h, m):
    s = fc["u_T"] + fc[f"{m}_{h}"]
    s.index = s.index + pd.DateOffset(months=h)
    return s


actual = (fc["u_T"]).copy()
# 1. 予測と実績（3か月先）
fig, ax = plt.subplots(figsize=(10, 4.6))
act = pd.concat([fc["actual_3"].set_axis(fc.index + pd.DateOffset(months=3)), fc["actual_1"].set_axis(fc.index + pd.DateOffset(months=1))]).groupby(level=0).first()
ax.plot(act.index, act.values, color="black", lw=2.2, label="実績（季節調整値）")
for m in ("naive", "SARIMAX", "ElasticNet", "LightGBM"):
    s = levels(3, m)
    ax.plot(s.index, s.values, lw=1.2, color=COLORS[KEY[m]], label=f"3か月前の予測：{KEY[m]}", alpha=.9)
ax.set_ylabel("完全失業率（%）")
ax.set_title("3か月先の失業率の予測と実績（2005年1月〜2026年8月）")
ax.legend(ncol=2, fontsize=9, frameon=False)
ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "a13_pred_vs_actual.png"); plt.close()

# 2. MAE（ナイーブ比）全期間
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
allp = met[met["期間"].str.startswith("全期間")]
for ax, h in zip(axes, (1, 3)):
    d = allp[allp.h == h].set_index("model").loc[ORDER]
    bars = ax.barh(range(len(d)), d["MAE_ナイーブ比"], color=[COLORS[m] for m in d.index])
    ax.axvline(1, color="black", lw=1)
    for i, (r, p, mae) in enumerate(zip(d["MAE_ナイーブ比"], d["DM_p値"], d["MAE"])):
        star = "" if np.isnan(p) else ("**" if p < .01 else "*" if p < .05 else "")
        ax.text(r + 0.005, i, f"{r:.2f}{star}（{mae:.3f}pt）", va="center", fontsize=9)
    ax.set_yticks(range(len(d))); ax.set_yticklabels(d.index)
    ax.set_xlim(0.75, 1.2)
    ax.set_title(f"{h}か月先")
    ax.set_xlabel("平均絶対誤差（前月の値＝1）")
    ax.invert_yaxis(); ax.grid(axis="x", alpha=.3)
fig.suptitle("前月の値と比べた予測の誤差（1未満なら前月の値より良い。* p<0.05、** p<0.01：DM検定）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "a13_mae.png"); plt.close()

# 3. コロナ期
fig, ax = plt.subplots(figsize=(10, 4.4))
lo, hi = pd.Timestamp("2019-07-01"), pd.Timestamp("2022-06-01")
a = act[(act.index >= lo) & (act.index <= hi)]
ax.plot(a.index, a.values, color="black", lw=2.2, marker="o", ms=3, label="実績")
for m in ("naive", "SARIMAX", "ElasticNet", "LightGBM"):
    for h, ls in ((3, "-"),):
        s = levels(h, m); s = s[(s.index >= lo) & (s.index <= hi)]
        ax.plot(s.index, s.values, ls=ls, color=COLORS[KEY[m]], lw=1.4, label=f"3か月前の予測：{KEY[m]}")
ax.axvspan(pd.Timestamp("2020-04-01"), pd.Timestamp("2020-05-31"), color="#fce8e6", alpha=.7)
ax.text(pd.Timestamp("2020-04-05"), 3.15, "緊急事態宣言\n（2020年4〜5月）", fontsize=8, color="#a50e0e")
ax.set_ylabel("完全失業率（%）"); ax.set_title("コロナ期の予測（3か月先）：上がり始めはどのモデルも遅れ、求人を使うモデルは上がりきる前後で上がり過ぎを予測した")
ax.legend(fontsize=9, frameon=False, ncol=2); ax.grid(alpha=.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y/%m"))
fig.tight_layout(); fig.savefig(FIG / "a13_covid.png"); plt.close()

# 4. 重要度（3か月先）
fig, axes = plt.subplots(1, 2, figsize=(11, 5))
s = imp["LightGBM_SHAP_3"].sort_values(ascending=False).head(12)[::-1]
axes[0].barh(s.index, s.values, color=COLORS["LightGBM"])
axes[0].set_title("LightGBM：予測への平均的な効き方（SHAP、3か月先）"); axes[0].set_xlabel("|SHAP| の平均（%ポイント）")
c = imp["ElasticNet_coef_3"]; c = c[c.abs() > 1e-4].sort_values(key=np.abs, ascending=False).head(12)[::-1]
axes[1].barh(c.index, c.values, color=[COLORS["ElasticNet"] if v < 0 else "#f9ab00" for v in c.values])
axes[1].axvline(0, color="black", lw=.8)
axes[1].set_title("ElasticNet：標準化した係数（3か月先）"); axes[1].set_xlabel("1標準偏差あたりの失業率の変化（%ポイント）")
for ax in axes: ax.tick_params(axis="y", labelsize=9); ax.grid(axis="x", alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "a13_importance.png"); plt.close()

# 5. 方向一致率
fig, ax = plt.subplots(figsize=(9, 4.2))
w = .38
for k, h in enumerate((1, 3)):
    d = allp[allp.h == h].set_index("model").loc[ORDER]
    x = np.arange(len(d)) + (k - .5) * w
    ax.bar(x, d["方向一致率"] * 100, w, label=f"{h}か月先", color=["#8ab4f8", "#1a73e8"][k])
    for xi, v in zip(x, d["方向一致率"] * 100):
        ax.text(xi, v + 1, f"{v:.0f}", ha="center", fontsize=8)
ax.set_xticks(range(len(ORDER))); ax.set_xticklabels([o.replace("（", "\n（") for o in ORDER], fontsize=9)
ax.set_ylabel("当たった割合（%）"); ax.set_ylim(0, 65)
ax.set_title("「上がる・横ばい・下がる」の向きが当たった割合（±0.05pt 未満を横ばい）")
ax.legend(frameon=False); ax.grid(axis="y", alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "a13_direction.png"); plt.close()

# 6. 頑健性（3か月先）
r = rob[rob.h == 3].copy()
r["lab"] = r["チェック"] + "：" + r["model"]
order = ["基本", "学習を直近15年に", "失業率の過去だけ", "未公表の値を使う（リーク）", "原数値で予測"]
r["o"] = r["チェック"].map({k: i for i, k in enumerate(order)})
r = r.sort_values(["o", "model"])
fig, ax = plt.subplots(figsize=(10, 5.4))
cols = ["#e37400" if c != "原数値で予測" else "#9aa0a6" for c in r["チェック"]]
ax.barh(range(len(r)), r["MAE_ナイーブ比"], color=cols)
ax.axvline(1, color="black", lw=1)
for i, v in enumerate(r["MAE_ナイーブ比"]):
    ax.text(v + .01, i, f"{v:.2f}", va="center", fontsize=8)
ax.set_yticks(range(len(r))); ax.set_yticklabels(r["lab"], fontsize=8.5); ax.invert_yaxis()
ax.set_xlabel("平均絶対誤差（それぞれの前月の値＝1）")
ax.set_title("頑健性チェック（3か月先）\n灰色＝原数値で予測。「前月の値」が季節を無視するので、楽に勝てて見える", fontsize=11)
ax.grid(axis="x", alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "a13_robustness.png"); plt.close()
print("ok")
