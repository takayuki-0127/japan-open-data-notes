"""F283 04 図：6枚。"""
import json
import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

BASE = pathlib.Path(__file__).resolve().parents[1]
FIG = BASE / "figures"
FIG.mkdir(exist_ok=True)
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.hashsalt"] = "f283"

panel = pd.read_csv(BASE / "data" / "panel.csv")
ev = pd.read_csv(BASE / "results" / "A_events.csv")
pl = pd.read_csv(BASE / "results" / "B_placebo.csv")
main = json.loads((BASE / "results" / "main.json").read_text(encoding="utf-8"))
C_UP, C_DN, C_GR = "#c0392b", "#2471a3", "#7f8c8d"
NAMES = {"T1": "たばこ 2018年", "T2": "たばこ 2020年", "T3": "たばこ 2021年",
         "A1": "発泡酒・ビール風 2020年", "A2": "発泡酒・ビール風 2023年",
         "W1": "ワイン 2020年", "W2": "ワイン 2023年",
         "B1": "ビール 2020年（値下げ）", "B2": "ビール 2023年（値下げ）",
         "S1": "清酒 2020年（値下げ）", "S2": "清酒 2023年（値下げ）"}


def ymdate(ym):
    return pd.to_datetime([f"{v // 100}-{v % 100:02d}-01" for v in ym])


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)


# 図1：たばこと発泡酒・ビール風の月の量（実質の支出、前年同月比）
fig, axes = plt.subplots(2, 1, figsize=(9, 6.4), sharex=True)
for ax, item, title, marks in [
    (axes[0], "tobacco", "たばこ", [201810, 202010, 202110]),
    (axes[1], "happo", "発泡酒・ビール風アルコール飲料", [202010, 202310]),
]:
    d = panel[panel.item == item].set_index("ym")["real"]
    yoy = (np.log(d) - np.log(d.shift(12))) * 100
    yoy = yoy.dropna()
    yoy = yoy[yoy.index >= 201801]
    ax.bar(ymdate(yoy.index), yoy.values, width=25,
           color=[C_UP if v > 0 else C_DN for v in yoy.values])
    for m in marks:
        ax.axvline(ymdate([m])[0], color="k", lw=0.8, ls="--")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("前年同月比（%）")
    ax.set_title(f"{title}：買われる量（支出÷物価）の前年同月比。点線は値上げの月", fontsize=10, loc="left")
fig.suptitle("値上げの前月に大きく増え、その月に大きく減る", fontsize=12)
save(fig, "fig1_monthly_yoy.png")

# 図2：値上げ7件の月ごとの上乗せ（k=-2..+2）
up = ev[ev.kind == "up"].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9.5, 4.8))
ks = [-2, -1, 0, 1, 2]
wbar = 0.11
for i, r in up.iterrows():
    # レビュー後：値上げの月以降は段差 S も足し、値上げ前の水準と比べた差にする
    vals = [(np.exp(r[f"p{k}"] + (r.S if k >= 0 else 0.0)) - 1) * 100 for k in ks]
    ax.bar(np.arange(5) + (i - 3) * wbar, vals, width=wbar, label=NAMES[r.event])
ax.axhline(0, color="k", lw=0.6)
ax.set_xticks(range(5))
ax.set_xticklabels(["2か月前", "前の月", "値上げの月", "1か月後", "2か月後"])
ax.set_ylabel("値上げ前の水準との差（%）")
ax.set_title("値上げ前の水準と比べた、前後の月の差（季節・トレンド・ほかの出来事を除いた値）", fontsize=10, loc="left")
ax.legend(fontsize=8, ncol=2)
save(fig, "fig2_event_pulses.png")

# 図3：駆け込み F と反動 R
fig, ax = plt.subplots(figsize=(7.2, 6))
ax.scatter(pl.F, pl.R, color=C_GR, alpha=0.6, s=25, label="出来事のない10月（偽の出来事）")
for _, r in ev.iterrows():
    c = C_UP if r.kind == "up" else C_DN
    ax.scatter(r.F, r.R, color=c, s=55, zorder=3)
    ax.annotate(NAMES[r.event], (r.F, r.R), fontsize=7.5, xytext=(4, 3), textcoords="offset points")
