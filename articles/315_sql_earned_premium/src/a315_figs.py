"""315 図3枚"""
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from common import RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

ex = pd.read_csv(RES / "one_policy.csv"); fy = pd.read_csv(RES / "fy2025_by_month.csv"); sc = pd.read_csv(RES / "scenarios.csv")
k12, k24 = ex.columns[2], ex.columns[3]

fig, ax = plt.subplots(figsize=(9.4, 4.4))
x = np.arange(len(ex)); w = 0.27
ax.bar(x - w, ex["日割り"], w, color=INK, label="日割り"); ax.bar(x, ex[k12], w, color=BLUE, label="12分の1"); ax.bar(x + w, ex[k24], w, color=ORANGE, label="24分の1")
ax.set_xticks(x); ax.set_xticklabels([f"{pd.Timestamp(m).month}月" for m in ex.month_start], fontsize=9); ax.set_ylabel("その月の売上にする額（円）")
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.0)); ax.set_ylim(0, 12500)
ax.set_title("始期 5月20日・保険料 12万円の契約1件を、月ごとに分けると\n（12分の1は始期の月をまるごと数え、翌年5月の分がない）", loc="left")
save(fig, "a315_one_policy.png")

fig, ax = plt.subplots(figsize=(9.4, 4.4))
x = np.arange(12); w = 0.38
ax.bar(x - w / 2, fy["12分の1の差(%)"], w, color=BLUE, label="12分の1"); ax.bar(x + w / 2, fy["24分の1の差(%)"], w, color=ORANGE, label="24分の1")
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels([f"{pd.Timestamp(m).month}月" for m in fy.month_start]); ax.set_ylabel("日割りとの差（%）"); ax.legend(frameon=False)
ax.set_title("月の売上は、日数の少ない2月に約9%多く、31日の月に1〜2%少なく出た\n（月割りは、どの月も同じ長さとして分けるため）", loc="left")
save(fig, "a315_by_month.png")

fig, ax = plt.subplots(figsize=(9.4, 4.4))
x = np.arange(len(sc)); w = 0.38
a, b = sc["未経過保険料の差・12分の1(%)"], sc["未経過保険料の差・24分の1(%)"]
ax.bar(x - w / 2, a, w, color=BLUE, label="12分の1"); ax.bar(x + w / 2, b, w, color=ORANGE, label="24分の1")
for i in range(len(sc)):
    ax.text(i - w / 2, a[i] - 0.5, f"{a[i]:+.1f}".replace("-", "−"), ha="center", va="top", fontsize=9)
    ax.text(i + w / 2, b[i] + (0.4 if b[i] >= 0 else -0.5), f"{b[i]:+.1f}".replace("-", "−"), ha="center", va="bottom" if b[i] >= 0 else "top", fontsize=9)
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels([s.replace("（基本）", "\n（基本）").replace("＋", "\n＋") for s in sc["置き方"]], fontsize=9)
ax.set_ylim(-15, 8); ax.set_ylabel("年度末の未経過保険料：日割りとの差（%）"); ax.legend(frameon=False, loc="upper right")
ax.set_title("年度末に残る未経過保険料は、12分の1だと 5〜12% 少なく出た。\n24分の1は、始期が月の中でばらばらなら合い、月初や月末に集まるとずれた", loc="left")
save(fig, "a315_unearned.png")
