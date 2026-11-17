"""04_figures.py : results の CSV・JSON から図を4枚作る（オフライン）。"""
import json
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

for f in sorted(font_manager.findSystemFonts()):
    if "NotoSansCJK" in f:
        font_manager.fontManager.addfont(f)
ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2})
SRC = "出典：総務省「家計消費状況調査」年報（2015〜2025年）をもとに作成者が加工して作成。デジタルコンテンツ＝電子書籍＋ダウンロード版の音楽・映像、アプリなど"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
Q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
A10 = ["A:-34", "A:35-44", "A:45-54", "A:55-64", "A:65-74", "A:75-84", "A:85-"]
LAB = ["〜34歳", "35〜44", "45〜54", "55〜64", "65〜74", "75〜84", "85歳〜"]


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


t = pd.read_csv(RES / "age_year_table.csv")
T = t[t.hh == "total"]

# 図1 年齢別の額（2015年と2025年）
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(len(A10))
for k, (y, c) in enumerate([(2015, "#9fc3ee"), (2025, C1)]):
    v = [T[(T.year == y) & (T.age == a)].D.iloc[0] for a in A10]
    ax.bar(x + (k - 0.5) * 0.4, v, width=0.4, color=c, label=f"{y}年")
    for i, vv in enumerate(v):
        ax.text(x[i] + (k - 0.5) * 0.4, vv + 30, f"{vv:,.0f}", ha="center", fontsize=8, color=INK2 if k == 0 else C1)
ax.set_xticks(x); ax.set_xticklabels(LAB); ax.set_xlabel("世帯主の年齢")
ax.set_ylabel("1世帯あたり1か月（円）"); ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False)
ax.set_title(f"デジタルコンテンツへのネットでの支出：2025年は〜34歳が{M['D_2025']['A:-34']:,.0f}円、65〜74歳の{M['hypotheses']['H1']['ratio_2025']:.1f}倍", loc="left", fontsize=10.5)
fig.subplots_adjust(left=0.1, right=0.98, top=0.9, bottom=0.18)
save(fig, "fig1_by_age.png")

# 図2 〜34歳 ÷ 65〜74歳 の比の推移（総世帯・二人以上の世帯・単身の割合をそろえた場合）
sm = pd.read_csv(RES / "single_mix.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(sm.year, sm.ratio_actual, color=C1, lw=2, marker="o", ms=4, label="総世帯")
ax.plot(sm.year, sm.ratio_cf, color=C3, lw=2, marker="o", ms=4, ls="--", label="総世帯（〜34歳の単身の割合を65〜74歳にそろえた計算）")
ax.plot(sm.year, sm.ratio_two_plus, color=C2, lw=2, marker="o", ms=4, label="二人以上の世帯")
ax.set_yscale("log"); ax.set_yticks([1, 2, 3, 5, 10, 20, 40]); ax.set_yticklabels(["1", "2", "3", "5", "10", "20", "40"])
ax.axhline(1, color=INK2, lw=0.8)
for col, c in [("ratio_actual", C1), ("ratio_cf", C3), ("ratio_two_plus", C2)]:
    ax.text(2025.2, sm[col].iloc[-1], f"{sm[col].iloc[-1]:.1f}倍", va="center", fontsize=8.5, color=c)
ax.set_xlim(2014.5, 2026.3); ax.set_xticks(range(2015, 2026, 2))
ax.set_ylabel("〜34歳 ÷ 65〜74歳（倍、対数目盛）"); ax.grid(axis="y", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="upper right", fontsize=8.5)
ax.set_title(f"年齢の差は縮んだ：総世帯で2015〜17年平均{M['ratio_2015_2017']:.0f}倍 → 2023〜25年{M['ratio_2023_2025']:.0f}倍", loc="left", fontsize=10.5)
fig.subplots_adjust(left=0.1, right=0.93, top=0.9, bottom=0.15)
save(fig, "fig2_age_ratio.png")

# 図3 2025年の分解：ネットで注文した世帯の割合 × 注文した世帯あたりの額
fig, axs = plt.subplots(1, 2, figsize=(8.4, 4.4))
r25 = [M["r_order_2025"][a] * 100 for a in A10]; d25 = [M["d_per_orderer_2025"][a] for a in A10]
axs[0].bar(x, r25, color=C3)
axs[1].bar(x, d25, color=C1)
for i in range(len(A10)):
    axs[0].text(x[i], r25[i] + 1, f"{r25[i]:.0f}%", ha="center", fontsize=8)
    axs[1].text(x[i], d25[i] + 40, f"{d25[i]:,.0f}", ha="center", fontsize=8)
for a_, tt, yl in [(axs[0], "ネットで注文した世帯の割合", "%"), (axs[1], "注文した世帯あたりのデジタルコンテンツ", "円（1か月）")]:
    a_.set_xticks(x); a_.set_xticklabels(LAB, rotation=45, fontsize=8.5); a_.set_title(tt, fontsize=10)
    a_.set_ylabel(yl); a_.grid(axis="y", color=GRID, lw=0.8); a_.set_axisbelow(True)
dd = M["decomp_2025"]
fig.suptitle(f"2025年の〜34歳と65〜74歳の差のうち、注文する世帯の割合の違いで説明できるのは{dd['rate_share'] * 100:.0f}%（log で分けた場合）",
             x=0.01, ha="left", fontsize=10.5)
fig.subplots_adjust(left=0.08, right=0.98, top=0.83, bottom=0.25, wspace=0.3)
save(fig, "fig3_rate_vs_amount.png")

# 図4 全国：支出のあった世帯の割合と、その世帯あたりの額
n = pd.read_csv(RES / "national_payers.csv")
fig, axs = plt.subplots(1, 2, figsize=(8.4, 4.4))
for it, lab, c in [("ebook", "電子書籍", C2), ("download", "ダウンロード版の音楽・映像、アプリなど", C1), ("digital", "どちらか（2019年から）", INK2)]:
    g = n[n["item"] == it]
    axs[0].plot(g.year, g.s * 100, color=c, lw=2, marker="o", ms=3.5, label=lab)
    axs[1].plot(g.year, g.m_yen, color=c, lw=2, marker="o", ms=3.5, label=lab)
axs[0].set_ylabel("支出のあった世帯の割合（%）"); axs[1].set_ylabel("支出のあった世帯あたり（円、1か月）")
axs[0].set_title("支出のあった世帯の割合", fontsize=10); axs[1].set_title("その世帯あたりの額", fontsize=10)
axs[1].set_ylim(0, 9000)
for a_ in axs:
    a_.set_xticks(range(2015, 2026, 2)); a_.grid(axis="y", color=GRID, lw=0.8)
axs[0].legend(frameon=False, fontsize=8, loc="upper left")
nat = M["national"]
fig.suptitle(f"全国の伸びは主に「払う世帯」が増えた分：電子書籍 {nat['ebook']['s0'] * 100:.1f}%→{nat['ebook']['s1'] * 100:.1f}%、"
             f"ダウンロード版 {nat['download']['s0'] * 100:.1f}%→{nat['download']['s1'] * 100:.1f}%（総世帯）", x=0.01, ha="left", fontsize=10.5)
fig.subplots_adjust(left=0.08, right=0.98, top=0.83, bottom=0.15, wspace=0.3)
save(fig, "fig4_national_payers.png")
print("ok")
