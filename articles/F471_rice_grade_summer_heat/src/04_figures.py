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
for cand in ["Noto Sans CJK JP", "IPAexGothic"]:
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand; break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "x"})
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
INK2, GRID = "#52514e", "#e4e3df"
META = {"Software": None}
S_K = "出典：農林水産省「米の農産物検査結果」、気象庁「過去の気象データ検索」をもとに作成者が加工して作成"
M = json.load(open(R / "main.json", encoding="utf-8"))
Q = json.load(open(R / "requestion.json", encoding="utf-8"))


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note="", src=S_K):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + src, fontsize=7.6, color=INK2)


# 図1：全国の1等比率と8月の気温の偏差
N = pd.read_csv(R / "national_series.csv")
fig, ax = plt.subplots(figsize=(8.8, 4.9))
ax.plot(N.year, N.r1, color=C1, lw=2.2, marker="o", ms=4, label="1等比率（全国、左の目盛り）")
for y in [2010, 2019, 2023]:
    v = float(N.loc[N.year == y, "r1"].iloc[0])
    off = (-48, -4) if y == 2023 else (0, -16)
    ax.annotate(f"{y}年 {v:.1f}%", (y, v), xytext=off, textcoords="offset points", ha="center", fontsize=9, color=C1)
ax.set_ylim(50, 92); ax.set_ylabel("1等比率（%）")
ax2 = ax.twinx(); ax2.spines["right"].set_visible(True); ax2.spines["top"].set_visible(False)
ax2.bar(N.year, N.a_aug_w, color=C2, alpha=0.35, width=0.7, label="8月の気温の平年差（右の目盛り）")
ax2.set_ylim(-1.5, 6); ax2.set_ylabel("8月の平均気温の平年差（℃）")
ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
ax.set_xticks(range(2006, 2025, 2)); ax.grid(axis="y", color=GRID)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left", fontsize=9, ncol=2)
ax.set_title(f"8月が暑い年ほど1等比率が低い（全国、2006〜2024年産。相関 {M['corr_national_r1_aaug']:.2f}）", fontsize=11.5, loc="left")
fig.subplots_adjust(bottom=0.17, top=0.9, left=0.08, right=0.91)
foot(fig, "注：気温の平年差は県庁所在地などの気象台の8月の平均気温と1991〜2020年の平均の差を、県の検査数量で重みづけした平均")
save(fig, "fig1_national_series.png")

# 図2：8月の平均気温の区間ごとの差
B = pd.read_csv(R / "h2_bins.csv")
fig, ax = plt.subplots(figsize=(8.8, 4.9))
x = np.arange(len(B))
ax.axhline(0, color=INK2, lw=0.8)
ax.errorbar(x, B.b, yerr=[B.b - B.lo, B.hi - B.b], fmt="o", color=C1, ms=7, capsize=4, lw=1.6)
for i, r in B.iterrows():
    ax.text(i + 0.12, r.b, "基準" if i == 2 else f"{r.b:+.1f}", fontsize=9, color=INK2, va="center")
    ax.text(i, -27, f"{int(r.n_obs)}件", ha="center", fontsize=8, color=INK2)
ax.set_xticks(x, B.bin); ax.set_ylim(-29, 11)
ax.set_xlabel("その県の8月の平均気温（県庁所在地などの気象台）")
ax.set_ylabel("26〜27℃の年と比べた1等比率の差（ポイント）")
h = M["H2"]
ax.set_title(f"27℃を超えると下がり方が急になる（27℃より下は1℃で{h['slope_below']['b']:.1f}、上は{h['slope_above']['b']:.1f}ポイント）", fontsize=11.5, loc="left")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
fig.subplots_adjust(bottom=0.2, top=0.9, left=0.09, right=0.97)
foot(fig, f"注：{M['n_pref_main']}道府県×2006〜2024年産。県の固定効果と年の直線を入れた回帰。縦の線は95%区間（年でクラスター）。件数は県×年の数")
save(fig, "fig2_temp_bins.png")

