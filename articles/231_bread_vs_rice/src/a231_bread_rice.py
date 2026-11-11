"""231 パンと米、どちらにお金を使う世帯が多いのか

家計調査（二人以上の世帯）の「米」と「パン」の1世帯当たり年間支出を、
  1. 全国の長期（2015〜2025年）と2026年1〜9月：パン÷米の比
  2. 年報（第4-6表の平均）の購入数量で、2019→2025年の「量」と「1kgあたりの値段」に分ける
  3. 都道府県庁所在市・政令指定都市の52市で、パンが米を上回る市の数（2015・2019・2023・2024・2025年）
  4. 世帯主の年齢別のパン÷米（2019・2025年）
で比べる。市の値は1年分で、集計世帯は1市あたり約100世帯（年による振れが大きい）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, AGES, setup_font, annual, monthly, detail, cpi

setup_font()
P = annual()
C = cpi()
YRS = list(range(2015, 2026))
nat = P.loc[YRS, ["米", "パン", "食パン", "他のパン"]]
ratio = nat["パン"] / nat["米"]

m = monthly()
mm = m[m.item.isin(["米", "パン"]) & (m.month <= 9)].groupby(["item", "year"]).value.sum().unstack("item")
ytd_ratio = (mm["パン"] / mm["米"]).loc[[2024, 2025, 2026]]
ytd_chg = (mm.loc[2026] / mm.loc[2025] - 1) * 100

D = detail()
avg = D[(D.kind == "age") & (D.group == "平均")]
Q = avg[avg.metric == "購入数量"].pivot_table(index="year", columns="item", values="value")[["米", "パン"]]
S = avg[avg.metric == "支出金額"].pivot_table(index="year", columns="item", values="value")[["米", "パン"]]
unit = pd.DataFrame({"米_kg": Q["米"], "米_円per_kg": S["米"] / Q["米"], "パン_kg": Q["パン"] / 1000, "パン_円per_kg": S["パン"] / Q["パン"] * 1000})

# 52市
city = D[(D.kind == "city") & (D.metric == "支出金額") & D.item.isin(["米", "パン"])]
CITIES = sorted(set(city[city.year == 2015].group))
cy = city[city.group.isin(CITIES)].pivot_table(index=["year", "group"], columns="item", values="value")
cy["ratio"] = cy["パン"] / cy["米"]
CY = sorted(set(cy.index.get_level_values(0)))
summary = pd.DataFrame({y: {"市の数": len(cy.loc[y]), "パンが米より多い市": int((cy.loc[y].ratio > 1).sum()),
                            "比の中央値": cy.loc[y].ratio.median(), "比の最小": cy.loc[y].ratio.min(), "比の最大": cy.loc[y].ratio.max()}
                        for y in CY}).T
# 2023年と2025年の両方で、市の比の順位はどれだけ保たれたか（順位相関）
r = cy.ratio.unstack(0)
rank_corr = {f"{a}-{b}": float(r[a].rank().corr(r[b].rank())) for a, b in [(2015, 2019), (2019, 2023), (2023, 2025), (2015, 2025)]}
# 米の量（市）：2023→2025年
cq = D[(D.kind == "city") & (D.metric == "購入数量") & (D.item == "米") & D.group.isin(CITIES)].pivot_table(index="group", columns="year", values="value")
rice_qty_city_chg = (cq[2025] / cq[2023] - 1) * 100
cyp = D[(D.kind == "city") & (D.metric == "平均価格") & (D.item == "米") & D.group.isin(CITIES)].pivot_table(index="group", columns="year", values="value")
rice_price_city_chg = (cyp[2025] / cyp[2023] - 1) * 100

# 年齢別
ag = D[(D.kind == "age") & (D.metric == "支出金額") & D.group.isin(AGES + ["平均"]) & D.item.isin(["米", "パン"])]
ar = ag.pivot_table(index=["year", "group"], columns="item", values="value")
ar["ratio"] = ar["パン"] / ar["米"]
age_ratio = ar.ratio.unstack(0).loc[AGES + ["平均"]]

# 保存
pd.concat([nat, ratio.rename("パン÷米")], axis=1).round(3).to_csv(RES / "national.csv")
unit.round(2).to_csv(RES / "unit_price_quantity.csv")
summary.round(3).to_csv(RES / "cities_summary.csv")
cy.round(3).to_csv(RES / "cities_bread_rice.csv")
age_ratio.round(3).to_csv(RES / "age_ratio.csv")
out = {
    "national_ratio": ratio.round(2).to_dict(),
    "rice_2015": float(nat.loc[2015, "米"]), "rice_2024": float(nat.loc[2024, "米"]), "rice_2025": float(nat.loc[2025, "米"]),
    "bread_2015": float(nat.loc[2015, "パン"]), "bread_2025": float(nat.loc[2025, "パン"]),
    "rice_2025_vs_2023_pct": round(float((nat.loc[2025, "米"] / nat.loc[2023, "米"] - 1) * 100), 1),
    "ytd_ratio": ytd_ratio.round(2).to_dict(), "ytd_2026_vs_2025_pct": ytd_chg.round(1).to_dict(),
    "unit": unit.round(1).to_dict(),
    "rice_kg_2025_vs_2023_pct": round(float((Q.loc[2025, "米"] / Q.loc[2023, "米"] - 1) * 100), 1),
    "rice_kg_2025_vs_2019_pct": round(float((Q.loc[2025, "米"] / Q.loc[2019, "米"] - 1) * 100), 1),
    "rice_price_2025_vs_2023_pct": round(float((unit.loc[2025, "米_円per_kg"] / unit.loc[2023, "米_円per_kg"] - 1) * 100), 1),
    "cpi_rice_2025_vs_2023_pct": round(float((C.loc[2025, "米類"] / C.loc[2023, "米類"] - 1) * 100), 1),
    "bread_kg_2025_vs_2019_pct": round(float((Q.loc[2025, "パン"] / Q.loc[2019, "パン"] - 1) * 100), 1),
    "cities": summary.round(2).to_dict(orient="index"),
    "rank_corr": {k: round(v, 2) for k, v in rank_corr.items()},
    "cities_rice_qty_2025_vs_2023_median_pct": round(float(rice_qty_city_chg.median()), 1),
    "cities_rice_qty_up_count": int((rice_qty_city_chg > 0).sum()),
    "cities_rice_price_2025_vs_2023_median_pct": round(float(rice_price_city_chg.median()), 1),
    "cities_bread_gt_rice_2025": sorted(cy.loc[2025][cy.loc[2025].ratio > 1].index.tolist()),
    "age_ratio": age_ratio.round(2).to_dict(),
}
json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

# 図1：全国の米とパン
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(YRS, nat["米"], marker="o", lw=2.4, color="#3a7d44", label="米")
ax.plot(YRS, nat["パン"], marker="s", lw=2.4, color="#c8833a", label="パン")
for y in (2015, 2023, 2025):
    ax.text(y - (0.5 if y == 2025 else 0), nat.loc[y, "米"] + (1200 if y != 2025 else -800), f"{nat.loc[y, '米']/1000:.1f}千", ha="center", fontsize=8, color="#3a7d44")
    ax.text(y, nat.loc[y, "パン"] + 1000, f"{nat.loc[y, 'パン']/1000:.1f}千", ha="center", fontsize=8, color="#c8833a")
ax.set_xticks(YRS)
ax.set_ylabel("1世帯当たり年間支出（円）")
ax.set_title("米とパンへの支出（全国、二人以上の世帯）")
ax.legend(frameon=False, loc="upper left")
ax.grid(axis="y", alpha=.3)
fig.text(0.01, 0.01, "出典：総務省統計局「家計調査」をもとに作成者が加工して作成。2025年は月の表の12か月の合計", fontsize=8, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a231_national.png", dpi=150)
plt.close(fig)

# 図2：米の量と値段（2019年＝100）
ui = unit / unit.loc[2019] * 100
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(ui.index, ui["米_円per_kg"], marker="^", lw=2.4, color="#c0392b", label="米 1kgあたりの値段")
ax.plot(ui.index, ui["米_kg"], marker="o", lw=2.4, color="#3a7d44", label="米 買った量（kg）")
ax.plot(ui.index, ui["パン_円per_kg"], marker="^", lw=1.6, color="#e0a96d", ls="--", label="パン 1kgあたりの値段")
ax.plot(ui.index, ui["パン_kg"], marker="s", lw=1.6, color="#c8833a", ls="--", label="パン 買った量（kg）")
for c, col in [("米_円per_kg", "#c0392b"), ("米_kg", "#3a7d44"), ("パン_円per_kg", "#b07a3a"), ("パン_kg", "#c8833a")]:
    ax.text(2025.1, ui.loc[2025, c], f"{ui.loc[2025, c]:.0f}", va="center", fontsize=8, color=col)
ax.axhline(100, color="gray", lw=.8)
ax.set_xticks(list(ui.index))
ax.set_xlim(2018.7, 2025.6)
ax.set_title("米とパン：買った量と1kgあたりの値段（2019年＝100）")
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.grid(axis="y", alpha=.3)
fig.text(0.01, 0.01, "出典：総務省統計局「家計調査」年報 第4-6表（平均）をもとに作成者が加工して作成", fontsize=8, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a231_qty_price.png", dpi=150)
plt.close(fig)

# 図3：52市のパン÷米の分布
fig, ax = plt.subplots(figsize=(8, 4.6))
rng = np.random.default_rng(0)
for i, y in enumerate(CY):
    v = cy.loc[y].ratio.values
    ax.scatter(np.full(len(v), i) + rng.uniform(-0.18, 0.18, len(v)), v, s=14, alpha=.7,
               color=np.where(v > 1, "#c8833a", "#3a7d44"))
    ax.text(i, max(v) + 0.08, f"パン＞米\n{int((v > 1).sum())}市", ha="center", fontsize=8)
ax.axhline(1, color="black", lw=1)
ax.text(-0.45, 1.02, "パン＝米", fontsize=8)
ax.set_xticks(range(len(CY)))
ax.set_xticklabels([str(y) for y in CY])
ax.set_ylabel("パンの支出 ÷ 米の支出")
ax.set_ylim(0.3, max(cy.ratio) + 0.35)
ax.set_title("52の市（都道府県庁所在市・政令指定都市）のパン÷米")
ax.grid(axis="y", alpha=.3)
fig.text(0.01, 0.01, "出典：総務省統計局「家計調査」年報 第4-1表をもとに作成者が加工して作成。1市あたりの集計世帯は約100で、1年分の値は振れが大きい", fontsize=7.5, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a231_cities.png", dpi=150)
plt.close(fig)
