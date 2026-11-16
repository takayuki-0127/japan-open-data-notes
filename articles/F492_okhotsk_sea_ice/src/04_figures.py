"""図4枚（PNG）。日付などのメタデータは入れない。"""
import datetime as dt, json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
D = ROOT / "data"
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "axes.unicode_minus": False})
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：気象庁「海洋の健康診断表」「北海道沿岸の海氷に関する初終日」をもとに作成者が加工して作成"
META = {"Software": None}


def mi(v, fmt):
    return format(v, fmt).replace("-", "−")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def tsline(ax, y, color):
    y = y.dropna()
    sl, ic, _, _ = stats.theilslopes(y.values, y.index.values.astype(float))
    x = np.array([y.index.min(), y.index.max()], dtype=float)
    ax.plot(x, ic + sl * x, color=color, lw=1.4, ls="--")


main = json.load(open(R / "main.json", encoding="utf-8"))
s = pd.read_csv(R / "season_table.csv", index_col=0)
st = pd.read_csv(D / "stations.csv")
clim = pd.read_csv(R / "pentad_climatology.csv")
noice = pd.read_csv(R / "requestion_no_ice.csv")

# ---- 図1：最大海氷域面積と積算海氷域面積 ------------------------------------------------------------
fig, axs = plt.subplots(2, 1, figsize=(8, 6.6), sharex=True)
ax = axs[0]
ax.plot(s.index, s["max_official"], color=C1, lw=1.2, marker="o", ms=3)
tsline(ax, s["max_official"], INK2)
ax.set_ylabel("万km²"); ax.set_ylim(60, 160)
ax.set_title("最大海氷域面積（海氷期でいちばん広がったとき）", fontsize=10.5, loc="left")
ax.text(1971, 64, f"傾き 10年あたり {mi(main['check_max']['theil_sen_per_decade'], '.1f')}万km²（Theil–Sen）", fontsize=9, color=INK2)
ax.grid(axis="y", color=GRID, lw=0.8)
ax = axs[1]
acc = s["acc_dec_may"]
ax.plot(acc.index, acc, color=C2, lw=1.2, marker="o", ms=3)
tsline(ax, acc, INK2)
ax.set_ylabel("万km²（36半旬の合計）"); ax.set_ylim(800, 3800)
ax.set_title("積算海氷域面積（12月5日〜5月31日の半旬ごとの面積の合計）", fontsize=10.5, loc="left")
h1 = main["H1"]
ax.text(1972, 950, f"傾き 10年あたり {mi(h1['acc']['pct_per_decade'], '.1f')}%（最大海氷域面積は {mi(h1['max']['pct_per_decade'], '.1f')}%）"
        "、1972〜2000年の平均に対する割合", fontsize=9, color=INK2)
ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_xlabel("海氷期（たとえば2025/26年を2026年と数える）")
fig.text(0.01, 0.01, SRC, fontsize=8, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
save(fig, "fig1_area.png")

# ---- 図2：季節の形 ---------------------------------------------------------------------------------
fig, axs = plt.subplots(2, 1, figsize=(8, 6.4), sharex=True, gridspec_kw={"height_ratios": [2, 1.2]})
x = np.arange(len(clim))
ax = axs[0]
ax.plot(x, clim["mean_1972_2000"], color=C1, lw=2, label="1972〜2000年の平均")
ax.plot(x, clim["mean_1997_2026"], color=C2, lw=2, label="1997〜2026年の平均")
ax.fill_between(x, clim["mean_1997_2026"], clim["mean_1972_2000"], color=GRID, zorder=0)
ax.set_ylabel("海氷域面積（万km²）"); ax.set_ylim(0, 125)
ax.legend(frameon=False, loc="upper right", fontsize=9.5)
ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_title("半旬ごとの海氷域面積の平均（オホーツク海）", fontsize=10.5, loc="left")
ax = axs[1]
ax.bar(x, clim["change_pct"], color=[C2 if v <= -15 else "#f4b48f" for v in clim["change_pct"]], width=0.8)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("変化（%）"); ax.set_ylim(-30, 0)
ax.set_yticks([-30, -20, -10, 0]); ax.set_yticklabels(["−30", "−20", "−10", "0"])
ax.grid(axis="y", color=GRID, lw=0.8)
ticks = [i for i, p in enumerate(clim["pentad"]) if p.endswith("/05")]
ax.set_xticks(ticks); ax.set_xticklabels([f"{int(clim['pentad'][i][:2])}月" for i in ticks])
ax.set_title("1972〜2000年 → 1997〜2026年の変化（色の濃い棒は −15% 以下）", fontsize=10, loc="left")
fig.text(0.01, 0.01, SRC, fontsize=8, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
save(fig, "fig2_season_shape.png")

# ---- 図3：網走の流氷初日・終日 -------------------------------------------------------------------------
ab = st[st.station == "abashiri"].set_index("season")
fig, ax = plt.subplots(figsize=(8, 5.2))
ax.scatter(ab.index, ab["first"], color=C1, s=16, label="流氷初日（1946〜2025年）")
ax.scatter(ab.index, ab["last"], color=C2, s=16, label="流氷終日（1946〜2021年）")
tsline(ax, ab["first"], C1); tsline(ax, ab["last"], C2)
yt = [(12, 15), (1, 1), (1, 15), (2, 1), (2, 15), (3, 1), (3, 15), (4, 1), (4, 15), (5, 1), (5, 15)]
pos = [(dt.date(2001 if m == 12 else 2002, m, d) - dt.date(2002, 1, 1)).days for m, d in yt]
ax.set_yticks(pos); ax.set_yticklabels([f"{m}月{d}日" for m, d in yt])
ax.set_ylim(-25, 140); ax.set_xlim(1943, 2028)
ax.grid(axis="y", color=GRID, lw=0.8)
h3, h4 = main["H3"], main["H4"]
ax.text(1946, 52, f"初日：10年あたり {mi(h3['slope_days_per_decade'], '+.1f')}日", color=C1, fontsize=9.5)
ax.text(1946, 135, f"終日：10年あたり {mi(h4['slope_days_per_decade'], '+.1f')}日", color=C2, fontsize=9.5)
ax.legend(frameon=False, loc="lower right", fontsize=9)
ax.set_title("網走の流氷初日と流氷終日（破線は Theil–Sen の傾き）", fontsize=10.5, loc="left")
fig.text(0.01, 0.01, SRC + "。終日は2022年以降の値がない", fontsize=8, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
save(fig, "fig3_abashiri_dates.png")

# ---- 図4：流氷が来なかった年（10年ごと） -------------------------------------------------------------
pv = noice.pivot(index="from", columns="station", values="no_ice_years")
yrs = noice.drop_duplicates("from").set_index("from")["to"]
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(len(pv))
ax.bar(x - 0.2, pv["wakkanai"], width=0.38, color=C1, label="稚内")
ax.bar(x + 0.2, pv["kushiro"], width=0.38, color=C3, label="釧路")
for i, (w, k) in enumerate(zip(pv["wakkanai"], pv["kushiro"])):
    ax.text(i - 0.2, w + 0.15, str(int(w)), ha="center", fontsize=9, color=C1)
    ax.text(i + 0.2, k + 0.15, str(int(k)), ha="center", fontsize=9, color=C3)
ax.set_xticks(x); ax.set_xticklabels([f"{a}〜\n{yrs[a]}" for a in pv.index], fontsize=9)
ax.set_ylim(0, 10.5); ax.set_ylabel("流氷が来なかった年の数（10年のうち）")
ax.legend(frameon=False, loc="upper left")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("稚内と釧路で、流氷初日がなかった年（網走は毎年来ている）", fontsize=10.5, loc="left")
fig.text(0.01, 0.01, SRC, fontsize=8, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
save(fig, "fig4_no_ice_years.png")
print("figures done")
