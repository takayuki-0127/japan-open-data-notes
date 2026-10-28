"""04 図：5枚"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from common import *

plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
C1, C2, CB = "#1f5fa8", "#9a9a9a", "#d8e2ef"
eff = pd.read_csv(RES / "effects.csv"); rec = pd.read_csv(RES / "recovery.csv")
rob = pd.read_csv(RES / "robustness.csv"); stk = pd.read_csv(RES / "stacked.csv", index_col="k")
E1L = pd.read_csv(RES / "E1_long.csv", index_col="k")
y = load("japanese")
pct = lambda v: (np.exp(v) - 1) * 100

# f01 被災した県と対照の県の、季節をならした宿泊者数（事前の同じ月の平均との差）
fig, axs = plt.subplots(2, 2, figsize=(11, 7), sharey=True)
for ax, (key, ev) in zip(axs.flat, EVENTS.items()):
    pre, h = (12, 23) if key == "E4" else (PRE, H)
    t0, lo, hi = window(ev, pre, h); dn = donors(ev, y.columns, pre, h)
    s = deseason(y, t0, lo, ev.get("seas")); s = s[(s.index >= lo) & (s.index <= hi)]
    for c in dn:
        ax.plot(s.index, pct(s[c]), color=C2, lw=0.5, alpha=0.35)
    ax.plot(s.index, pct(s[dn].mean(axis=1)), color="k", lw=1.6, label=f"対照の県の平均（{len(dn)}県）")
    ax.plot(s.index, pct(s[ev["tr"]].mean(axis=1)), color=C1, lw=2.2, label="・".join(p[2:] for p in ev["tr"]))
    ax.axvline(t0, color="#c0392b", lw=1, ls="--"); ax.axhline(0, color="k", lw=0.5)
    ax.set_title(f"{ev['name']}（{t0:%Y年%-m月}）", fontsize=12); ax.legend(fontsize=8.5, loc="lower left", frameon=False)
    ax.set_ylim(-60, 45); ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
axs[0, 0].set_ylabel("事前の同じ月の平均との差（%）"); axs[1, 0].set_ylabel("事前の同じ月の平均との差（%）")
fig.suptitle("日本人の延べ宿泊者数：事例の県と対照の県（灰色の細線は対照の各県）", fontsize=13)
fig.text(0.01, 0.005, "出典：観光庁「宿泊旅行統計調査」をもとに作成者が加工。事前24か月の同じ月の平均との差（能登半島地震はコロナ前2017〜2019年の同じ月の平均との差）", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.02, 1, 0.96)); fig.savefig(FIG / "f01_series.png", dpi=150); plt.close()

# f02 イベントスタディ：対照との差と、プラセボの90%の帯
fig, axs = plt.subplots(2, 2, figsize=(11, 7), sharey=True)
for ax, (key, ev) in zip(axs.flat, EVENTS.items()):
    d = eff[(eff.event == key) & (eff.name == ev["name"])].set_index("k")
    ax.fill_between(d.index, pct(d.lo), pct(d.hi), color=CB, label="プラセボの90%の帯")
    ax.plot(d.index, pct(d.effect), color=C1, lw=2, marker="o", ms=3, label="対照の県との差")
    ax.axvline(-0.5, color="#c0392b", lw=1, ls="--"); ax.axhline(0, color="k", lw=0.5)
    ax.axhline(-5, color="#888", lw=0.8, ls=":")
    r = rec[rec.name == ev["name"]].iloc[0]
    rr = "期間内に戻らず" if pd.isna(r.thr5) else f"{int(r.thr5)}か月目"
    ttl = f"{ev['name']}：−5%以内に戻ったのは {rr}" if key != "E4" else f"{ev['name']}：最初の1年は対照より多く、13か月目から下に"
    ax.set_title(ttl, fontsize=11.5)
    ax.set_xlabel("開始月からの月数"); ax.set_ylim(-45, 50)
    ax.legend(fontsize=8.5, loc="lower right", frameon=False)
axs[0, 0].set_ylabel("対照の県との差（%）"); axs[1, 0].set_ylabel("対照の県との差（%）")
fig.suptitle("災害のあとの宿泊者数（日本人）の、対照の県との差", fontsize=13)
fig.text(0.01, 0.005, "点線は −5%。帯は、対照の県から同じ数の県を「被災した」とみなして同じ計算をした値の5〜95%。出典：観光庁「宿泊旅行統計調査」をもとに作成者が加工", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.02, 1, 0.96)); fig.savefig(FIG / "f02_event_study.png", dpi=150); plt.close()

# f03 県ごとの、最初の6か月の差と戻るまでの月数
r = rec[rec.name.str.contains("／")].copy()
r["lab"] = r.name.str.replace("／", "\n")
fig, axs = plt.subplots(1, 2, figsize=(11, 5.2), gridspec_kw=dict(width_ratios=[1.1, 1]))
yy = np.arange(len(r))[::-1]
axs[0].barh(yy, pct(r.mean_0_5), color=C1, height=0.6)
axs[0].barh(yy, pct(r.trough), color="none", edgecolor="#333", height=0.6, ls="--")
axs[0].set_yticks(yy, r.lab, fontsize=9); axs[0].axvline(0, color="k", lw=0.6)
axs[0].set_xlabel("対照の県との差（%）"); axs[0].set_title("開始から6か月の平均（塗り）と、最も下がった月（枠）", fontsize=11)
for i, (a, b) in enumerate(zip(r.mean_0_5, r.trough)):
    axs[0].text(max(pct(a), 0) + 0.8, yy[i], f"{pct(a):+.0f}%（最低 {pct(b):.0f}%）", va="center", ha="left", fontsize=8)
axs[0].set_xlim(-32, 48)
for j, (col, lab, c) in enumerate([("thr3", "−3%以内", "#9ec3e6"), ("thr5", "−5%以内", C1), ("thr10", "−10%以内", "#0b2e59")]):
    v = r[col].fillna(r.h + 1)
    axs[1].barh(yy + (1 - j) * 0.25, v, height=0.25, color=c, label=lab)
    for i, (vv, raw) in enumerate(zip(v, r[col])):
        axs[1].text(vv + 0.3, yy[i] + (1 - j) * 0.25, "戻らず" if pd.isna(raw) else f"{int(raw)}", va="center", fontsize=7.5)
axs[1].set_yticks(yy, [""] * len(r)); axs[1].set_xlabel("戻るまでの月数（3か月続けて基準以内に入った最初の月）")
axs[1].set_title("戻るまでの月数は、基準の置き方で変わる", fontsize=11); axs[1].legend(fontsize=8.5, frameon=False, loc="lower right")
fig.text(0.01, 0.005, "「戻らず」は、見た期間（コロナ前の事例は2020年1月まで、能登半島地震は2025年12月まで）のうちに基準に入らなかったもの。出典：観光庁「宿泊旅行統計調査」をもとに作成者が加工", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "f03_by_pref.png", dpi=150); plt.close()

# f04 3事例を重ねた平均と、熊本地震の長い期間
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
d = stk.loc[-12:H]
axs[0].fill_between(d.index, pct(d.lo), pct(d.hi), color=CB, label="プラセボの90%の帯")
axs[0].plot(d.index, pct(d.effect), color=C1, lw=2, marker="o", ms=3, label="3事例の平均")
axs[0].axvline(-0.5, color="#c0392b", lw=1, ls="--"); axs[0].axhline(0, color="k", lw=0.5); axs[0].axhline(-5, color="#888", lw=0.8, ls=":")
axs[0].set_title("コロナ前の3事例を開始月でそろえた平均", fontsize=11); axs[0].set_xlabel("開始月からの月数"); axs[0].set_ylabel("対照の県との差（%）")
axs[0].legend(fontsize=8.5, frameon=False, loc="lower right")
d = E1L.loc[-12:]
axs[1].fill_between(d.index, pct(d.lo), pct(d.hi), color=CB)
axs[1].plot(d.index, pct(d.effect), color=C1, lw=1.6, marker="o", ms=2.5)
axs[1].axvline(-0.5, color="#c0392b", lw=1, ls="--"); axs[1].axhline(0, color="k", lw=0.5); axs[1].axhline(-5, color="#888", lw=0.8, ls=":")
axs[1].set_title("熊本地震：コロナ前（2019年12月）まで長く見る", fontsize=11); axs[1].set_xlabel("開始月からの月数")
fig.text(0.01, 0.005, "3事例：熊本地震・平成30年7月豪雨・北海道胆振東部地震（各事例を同じ重みで平均）。出典：観光庁「宿泊旅行統計調査」をもとに作成者が加工", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "f04_stacked_long.png", dpi=150); plt.close()

# f05 頑健性：設定ごとの、最も下がった月の差と、−5%以内に戻るまでの月数（コロナ前の事例）
rb = rob[rob.event != "E4"]
sets = list(dict.fromkeys(rb.setting))
fig, axs = plt.subplots(1, 2, figsize=(11, 5.4), sharey=True)
cols = {"E1": "#1f5fa8", "E2": "#e08a1e", "E3": "#3a9e5c", "E5": "#7f7f7f"}
off = {"E1": .2, "E2": 0, "E3": -.2, "E5": -.2}
for key, g in rb.groupby("event", sort=False):
    yy = [len(sets) - 1 - sets.index(s) + off[key] for s in g.setting]
    axs[0].scatter(pct(g.trough), yy, color=cols[key], s=34, label=g.name.iloc[0], zorder=3)
    v = g.rec5.fillna(g.h + 1)
    axs[1].scatter(v, yy, color=cols[key], s=34, zorder=3, marker="s")
axs[0].set_yticks(range(len(sets))[::-1], sets, fontsize=9)
axs[0].set_xlabel("最も下がった月の、対照の県との差（%）"); axs[0].grid(axis="x", alpha=0.3); axs[0].axvline(0, color="k", lw=0.6)
axs[1].set_xlabel("−5%以内に戻るまでの月数"); axs[1].grid(axis="x", alpha=0.3); axs[1].set_xlim(-0.5, 17.5)
fig.legend(*axs[0].get_legend_handles_labels(), loc="upper center", ncol=4, fontsize=9, frameon=False)
fig.text(0.01, 0.005, "九州北部豪雨（灰）は事例を増やした確認。能登半島地震は最初の1年が対照より多いため、ここには入れていない。出典：観光庁「宿泊旅行統計調査」をもとに作成者が加工", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 0.93)); fig.savefig(FIG / "f05_robustness.png", dpi=150); plt.close()
print("figs ok")
