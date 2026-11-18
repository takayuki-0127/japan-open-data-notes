"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "f415"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#7d5ba6"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：経済産業省「商業動態統計」（e-Stat）をもとに作成者が加工して作成"
META = {"Software": None}
m = json.load(open(R / "main.json", encoding="utf-8"))
d = pd.read_csv(ROOT / "data" / "monthly_machinery.csv", index_col="ym")


def finish(fig, ax, title, grid="y", bottom=0.17):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.015, SRC, fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.88, bottom=bottom)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def xpos(ym):
    return int(ym[:4]) + (int(ym[5:7]) - 1) / 12


# 図1：季節調整済指数の推移と山の窓
fig, ax = plt.subplots(figsize=(9, 4.8))
s = d["index_sa"].dropna().loc["2005-01":]
x = [xpos(i) for i in s.index]
for k, col in (("E1", C[1]), ("E2", C[2]), ("E3", C[3])):
    e = m["events"][k]
    ax.axvspan(xpos(e["peak"][0]), xpos(e["peak"][1]) + 1 / 12, color=col, alpha=0.16, lw=0)
    ax.text((xpos(e["peak"][0]) + xpos(e["peak"][1])) / 2 + 1 / 24, 196, e["name"].replace("2014年の税率引き上げ", "2014年\n税率").replace("2019年の税率引き上げ", "2019年\n税率").replace("エコポイント・地デジ", "エコポイント\n・地デジ"),
            ha="center", va="top", fontsize=9, color=INK2)
ax.plot(x, s.values, color=C[0], lw=1.4)
pre = m["requestion"]["pre_level_sa"]
ax.axhline(pre, color=INK2, lw=1, ls="--")
ax.text(2013.0, pre + 3, f"山の前の1年（2007年5月〜2008年4月）の平均 {pre:.1f}", fontsize=8.8, color=INK2)
ax.set_ylim(70, 200); ax.set_xlim(2005, 2027)
ax.set_xticks(range(2005, 2028, 3)); ax.set_xticklabels([f"{v}年" for v in range(2005, 2028, 3)])
ax.set_ylabel("指数（2020年=100、季節調整済）")
ax.text(2020.3, 74, "2020年3月以降はコロナの影響あり", fontsize=8, color=INK2)
finish(fig, ax, "図1 機械器具小売業の販売額指数：3つの山と、そのあとの水準")
save(fig, "fig1_index_timeline.png")

