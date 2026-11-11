# 05_図：図1〜5（図6はダッシュボードの画像。06_ダッシュボード画像.py）
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
ROOT = Path(__file__).resolve().parents[1]
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
M = json.load(open(R / "main.json"))

# 図1：業界全体の広告と小売の前年同月比、どちらが先に動くか
p = pd.read_csv(D / "panel_2014_2024.csv", index_col="ym")
p.index = pd.PeriodIndex(p.index, freq="M").to_timestamp()
g = (np.log(p) - np.log(p).shift(12)) * 100
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.7, 1]})
ax[0].axvspan(pd.Timestamp("2020-04-01"), pd.Timestamp("2021-12-31"), color="#eee")
ax[0].plot(g.index, g["total"], color="#2b6cb0", lw=1.6, label="広告業の売上高（広告費の目安）")
ax[0].plot(g.index, g["小売3業態計"], color="#c05621", lw=1.6, label="小売3業態の販売額")
ax[0].axhline(0, color="#999", lw=0.8)
ax[0].set_title("前年同月比（%）。灰色はコロナ期", fontsize=11)
ax[0].legend(fontsize=9, frameon=False, loc="lower left")
cc = pd.DataFrame(M["A"]["lead_lag"])
cols = ["#c05621" if k < 0 else ("#888" if k == 0 else "#2b6cb0") for k in cc["ずれ_月"]]
ax[1].bar(cc["ずれ_月"], cc["相関"], color=cols)
ax[1].axhline(0, color="#999", lw=0.8)
ax[1].set_xlabel("ずれ（月）　← 売上が先に動く ｜ 広告が先に動く →")
ax[1].set_title("広告と売上の前年同月比の相関（コロナ期を除く）", fontsize=11)
fig.suptitle("業界全体では、売上が先に動き、広告があとから動く形が見えた（相関は弱い）", fontsize=13, x=0.01, ha="left")
fig.tight_layout()
fig.savefig(F / "fig1_industry_lead_lag.png", dpi=150)
plt.close(fig)

# 図2：推定の仕方で「広告の効き目」が変わる
A = pd.DataFrame(M["A"]["rows"])
fig, ax = plt.subplots(figsize=(11, 4.8))
specs = A["推定"].unique()
media = ["広告業の売上高合計", "テレビ", "インターネット広告"]
colm = ["#2b6cb0", "#805ad5", "#2f855a"]
for i, sp in enumerate(specs):
    for j, m in enumerate(media):
        r = A[(A["推定"] == sp) & (A["媒体"] == m)].iloc[0]
        y = i + (j - 1) * 0.22
        ax.plot([r["下限"], r["上限"]], [y, y], color=colm[j], lw=2)
        ax.plot(r["弾力性"], y, "o", color=colm[j], label=m if i == 0 else None)
ax.axvline(0, color="#999", lw=0.8)
ax.set_yticks(range(len(specs)))
ax.set_yticklabels(specs)
ax.invert_yaxis()
ax.set_xlabel("広告費が1%多い月の小売販売額の差（%）＝弾力性。線は95%区間")
ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title("業界全体のデータでは、季節とトレンドをそろえると広告の効き目は0と区別できなくなる", fontsize=12, loc="left")
fig.tight_layout()
fig.savefig(F / "fig2_industry_specs.png", dpi=150)
plt.close(fig)

# 図3：アドストックと飽和（架空の会社の本当の設定）
T = M["TRUE"]
CH = ["テレビ", "Web", "チラシ"]
col3 = ["#2b6cb0", "#2f855a", "#c05621"]
SC = np.array(M["SCALE"])
MS = np.array(M["MEAN_SP"])
fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
for j, c in enumerate(CH):
    d = T["decay"][j]
    w = np.arange(0, 9)
    ax[0].plot(w, d ** w, "o-", color=col3[j], label=f"{c}（減り方 {d}）")
    s = np.linspace(0, 120, 200)
    x = s / (1 - d) / SC[j]
    ax[1].plot(s, T["beta"][j] * x / (x + T["K"][j]), color=col3[j], label=c)
    xm = MS[j] / (1 - d) / SC[j]
    ax[1].plot(MS[j], T["beta"][j] * xm / (xm + T["K"][j]), "o", color=col3[j])
