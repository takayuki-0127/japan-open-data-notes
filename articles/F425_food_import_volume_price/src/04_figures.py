"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：財務省「貿易統計」、日本銀行「外国為替相場」「輸入物価指数」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
lv = pd.read_csv(R / "item_levels.csv").set_index("year")
dc = pd.read_csv(R / "decomp_items.csv")
yd = pd.read_csv(R / "yearly_decomp.csv").set_index("year")
fx = pd.read_csv(D / "fx_prices_annual.csv").set_index("year")
JP = {"fish": "魚介類", "meat": "肉類", "cereals": "穀物類", "vegetables": "野菜", "fruit": "果実"}

# 図1 金額（5品目と食料品計）
s = lv.loc[2000:2025]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
bottom = np.zeros(len(s))
for i, it in enumerate(JP):
    ax.bar(s.index, s[f"{it}_value_cho"], bottom=bottom, color=C[i], width=0.8, label=JP[it])
    bottom += s[f"{it}_value_cho"].values
ax.plot(s.index, s["food_total_value_cho"], color=INK, lw=1.8, marker="o", ms=3, label="食料品の輸入額（計）")
ax.set_ylabel("兆円（暦年）")
ax.legend(frameon=False, loc="upper left", fontsize=9, ncol=2)
style(ax)
ax.set_title(f"食料品の輸入額は2020年の{m['food_total_2020']:.1f}兆円から2025年の{m['food_total_2025']:.1f}兆円へ（+{m['food_total_g']:.0f}%）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig1_food_imports.png", SRC, f"注：5品目は2025年の食料品の輸入額の{m['cover_5items_2025']:.0f}%。")

# 図2 2020→2025年の分解（品目別）
order = ["total5", "fish", "meat", "cereals", "vegetables", "fruit"]
d = dc.set_index("item").loc[order]
labs = ["5品目の合計"] + [JP[i] for i in order[1:]]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = np.arange(len(order))
parts = [("l_qty", "数量", C[2]), ("l_usd_price", "ドルで見た単価", C[3]), ("l_fx", "ドル円（円安）", C[1])]
pos = np.zeros(len(order)); neg = np.zeros(len(order))
for k, lab, col in parts:
    v = d[k].values * 100
    b = np.where(v >= 0, pos, neg)
    ax.bar(x, v, bottom=b, color=col, width=0.6, label=lab)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.scatter(x, d.l_value * 100, color=INK, zorder=3, s=22, label="金額の伸び（対数×100）")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x, labs)
ax.set_ylabel("2020→2025年の伸び（対数×100）")
ax.legend(frameon=False, loc="upper left", fontsize=9, ncol=2)
style(ax)
qtxt = "ほぼ0" if abs(m['t5_share_qty']) < 1 else f"{m['t5_share_qty']:.0f}%"
ax.set_ylim(-6, 68)
ax.set_title(f"2020→25年の金額の伸びの{m['t5_share_fx']:.0f}%は円安、ドル単価は{m['t5_share_usd_price']:.0f}%、数量は{qtxt}", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig2_decomp_2020_2025.png", SRC, f"注：金額＝数量×ドル単価×ドル円（年平均 {m['usdjpy_2020']:.1f}円→{m['usdjpy_2025']:.1f}円）。5品目の合計は金額の割合で重みづけた（ディビジア型）。")

# 図3 年ごとの分解
fig, ax = plt.subplots(figsize=(8.8, 5.0))
pos = np.zeros(len(yd)); neg = np.zeros(len(yd))
for k, lab, col in parts:
    v = yd[k].values
    b = np.where(v >= 0, pos, neg)
    ax.bar(yd.index, v, bottom=b, color=col, width=0.7, label=lab)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.plot(yd.index, np.log(1 + yd.value_pct / 100) * 100, color=INK, marker="o", ms=3.5, lw=1.4, label="金額の伸び")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("前年比（対数×100）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"ドル単価は2021〜22年に+{q['usd_price_2021_2022']:.0f}、2023〜25年に{q['usd_price_2023_2025']:.0f}。円安は5年で+{q['fx_2021_2025']:.0f}", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig3_yearly_decomp.png", SRC, "注：5品目（魚介類・肉類・穀物類・野菜・果実）。単位は対数×100（足し算できる伸び率）。")

# 図4 輸入物価指数と通関の円単価
lv2 = pd.read_csv(R / "item_levels.csv").set_index("year")
dd = []
base = 2020
idx_unit = [100.0]
for y in range(2021, 2026):
    x = dc  # 2020→2025 only; 年ごとの連鎖を作る
for y in range(base + 1, 2026):
    r_ = yd.loc[y]
    idx_unit.append(idx_unit[-1] * np.exp((r_.l_usd_price + r_.l_fx) / 100))
yrs = list(range(base, 2026))
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(yrs, fx.loc[base:2025, "ipi_food_yen"] / fx.loc[base, "ipi_food_yen"] * 100, color=C[1], lw=2.2, marker="o", ms=3.5, label="輸入物価指数（円ベース）")
ax.plot(yrs, fx.loc[base:2025, "ipi_food_contract"] / fx.loc[base, "ipi_food_contract"] * 100, color=C[0], lw=2.2, marker="o", ms=3.5, label="輸入物価指数（契約通貨ベース）")
ax.plot(yrs, idx_unit, color=C[1], lw=1.6, ls="--", marker="s", ms=3, label="通関の円単価（5品目、連鎖）")
ax.plot(yrs, fx.loc[base:2025, "usdjpy_avg"] / fx.loc[base, "usdjpy_avg"] * 100, color=C[5], lw=1.2, ls=":", label="ドル円")
ax.set_ylabel("2020年＝100")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"輸入物価指数（飲食料品）は円で+{m['ipi_food_yen_g']:.0f}%、契約通貨で+{m['ipi_food_contract_g']:.0f}%。通関の5品目より大きい", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig4_ipi_vs_unit_value.png", SRC, "注：輸入物価指数は「飲食料品・食料用農水産物」（2020年基準、年平均）。通関の円単価は5品目の数量あたり金額を年ごとに連鎖。")
