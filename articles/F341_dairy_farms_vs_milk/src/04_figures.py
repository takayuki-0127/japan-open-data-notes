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
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：農林水産省「畜産統計調査」「牛乳乳製品統計調査」（e-Stat）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
idx = pd.read_csv(R / "index_series.csv")

# ---- 図1：指数 ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.6, 5.2))
items = [("milk_idx", "生乳生産量", INK), ("cows_per_farm_idx", "1戸あたり経産牛", C[1]), ("yield_kg_idx", "経産牛1頭あたり生産量", C[2]),
         ("farms_idx", "飼養戸数", C[0])]
for col, lab, c in items:
    ax.plot(idx.year, idx[col], color=c, lw=2.2 if col == "milk_idx" else 2)
    v = idx[col].iloc[-1]
    ax.text(2024.6, v, f"{lab}\n{v:.0f}", color=INK, fontsize=9, va="center")
ax.set_yscale("log")
ax.set_yticks([10, 20, 50, 100, 200, 400], ["10", "20", "50", "100", "200", "400"])
ax.set_xlim(1985, 2033)
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.set_ylabel("1985年＝100（対数目盛）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
d = main["decomposition"]["main_1985_2024"]
ax.set_title(f"戸数は{abs(d['farms_change_pct']):.0f}%減ったが、1戸あたりの頭数が{d['cows_per_farm_ratio']:.1f}倍、1頭あたりが{d['yield_ratio']:.1f}倍になった", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：戸数・経産牛は各年2月1日現在、生乳生産量は暦年。1985〜2024年。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.98, top=0.92, bottom=0.14)
save(fig, "fig1_index_decomposition.png")

# ---- 図2：北海道と都府県 ---------------------------------------------------------
h = pd.read_csv(ROOT / "data" / "dairy_herd.csv")
h["version"] = h["version"].fillna("")
h = h[(h.year != 2019) | (h.version == "旧")]
fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.6))
for g, c in [("北海道", C[0]), ("都府県", C[1])]:
    q = h[h.region == g].sort_values("year")
    axes[0].plot(q.year, q.parous / 1e4, color=c, lw=2)
    axes[0].text(2026, q.parous.iloc[-1] / 1e4, g, color=INK, fontsize=9.5, va="center")
    axes[1].plot(q.year, q.parous / q.farms, color=c, lw=2)
    axes[1].text(2026, (q.parous / q.farms).iloc[-1], g, color=INK, fontsize=9.5, va="center")
axes[0].set_title("経産牛の頭数（万頭）", loc="left", fontsize=11)
axes[1].set_title("1戸あたりの経産牛（頭）", loc="left", fontsize=11)
for ax in axes:
    ax.set_xlim(1960, 2033); ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
axes[0].set_ylim(0, 100)
y0 = main["hokkaido_parous_exceeds_tofuken_year"]
axes[0].annotate(f"{y0}年に北海道が上回る", xy=(y0, h[(h.region == '北海道') & (h.year == y0)].parous.iloc[0] / 1e4),
                 xytext=(1990, 80), fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
fig.suptitle(f"経産牛の{main['hokkaido_share_parous_pct']['2025']:.0f}%は北海道に（2025年）。都府県の頭数は1985年から{abs(main['region']['都府県']['parous_change_pct']):.0f}%減った",
             x=0.01, ha="left", fontsize=12)
fig.text(0.01, 0.01, "注：各年2月1日現在。線の切れ目は値のない年。2019年は旧集計を使用（2020年からは牛個体識別全国データベースなどを使う集計）。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.06, right=0.95, top=0.84, bottom=0.16, wspace=0.3)
save(fig, "fig2_hokkaido_tofuken.png")

# ---- 図3：規模 ---------------------------------------------------------------------
s = pd.read_csv(R / "size_share.csv").dropna(subset=["ge100_share_pct"])
s = s[s.year >= 1996]
fig, ax = plt.subplots(figsize=(8.4, 4.8))
ax.plot(s.year, s.ge100_share_pct, color=C[0], lw=2.2, marker="o", ms=4)
for y in [1996, 2005, 2015, 2025]:
    v = s.set_index("year").loc[y, "ge100_share_pct"]
    ax.text(y, v + 2.5, f"{v:.0f}%", ha="center", fontsize=9.5, color=INK)
ax.set_ylim(0, 70); ax.set_xlim(1995, 2026)
ax.set_ylabel("成畜（2歳以上のめす）に占める割合（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"成畜の{main['hypotheses']['H4']['value']:.0f}%は、100頭以上を飼う{main['farms_ge100_share_2025_pct']:.0f}%の農家にいる（2025年）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：成畜飼養頭数が100頭以上の規模の農家が飼う成畜の割合。2000年は調査なし。2019年は旧集計。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.15)
save(fig, "fig3_large_farms_share.png")

# ---- 図4：問い直し（期間ごと） ---------------------------------------------------------
per = pd.read_csv(R / "requestion_periods.csv")
fig, ax = plt.subplots(figsize=(9.0, 5.0))
x = np.arange(len(per))
ax.bar(x, per["farms"], color=C[0], width=0.6, label="飼養戸数")
ax.bar(x, per["scale"], color=C[1], width=0.6, label="1戸あたり経産牛")
ax.bar(x, per["yield"], bottom=per["scale"], color=C[2], width=0.6, label="1頭あたり生産量")
ax.plot(x, per["milk"], color=INK, marker="D", ms=7, lw=0, label="生乳生産量（合計）", zorder=4)
for xi, v in zip(x, per["milk"]):
    ax.text(xi + 0.33, v, f"{v:+.1f}", fontsize=8.8, va="center", color=INK)
ax.axhline(0, color=INK2, lw=1)
ax.set_xticks(x, per["period"], fontsize=9)
ax.set_ylabel("年平均の変化（%、対数）")
ax.legend(frameon=False, fontsize=9, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.09))
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
q = json.load(open(R / "requestion.json", encoding="utf-8"))
ax.set_title(f"1996年からは1頭あたりの伸びが年{q['1985_1996']['yield']:.1f}%から{q['1996_2024']['yield']:.1f}%に鈍り、生乳は減る側に", loc="left", fontsize=11.5, pad=28)
fig.text(0.01, 0.01, "注：棒の合計（戸数＋規模＋乳量）が生乳生産量の変化（◆）に一致する。1996年は生乳生産量がいちばん多かった年。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.85, bottom=0.15)
save(fig, "fig4_periods.png")
print("figures done")
