"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：総務省「消費者物価指数」2025年基準 財・サービス分類指数をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
d = pd.read_csv(D / "cpi_monthly.csv").set_index("ym")
yoy = pd.read_csv(R / "yoy.csv").set_index("ym")
x = (yoy.index // 100) + ((yoy.index % 100) - 0.5) / 12

# 図1 前年比
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(x, yoy.goods, color=C[1], lw=1.3, label="財")
ax.plot(x, yoy.services, color=C[0], lw=1.8, label="サービス")
ax.axhline(0, color=INK2, lw=0.8)
ax.axvspan(1995, 2013, color="#f1efe8", lw=0)
ax.text(1996, 20, f"1995〜2012年の平均\n財 {m['goods_1995_2012']:+.1f}%・サービス {m['services_1995_2012']:+.1f}%", fontsize=9, color=INK2)
ax.set_xlim(1971, 2027); ax.set_ylim(-6, 32)
ax.set_ylabel("前年同月比（%）")
ax.legend(frameon=False, loc="upper right", fontsize=9)
style(ax)
ax.set_title(f"1970〜80年代はサービスの方が速く上がった。2022年からは財が{m['goods_2022_2025']:.1f}%、サービスは{m['services_2022_2025']:.1f}%（年平均）", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig1_yoy_goods_services.png", SRC, "注：1989・97・2014・19年の消費税率の引き上げを含む。")

# 図2 2021年平均＝100
ann21 = d.loc[202101:202112].mean()
s = d.loc[202101:] / ann21 * 100
xs = (s.index // 100) + ((s.index % 100) - 0.5) / 12
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for col, lab, c, lw in [("goods", "財", C[1], 2.2), ("eating_out", "外食", C[3], 1.8), ("other_services", "他のサービス", C[2], 1.8),
                        ("services", "サービス（計）", C[0], 2.4), ("public_services", "公共サービス", C[5], 1.4), ("imputed_rent", "持家の帰属家賃", C[4], 1.4)]:
    ax.plot(xs, s[col], color=c, lw=lw, label=lab)
    ax.text(xs[-1] + 0.05, s[col].iloc[-1], f"{s[col].iloc[-1]:.0f}", fontsize=8.6, color=c, va="center")
ax.set_xlim(2021, 2027.1)
ax.set_ylabel("2021年平均＝100")
ax.legend(frameon=False, loc="upper left", fontsize=9, ncol=2)
style(ax)
ax.set_title(f"2021年→2026年9月：財は+{m['goods_since2021']:.0f}%、サービスは+{m['services_since2021']:.0f}%（外食は+{m['eating_out_since2021']:.0f}%）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.14)
save(fig, F / "fig2_since_2021.png", SRC)

# 図3 動かなかった月の割合
z = pd.read_csv(R / "zero_change.csv").set_index("series")
lab = {"goods": "財", "goods_ex_fresh": "生鮮食品を除く財", "services": "サービス", "services_ex_rent": "帰属家賃を除くサービス",
       "public_services": "公共サービス", "general_services": "一般サービス", "eating_out": "外食", "private_rent": "民営家賃"}
order = ["goods", "goods_ex_fresh", "services", "services_ex_rent", "general_services", "public_services", "eating_out", "private_rent"]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
xx = np.arange(len(order))
ax.bar(xx - 0.2, z.loc[order, "z_1995_2012"], 0.4, color=C[0], label="1995〜2012年")
ax.bar(xx + 0.2, z.loc[order, "z_2013_2026"], 0.4, color=C[1], label="2013年〜2026年9月")
ax.set_xticks(xx, [lab[o] for o in order], rotation=20, ha="right")
ax.set_ylabel("前月から指数が動かなかった月の割合（%）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"サービスは{m['zero_services']:.0f}%の月で動かない（生鮮食品を除く財は{m['zero_goods_ex_fresh']:.0f}%）。外食は動く月が増えた", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.26)
save(fig, F / "fig3_zero_change.png", SRC, "注：指数（小数第1位）の前月差が0の月の割合。")

# 図4 サービスの上昇の内訳
c = pd.read_csv(R / "services_contrib.csv")
fig, ax = plt.subplots(figsize=(8.8, 4.6))
ax.barh(c.part[::-1], c.contrib_pt[::-1], color=[C[3] if p == "外食" else (C[2] if p == "他のサービス" else C[5]) for p in c.part[::-1]])
for yv, (v, ch, ws) in enumerate(zip(c.contrib_pt[::-1], c.change_pct[::-1], c.weight_share[::-1])):
    ax.text(v + 0.05, yv, f"{v:.2f}ポイント（上昇 {ch:+.1f}%、重み {ws:.0f}%）", va="center", fontsize=9)
ax.set_xlim(0, 5.6)
ax.set_xlabel("2021年平均→2026年9月のサービスの上昇への寄与（ポイント、近似）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"サービスの上昇の{q['other_services_share_of_rise']:.0f}%は他のサービス、{q['eating_out_share_of_rise']:.0f}%は外食。家賃と公共サービスはほぼ動かない", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.17, right=0.97, top=0.9, bottom=0.21)
save(fig, F / "fig4_services_contrib.png", SRC, "注：寄与＝2025年基準のウエイトの割合×上昇率。基準年の違いがあるので近似（合計6.6ポイント、実際のサービスの上昇は6.2%）。")
