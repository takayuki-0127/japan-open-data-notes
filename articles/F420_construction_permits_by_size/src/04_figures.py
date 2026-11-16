"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：国土交通省「建設業許可業者数調査の結果について（令和7年3月末現在）」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
tot = pd.read_csv(D / "total.csv").set_index("year")
cap = pd.read_csv(D / "capital_long.csv")
w = cap.pivot(index="year", columns="cls", values="firms")
c = pd.read_csv(R / "contrib.csv")

# 図1 総数の推移
fig, ax = plt.subplots(figsize=(8.8, 4.9))
ax.plot(tot.index, tot.total / 1e4, color=C[0], lw=2.3)
ax.annotate(f"2000年3月末 {m['total_2000']/1e4:.1f}万（最多）", (2000, m["total_2000"] / 1e4), xytext=(1975, 61), fontsize=9,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.annotate(f"2025年3月末 {m['total_2025']/1e4:.1f}万", (2025, m["total_2025"] / 1e4), xytext=(2008, 40), fontsize=9,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xlim(1957, 2026); ax.set_ylim(0, 65)
ax.set_ylabel("許可業者数（万、各年3月末）")
style(ax)
ax.set_title(f"許可業者は2000年から{-m['net_change']/1e4:.1f}万（{-m['net_pct']:.1f}%）減り、ここ数年は少し増えている", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.17)
save(fig, F / "fig1_total.png", SRC, "注：1972年の急増は、登録制から許可制への切り替えの時期にあたる（理由は推測）。")

# 図2 階層のまとまりごとの推移
grp = {"個人": ["individual"], "法人 資本金1,000万円未満": ["lt2m", "2m_5m", "5m_10m"],
       "法人 1,000万〜5,000万円": ["10m_50m"], "法人 5,000万円以上": ["50m_100m", "100m_1b", "ge1b"]}
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for i, (k, cols) in enumerate(grp.items()):
    s = w[cols].sum(axis=1) / 1e4
    ax.plot(s.index, s.values, color=C[i], lw=2.2)
    ax.text(2025.4, s.iloc[-1], f"{k}\n{s.iloc[-1]:.1f}万", fontsize=8.6, color=C[i], va="center")
ax.axvline(2006, color=GRID, lw=1); ax.text(2006.3, 24.5, "2006年 会社法\n（最低資本金の撤廃）", fontsize=8, color=INK2)
ax.set_xlim(1993, 2033); ax.set_ylim(0, 26)
ax.set_ylabel("許可業者数（万）")
style(ax)
ax.set_title("個人と資本金1,000万〜5,000万円の会社が減り、1,000万円未満の会社が増えた", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.17)
save(fig, F / "fig2_capital_groups.png", SRC, "注：1996〜97年の1,000万円未満の会社の減少は、商法改正で最低資本金（株式会社1,000万円、有限会社300万円）が求められたため（推測を含む）。")

# 図3 2000→2025年の増減（階層別）
order = ["individual", "lt2m", "2m_5m", "5m_10m", "10m_50m", "50m_100m", "100m_1b", "ge1b"]
c = c.set_index("cls").loc[order[::-1]].reset_index()
fig, ax = plt.subplots(figsize=(8.8, 5.0))
cols = [C[1] if v < 0 else C[2] for v in c.change]
ax.barh(c.label, c.change / 1e4, color=cols)
for y, v in enumerate(c.change):
    lab_ = f"{v/1e4:+.1f}万" if abs(v) >= 5000 else f"{v:+,}業者"
    ax.text(v / 1e4 + (0.2 if v >= 0 else -0.2), y, lab_, va="center", ha="left" if v >= 0 else "right", fontsize=9)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlim(-11.5, 5)
ax.set_xlabel("2000→2025年の増減（万、各年3月末）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"純減{-m['net_change']/1e4:.1f}万の内訳：個人 {m['chg_individual']/1e4:.1f}万、1,000万〜5,000万円の会社 {m['chg_10m_50m']/1e4:.1f}万", loc="left", fontsize=12)
fig.subplots_adjust(left=0.25, right=0.97, top=0.91, bottom=0.17)
save(fig, F / "fig3_change_by_class.png", SRC)

# 図4 前年比と5年ごとの波
yo = tot.loc[1996:2025, "yoy_pct"]
fig, ax = plt.subplots(figsize=(8.8, 4.9))
for b in (2001, 2006, 2011, 2016, 2021):
    ax.axvspan(b - 0.5, b + 2.5, color="#f1efe8", lw=0)
ax.bar(yo.index, yo.values, color=[C[1] if v < 0 else C[0] for v in yo.values], width=0.75)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlim(1995.3, 2025.7)
ax.set_ylabel("許可業者数の前年比（%）")
style(ax)
ax.set_title(f"減少は5年ごとにまとまる（網かけの年に2001年以降の純減の{q['wave_share_of_net']:.0f}%）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.17)
save(fig, F / "fig4_yoy_waves.png", SRC, f"注：網かけは2001〜03、06〜08、11〜13、16〜18、21〜23年。前年比の5年ずらしの自己相関は{m['acf_lag5']:.2f}。許可の有効期間は5年。")
