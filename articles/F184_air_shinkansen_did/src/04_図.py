# -*- coding: utf-8 -*-
"""F184 図（results/*.csv から）"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
R = os.path.join(ROOT, "results")
F = os.path.join(ROOT, "figures")
os.makedirs(F, exist_ok=True)
for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if os.path.exists(p):
        font_manager.fontManager.addfont(p)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150

CORE = [("東北・新青森", "羽田―青森"), ("九州・全線", "鹿児島―福岡"), ("九州・全線", "大阪―熊本"),
        ("九州・全線", "大阪―鹿児島"), ("北陸・金沢", "羽田―富山"), ("北陸・金沢", "羽田―金沢(小松)"),
        ("北海道・新函館北斗", "羽田―函館")]
COL = {"羽田―青森": "#4c72b0", "鹿児島―福岡": "#c44e52", "大阪―熊本": "#dd8452", "大阪―鹿児島": "#937860",
       "羽田―富山": "#55a868", "羽田―金沢(小松)": "#8172b3", "羽田―函館": "#64b5cd"}
LAB = {"羽田―金沢(小松)": "羽田―小松"}

main = pd.read_csv(os.path.join(R, "did_main.csv"))
rob = pd.read_csv(os.path.join(R, "did_robustness.csv"))
es = pd.read_csv(os.path.join(R, "event_study.csv"))
pool = pd.read_csv(os.path.join(R, "event_study_pooled.csv"))
mi = pd.read_csv(os.path.join(R, "monthly_index.csv"))
pooled = pd.read_csv(os.path.join(R, "did_pooled.csv")).iloc[0]

# 図1 イベントスタディ
fig, ax = plt.subplots(figsize=(8, 4.8))
for ev, r in CORE:
    s = es[(es.event == ev) & (es.route == r)].sort_values("k")
    s = s[(s.k >= -4) & (s.k <= 4)]
    ax.plot(s.k, s.gap_pct, "-o", ms=3, lw=1.2, color=COL[r], alpha=0.8, label=f"{LAB.get(r, r)}（{ev.split('・')[0]}）")
p = pool[(pool.k >= -4) & (pool.k <= 4)]
ax.plot(p.k, p.gap_pct, "-", lw=3.2, color="black", label="7路線の平均")
ax.axhline(0, color="gray", lw=0.8)
ax.axvline(-0.5, color="gray", lw=0.8, ls="--")
ax.set_xlabel("開業の年からの年数（0＝開業後最初の年）")
ax.set_ylabel("対照路線との差（開業前年＝0、%）")
ax.set_title("新幹線の開業前後の旅客数：対照路線の平均との差")
ax.legend(fontsize=7.5, ncol=2, loc="lower left")
fig.tight_layout()
fig.savefig(os.path.join(F, "f184_event_study.png"))
plt.close(fig)

# 図2 路線ごとの差の差と頑健性の幅、偶然の幅
order = ["鹿児島―福岡", "羽田―富山", "羽田―金沢(小松)", "大阪―熊本", "大阪―鹿児島", "羽田―青森", "羽田―函館", "羽田―三沢", "羽田―金沢(小松)@敦賀"]
rows = []
for _, x in main.iterrows():
    key = x.route + ("@敦賀" if x.event == "北陸・敦賀" else "")
    rr = rob[(rob.event == x.event) & (rob.route == x.route)]
    rows.append(dict(key=key, est=x.did_pct, lo=rr.did_pct.min(), hi=rr.did_pct.max(), p=x.perm_p, ev=x.event))
d = pd.DataFrame(rows).set_index("key").loc[order].reset_index()
pl = pd.read_csv(os.path.join(R, "placebo_spread.csv")).iloc[0]
fig, ax = plt.subplots(figsize=(8, 4.8))
y = np.arange(len(d))[::-1]
ax.axvspan(pl.q05, pl.q95, color="#dddddd", label="対照路線どうしの偶然の幅（95%）")
ax.hlines(y, d.lo, d.hi, color="#555555", lw=2, label="条件を変えた13通りの幅")
ax.plot(d.est, y, "o", color="#c44e52", ms=7, label="主の推定")
names = []
for _, x in d.iterrows():
    k = x["key"]
    n = LAB.get(k.replace("@敦賀", ""), k.replace("@敦賀", ""))
    names.append(n + ("（敦賀延伸）" if "@敦賀" in k else f"（{x.ev.split('・')[0]}）"))
ax.set_yticks(y)
ax.set_yticklabels(names, fontsize=9)
ax.axvline(0, color="gray", lw=0.8)
ax.set_xlabel("開業後3年の旅客数の変化：対照との差（%）")
ax.set_title("路線ごとの差の差（三沢は所要時間がほぼ変わらない比較用）")
ax.legend(fontsize=8, loc="lower right")
fig.tight_layout()
fig.savefig(os.path.join(F, "f184_did_routes.png"))
plt.close(fig)

# 図3 鉄道の所要時間と減り方
c = main.set_index(["event", "route"]).loc[CORE].reset_index()
fig, ax = plt.subplots(figsize=(7, 4.6))
ax.scatter(c.rail_h, c.did_pct, s=60, color=[COL[r] for r in c.route], zorder=3)
for _, x in c.iterrows():
    ax.annotate(LAB.get(x.route, x.route), (x.rail_h, x.did_pct), xytext=(6, 4), textcoords="offset points", fontsize=9)
b = np.polyfit(c.rail_h, np.log(c.did_pct / 100 + 1), 1)
xx = np.linspace(1.2, 4.0, 50)
ax.plot(xx, np.expm1(b[1] + b[0] * xx) * 100, color="gray", ls="--", lw=1)
ax.axhline(0, color="gray", lw=0.8)
ax.set_xlabel("開業時の鉄道の最速所要時間（新幹線の駅まで、時間、おおよそ）")
ax.set_ylabel("開業後3年の旅客数：対照との差（%）")
ax.set_title(f"鉄道が速いほど、空の便は大きく減った（順位相関 {pooled.spearman_rail:.2f}）")
ax.set_ylim(-85, 5)
fig.tight_layout()
fig.savefig(os.path.join(F, "f184_rail_time.png"))
plt.close(fig)

# 図4 月次の指数（開業の13〜24か月前の同じ月＝100、対照で割る）
fig, axes = plt.subplots(2, 2, figsize=(9, 5.6), sharey=True)
pick = [("九州・全線", "鹿児島―福岡"), ("北陸・金沢", "羽田―富山"), ("北陸・金沢", "羽田―金沢(小松)"), ("北海道・新函館北斗", "羽田―函館")]
for ax, (ev, r) in zip(axes.ravel(), pick):
    s = mi[(mi.event == ev) & (mi.route == r)].sort_values("t")
    s = s[(s.t >= -24) & (s.t <= 36)]
    ax.plot(s.t, s.idx, color=COL[r], lw=1.4)
    ax.axhline(100, color="gray", lw=0.8)
    ax.axvline(0, color="gray", lw=0.8, ls="--")
    ax.set_title(f"{LAB.get(r, r)}（{ev}）", fontsize=10)
    ax.set_ylim(0, 140)
for ax in axes[1]:
    ax.set_xlabel("開業月からの月数")
for ax in axes[:, 0]:
    ax.set_ylabel("開業の2年前の同じ月＝100\n（対照路線の動きを除く）")
fig.suptitle("月ごとの旅客数：開業の月からすぐに下がり、その後の戻りは小さい", fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(F, "f184_monthly.png"))
plt.close(fig)

# 図5 旅客・座席・搭乗率
c = main.set_index(["event", "route"]).loc[CORE].reset_index()
fig, ax = plt.subplots(figsize=(8, 4.4))
x = np.arange(len(c))
ax.bar(x - 0.2, c.did_pct, 0.4, color="#c44e52", label="旅客数（%）")
ax.bar(x + 0.2, c.did_seats_pct, 0.4, color="#4c72b0", label="座席数（%）")
for i, v in enumerate(c.did_lf_pts):
    ax.text(i, 3, f"{v:+.1f}pt", ha="center", fontsize=8.5)
ax.axhline(0, color="gray", lw=0.8)
ax.set_xticks(x)
ax.set_xticklabels([LAB.get(r, r) for r in c.route], fontsize=9)
ax.set_ylabel("開業後3年：対照との差（%）")
ax.set_ylim(-85, 12)
ax.set_title("座席もほぼ同じだけ減った（上の数字は搭乗率の差、ポイント）")
ax.legend(fontsize=8.5, loc="lower right")
fig.tight_layout()
fig.savefig(os.path.join(F, "f184_seats.png"))
plt.close(fig)
print("ok")
