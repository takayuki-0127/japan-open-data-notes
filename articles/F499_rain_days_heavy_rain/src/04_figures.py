"""図4枚（PNG）。日付などのメタデータは入れない。地域は北から南の順。地点の順位は作らない。"""
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
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C1, C2, C3, C4, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#9a9893"
INK2, GRID = "#52514e", "#e4e3df"
SRC = "出典：気象庁「過去の気象データ検索」（年ごとの値、51地点）をもとに作成者が加工して作成"
META = {"Software": None}
REGIONS = ["北日本", "東日本", "西日本", "沖縄奄美"]
RC = dict(zip(REGIONS, [C1, C3, C2, C4]))


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=8, color=INK2)
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


M = json.load(open(R / "main.json", encoding="utf-8"))
Q = json.load(open(R / "requestion.json", encoding="utf-8"))
Y = pd.read_csv(R / "yearly.csv").set_index("year")
S = pd.read_csv(R / "station_table.csv")
G = pd.read_csv(R / "region_table.csv").set_index("region").loc[REGIONS]
PT = pd.read_csv(R / "period_table.csv")

# ---- 図1：雨の日と強い雨の日（51地点平均） ----------------------------------------------------------
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.4, 6.4), sharex=True)
a1.plot(Y.index, Y.d1, color=GRAY, lw=0.8, label="年ごとの値")
a1.plot(Y.index, Y.d1_11yr, color=C1, lw=2.2, label="前後11年の平均")
a1.set_ylabel("日降水量1.0mm以上の日数\n（日／年、51地点平均）")
a1.grid(axis="y", color=GRID, lw=0.7)
a1.legend(frameon=False, loc="upper right", ncol=2)
a1.text(0.01, 0.06, f"1901〜30年 {M['d1_mean_p1']:.0f}日 → 1996〜2025年 {M['d1_mean_p2']:.0f}日（100年あたり {M['H1_d1_slope_per100y']:.1f}日）".replace("-", "−") + "",
        transform=a1.transAxes, color=C1, fontsize=9.5)
a2.bar(Y.index, Y.d100, color=GRAY, width=0.8, label="年ごとの値")
a2.plot(Y.index, Y.d100_11yr, color=C2, lw=2.2, label="前後11年の平均")
a2.set_ylabel("日降水量100mm以上の日数\n（日／年、51地点平均）")
a2.grid(axis="y", color=GRID, lw=0.7)
a2.legend(frameon=False, loc="upper left", ncol=2)
a2.set_ylim(0, 2.45)
a2.text(0.99, 0.90, f"1901〜30年 {M['H2_d100_mean_p1']:.2f}日 → 1996〜2025年 {M['H2_d100_mean_p2']:.2f}日（{M['H2_ratio']:.2f}倍）",
        transform=a2.transAxes, color=C2, fontsize=9.5, ha="right")
