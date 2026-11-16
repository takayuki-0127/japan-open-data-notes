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
SRC = "出典：財務省「貿易統計」、日本銀行「時系列統計データ」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
ser = pd.read_csv(R / "annual_series.csv")

# ---- 図1：貿易収支と、燃料を除いた収支 -----------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.bar(ser.year, ser.balance_tyen, color=[C[1] if v < 0 else C[0] for v in ser.balance_tyen], width=0.7)
ax.plot(ser.year, ser.balance_ex_fuel_tyen, color=INK, lw=2, marker="o", ms=4)
ax.axhline(0, color=INK2, lw=1)
ax.text(2000.3, 27.5, "鉱物性燃料の輸入を除いた収支（線）", fontsize=9.5, color=INK)
ax.text(2016.5, -17.5, "貿易収支（棒）", fontsize=9.5, color=INK)
y22 = ser.set_index("year").loc[2022]
ax.text(2022, y22.balance_tyen - 1.8, f"{y22.balance_tyen:.1f}", ha="center", fontsize=9, color=INK)
ax.text(2022, y22.balance_ex_fuel_tyen - 3.2, f"+{y22.balance_ex_fuel_tyen:.1f}", ha="center", fontsize=9, color=INK)
ax.set_ylabel("兆円")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("2022年の貿易赤字は20.3兆円。燃料の輸入を除くと13.4兆円の黒字だった", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：通関ベース（輸出 − 輸入）、暦年、2000〜2025年。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_trade_balance.png")

# ---- 図2：燃料3品目の分解（期間ごと） ---------------------------------------------------
cases = [("2019_2022", "2019→2022"), ("2020_2022", "2020→2022"), ("2022_2025", "2022→2025"), ("2020_2025", "2020→2025")]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = np.arange(len(cases)); w = 0.22
for i, (k, lab, c) in enumerate([("qty_tyen", "数量", C[2]), ("usd_price_tyen", "ドル建ての値段", C[1]), ("fx_tyen", "円安（ドル円）", C[0])]):
    v = [main[f"fuel3_{cs}"][k] for cs, _ in cases]
    ax.bar(x + (i - 1) * w, v, width=w - 0.02, color=c, label=lab)
    for xi, vi in zip(x, v):
        ax.text(xi + (i - 1) * w, vi + (0.3 if vi >= 0 else -1.0), f"{vi:+.1f}", ha="center", fontsize=8.5, color=INK)
tot = [main[f"fuel3_{cs}"]["dV_tyen"] for cs, _ in cases]
ax.plot(x, tot, color=INK, marker="D", lw=0, ms=7, label="輸入額の変化（合計）")
ax.axhline(0, color=INK2, lw=1)
ax.set_xticks(x, [lab for _, lab in cases])
ax.set_ylabel("燃料3品目の輸入額の変化への寄与（兆円）")
ax.legend(frameon=False, fontsize=9, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.08))
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
f = main["fuel3_2020_2022"]
ax.set_title(f"2020→22年の燃料の輸入増 {f['dV_tyen']:.1f}兆円のうち、ドル建ての値上がりが{f['usd_price_tyen']:.1f}兆円、円安が{f['fx_tyen']:.1f}兆円", loc="left", fontsize=11, pad=26)
fig.text(0.01, 0.01, "注：燃料3品目＝原油及び粗油・液化天然ガス・石炭。LMDI 法（対数平均の重み）で、3つの寄与の和が輸入額の変化に一致する。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.85, bottom=0.14)
save(fig, "fig2_fuel_decomposition.png")

# ---- 図3：品目ごと（2020→2022） -----------------------------------------------------------
bi = main["by_item_2020_2022"]
items = ["原油", "LNG", "石炭"]
fig, ax = plt.subplots(figsize=(8.4, 4.8))
x = np.arange(3)
bottom_pos = np.zeros(3); bottom_neg = np.zeros(3)
for k, lab, c in [("qty_tyen", "数量", C[2]), ("price_tyen", "ドル建ての値段", C[1]), ("fx_tyen", "円安（ドル円）", C[0])]:
    v = np.array([bi[i][k] for i in items])
    b = np.where(v >= 0, bottom_pos, bottom_neg)
    ax.bar(x, v, bottom=b, color=c, width=0.55, label=lab, edgecolor="#fcfcfb", lw=1)
    bottom_pos += np.where(v >= 0, v, 0); bottom_neg += np.where(v < 0, v, 0)
for xi, i in zip(x, items):
    ax.text(xi, bottom_pos[xi] + 0.2, f"+{bi[i]['dV_tyen']:.1f}兆円\nドル建て単価 {bi[i]['usd_price_change_pct']:+.0f}%\n数量 {bi[i]['qty_change_pct']:+.1f}%", ha="center", fontsize=9, color=INK)
ax.set_xticks(x, items)
ax.set_ylim(-0.6, 12.5)
ax.set_ylabel("輸入額の変化への寄与（兆円）")
ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("どの燃料でも、増えた分の大半はドル建ての値上がり（2020→2022年）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：ドル建て単価＝円の輸入単価÷ドル円の年平均。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.13)
save(fig, "fig3_fuel_items.png")

# ---- 図4：問い直し（円安の分を輸出と輸入で差し引く） --------------------------------------------
cs = [("2020_2022", "2020→2022"), ("2019_2022", "2019→2022"), ("2020_2025", "2020→2025")]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = np.arange(len(cs)); w = 0.2
for i, (k, lab, c, sign) in enumerate([("exports_fx_part_tyen", "輸出の円安の分（収支を良くする）", C[0], 1),
                                        ("imports_fx_part_tyen", "輸入の円安の分（収支を悪くする）", C[1], -1),
                                        ("net_fx_on_balance_tyen", "差し引き（円安の分）", INK2, 1),
                                        ("d_balance_tyen", "貿易収支の変化（全体）", C[2], 1)]):
    v = [sign * req[c_][k] for c_, _ in cs]
    ax.bar(x + (i - 1.5) * w, v, width=w - 0.02, color=c, label=lab)
    for xi, vi in zip(x, v):
        ax.text(xi + (i - 1.5) * w, vi + (0.4 if vi >= 0 else -1.4), f"{vi:+.1f}", ha="center", fontsize=8.3, color=INK)
ax.axhline(0, color=INK2, lw=1)
ax.set_xticks(x, [lab for _, lab in cs])
ax.set_ylabel("貿易収支への寄与（兆円）")
ax.set_ylim(-25, 24)
ax.legend(frameon=False, fontsize=8.8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.12))
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
q = req["2020_2022"]
ax.set_title(f"2020→22年の収支の悪化 {abs(q['d_balance_tyen']):.1f}兆円のうち、輸出と輸入の円安の分を差し引いた分は {abs(q['net_fx_on_balance_tyen']):.1f}兆円", loc="left", fontsize=11, pad=40)
fig.text(0.01, 0.01, "注：円安の分＝輸出入額 ×（物価指数の円ベース÷契約通貨ベース）の変化（LMDI）。契約通貨での値段が為替で変わらないと仮定した近似。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.14)
save(fig, "fig4_fx_net_effect.png")
print("figures done")
