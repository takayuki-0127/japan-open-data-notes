"""図4枚（PNG）。日付などのメタデータは入れない。地点は北から南の順。"""
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
SRC_J = "出典：気象庁「大気中二酸化炭素濃度の観測結果」をもとに作成者が加工して作成"
SRC_JN = "出典：気象庁「大気中二酸化炭素濃度の観測結果」、国立環境研究所「日本の温室効果ガス排出量データ」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
M = pd.read_csv(ROOT / "data" / "monthly.csv"); M = M[M.year <= 2025]
A = pd.read_csv(R / "annual.csv")
E = pd.read_csv(ROOT / "data" / "emissions.csv")
Q = pd.read_csv(R / "requestion_series.csv")

# ---- 図1：月平均の濃度（北から南） ----
fig, ax = plt.subplots(figsize=(8.8, 4.9))
for st, c in [("綾里", C[1]), ("与那国島", C[2]), ("南鳥島", C[0])]:
    d = M[M.station == st]; t = d.year + (d.month - 0.5) / 12
    ax.plot(t, d.co2, color=c, lw=1.0, label=st)
ax.set_xlim(1987, 2026); ax.set_ylabel("CO2 の濃度（ppm、月平均）")
ax.legend(loc="upper left", frameon=False, fontsize=9.5, title="北から南の順", title_fontsize=8.5)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"綾里の年平均は{m['ryori_annual_first_year']}年{m['ryori_annual_first']:.0f}ppm → 2025年{m['ryori_annual_2025']:.0f}ppm。季節で上下しながら上がり続けている", loc="left", fontsize=11)
fig.text(0.01, 0.01, "注：綾里は岩手県、与那国島は沖縄県（2024年3月で観測終了）、南鳥島は東京都の島。綾里の2011年4月は欠測。\n" + SRC_J, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_co2_monthly.png")

# ---- 図2：年増加量と日本の排出 ----
fig, axes = plt.subplots(2, 1, figsize=(8.8, 6.4), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
ax = axes[0]; r = A[A.station == "綾里"].dropna(subset=["growth"])
ax.bar(r.year, r.growth, color=C[1], width=0.75, alpha=0.85)
for (y0, y1, k) in [(1991, 2013, "ryori_growth_1991_2013"), (2014, 2025, "ryori_growth_2014_2025")]:
    ax.hlines(m[k], y0 - 0.4, y1 + 0.4, color=INK, lw=2)
    ax.text(y0, m[k] + 0.25, f"{y0}〜{y1}年の平均 {m[k]:.2f}ppm/年", fontsize=9, color=INK)
ax.set_ylabel("綾里の年増加量（ppm/年）"); ax.set_ylim(0, 4.2)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("日本の排出が減った2014年以降も、濃度の伸びは鈍っていない", loc="left", fontsize=11.5)
ax = axes[1]
ax.plot(E.fy, E.co2_total_Mt, color=C[0], lw=2.2, marker="o", ms=3)
ax.set_ylabel("日本の CO2 排出（百万トン）"); ax.set_ylim(900, 1400)
ax.text(2013, m["em_2013"] + 25, f"2013年度 {m['em_2013']:.0f}", fontsize=9, ha="center")
ax.text(2024, m["em_2024"] - 60, f"2024年度 {m['em_2024']:.0f}（−{m['em_drop_pct']:.0f}%）", fontsize=9, ha="right")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_xlim(1987.5, 2025.5)
fig.text(0.01, 0.01, "注：年増加量は年平均の前年差（2011年は欠測の月があり、2011・2012年を除く）。排出は年度。\n" + SRC_JN, fontsize=7.4, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.93, bottom=0.12, hspace=0.12)
save(fig, "fig2_growth_vs_emissions.png")

# ---- 図3：大きさの比べ ----
fig, ax = plt.subplots(figsize=(8.8, 4.6))
items = [("綾里の年増加量（2014〜2025年の平均）", m["ryori_growth_2014_2025"], C[1]),
         ("年増加量の年ごとのぶれ（標準偏差、1991〜2025年）", m["ryori_growth_sd_1991_2025"], C[3]),
         ("日本の2024年度の排出を全部大気に残るとした量", m["em_2024_ppm_upper"], C[0]),
         ("日本の排出の減少（2013→2024年度）：全部残るとした上限", m["em_drop_ppm_upper"], C[0]),
         ("同：半分が大気に残るとした場合", m["em_drop_ppm_half"], C[0])]
yy = np.arange(len(items))
for i, (lab, v, c) in enumerate(items):
    ax.barh(i, v, color=c, height=0.6, alpha=1 if i < 3 else 0.6)
    ax.text(v + 0.03, i, f"{v:.3f}" if v < 0.2 else f"{v:.2f}", va="center", fontsize=9.5)
ax.set_yticks(yy); ax.set_yticklabels([x[0] for x in items], fontsize=9); ax.invert_yaxis()
ax.set_xlim(0, 3.0); ax.set_xlabel("ppm/年")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"日本の排出の減少は、上限でも年増加量の{m['em_drop_share_of_growth_2014_2025']*100:.1f}%", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：換算は 1ppm＝CO2 7.78ギガトン（炭素2.124ギガトン）。「半分が残る」は置き方の一例（推測）。\n" + SRC_JN, fontsize=7.4, color=INK2)
fig.subplots_adjust(left=0.42, right=0.97, top=0.9, bottom=0.17)
save(fig, "fig3_scale.png")

# ---- 図4：問い直し（エルニーニョ） ----
mm = {r["model"]: r for r in q["models"]}
fig, ax = plt.subplots(figsize=(8.8, 4.9))
ax.plot(Q.year, Q.growth, color=C[1], lw=0, marker="o", ms=5, label="綾里の年増加量")
ax.plot(Q.year, Q.fit_trend, color=INK2, lw=1.5, ls="--", label=f"直線だけ（説明できる割合 R²={mm['trend']['r2']:.2f}）")
ax.plot(Q.year, Q.fit_nino, color=C[0], lw=2.2, label=f"直線＋エルニーニョ監視指数（R²={mm['trend+nino_jul_jun']['r2']:.2f}）")
ax.set_ylabel("ppm/年"); ax.set_xlim(1990, 2025); ax.set_ylim(0, 4.2)
ax.legend(loc="upper left", frameon=False, fontsize=8.8)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"年ごとの上下は、日本の排出を足しても説明が増えず（R²{mm['trend+em']['r2']:.2f}）、エルニーニョを足すと{mm['trend+nino_jul_jun']['r2']:.2f}", loc="left", fontsize=11)
fig.text(0.01, 0.01, "注：エルニーニョ監視指数は NINO.3 の海面水温の基準値との差の、前年7月〜当年6月の平均。日本の排出を足した式の R² も、直線だけとほぼ同じ。\n" + "出典：気象庁「大気中二酸化炭素濃度の観測結果」「エルニーニョ監視速報」、国立環境研究所「日本の温室効果ガス排出量データ」をもとに作成者が加工して作成", fontsize=7.2, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig4_requestion_enso.png")
print("ok")