a2.set_xlabel("年")
fig.suptitle("雨の日は減り、100mm以上の日は増えた。ただし減ったのは主に1990年ごろまで、増えたのは主にその後", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(left=0.13, right=0.98, top=0.92, bottom=0.12, hspace=0.12)
save(fig, "fig1_national_series.png")

# ---- 図2：地域ごと（北から南） ----------------------------------------------------------------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.4, 4.4))
x = np.arange(len(REGIONS))
a1.bar(x, G.d1_diff, color=[RC[g] for g in REGIONS], width=0.6)
for i, v in enumerate(G.d1_diff):
    a1.text(i, v - 0.4, f"{v:.1f}日", ha="center", va="top", fontsize=9.5)
a1.axhline(0, color=INK2, lw=0.8)
a1.set_xticks(x, [f"{g}\n（{int(n)}地点）" for g, n in zip(REGIONS, G.n_stations)])
a1.set_ylim(min(G.d1_diff) * 1.3, 2)
a1.set_title("雨の日（≧1.0mm）の変化（日／年）", fontsize=11)
a1.grid(axis="y", color=GRID, lw=0.7)
a2.bar(x, G.d100_ratio, color=[RC[g] for g in REGIONS], width=0.6)
for i, (v, p1, p2) in enumerate(zip(G.d100_ratio, G.d100_p1, G.d100_p2)):
    a2.text(i, v + 0.03, f"{v:.2f}倍\n{p1:.2f}→{p2:.2f}日", ha="center", va="bottom", fontsize=8.8)
a2.axhline(1, color=INK2, lw=0.8)
a2.set_xticks(x, [f"{g}\n（{int(n)}地点）" for g, n in zip(REGIONS, G.n_stations)])
a2.set_ylim(0, 1.95)
a2.set_title("100mm以上の日数（地域平均）の倍率", fontsize=11)
a2.grid(axis="y", color=GRID, lw=0.7)
fig.suptitle("4つの地域すべてで同じ形。ただし北日本は雨の日の減りが小さい（1901〜30年→1996〜2025年）", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.98, top=0.84, bottom=0.2, wspace=0.25)
save(fig, "fig2_regions.png")

# ---- 図3：地点ごとの散布図（どの象限に何地点） -------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.4, 5.4))
for g in REGIONS:
    s = S[S.region == g]
    ax.scatter(s.d1_diff, s.d100_diff, s=36, color=RC[g], label=f"{g}（{len(s)}地点）", alpha=0.85, edgecolor="white", lw=0.5)
ax.axhline(0, color=INK2, lw=0.8); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("雨の日（≧1.0mm）の変化（日／年、1901〜30年→1996〜2025年）")
ax.set_ylabel("100mm以上の日数の変化（日／年）")
xl, yl = ax.get_xlim(), ax.get_ylim()
n_dn_flat = int(((S.d1_diff < 0) & (S.d100_diff <= 0)).sum())
ax.text(xl[0] + 0.5, yl[1] * 0.92, f"雨の日が減り、強い雨が増えた：{M['H3_n_both']}地点", color=INK2, fontsize=10, va="top")
ax.text(xl[1] - 0.3, yl[1] * 0.92, f"雨の日が増えた：{51 - M['H3_n_d1_down']}地点", color=INK2, fontsize=10, va="top", ha="right")
y0 = yl[0] - 0.08 * (yl[1] - yl[0])  # 下に余白を足し、注記が点に重ならないようにする（レビューで直した）
ax.set_ylim(y0, yl[1])
ax.text(-5.5, y0 + 0.035 * (yl[1] - yl[0]), f"雨の日が減り、強い雨は減った・同じ：{n_dn_flat}地点", color=INK2, fontsize=10, va="center", ha="right")
ax.grid(color=GRID, lw=0.6)
ax.legend(frameon=False, loc="center right", fontsize=9.5)
ax.set_title(f"51地点のうち{M['H3_n_both']}地点（{M['H3_share'] * 100:.0f}%）で「雨の日は減り、強い雨は増えた」", loc="left", fontsize=12.5)
fig.subplots_adjust(left=0.1, right=0.98, top=0.92, bottom=0.15)
save(fig, "fig3_station_scatter.png")

# ---- 図4：問い直し：減ったのは弱い雨の日 -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.4, 4.8))
labs = ["1901〜30", "1931〜60", "1961〜90", "1991〜2020", "1996〜2025"]
x = np.arange(len(PT))
ax.bar(x, PT.light, color=C1, width=0.6, label="弱い雨の日（1mm以上10mm未満）")
ax.bar(x, PT.d10, bottom=PT.light, color=C3, width=0.6, label="10mm以上の日")
for i, r in PT.iterrows():
    ax.text(i, r.light / 2, f"{r.light:.1f}", ha="center", va="center", color="white", fontsize=9.5)
    ax.text(i, r.light + r.d10 / 2, f"{r.d10:.1f}", ha="center", va="center", color="white", fontsize=9.5)
    ax.text(i, r.d1 + 1.5, f"{r.sdii:.1f}mm", ha="center", va="bottom", fontsize=9, color=C2)
ax.set_xticks(x, [l + "年" for l in labs])
ax.set_ylim(0, 150)
ax.set_ylabel("日数（日／年、51地点平均）")
ax.grid(axis="y", color=GRID, lw=0.7)
ax.legend(frameon=False, loc="upper right", ncol=2, fontsize=9.5)
ax.set_xlabel("棒の上の数字（橙）：雨の日1日あたりの雨量（年降水量÷1mm以上の日数）", fontsize=9.5, color=C2)
ax.set_title(f"減った雨の日の{Q['light_share_of_d1_decrease'] * 100:.0f}%は弱い雨の日。雨の日1日あたりの雨量は{Q['sdii_change_pct']:.0f}%増えた", loc="left", fontsize=12.5)
fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.17)
save(fig, "fig4_light_rain.png")
print("figures done")
