"""313 図3枚"""
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from common import RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

s = pd.read_csv(RES / "nine_writings.csv"); bm = pd.read_csv(RES / "by_month.csv"); sw = pd.read_csv(RES / "last_day_weight_sweep.csv")
lab = [n.replace("_", " ", 1) for n in s["書き方"]]

# 図1：落ちた行と余分な行
fig, ax = plt.subplots(figsize=(9.4, 5.2))
y = np.arange(9)
ax.barh(y, -s["落ちた行(%)・12か月平均"], color=BLUE, label="落ちた行"); ax.barh(y, s["余分な行(%)・12か月平均"], color=ORANGE, label="余分に入った行")
ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=9); ax.invert_yaxis(); ax.axvline(0, color=INK, lw=0.8)
for i, r in s.iterrows():
    a, b = r["落ちた行(%)・12か月平均"], r["余分な行(%)・12か月平均"]
    if a == 0 and b == 0:
        ax.text(0.15, i, "ずれなし" if r["正しい月の数"] == 12 else "12か月で1行だけ落ちた", va="center", fontsize=9, color=GRAY)
    if a > 0: ax.text(-a - 0.15, i, f"−{a:.1f}%", va="center", ha="right", fontsize=9.5)
    if b > 0: ax.text(b + 0.15, i, f"+{b:.1f}%", va="center", ha="left", fontsize=9.5)
ax.set_xlim(-8, 6); ax.set_xlabel("その月の正しい行数に対する割合（%、12か月の平均）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("BETWEEN 初日 AND 最終日 は、最終日の0時より後を全部落とした\n（最終日の取引がふつうの日の2倍ある置き方で、月の行の6.2%）", loc="left")
save(fig, "a313_nine.png")

# 図2：UTC の列にそのまま当てたとき（W8）の月ごとの入れ替わり
fig, ax = plt.subplots(figsize=(9.4, 4.6))
months = sorted(bm["月"].unique()); x = np.arange(12)
d = bm[bm["書き方"].str.startswith("W8")].set_index("月").loc[months]
ax.bar(x, -d["落ちた行(%)"], color=BLUE, label="落ちた行（月初の0〜9時）"); ax.bar(x, d["余分な行(%)"], color=ORANGE, label="余分に入った行（翌月の0〜9時）")
ax.plot(x, d["合計の差(%)"], "-o", color=INK, ms=4, label="その月の合計の差")
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels([m[2:].replace("-", "/") for m in months], fontsize=9)
ax.set_ylabel("その月の正しい値に対する割合（%）"); ax.set_ylim(-4.2, 5.2); ax.legend(frameon=False, fontsize=9, loc="upper left", ncol=3)
mx = d["合計の差(%)"].abs().iloc[:-1].max()
ax.set_title(f"UTC の列にそのまま当てると、毎月 約{d['落ちた行(%)'].mean():.1f}% の行が隣の月と入れ替わる。\n合計の差は {mx:.1f}% 以内で、ほぼ合って見える（データの最後の月を除く）", loc="left")
save(fig, "a313_by_month.png")

# 図3：最終日に取引が集まるほど
fig, ax = plt.subplots(figsize=(8.6, 4.4))
for key, c, name in [("W1", BLUE, "W1 BETWEEN 初日 AND 最終日"), ("W8", GREEN, "W8 UTC の列にそのまま")]:
    d = sw[sw["書き方"].str.startswith(key)]
    ax.plot(d["最終日の重み"], d["落ちた行(%)"], "-o", color=c, label=name)
    for _, r in d.iterrows(): ax.text(r["最終日の重み"], r["落ちた行(%)"] + 0.6, f"{r['落ちた行(%)']:.1f}%", ha="center", fontsize=9)
ax.set_xticks([1, 2, 3, 5]); ax.set_xticklabels(["1倍\n（毎日同じ）", "2倍\n（基本）", "3倍", "5倍"]); ax.set_ylim(0, 17)
ax.set_xlabel("月の最終日の取引が、ふつうの日の何倍あるか"); ax.set_ylabel("落ちた行（%、12か月の平均）"); ax.legend(frameon=False, loc="upper left")
ax.set_title("月末に取引が集まる業務ほど、最終日を落とす書き方の影響は大きい", loc="left")
save(fig, "a313_weight.png")