# 図2：山と谷の大きさ（平常の月数）
fig, ax = plt.subplots(figsize=(9, 4.8))
ev = ["E1", "E2", "E3"]
lab = ["エコポイント・地デジ\n（山27か月／谷12・26か月）", "2014年の税率引き上げ\n（山6か月／谷5・12か月）", "2019年の税率引き上げ\n（山6か月／谷5か月）"]
M = m["main"]
pk = [M[k]["peak"] for k in ev]; ts = [M[k]["trough_short"] for k in ev]; tl = [M[k]["trough"] for k in ev]
xx = np.arange(3); w = 0.26
b1 = ax.bar(xx - w, pk, w, color=C[0], label="山（上乗せの合計）")
b2 = ax.bar(xx, ts, w, color=C[1], label="谷・短い窓（12か月／5か月／5か月）")
tl_plot = [tl[0], tl[1], np.nan]
b3 = ax.bar(xx + w, tl_plot, w, color=C[4], label="谷・長い窓（26か月／12か月）")
for bars in (b1, b2, b3):
    for b in bars:
        h = b.get_height()
        if np.isfinite(h):
            ax.text(b.get_x() + b.get_width() / 2, h + (0.08 if h >= 0 else -0.08), f"{h:+.2f}", ha="center",
                    va="bottom" if h >= 0 else "top", fontsize=9, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(xx); ax.set_xticklabels(lab, fontsize=9.5)
ax.set_ylabel("平常の月の販売額の何か月分")
ax.set_ylim(-5.6, 2.8)
ax.legend(frameon=False, fontsize=9, loc="lower right")
finish(fig, ax, "図2 山と谷の大きさ（直前の平常の1年の同じ月と比べた上乗せ・不足の合計）", bottom=0.2)
save(fig, "fig2_peak_trough.png")

# 図3：2019年の商品別（家電大型専門店）
gd = pd.read_csv(R / "goods_E3.csv")
gd = gd[gd.goods != "total"].reset_index(drop=True)
order = ["living", "av", "info", "other", "comm", "camera"]
gd = gd.set_index("goods").loc[order].reset_index()
fig, ax = plt.subplots(figsize=(9, 4.8))
yy = np.arange(len(gd))[::-1]
ax.barh(yy + 0.18, gd.peak, 0.36, color=C[0], label="山（2019年4〜9月）")
ax.barh(yy - 0.18, gd.trough, 0.36, color=C[1], label="谷（2019年10月〜2020年2月）")
for y_, p_, t_ in zip(yy, gd.peak, gd.trough):
    ax.text(p_ + (0.03 if p_ >= 0 else -0.03), y_ + 0.18, f"{p_:+.2f}", va="center", ha="left" if p_ >= 0 else "right", fontsize=8.8)
    ax.text(t_ + (0.03 if t_ >= 0 else -0.03), y_ - 0.18, f"{t_:+.2f}", va="center", ha="left" if t_ >= 0 else "right", fontsize=8.8)
ax.set_yticks(yy)
ax.set_yticklabels([f"{n}（{s*100:.0f}%）" for n, s in zip(gd.name, gd.share_pre_year)])
ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlim(-1.5, 1.4)
ax.set_xlabel("平常の月の販売額の何か月分（基準：2018年4月〜2019年3月の同じ月）　（ ）は基準の1年の売上の割合")
ax.legend(frameon=False, fontsize=9, loc="upper left")
finish(fig, ax, "図3 2019年の山と谷を商品別に見る（家電大型専門店）", grid="x", bottom=0.19)
fig.subplots_adjust(left=0.2)
save(fig, "fig3_goods_2019.png")

# 図4：谷の深さ（戻り率）は基準の置き方でどれだけ変わるか
rb = pd.read_csv(R / "robustness.csv")
short = {"本線：直前の平常の1年の同じ月が基準（原指数）": "本線：直前の1年の同じ月",
         "E1 の基準をリーマン・ショック後の1年（2008年5月〜2009年4月）に": "E1 の基準を2008年5月〜09年4月に",
         "E2・E3 の基準を別の平常の1年に（E2：2015年10月〜2016年9月、E3：2016年4月〜2017年3月）": "E2・E3 の基準を谷のあとの1年に",
         "季節調整済指数・直前の1年の平均の水準が基準": "季節調整済指数・直前の1年の平均",
         "業種別商業販売額（金額）で同じ計算": "金額（10億円）で同じ計算",
         "計画どおり：平常の年 2007・2016〜2018 のトレンドと月のダミー": "計画どおり：平常の4年のトレンド",
         "計画どおりの方法で平常の年に 2005・2006 を足す": "計画どおり＋2005・06年"}
rb["lab"] = rb.check.map(short)
labs = list(short.values())
fig, ax = plt.subplots(figsize=(9, 4.8))
for j, (k, col, nm) in enumerate((("E1", C[1], "エコポイント・地デジ（谷26か月）"), ("E2", C[2], "2014年（谷12か月）"), ("E3", C[3], "2019年（谷5か月）"))):
    sub = rb[rb.event == k].set_index("lab")
    ys = [len(labs) - 1 - labs.index(l) + (0.2 - 0.2 * j) for l in sub.index]
    ax.scatter(sub.payback.clip(-1, 8), ys, color=col, s=36, label=nm, zorder=3)
ax.axvline(1, color=INK2, lw=0.8, ls="--"); ax.axvline(0, color=INK2, lw=0.8)
ax.text(1.08, -0.45, "1＝山の分がちょうど戻る", fontsize=8.5, color=INK2)
ax.set_yticks(range(len(labs))); ax.set_yticklabels(labs[::-1], fontsize=9); ax.set_ylim(-0.7, len(labs) - 0.5)
ax.set_xlim(-1, 8)
ax.set_xlabel("戻り率（谷の不足÷山の上乗せ）。8以上は8の位置に置いた")
ax.legend(frameon=False, fontsize=9, loc="lower right")
finish(fig, ax, "図4 戻り率は、基準の置き方で大きく変わる", grid="x", bottom=0.17)
fig.subplots_adjust(left=0.3)
save(fig, "fig4_payback_sensitivity.png")
print("ok")