# 図3：時期と地方
G = pd.read_csv(R / "h4_regions.csv")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 5.0), gridspec_kw={"width_ratios": [1, 2.6]})
e, l = M["H3"]["early"], M["H3"]["late"]
for i, (lab, c) in enumerate([("2006〜14年", e), ("2015〜24年", l)]):
    a1.bar(i, c["b"], color=[C2, C1][i], width=0.6)
    a1.errorbar(i, c["b"], yerr=[[c["b"] - c["lo"]], [c["hi"] - c["b"]]], color=INK2, capsize=4)
    a1.text(i, 0.4, f"{c['b']:.1f}", ha="center", fontsize=9.5, color=INK2)
a1.set_xticks([0, 1], ["2006〜14年", "2015〜24年"]); a1.set_ylim(-15.5, 2); a1.axhline(0, color=INK2, lw=0.8)
a1.set_ylabel("8月が平年より1℃暑いときの1等比率の差（ポイント）")
a1.set_title("時期で分けると", fontsize=10.5, loc="left")
xs = np.arange(len(G))
a2.bar(xs, G.b, color=C1, width=0.6, alpha=0.85)
a2.errorbar(xs, G.b, yerr=[G.b - G.lo, G.hi - G.b], fmt="none", color=INK2, capsize=4)
for i, r in G.iterrows():
    a2.text(i, 0.4, f"{r.b:.1f}", ha="center", fontsize=9.5, color=INK2)
a2.set_xticks(xs, [f"{r.region}\n({r.n_pref}{'道県' if '北海道' in r.region else '県'})" for r in G.itertuples()], fontsize=9)
a2.set_ylim(-15.5, 2); a2.axhline(0, color=INK2, lw=0.8)
a2.set_title("地方で分けると（北から南の順）", fontsize=10.5, loc="left")
for a in (a1, a2):
    a.grid(axis="y", color=GRID); a.set_axisbelow(True)
fig.suptitle(f"どの時期・どの地方でも、8月が暑い年は1等比率が低い（全体では1℃で{M['H1']['b']:.1f}ポイント）", fontsize=11.5, x=0.01, ha="left")
fig.subplots_adjust(bottom=0.19, top=0.86, left=0.09, right=0.98, wspace=0.18)
foot(fig, "注：県の固定効果と年の直線を入れた回帰。縦の線は95%区間（年でクラスター）。北海道・東北は北海道と東北6県。地方は表の農政局の見出しで分けた")
save(fig, "fig3_period_region.png")

# 図4：2023年の下がり方（コシヒカリとそれ以外、同じ県の中）
W = pd.read_csv(R / "requestion_within_pref.csv")
fig, ax = plt.subplots(figsize=(8.8, 5.2))
lim = (-75, 25)
ax.plot(lim, lim, color=INK2, lw=0.8, ls=":")
ax.scatter(W.other_drop, W.koshi_drop, s=30 + 120 * W.koshi_share23, color=C1, alpha=0.75, edgecolor="white")
for r in W.itertuples():
    if abs(r.gap) >= 14 or r.pref in ("新潟", "山形"):
        ax.annotate(r.pref, (r.other_drop, r.koshi_drop), xytext=(4, 3), textcoords="offset points", fontsize=8.5, color=INK2)
ax.text(-72, 20, "点線より下：コシヒカリの方が大きく下がった", fontsize=9, color=INK2)
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("コシヒカリ以外の品種（数量で重み）の下がり方（ポイント）")
ax.set_ylabel("コシヒカリの下がり方（ポイント）")
ax.axhline(0, color=GRID, lw=0.8); ax.axvline(0, color=GRID, lw=0.8)
ax.set_title(f"2023年、同じ県の中でコシヒカリの方が大きく下がったのは{Q['n_pref_both']}県中{Q['n_pref_koshi_dropped_more']}県", fontsize=11.5, loc="left")
fig.subplots_adjust(bottom=0.19, top=0.9, left=0.1, right=0.97)
foot(fig, "注：下がり方＝2023年産の1等比率−2016〜2022年産の平均。各年1,000t 以上の銘柄。点の大きさは2023年のコシヒカリの割合。小規模の6都府県を除く", src="出典：農林水産省「米の農産物検査結果」をもとに作成者が加工して作成")
save(fig, "fig4_koshihikari_2023.png")
print("ok")