ax[0].set_title("アドストック：1週の広告の効き目が何週残るか", fontsize=11)
ax[0].set_xlabel("広告を出してからの週")
ax[0].legend(frameon=False, fontsize=9)
ax[1].set_title("飽和：週の広告費と売上の上乗せ（点はいまの出し方）", fontsize=11)
ax[1].set_xlabel("週の広告費（万円、出し続けた場合）")
ax[1].set_ylabel("売上の上乗せ（万円／週）")
ax[1].legend(frameon=False, fontsize=9)
fig.suptitle("みどりホーム（架空）の本当の設定：テレビは効き目が残り、チラシは出しすぎで頭打ち", fontsize=12, x=0.01, ha="left")
fig.tight_layout()
fig.savefig(F / "fig3_adstock_saturation.png", dpi=150)
plt.close(fig)

# 図4：ROI の当たり方（60回のシミュレーション）
B = pd.read_csv(R / "B_simulation_roi.csv")
fig, ax = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
for k, scen in enumerate(["ばらばら", "需要に合わせる"]):
    g = B[B["場面"] == scen]
    data, labels, cl = [], [], []
    for j, c in enumerate(CH):
        data.append((g[f"MMM_{c}"] / g[f"真_{c}"] - 1) * 100)
        labels.append(f"MMM\n{c}")
        cl.append(col3[j])
    data.append((g["実験_Web"] / g["真_Web"] - 1) * 100)
    labels.append("地域実験\nWeb")
    cl.append("#555")
    data.append((g["補正MMM_チラシ"] / g["真_チラシ"] - 1) * 100)
    labels.append("実験で補正\nしたMMM\nチラシ")
    cl.append("#e9a06a")
    bp = ax[k].boxplot(data, tick_labels=labels, patch_artist=True, showfliers=False, widths=0.55)
    for patch, c in zip(bp["boxes"], cl):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
    ax[k].axhline(0, color="#999", lw=0.8)
    ax[k].set_title({"ばらばら": "広告費が需要と関係なく動く場合", "需要に合わせる": "広告費を需要の見込みに合わせて動かす場合"}[scen], fontsize=11)
ax[0].set_ylabel("ROI の推定 ÷ 本当の ROI − 1（%）")
fig.suptitle("需要に合わせて広告費を動かすと、MMM は Web とチラシを大きく見積もる。地域実験はずれが小さい", fontsize=12, x=0.01, ha="left")
fig.tight_layout()
fig.savefig(F / "fig4_roi_recovery.png", dpi=150)
plt.close(fig)

# 図5：予算配分（本当の売上の上乗せ、最適＝100）
C = pd.read_csv(R / "C_allocation.csv")
fig, ax = plt.subplots(figsize=(12, 4.6))
y = np.arange(len(C))
v = C["最適に対する割合"] * 100
lo = C["25%点"] * 100
hi = C["75%点"] * 100
ax.barh(y, v, color=["#999", "#2b6cb0"] + ["#7aa6d6"] * (len(C) - 2))
ax.errorbar(v, y, xerr=[v - lo, hi - v], fmt="none", ecolor="#333", capsize=3)
for i, r in C.iterrows():
    ax.text(100.6, i, f'{r["最適に対する割合"]*100:.1f}　（テレビ{r["テレビ"]*100:.0f}・Web{r["Web"]*100:.0f}・チラシ{r["チラシ"]*100:.0f}%）', va="center", fontsize=9)
ax.set_yticks(y)
ax.set_yticklabels(C["配分の決め方"])
ax.invert_yaxis()
ax.set_xlim(90, 108)
ax.set_xlabel("本当の売上の上乗せ（本当の曲線で最適化した配分＝100）。MMM の行は60回の中央値、線は25〜75%点")
ax.set_title("配分の見直しで上がるのは約5%。MMM で決めると多くはその近くだが、4〜10回に1回はいまより悪くなる", fontsize=11, loc="left")
fig.tight_layout()
fig.savefig(F / "fig5_allocation.png", dpi=150)
plt.close(fig)
print("ok")
