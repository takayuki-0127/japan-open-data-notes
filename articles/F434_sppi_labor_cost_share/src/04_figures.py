"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：日本銀行「企業向けサービス価格指数」（2020年基準、消費税を除く）をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
e = pd.read_csv(D / "extax.csv").set_index("ym")
x = (e.index // 100) + ((e.index % 100) - 0.5) / 12

# 図1 指数（2000年平均＝100）
a00 = e.loc[200001:200012].mean()
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for c, lab, col in [("high_labor", "高人件費率サービス", C[1]), ("low_labor", "低人件費率サービス", C[0]), ("all", "総平均", C[5])]:
    s = e[c] / a00[c] * 100
    ax.plot(x, s, color=col, lw=2.2 if c != "all" else 1.3, label=lab)
    ax.text(x[-1] + 0.2, s.iloc[-1], f"{s.iloc[-1]:.0f}", fontsize=9, color=col, va="center")
ax.set_xlim(2000, 2027.8); ax.set_ylabel("2000年平均＝100")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"人件費の割合が高いサービスは2000〜20年に年{m['high_cagr_2000_2020']:+.2f}%、低いサービスは{m['low_cagr_2000_2020']:+.2f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.14)
save(fig, F / "fig1_index_high_low.png", SRC, "注：高人件費率・低人件費率は、日本銀行が産業連関表の人件費の割合をもとに分けた参考指数。")

# 図2 前年比
yoy = pd.read_csv(R / "yoy.csv").set_index("ym")
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(x, yoy.high_labor, color=C[1], lw=2, label="高人件費率サービス")
ax.plot(x, yoy.low_labor, color=C[0], lw=1.6, label="低人件費率サービス")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlim(2000, 2027); ax.set_ylabel("前年同月比（%）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"前年比の振れ（標準偏差）は高人件費率{m['sd_high']:.1f}%、低人件費率{m['sd_low']:.1f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig2_yoy.png", SRC)

# 図3 年ごとの差
t = pd.read_csv(R / "yearly_gap.csv").dropna(subset=["gap"])
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.bar(t.year, t.gap, color=[C[1] if g > 0 else C[0] for g in t.gap], width=0.75)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("前年比（年平均）の差：高人件費率 − 低人件費率（ポイント）")
style(ax)
ax.set_title(f"2001〜20年は{q['years_high_above_2001_2020']}年で高人件費率の方が上がった。2021〜23年だけ逆", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.14)
save(fig, F / "fig3_yearly_gap.png", SRC, f"注：2026年は1〜9月のうち、高人件費率の前年比の方が高かったのは{q['months_high_above_2026']}か月。")

# 図4 大類別
JP = {"finance": "金融・保険", "real_estate": "不動産", "transport": "運輸・郵便", "ict": "情報通信", "leasing": "リース・レンタル", "advertising": "広告", "other_services": "諸サービス"}
v = pd.Series({JP[k]: m[f"{k}_since2021"] for k in JP}).sort_values()
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.barh(v.index, v.values, color=C[2])
for yv, val in enumerate(v.values):
    ax.text(val + 0.3, yv, f"{val:+.1f}%", va="center", fontsize=9)
ax.axvline(m["all_since2021"], color=INK2, ls="--", lw=1); ax.text(m["all_since2021"] + 0.3, -0.6, f"総平均 {m['all_since2021']:+.1f}%", fontsize=8.8, color=INK2)
ax.set_xlim(0, 30); ax.set_xlabel("2021年平均→2026年9月の上昇率（%）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("2021年からはリース・レンタルと運輸・郵便が大きく上がった", loc="left", fontsize=12)
fig.subplots_adjust(left=0.18, right=0.97, top=0.9, bottom=0.15)
save(fig, F / "fig4_major_groups.png", SRC)
