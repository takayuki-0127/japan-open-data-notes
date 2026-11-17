"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib, importlib.util
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：総務省「消費者物価指数」2025年基準 品目別価格指数、気象庁「過去の気象データ検索」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
JP = {"fresh_veg": "生鮮野菜", "cabbage": "キャベツ", "chinese_cabbage": "はくさい", "lettuce": "レタス", "radish": "だいこん", "cucumber": "きゅうり",
      "tomato": "トマト", "spinach": "ほうれんそう", "leek": "ねぎ"}

# 図1 値段のずれと、天気で説明できる分
p = pd.read_csv(R / "panel.csv").set_index("ym")
x = (p.index // 100) + ((p.index % 100) - 0.5) / 12
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(x, p.y, color=C[5], lw=1.2, label="生鮮野菜の値段のずれ（実際）")
ax.plot(x, p.fitted, color=C[1], lw=1.8, label="天気のずれで説明できる分")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("ずれ（%、季節と長い流れを除く）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"天気（気温・雨・日照、当月〜2か月前）で説明できるのは、月ごとのずれの{m['adj_r2']*100:.0f}%だけ", loc="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig1_fit.png", SRC, "注：生鮮野菜の指数÷生鮮食品を除く総合の対数から、25か月移動平均と暦月の平均を除いた。天気は7地点（札幌・水戸・前橋・銚子・長野・名古屋・熊本）の平年とのずれ。")

# 図2 季節・品目ごとの説明力
it = pd.read_csv(R / "items.csv")
rb = pd.read_csv(R / "robustness.csv").set_index("check")
fig, ax = plt.subplots(1, 2, figsize=(9.6, 4.8), gridspec_kw={"width_ratios": [1, 1.7]})
vals = [m["adj_r2"], rb.loc["夏（6〜9月）", "adj_r2"], rb.loc["冬（12〜3月）", "adj_r2"]]
ax[0].bar(["全部の月", "夏\n（6〜9月）", "冬\n（12〜3月）"], [v * 100 for v in vals], color=[C[5], C[3], C[0]])
for i, v in enumerate(vals):
    ax[0].text(i, v * 100 + 0.8, f"{v*100:.0f}%", ha="center", fontsize=9.5)
ax[0].set_ylabel("説明できる割合（自由度調整済み決定係数、%）"); ax[0].set_ylim(0, 40); style(ax[0])
ax[0].set_title("生鮮野菜", loc="left", fontsize=10.5)
o = it.sort_values("adj_r2")
ax[1].barh([JP[i] for i in o.item], o.adj_r2 * 100, color=C[2])
for yv, v in enumerate(o.adj_r2):
    ax[1].text(v * 100 + 0.4, yv, f"{v*100:.0f}%", va="center", fontsize=9)
ax[1].set_xlabel("説明できる割合（%、全部の月）"); ax[1].set_xlim(0, 25)
ax[1].grid(axis="x", color=GRID, lw=0.8); ax[1].set_axisbelow(True)
ax[1].set_title("品目別", loc="left", fontsize=10.5)
fig.suptitle(f"冬は{rb.loc['冬（12〜3月）','adj_r2']*100:.0f}%を天気で説明できる。品目ではきゅうりが最も高い（{m['best_item_r2']*100:.0f}%）", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.97, top=0.86, bottom=0.15, wspace=0.45)
save(fig, F / "fig2_explained_share.png", SRC)

# 図3 冬の気温と値段
spec = importlib.util.spec_from_file_location("a3", ROOT / "src" / "03_analysis.py"); a3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(a3)
c = pd.read_csv(D / "cpi_veg.csv").set_index("ym"); W = pd.read_csv(D / "weather.csv", dtype={"st": str})
wa = a3.weather_anom(W, a3.ALL7); t2 = (wa.temp + wa.temp.shift(1)) / 2
df = pd.concat([a3.price_anom(c, "fresh_veg").rename("y"), t2.rename("t")], axis=1).dropna()
df = df[(df.index % 100).isin([12, 1, 2, 3]) & (df.index >= 200001)]
fig, ax = plt.subplots(figsize=(7.6, 5.6))
ax.scatter(df.t, df.y, s=22, color=C[0], alpha=0.75)
xx = np.linspace(df.t.min(), df.t.max(), 10); b = np.polyfit(df.t, df.y, 1)
ax.plot(xx, np.polyval(b, xx), color=C[1], lw=1.6)
ax.axhline(0, color=GRID, lw=0.8); ax.axvline(0, color=GRID, lw=0.8)
ax.set_xlabel("当月と前月の気温の平年とのずれ（℃、7地点平均）"); ax.set_ylabel("生鮮野菜の値段のずれ（%）")
style(ax)
ax.set_title(f"冬は暖かいほど野菜が安い：1℃で{q['fresh_slope']:.1f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.12, right=0.97, top=0.92, bottom=0.15)
save(fig, F / "fig3_winter_temp.png", SRC, f"注：2000〜2025年の12〜3月（{q['n']}か月）。")

# 図4 品目別の冬の気温の効き方
wt = pd.read_csv(R / "winter_temp.csv")
wt = wt[wt.item != "fresh_veg"].sort_values("slope_pct_per_degC")
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.barh([JP[i] for i in wt.item], wt.slope_pct_per_degC, xerr=1.96 * wt.se, color=C[0], ecolor=INK2, capsize=3)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("冬の気温が平年より1℃高いときの値段の変化（%、95%区間）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"キャベツは1℃で{q['cabbage_slope']:.0f}%、レタス{q['lettuce_slope']:.0f}%、だいこん{q['radish_slope']:.0f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.16, right=0.97, top=0.9, bottom=0.17)
save(fig, F / "fig4_winter_items.png", SRC, "注：12〜3月の月だけ。標準誤差は月の並びの自己相関を考えた HAC。")