xs = np.linspace(-0.6, 0.8, 10)
ax.plot(xs, -xs, color="k", lw=0.7, ls=":")
ax.text(-0.55, 0.45, "点線：前の上乗せが\nちょうど戻る線", fontsize=8)
ax.axhline(0, color="k", lw=0.5)
ax.axvline(0, color="k", lw=0.5)
ax.set_xlabel("駆け込み：2か月前＋前の月の上乗せ（対数の差）")
ax.set_ylabel("反動：値上げの月〜2か月後の差の合計（対数の差）")
ax.set_title("たばこは前に増えた分が戻る。発泡酒・ビール風は戻らない", fontsize=10, loc="left")
ax.scatter([], [], color=C_UP, label="値上げ")
ax.scatter([], [], color=C_DN, label="値下げ（比べるため）")
ax.legend(fontsize=8, loc="lower left")
save(fig, "fig3_front_vs_rebound.png")

# 図4：定着した水準の変化（ビールと発泡酒・ビール風）
sel = ["B1", "A1", "B2", "A2", "S1", "S2", "W1", "W2", "T1", "T2", "T3"]
sub = ev.set_index("event").loc[sel]
fig, ax = plt.subplots(figsize=(9, 4.8))
vals = (np.exp(sub.S) - 1) * 100
err = sub.S_se * 1.96 * 100
cols = [C_UP if k == "up" else C_DN for k in sub.kind]
ax.bar(range(len(sel)), vals, yerr=err, color=cols, capsize=3)
ax.set_xticks(range(len(sel)))
SH = {"B1": "ビール\n2020↓", "A1": "発泡酒等\n2020↑", "B2": "ビール\n2023↓", "A2": "発泡酒等\n2023↑", "S1": "清酒\n2020↓", "S2": "清酒\n2023↓", "W1": "ワイン\n2020↑", "W2": "ワイン\n2023↑", "T1": "たばこ\n2018↑", "T2": "たばこ\n2020↑", "T3": "たばこ\n2021↑"}
ax.set_xticklabels([SH[e] for e in sel], fontsize=8.5)
ax.set_xlabel("↑は値上げ、↓は値下げ。発泡酒等＝発泡酒・ビール風アルコール飲料", fontsize=8.5)
ax.axhline(0, color="k", lw=0.6)
b = main["placebo_band_90"]["S"]
ax.axhspan((np.exp(b[0]) - 1) * 100, (np.exp(b[1]) - 1) * 100, color=C_GR, alpha=0.15,
           label="出来事のない10月の90%の幅")
ax.set_ylabel("3か月後以降に残った量の変化（%）")
ax.set_title("落ち着いた後：ビールは増え、発泡酒・ビール風は減った（線は95%の幅）", fontsize=10, loc="left")
ax.legend(fontsize=8)
save(fig, "fig4_persistent_steps.png")

# 図5：値上げの月の前年比と、3〜8か月後の前年比
fig, ax = plt.subplots(figsize=(8.5, 4.6))
x = np.arange(len(up))
ax.bar(x - 0.2, (np.exp(up.yoy_0) - 1) * 100, width=0.4, color="#e67e22", label="値上げの月の前年同月比")
ax.bar(x + 0.2, (np.exp(up.yoy_3_8) - 1) * 100, width=0.4, color="#16a085", label="3〜8か月後の前年同月比の平均")
ax.set_xticks(x)
ax.set_xticklabels([NAMES[e].replace("発泡酒・ビール風", "発泡酒等").replace(" ", "\n", 1) for e in up.event], fontsize=8.5)
ax.set_xlabel("発泡酒等＝発泡酒・ビール風アルコール飲料", fontsize=8.5)
ax.axhline(0, color="k", lw=0.6)
ax.set_ylabel("買われる量の前年同月比（%）")
ax.set_title("値上げの月の前年比だけでは、後に残る減りを読み違える", fontsize=10, loc="left")
ax.legend(fontsize=8)
save(fig, "fig5_yoy_trap.png")

# 図6：問い直し 2022年10月（税ではない値上げ）
ra = main["reask"]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
lab = {"beer": "ビール 2022年10月", "happo": "発泡酒・ビール風 2022年10月"}
for i, item in enumerate(["beer", "happo"]):
    vals = [(np.exp(ra[item]["pulses"][str(k)]) - 1) * 100 for k in ks]
    ax.bar(np.arange(5) + (i - 0.5) * 0.35, vals, width=0.35, label=lab[item],
           color=["#8e44ad", "#d35400"][i])
ax.set_xticks(range(5))
ax.set_xticklabels(["2か月前", "前の月", "値上げの月", "1か月後", "2か月後"])
ax.axhline(0, color="k", lw=0.6)
ax.set_ylabel("ふだんの月との差（%）")
ax.set_title("税ではない値上げ（2022年10月）でも、前の月に増えてその月に減った", fontsize=10, loc="left")
ax.legend(fontsize=8)
save(fig, "fig6_reask_2022.png")
print("ok")
