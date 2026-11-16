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
SRC = "出典：財務省・日本銀行「国際収支統計」、日本銀行「外国為替市況」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
net = pd.read_csv(R / "annual_net.csv", index_col=0).loc[2014:2025]
tab = pd.read_csv(R / "digital_annual.csv").set_index("year")

# ---- 図1：項目別の赤字（積み上げ） -------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
items = [("コンピュータ", C[0]), ("著作権等使用料", C[1]), ("専門・経営コンサル", C[2])]
bottom = np.zeros(len(net))
for it, c in items:
    v = -net[it].values
    ax.bar(net.index, v, bottom=bottom, color=c, width=0.7, label=it, edgecolor="#fcfcfb", lw=1)
    bottom += v
for y, v in zip(net.index, bottom):
    if y in (2014, 2019, 2024, 2025):
        ax.text(y, v + 0.12, f"{v:.1f}", ha="center", fontsize=9.5, color=INK)
ax.set_ylabel("赤字（兆円、受取 − 支払 の符号を反転）")
ax.legend(frameon=False, fontsize=9.5, loc="upper left")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"デジタル赤字（3項目）は2014年の{main['deficit3_tyen']['2014']:.1f}兆円から2025年の{main['deficit3_tyen']['2025']:.1f}兆円に。年率{main['cagr_3_2014_2025_pct']:.0f}%", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：3項目＝コンピュータサービス・著作権等使用料・専門・経営コンサルティングサービス（情報通信白書と同じ）。暦年。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_deficit_by_item.png")

# ---- 図2：円とドル --------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.6))
yen = -tab["3項目_ネット"].loc[2014:2025]
usd = pd.Series(req["deficit_busd_annual"]).astype(float); usd.index = usd.index.astype(int)
axes[0].plot(yen.index, yen.values, color=C[0], lw=2, marker="o", ms=4); axes[0].set_title("円で見た赤字（兆円）", loc="left", fontsize=11)
axes[1].plot(usd.index, usd.values, color=C[1], lw=2, marker="o", ms=4); axes[1].set_title("ドルで見た赤字（10億ドル）", loc="left", fontsize=11)
for ax, s in zip(axes, [yen, usd]):
    for y in (2020, 2025):
        ax.text(y, s.loc[y] * 1.04, f"{s.loc[y]:.1f}", ha="center", fontsize=9.5, color=INK)
    ax.set_ylim(0, s.max() * 1.2); ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
h = main["h2"]
fig.suptitle(f"2020→25年に、円では{h['yen_change_pct']:+.0f}%、ドルでは{h['usd_change_pct']:+.0f}%。円での伸びの{h['fx_share_pct']:.0f}%は円安の分", x=0.01, ha="left", fontsize=12)
fig.text(0.01, 0.01, "注：ドル建ては、各月の円の額をその月のドル円（月中平均）で割って足したもの。3項目の定義。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.06, right=0.98, top=0.84, bottom=0.15, wspace=0.25)
save(fig, "fig2_yen_vs_usd.png")

# ---- 図3：受取と支払 ---------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.6, 4.9))
for col, lab, c in [("3項目_支払", "支払", C[1]), ("3項目_受取", "受取", C[0])]:
    s = tab[col].loc[2014:2025]
    ax.plot(s.index, s.values, color=c, lw=2.2, marker="o", ms=4)
    ax.text(2025.3, s.iloc[-1], f"{lab}\n{s.iloc[-1]:.1f}兆円", fontsize=9.5, color=INK, va="center")
    ax.text(2014, s.iloc[0] + 0.35, f"{s.iloc[0]:.1f}", ha="center", fontsize=9.5, color=INK)
ax.set_xlim(2013.5, 2027.5); ax.set_ylim(0, 13)
ax.set_ylabel("兆円")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
h3 = main["h3"]
ax.set_title(f"支払は{h3['d_payments_tyen']:.1f}兆円増、受取も{h3['d_receipts_tyen']:.1f}兆円増。差の赤字は{h3['d_deficit_tyen']:.1f}兆円の拡大（2014→25年）", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：3項目の合計。暦年。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.13)
save(fig, "fig3_payments_receipts.png")

# ---- 図4：問い直し（12か月の移動合計） --------------------------------------------------
rl = pd.read_csv(R / "requestion_rolling12.csv")
rl["date"] = pd.to_datetime(rl["period"].astype(str) + "01", format="%Y%m%d")
rl = rl[rl.date >= "2018-01-01"]
fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.6))
axes[0].plot(rl.date, rl.deficit_tyen_12m, color=C[0], lw=2); axes[0].set_title("円（兆円、直近12か月の合計）", loc="left", fontsize=11)
axes[1].plot(rl.date, rl.deficit_busd_12m, color=C[1], lw=2); axes[1].set_title("ドル（10億ドル、直近12か月の合計）", loc="left", fontsize=11)
for ax, col in zip(axes, ["deficit_tyen_12m", "deficit_busd_12m"]):
    pk = rl.loc[rl[col].idxmax()]; la = rl.iloc[-1]
    ax.annotate(f"山 {pk.date.year}年{pk.date.month}月\n{pk[col]:.1f}", xy=(pk.date, pk[col]), xytext=(pd.Timestamp("2019-01-01"), pk[col] * 0.97),
                fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.text(la.date, la[col] * 0.82, f"{la.date.year}年{la.date.month}月\n{la[col]:.1f}", fontsize=9, color=INK, ha="right")
    ax.set_ylim(0, rl[col].max() * 1.15); ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
fig.suptitle(f"伸びは2025年春から止まり、ドルで見ると直近は前年比{req['yoy_usd_last_pct']:+.1f}%", x=0.01, ha="left", fontsize=12)
fig.text(0.01, 0.01, "注：3項目、月次の12か月移動合計。2018年1月〜2026年9月。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.06, right=0.98, top=0.84, bottom=0.15, wspace=0.25)
save(fig, "fig4_rolling12.png")
print("figures done")
